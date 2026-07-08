# Delibra — Architectural Review

## 1. What problem does Delibra actually solve?

It solves a narrow, real problem: **making multi-role LLM deliberation reproducible and auditable**. Given a fixed protocol (roles + steps), fixed inputs, and fixed model outputs, the *sequence of artifacts produced* is deterministic and replayable — the non-determinism of the LLM is quarantined behind a `LLMClient` boundary, and everything downstream of it (id generation, trace events, status transitions, artifact linkage) is pure bookkeeping. That's genuinely useful and genuinely underserved: most agent frameworks conflate "what the model said" with "what happened," and lose the distinction between transient conversational state and durable derivation history.

It does **not** solve orchestration, control flow, or multi-agent coordination in any general sense. There is no branching, no loop, no gate, no retry-with-backoff, no human-in-the-loop step. This is a design choice they state explicitly, not a gap they've missed — but it means the actual solved problem is much smaller than "workflow for AI systems." It is closer to: *a schema and event log for staged, role-based LLM fan-in/fan-out with immutable provenance*.

## 2. Is "artifact-first" fundamental, or just a rebrand of dataflow?

It is dataflow programming with LLM steps as node functions, and the "artifact" is exactly what a build system calls an *output* or a functional pipeline calls a *value*. That's not an insult — dataflow is a legitimately fundamental abstraction, and it is a better fit for this problem than the graph-of-mutable-state model LangGraph/AutoGen use. But "artifact-first" is not a *new* abstraction; it's the correct application of an old one (SSA-style single-assignment values, Makefile-style output naming) to a domain (multi-agent deliberation) that has mostly been built on mutable shared state instead. The genuine insight isn't "artifacts exist," it's the RFC's explicit separation of `step.id` (operation identity) from `produces.output` (value identity) — that's a compiler-IR-grade distinction, and it's the single most technically serious idea in the codebase. Everything else about "artifact-first" is marketing for "we do SSA."

## 3. Concepts that are truly essential

- The `step.id` / `produces.output` split. This is what lets steps be renamed, retried, or re-derived without breaking downstream references — the one abstraction with real compiler-IR lineage.
- Artifact immutability + append-only trace. Necessary and sufficient for the audit/replay story; without it there's no product.
- The engine/durable-core split (`ExecutionContext` ephemeral vs. `Run`/`Trace`/`Artifact` durable). This is the correct boundary for a system that wants deterministic replay later.
- Opaque payload (core doesn't interpret artifact content). Correct — it's what keeps the core protocol-agnostic instead of becoming a taxonomy of domain schemas.

## 4. Concepts that feel accidental or unnecessary

- **`Role` as a separate entity from `StepDefinition.role`.** Right now a Role is just `{id, name, instruction}` — a named prompt fragment. It doesn't yet do anything a string field on the step couldn't. It's justified only by anticipated reuse across steps (`fanout` referencing multiple roles) — legitimate, but it's speculative generality dressed as a core entity today.
- **Four hardcoded `StepKind` values as an enum rather than a registered/extensible primitive set.** "No primitives beyond these four" is fine as a *v0.1 discipline*, but baking it into a closed enum (not a plugin point) means every future primitive is a breaking core change, not an extension — this is the single biggest tension with "artifact-first" being a durable foundation vs. a temporary scaffold.
- **`Message` as a defined type that explicitly must never touch durable core.** Fine in principle, but the fact that they had to write a *test* (`test_message_is_not_in_core_run_or_artifact_json`) to keep it out suggests the boundary is enforced by vigilance, not by the type system — i.e., it's a convention, not a structural guarantee.

## 5/6. What survives five years vs. collapses

**Survives:** the `step.id`/`produces.output` split, artifact immutability, trace-as-event-stream, opaque-payload core. These are load-bearing and cheap to keep no matter how large the primitive set grows — they're structural properties of the model, not features.

**Collapses or gets forced into major redesign:** the closed 4-primitive `StepKind` enum, the assumption that a `Run` is a *linear sequence* of steps (no evidence yet of DAG scheduling, and `ExecutionContext.output_index` is built by simple accumulation — nothing in the current data model handles two steps racing to write the same output, or steps that are genuinely concurrent rather than "fanout, sequentially executed"), and the assumption baked into validation that inputs can only reference *prior* `produces.output` (no forward refs) — this rules out cyclic protocols, but it also implicitly rules out speculative execution, incremental recomputation, and anything build-system-like (Make/Bazel-style) where a DAG, not a list, is the real shape of the problem. If Delibra grows toward "hundreds of protocols," someone will want a step whose inputs are dynamically discovered at runtime — and that will force a core change, not a preset.

## 7. Is the runtime boundary intellectually clean?

Yes, more than most projects at this stage — because there's so little runtime yet. The `LLMClient` structural protocol is clean. `ExecutionContext.from_run` requiring `RUNNING` status is a real invariant, not decoration. But the cleanliness is currently *cheap* — it's clean because the surface is tiny (2 of 4 primitives implemented, 1 provider, no persistence, no concurrency). The real test of "clean boundary" is what happens when Lot 9 (fanout/criticize execution), Lot 14 (real providers), and Lot 15 (hardening) land — those are exactly the phases where boundary discipline usually erodes. Nothing in the current code proves the boundary survives contact with those problems; the invariants doc is aspirational there, not yet tested.

## 8. Core / Runtime / Engine / LLM Interface / Provider — inevitable or convenient?

Convenient, not inevitable — and importantly, **two of the five don't exist as real things yet.** There is no `Provider` type or class anywhere in the codebase; it is pure documentation vocabulary for a not-yet-built Lot 14. There is no `Engine` class either — it's a function (`execute_prompt_synthesize_protocol`) that only handles 2 of 4 primitives. So the five-layer separation described is currently a **roadmap**, not an implemented architecture. The Core/Runtime split (durable vs. ephemeral) is real and is the one boundary that's actually been pressure-tested by code and tests.

## 9. Can it support multiple providers, non-LLM producers, deterministic replay, persistence, distributed execution — without redesigning core?

- **Multiple providers:** plausible, since `LLMClient` is already a structural protocol with one swappable implementation. Low risk.
- **Non-LLM producers:** *not really* — `StepDefinition.kind` is closed to `prompt/fanout/criticize/synthesize`, all of which assume "a role instructs a model." A deterministic non-LLM producer has no natural home in the current primitive set — you'd either abuse `prompt` semantics or add a primitive, which the philosophy explicitly gatekeeps.
- **Deterministic replay:** structurally set up for it (fixed ids, fixed clock, immutable artifacts) but explicitly deferred, and nothing today captures the actual LLM request/response pair as a durable, replayable artifact — `Message` is deliberately excluded from core, which means "replay" currently means "replay the bookkeeping," not "replay the conversation."
- **Persistence:** explicitly deferred; JSON-serializable dataclasses make it feasible, but no evidence persistence won't need artifact versioning/migration concepts absent today.
- **Distributed execution:** the biggest question mark. `IdSequence`/`FixedClock` are deliberately single-process deterministic generators. Real parallel fanout execution is explicitly deferred and flagged as architecturally risky. Nothing addresses partial-ordering of trace events from concurrent producers, idempotent artifact creation under retries, or distributed id generation. Likely requires rethinking `TraceEvent` ordering semantics.

3 of 5 are plausible without redesign, 2 (non-LLM producers, distributed execution) probably require touching the core primitive set or the trace ordering model.

## 10. What would I challenge first, seeing this cold?

The closed `StepKind` enum. Everything else in this project is deliberately, defensibly minimal — but locking the primitive set into a 4-value enum, in a system whose own philosophy says "the core grows only when multiple protocols demand it," creates a contradiction: the mechanism for *proving* that demand (writing new protocols that need a 5th primitive) is exactly the mechanism the enum forecloses without a core code change. A discipline of "resist adding primitives" doesn't require a *closed type* — it could be a *convention* enforced by review, leaving room for the inevitable extension without every extension being a breaking core change. As written, "small core" and "closed core" have been conflated, and that conflation is what will hurt most in year 2–3.

---

## Comparison — architectural ideas, not features

- **vs. LangGraph:** LangGraph's core idea is a mutable-state graph with edges as control flow; Delibra's is immutable values with no control flow at all in v0.1. Delibra is more honest about where non-determinism lives, but LangGraph's graph model can express loops/cycles that Delibra's model structurally cannot yet, and may never without abandoning "no workflow features in core."
- **vs. DSPy:** DSPy treats prompts as compiled/optimized programs; Delibra treats the model call as an opaque black box and optimizes the bookkeeping around it. Near-orthogonal concerns that could in principle compose.
- **vs. CrewAI / AutoGen:** both are agent-conversation-centric — the message thread *is* the state. Delibra's "Message is not durable core" is a direct rejection of that model, and it's the most defensible design decision in the project.
- **vs. Semantic Kernel:** SK is plugin/skill-composition-centric, closer to a scripting runtime. Delibra's protocol/artifact model is more static and declarative.
- **vs. compiler IRs / build systems (Make, Bazel):** the closest real analogy, underexploited. Bazel/Make already solved typed outputs named by output identity, DAG dependency resolution, immutable artifacts, determinism. Delibra hasn't yet borrowed content-addressed artifacts, a real DAG scheduler, or incremental re-derivation — risking reinventing a worse version of that wheel.
- **vs. dataflow / functional pipelines:** this is what Delibra actually *is*. Single-assignment dataflow applied to role-based LLM deliberation with durability/audit as first-class requirements — a fine, real niche, not a new abstraction.

---

## Thought Experiment — Delibra in 5 years, hundreds of protocols

**Unchanged:** artifact immutability, append-only trace, opaque payload, and the `step.id`/`produces.output` distinction. Cheap invariants that don't fight scale.

**Almost certainly redesigned:** the `StepKind` enum, the implicit linear/sequential execution model (hundreds of protocols will want real DAG scheduling, partial reruns, incremental recomputation), and the total absence of a `Provider` abstraction will have had to become real — provider-specific concerns (rate limits, retries, streaming, cost) always try to leak upward into orchestration logic.

---

## Red Team — why Delibra fails (architecture only)

**Most likely architectural failure mode:** the closed primitive set becomes a wall the project can't climb over gracefully, and the "prove it can't remain a preset" discipline — a *process* commitment, not a *type-system* commitment — erodes under real usage pressure. The first time a genuinely important protocol needs conditional branching or a loop ("criticize until converged," "retry synthesis if confidence is low"), the team faces a binary choice: violate the philosophy (add `if`/`loop` to core) or contort the primitive set into unnatural shapes. Either choice damages the thing that made the project distinctive. Compounding this: the test suite currently encodes "fanout unsupported" as a passing assertion, meaning correctness is partly defined by current incompleteness, not a stable target shape.

A secondary risk: `ExecutionContext`'s single-process, sequential, in-memory model has no story yet for concurrency or distribution, and retrofitting that onto a trace model whose ordering semantics are "whatever order things got appended" tends to force a rewrite of the durable core rather than an additive extension.

## Green Team — why Delibra succeeds

If it survives, it's because the team holds the line: new primitives added rarely and only after real cross-protocol pressure, non-LLM producers modeled as a `kind` extension rather than a `StepKind` extension, concurrency solved by making `Trace` ordering explicit rather than positional. The property that would make it fundamentally different from LangGraph/CrewAI/AutoGen: **a Delibra run is a value, not a conversation** — you can diff two runs, cache a run, replay a run, and reason about a run without a model in the loop, because the durable state is a typed, immutable derivation graph rather than a chat transcript. If that property survives contact with real workflows (branching, retries, human input) without being diluted, Delibra becomes genuinely useful as an audit/compliance layer for AI deliberation — a niche none of the comparison projects targets.

---

## Strengths

- The `step.id` vs `produces.output` distinction is a real, transferable insight, not decoration.
- Durable/ephemeral separation (Artifact/Run/Trace vs. ExecutionContext/Message) is enforced by both types and tests, not just documentation.
- The development discipline (RFC → concept validation → compliance review) is unusually rigorous for a project this size, and it shows in the low defect surface.
- Explicit, written-down non-goals list (§12 of the RFC) — most projects don't have the discipline to say "we are not doing X" this specifically this early.
- Failure semantics ("preserve partial artifacts, no synthetic failure artifact") is a mature, tested design decision, not an afterthought.

## Weaknesses

- "Artifact-first" is dataflow/SSA applied to LLM steps, not a new abstraction — the marketing claim exceeds the technical claim.
- The primitive set is closed by an enum, in direct tension with the stated philosophy that the core should grow only under cross-protocol pressure.
- Two of the five architectural layers named in the brief (`Engine`, `Provider`) don't exist as real code yet — evaluating their boundary cleanliness is currently evaluating a roadmap.
- No model yet for non-LLM producers, concurrency, or distributed execution, and the current sequential/single-process assumptions will likely require real core surgery to fix.
- `Role` as a first-class entity is speculative generality — it does nothing today that a string field wouldn't.

## Biggest Architectural Risk

The closed, enum-based primitive set combined with an explicit philosophical refusal to add control-flow concepts. The project has pre-committed to a position (no branching, no loops, no gates) that real deliberation protocols will eventually need, and has structurally (not just culturally) foreclosed the cheap way of extending toward that need. When the pressure arrives, the team will either compromise the philosophy or contort the model, and either path erodes exactly the thing that makes Delibra worth building instead of just using LangGraph.

## Most Valuable Insight

The separation of *operation identity* (`step.id`) from *value identity* (`produces.output`), combined with treating a deliberation run as an immutable derivation *value* rather than a conversation *transcript*. That's the one idea here with genuine staying power — it's what would let Delibra diff, cache, and audit runs the way a build system diffs, caches, and audits builds, which no comparable agent framework does today.

## Recommendation

**Continue with architectural corrections.**

The core insight is sound and worth building on, but two corrections are needed before Lot 9+ compounds the debt: (1) replace the closed `StepKind` enum with an extensible-but-disciplined primitive registry, so "resist adding primitives" remains a process norm rather than a type-system wall that forces philosophy-violating workarounds; and (2) make `Trace` ordering and artifact production explicit about causality (not just append-order) before any concurrent/distributed execution work begins, since retrofitting that later is exactly the kind of change that breaks "the core stays boring." Do this before, not after, real providers and real fanout land — those are the two events most likely to expose whichever of these gaps was left unaddressed.
