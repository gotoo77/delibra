# Local Runtime Experience Design Review

## Status

This document is a design review, not an accepted architecture decision.

It records the current target direction, known constraints, hypotheses, and open
questions for Delibra's Local Runtime Experience.

Normative decisions must be accepted separately through ADRs or existing
architecture documentation. This review is structured, non-normative, and
expected to evolve after real experiments with local runtimes, advisors, setup
flows, and Delibra smoke runs.

## Purpose

The problem is not "support Ollama".

The problem is:

> A user wants to run a Delibra protocol locally, but may not know what a local
> LLM runtime is, whether their machine can run one, which model to use, how to
> install or start the runtime, or how to recover when something fails.

The Local Runtime Experience is the product and application layer that bridges
that gap.

It should help users move from local uncertainty to a verified Delibra run while
preserving the separation between durable derivation state and volatile
execution infrastructure.

## Evidence So Far

Established observations:

- Delibra has a minimal Ollama provider behind the runtime `LLMClient` boundary.
- Delibra has passive local diagnostics for Ollama and OpenAI-compatible local
  endpoints.
- Delibra has an explicit opt-in minimal Ollama inference check.
- A machine without the `ollama` command and without an Ollama server was tested.
- On that machine, `delibra doctor local` reported unreachable local endpoints
  cleanly and did not install, download, or write files.
- On that machine, `delibra doctor local --check-inference` skipped inference
  when the Ollama server was unreachable and stated that no inference was
  attempted.
- The automated test suite passed after the local inference diagnostics tranche.

Not yet established:

- A real installed local model has not yet been validated through this flow.
- A real Delibra protocol has not yet been executed with a local model as part
  of this local runtime validation ladder.
- Delibra does not yet guide a user from a fresh machine to installed runtime,
  installed model, minimal inference, and first local Delibra run.
- No advisor such as `llmfit` has been evaluated or integrated.

## User Problem

A non-expert user should be able to answer:

- Can this machine run a local LLM workflow?
- Is a supported local runtime installed?
- Is it running?
- Are any models available?
- Which model should I try?
- Can the selected model produce a minimal response?
- Can it complete a real Delibra protocol?
- Were artifacts produced?
- Can I inspect and analyze the run?
- If something failed, what should I do next?

The user should not need to understand ports, environment variables,
quantization, GPU memory, PATH, Docker, Python packaging, or provider-specific
APIs unless they deliberately enter an advanced path.

## Scope

Local Runtime Experience covers:

- local runtime discovery;
- diagnostics;
- guided setup;
- model selection support;
- explicit consent for installation or download actions;
- minimal inference validation;
- Delibra smoke validation;
- local benchmark protocols;
- protocol-specific qualification;
- user-facing recovery guidance;
- durable capture of lessons learned when appropriate.

It does not change the durable Delibra domain model.

## Decisions Already Established

These constraints are already established by the current architecture or recent
implementation:

- Providers are runtime or application infrastructure, not durable domain
  objects.
- Provider and model details must not enter durable protocol, run, trace, or
  artifact records.
- Presets remain provider-independent recipes.
- `doctor local` is passive by default.
- Minimal local inference is explicit opt-in.
- Delibra does not install runtimes, download models, or write setup files in
  the current local diagnostics flow.
- Model selection for the current inference check is explicit via `--model` or
  fallback via `OLLAMA_MODEL`; there is no durable preference.

## Recommended Direction

The Local Runtime Experience should become a set of application-layer services
and CLI or product workflows above the provider boundary.

Recommended direction:

- keep providers small and provider-specific;
- keep diagnostics observational and safe by default;
- make validation progressive and explicit;
- treat recommendations as reversible advice, not automatic decisions;
- introduce setup assistance only with explicit consent;
- evaluate model advisors behind a Delibra-owned abstraction;
- defer general capability frameworks until multiple local runtimes create real
  pressure.

## Responsibilities

### Delibra

Delibra is responsible for:

- explaining local execution state in user terms;
- separating observation from recommendation;
- requiring consent before system-changing actions;
- validating progressively from runtime detection to real Delibra artifacts;
- keeping provider and model details out of durable artifacts;
- making failures actionable;
- preserving reproducibility around Delibra runs;
- keeping local setup state outside `Run`, `Trace`, `Artifact`, and `Protocol`.

Delibra may guide, recommend, and validate.

Delibra must not silently install, download, select models, change providers, or
mutate user configuration.

### Local Runtime

A local runtime is external infrastructure capable of serving model inference
locally.

Examples may include:

- Ollama;
- LM Studio;
- llama.cpp server;
- vLLM;
- MLX-based runtimes;
- Docker Model Runner;
- OpenAI-compatible local gateways.

A runtime is responsible for:

- installing and running its own server or process;
- storing and serving local models;
- exposing runtime-specific APIs;
- reporting model availability;
- executing inference requests;
- returning runtime-specific errors.

Delibra should treat local runtimes as infrastructure dependencies, not as
domain concepts.

### Provider

A provider is the adapter boundary between Delibra and an inference API.

A provider is responsible for:

- translating Delibra runtime requests into provider API calls;
- normalizing model output into Delibra's `LLMResponse`;
- surfacing provider-specific errors cleanly;
- avoiding durable contamination from provider metadata.

A provider should stay small.

It should not:

- own onboarding;
- recommend models;
- install runtimes;
- download models;
- benchmark hardware;
- qualify models for protocols;
- make product decisions;
- write provider details into durable objects.

### Advisor

An advisor recommends possible local model choices or setup paths.

An advisor is responsible for:

- interpreting machine, runtime, model, and possibly protocol constraints;
- producing explained options;
- exposing uncertainty;
- allowing rejection or manual override;
- staying replaceable.

An advisor may use external tools such as `llmfit`, but Delibra must depend on
an internal advisor contract, not directly on a specific tool.

Advisor output is recommendation, not decision.

Recommended categories may include:

- lightweight;
- balanced;
- higher quality;
- manual selection.

A recommendation is valid only when the user can inspect, accept, reject, or
change it.

### Diagnostic

A diagnostic observes local state.

Diagnostics answer questions such as:

- Is a runtime endpoint reachable?
- Does it expose the expected API?
- Which models are visible?
- Is the requested model visible?
- Did an inference attempt run?
- What error was observed?

Diagnostics must distinguish observed facts from interpretations.

Examples:

- Observed: connection refused.
- Interpretation: server may not be running.
- Suggested action: start the runtime or verify the configured base URL.

Diagnostics should be safe by default:

- no installation;
- no download;
- no writes;
- short timeouts unless explicitly overridden;
- no hidden privileged actions.

### Validation

Validation establishes increasing levels of proof.

A useful validation ladder is:

1. Runtime candidate known.
2. Runtime endpoint reachable.
3. Model list available.
4. Explicit model selected.
5. Minimal inference succeeds.
6. Delibra protocol executes.
7. Artifacts are produced.
8. Run can be inspected.
9. Run can be analyzed.
10. User understands next action.

Only the later levels validate Delibra integration. A successful provider
response alone is not sufficient.

Validation should remain explicit, observable, and repeatable.

### Benchmark

A benchmark measures local behavior under controlled conditions.

Benchmarks may measure:

- time to first response;
- full response latency;
- protocol completion time;
- timeout frequency;
- approximate throughput;
- failure modes under context pressure.

Benchmarks must not be confused with diagnostics, validation, or qualification.

A benchmark answers "how well did this configuration perform under this
protocol?", not merely "does it work?"

Benchmarks should be opt-in, reproducible, and clearly scoped.

### Qualification

Qualification evaluates whether a runtime and model are suitable for a specific
Delibra use case.

It is distinct from diagnostics, validation, and benchmark:

- A diagnostic says whether something is observable.
- A validation says whether it works at a defined level.
- A benchmark measures how it performs.
- A qualification asks whether it is good enough for a protocol, preset, or
  user goal.

Examples:

- A small model may pass minimal inference but fail to produce useful critique
  artifacts.
- A local runtime may complete a smoke protocol but be unsuitable for long
  design reviews.
- A model may be fast enough but not reliable enough for decision review.
- A high-quality model may be useful but too slow for interactive workflows.

Qualification should be evidence-based.

It may use:

- repeated protocol runs;
- explicit rubrics;
- human review;
- artifact comparisons;
- failure-rate observations;
- protocol-specific constraints.

Qualification must not be confused with semantic truth. Delibra can help
structure qualification evidence, but it does not know universal model quality
or truth unless an explicit product layer or review process defines the
criterion.

### Knowledge Vault

Knowledge Vault is for durable learning, not logs.

It may capture:

- repeated setup frictions;
- validated or invalidated hypotheses;
- platform-specific limitations;
- advisory model limitations;
- architecture decisions needing review;
- reusable diagnostic methods;
- benchmark findings;
- qualification findings;
- open questions.

Captures should remain draft, review-required, and provenance-backed.

Knowledge Vault must not become an automatic telemetry sink or raw session
journal.

## Durable Domain Boundary

The following must not enter durable domain objects such as `Protocol`, `Run`,
`Trace`, `Artifact`, `StepDefinition`, or `Produces`:

- provider names;
- model names;
- local runtime names;
- ports;
- base URLs;
- API keys;
- environment variable names;
- installation paths;
- hardware details;
- token usage;
- cost;
- raw provider responses;
- benchmark timings;
- qualification results;
- advisory recommendations;
- setup state;
- user consent records.

These details may exist in application-layer reports, diagnostics, logs, or
user-facing output, but not as durable derivation facts.

A Delibra artifact records what was derived, not which volatile infrastructure
produced a model response.

## Candidate Principles

These are candidate principles for future review. They are not yet additions to
`docs/architecture-principles.md`.

- Diagnostics observe before they recommend.
- Validation progresses by levels of proof.
- Qualification is protocol-specific and evidence-based.
- Recommendations never become automatic decisions.
- Providers are adapters, not onboarding orchestrators.
- A successful provider response is not proof of Delibra integration.
- Local runtime support must not become Ollama-specific architecture.

## CLI Shape

The current CLI exposes local diagnostics through `delibra doctor local`.

A future full local runtime command family may justify a `delibra local ...`
namespace:

- `delibra local doctor`
- `delibra local setup`
- `delibra local models`
- `delibra local benchmark`
- `delibra local test`

This should be decided before adding setup, model management, benchmark, or
smoke-test commands.

The decision should consider:

- backwards compatibility;
- aliases or deprecation path;
- consistency with existing commands;
- whether `local` is a product surface or only a doctor subdomain;
- whether local runtime workflows will become large enough to merit a
  namespace.

## Consent Model

Delibra may display commands or installation options.

Delibra must not execute system-changing actions unless the user explicitly
consents.

Actions requiring consent include:

- installing a runtime;
- launching an installer;
- downloading a model;
- changing persistent configuration;
- starting background services;
- writing setup files;
- modifying shell profiles;
- changing PATH;
- using privileged commands.

Delibra should prefer official installation methods and explain what will
happen before any action.

## ADR Candidates

These are candidate decisions. No ADR is created by this document.

### CLI Namespace

Question: Should the future local command family use `delibra doctor local`,
`delibra local doctor`, both, or a migration path?

Why it is structural: setup, models, benchmark, test, and doctor commands may
form a product surface larger than ordinary diagnostics.

ADR trigger: before adding `setup`, `models`, `benchmark`, or `test` commands
under either namespace.

### Consent Model

Question: What actions may Delibra suggest, prepare, or execute, and what form
of consent is required?

Why it is structural: local setup can involve installers, downloads, services,
PATH changes, shell configuration, and privileged commands.

ADR trigger: before Delibra executes any system-changing local setup action.

### LocalModelAdvisor Contract

Question: What internal advisor interface should Delibra depend on, and should
tools such as `llmfit` be wrapped, adopted, or rejected?

Why it is structural: model advice depends on hardware, runtime, model catalog,
protocol expectations, and user tradeoffs.

ADR trigger: before adding automatic or semi-automatic local model
recommendations.

### ExecutionPolicy Routes Semantics

Question: Are `ExecutionPolicy.routes` only neutral policy annotations, or can
they become explicit runtime/provider/model selection inputs?

Why it is structural: routing could affect execution while still needing to
keep provider details out of durable domain objects.

ADR trigger: before using policy routes to select providers or models.

### Durable Boundary For Diagnostics, Benchmarks, And Qualification

Question: Where should diagnostic, benchmark, advisor, and qualification data
live, and what is forbidden from durable Delibra records?

Why it is structural: these data are useful but volatile. If persisted in the
wrong layer, they can contaminate the artifact-first model.

ADR trigger: before persisting local runtime reports, benchmark results, or
qualification outcomes beyond transient CLI output.

## Knowledge Vault And Field Note Candidates

This document does not create Knowledge Vault captures or field notes.

Candidate durable observations:

- a machine without Ollama was diagnosed cleanly and non-destructively;
- a fresh machine is not yet accompanied through the path to first local
  Delibra run;
- future CLI tension exists between `delibra doctor local` and
  `delibra local ...`;
- the `Skipped / Reason / No inference was attempted` rendering improved the
  clarity of non-attempted inference checks.

Avoid duplicates with existing frictions, especially F005 and F006 in
`docs/field-notes/FRICTIONS.md`. New captures should be created only when they
add distinct durable knowledge, evidence, or a provisional decision needing
human review.

## Open Questions

- Should the primary future CLI be `delibra doctor local` or
  `delibra local doctor`?
- Should `delibra doctor local` become an alias if `delibra local doctor` is
  introduced?
- What is the minimal advisor contract?
- Should `llmfit` be integrated, wrapped, or rejected?
- What machine facts may be inspected safely without surprising users?
- Where should consent records live, if anywhere?
- Should local runtime setup produce temporary reports, persistent config, or
  both?
- What is the first canonical Delibra smoke protocol for local validation?
- How should benchmark results be represented without contaminating durable
  runs?
- How should qualification evidence be represented without pretending Delibra
  can judge universal model quality?
- How should OpenAI-compatible local endpoints be represented without
  collapsing all local runtimes into one provider model?
- Should model recommendations be per-provider, per-machine, per-protocol, or
  all three?
- What evidence is sufficient before adding a new local runtime integration?

## Non-Goals

This design review does not require:

- automatic runtime installation;
- automatic model download;
- automatic model selection;
- persistent user preferences;
- durable provider metadata;
- a general capability framework before multiple runtimes demand it;
- a full onboarding state machine before simpler workflows prove insufficient.

## Proposed Next Experiment

The next concrete experiment should not start with broad onboarding.

Recommended next experiment:

1. Use a machine with Ollama already installed, or install it manually outside
   Delibra with explicit human action.
2. Pull a small model manually.
3. Run `delibra doctor local`.
4. Run `delibra doctor local --check-inference --model <model>`.
5. Execute a minimal real Delibra protocol with the local model.
6. Inspect the produced artifacts.
7. Analyze the run.
8. Record which validation level failed or succeeded.

This would test the validation ladder from local provider readiness to real
Delibra artifact proof without yet introducing setup automation or model
advice.
