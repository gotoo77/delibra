# Experimental Qualification Field Note

## Experiment identity

| Field | Value |
|---|---|
| Run date | 2026-07-16, from `local_first.run.json` (`started_at`: `2026-07-16T10:47:49.737347Z`) |
| Preset | `decision_review@0.1.0`, from persisted run metadata |
| Provider | `ollama`, from captured CLI invocation |
| Model | `qwen3:4b`, from captured CLI invocation |
| Input | `Should Delibra support local LLMs by default?`, from captured CLI invocation and persisted run input |
| Run file | `local_first.run.json`, persisted run data |
| Trace file | `local_first.trace.json`, persisted trace data |
| Artifacts | 7, from persisted run data |
| Observed duration | 237.14 seconds, from captured CLI progress output |

Qualification objective:

> Evaluate whether `decision_review@0.1.0`, executed with `qwen3:4b` on a
> short and underspecified question, produces a sufficiently grounded decision
> analysis and preserves the epistemic status of information correctly.

This field note preserves an experimental observation. It does not modify the
preset, prompts, roles, runtime model, provider integration, or artifact format.

## Qualification scope

This verdict applies only to:

`decision_review@0.1.0 + qwen3:4b + this input`

It does not establish that:

- `qwen3:4b` is generally unsuitable;
- `decision_review@0.1.0` is generally unsuitable;
- the same behavior will reproduce across models, inputs, temperatures, or
  protocol variants.

The run is a single qualification sample, not a benchmark and not a general law
about multi-role protocols.

## Execution result

| Dimension | Result | Evidence |
|---|---|---|
| Runtime execution | pass | `local_first.run.json` records status `completed` and 7 artifacts. |
| Ollama provider integration | pass | The run completed with `provider=ollama` and `model=qwen3:4b`. |
| CLI progress behavior in this run | pass | The captured CLI output reported elapsed stage durations; the files preserve standard run/trace artifacts. |
| Grounding for this configuration | fail | Later artifacts contain dates, reports, percentages, approvals, and guarantees not provided by the input or external evidence. |
| Cross-artifact epistemic-status preservation | fail, with nuance | Some initial scenario labels remain visible, but later stages repeatedly promote scenarios and unsupported claims into evidence, approvals, or final decision authority. |
| General qualification of model or preset | indeterminate | More runs and comparisons are needed. |

## Observed facts

The following facts are directly visible in the persisted run and trace,
inspected artifact contents, or captured CLI execution context. Each statement
identifies the relevant source.

- `artifact_0001`, produced by `frame` / `framer`, introduced GDPR/CCPA as a
  compliance example: "Must satisfy data privacy regulations (e.g., GDPR,
  CCPA)".
- `artifact_0001`, produced by `frame` / `framer`, introduced healthcare and
  enterprise as example stakes or assumptions: "healthcare, finance" and
  "enterprise, education, or privacy-conscious individuals".
- `artifact_0002`, produced by `role_reviews` / `strategist`, introduced
  unsupported numeric market and compliance claims, including "40% of
  Delibra's target clients" and "$2M+ compliance fines/year".
- `artifact_0003`, produced by `role_reviews` / `risk_reviewer`, introduced an
  approval-like footer: "Approved by: Risk Reviewer" and "Date: October 26,
  2023".
- `artifact_0004`, produced by `role_reviews` / `operator`, introduced an
  operator signature: "Alex Chen", "Date: 2023-10-15", and "Confidence: 92%".
- `artifact_0004`, produced by `role_reviews` / `operator`, introduced the
  first exact "40% attrition in low-end markets" formulation.
- `artifact_0005`, produced by `critique_reviews` / `critic`, named the
  operator artifact an "Operator Report" and treated it as "the most recent and
  comprehensive review".
- `artifact_0006`, produced by `critique_reviews` / `risk_reviewer`, treated a
  prior generated artifact as an "approved decision" and added 2-week and
  4-week deadlines.
- `artifact_0007`, produced by `final` / `synthesizer`, presented a "final
  approved decision" and introduced or hardened several claims, including
  "90%+ of compliance risks", "95%+ retention", and "No trade-offs".

## Interpretations

- The run technically succeeded, but technical success did not imply semantic
  qualification.
- The framer created plausible scenario dimensions. Later roles frequently
  converted those dimensions into facts, metrics, deadlines, or authority
  signals.
- The critique stage did not consistently challenge unsupported claims. In this
  run, it often performed synthesis and authority assignment.
- The final synthesis privileged recent and detailed artifacts as if recency and
  detail were evidence quality signals.
- The word `default` changed meaning across artifacts: no configuration for all
  users, targeted default for privacy-sensitive segments, no default activation,
  and enterprise toggle all appear as variants.
- Some contradictions were not preserved. `artifact_0005` preferred targeted
  default support, while `artifact_0006` preferred no default support with an
  enterprise toggle. `artifact_0007` resolved this as a final approved decision
  rather than preserving the conflict.

## Provisional hypotheses

These mechanisms are possible explanations for this run. They are not presented
as general rules.

- Short, underspecified input may leave too much room for role artifacts to
  invent operational context.
- Role labels such as `Risk Reviewer` and `Operator` may encourage the model to
  produce report-like metadata, signatures, approval dates, and confidence
  scores.
- Later protocol stages may over-trust earlier generated artifacts because they
  are structured, recent, and role-specific.
- The synthesizer may optimize for a complete executive decision, even when the
  evidence base is incomplete or contradictory.
- The critic roles may need stronger instruction to preserve uncertainty rather
  than resolve it.

## Artifact-by-artifact observations

### `artifact_0001` -- framer

Expected role: frame the decision, options, constraints, assumptions, and
stakes.

Observed behavior:

- Produced a structured JSON-like frame.
- Reduced the option space to two options: support local LLMs by default, or do
  not support them by default and require cloud models exclusively.
- Introduced assumptions and scenario examples not present in the input.

New information introduced:

- GDPR/CCPA as compliance examples.
- Healthcare, finance, enterprise, education, and low-connectivity regions as
  relevant segments.
- A definition of "by default" as "immediate functionality without user
  configuration steps".

Inherited and transformed information:

- The user input only asked whether Delibra should support local LLMs by
  default. The frame transformed this into a two-option decision and added
  compliance, infrastructure, and UX constraints.

Epistemic status:

- Mostly scenario and hypothesis. The artifact labels some items as
  "assumptions", but later artifacts do not preserve that status reliably.

Drifts or contradictions:

- The second option is narrower than the original question because it equates
  not supporting local LLMs by default with requiring cloud models exclusively.

### `artifact_0002` -- strategist

Expected role: evaluate strategic fit, reversibility, opportunity cost, and
timing.

Observed behavior:

- Selects "Support local LLMs by default" as the option under review.
- Introduces numerous unsupported market, regulatory, timing, and competitive
  claims.

New information introduced:

- "68% of healthcare organizations require on-device AI".
- "40% of Delibra's target clients" require offline processing.
- "12-18 months" of development.
- "22% increase in enterprise contracts".
- "$2M+ compliance fines/year".
- "By Q4 2026" as a future default date.

Inherited and transformed information:

- GDPR/CCPA and enterprise adoption from the frame are transformed into hard
  strategic urgency and market-risk estimates.

Epistemic status:

- Unsupported claims. The role presents estimates as if they were market data
  or strategic facts, but no source exists in the input or artifacts.

Drifts or contradictions:

- The role recommends supporting local LLMs by default while also saying the
  initial launch should be a user-configurable option, not a hard default.

### `artifact_0003` -- risk reviewer

Expected role: identify downside risks, unknowns, mitigations, and failure
modes.

Observed behavior:

- Challenges the framing more than the strategist did.
- Introduces a competing recommendation: do not support local LLMs by default,
  but add a mandatory offline toggle for enterprise users.
- Adds authority-like metadata at the end.

New information introduced:

- "50% of users have <4GB RAM".
- "60% of users in rural areas prioritize offline access over privacy".
- "20% lower accuracy on edge devices".
- "2023 Global Connectivity Report".
- "Approved by: Risk Reviewer" and "Date: October 26, 2023".

Inherited and transformed information:

- The frame's privacy and compliance assumptions are challenged, but they are
  replaced by other unsupported statistics.

Epistemic status:

- Mixed: some items are legitimate risk hypotheses, but many percentages,
  citations, and approval metadata are unsupported claims.

Drifts or contradictions:

- The artifact is valuable as risk pressure, but it also fabricates evidence and
  self-approval.
- It turns a role review into something that looks like a signed decision
  report.

### `artifact_0004` -- operator

Expected role: evaluate implementation practicality, sequencing, ownership,
cost, and validation.

Observed behavior:

- Produces an operational implementation report.
- Recommends support for privacy-sensitive segments rather than all users.
- Adds named signature, date, and confidence metadata.

New information introduced:

- "Alex Chen" as Product Operations Lead.
- `2023-10-15` as date.
- "Confidence: 92%".
- "$24k-$39k" year-one cost.
- "40% attrition in low-end markets (per real-world tests)".
- "2.1x faster" adoption.

Inherited and transformed information:

- Healthcare and enterprise scenarios become target segments.
- Compliance constraints become operational requirements and ownership rows.

Epistemic status:

- Operational recommendations mixed with unsupported claims. The signature,
  date, confidence score, and real-world-test reference are unsupported.

Drifts or contradictions:

- The artifact narrows "default" into "targeted segments and fallback".
- It gives report-like authority to generated content.

### `artifact_0005` -- critic

Expected role: critique previous artifacts and expose weaknesses.

Observed behavior:

- Produces a concise decision summary rather than a critique.
- Treats `artifact_0004` as an "Operator Report".
- Claims that the Operator Report "proves" the Risk Reviewer's recommendation
  is over-engineered.

New information introduced:

- "0 compliance failures".
- "92% retention in target segments".
- "Pilot with 1 healthcare enterprise client (within 2 weeks)".
- "No trade-offs".

Inherited and transformed information:

- `artifact_0004`'s operator review becomes a named authoritative report.
- The 40% attrition claim is preserved and used as proof for a targeted rollout.
- The 92% confidence value reappears near retention language, creating a risk
  of metric confusion.

Epistemic status:

- Mostly unsupported claims and recommendations. The artifact uses generated
  evidence as if it were validated evidence.

Drifts or contradictions:

- The critic role does not preserve the disagreement between risk reviewer and
  operator; it declares the operator view superior.

### `artifact_0006` -- risk reviewer in critique step

Expected role: critique prior outputs from a risk perspective.

Observed behavior:

- Produces another decision summary.
- Reverses the prior critic's direction by returning to "do not support local
  LLMs by default" plus enterprise toggle.
- Treats the Risk Reviewer decision and Operator Report as validated inputs.

New information introduced:

- Survey deadline: 2 weeks.
- Pilot deadline: 4 weeks.
- "95%+ of users" seamless cloud fallback.
- "Approved by Risk Reviewer | October 26, 2023".
- "Validated by Operator Report (92% confidence)".

Inherited and transformed information:

- The Risk Reviewer's self-approval becomes an approved decision.
- The operator review becomes an Operator Report.
- The 92% confidence score becomes validation metadata for the report.

Epistemic status:

- Recommendations and unsupported claims. The deadlines are recommended next
  steps; the approval and validation statements are unsupported.

Drifts or contradictions:

- The artifact treats generated artifacts as authoritative while still being
  part of the critique stage.

### `artifact_0007` -- synthesizer

Expected role: synthesize final output from prior artifacts.

Observed behavior:

- Produces a final approved decision.
- Resolves disagreement in favor of no default support for all users plus
  mandatory enterprise toggle.
- Adds or hardens several claims.

New information introduced:

- "90%+ of compliance risks".
- "Operator Report (Oct 15)" as a cited basis for the pilot.
- "Risk Reviewer confirmed this is the fastest path to ROI".
- "No trade-offs" and "eliminates" default-activation risk.
- "2-week survey is non-negotiable".

Inherited and transformed information:

- `artifact_0006`'s "95%+ of users" becomes "95%+ retention".
- The operator date `2023-10-15` becomes "Operator Report (Oct 15)".
- The Risk Reviewer's self-approval becomes final approval authority.

Epistemic status:

- Final decision plus unsupported claims. The artifact presents certainty and
  authority that the provenance does not justify.

Drifts or contradictions:

- Contradictions among the role reviews are closed rather than surfaced.
- Mitigations become guarantees: explicit toggle implies "0 compliance
  failures"; pilot implies "90%+ compliance risk prevention".

## Claim provenance table

| Claim | First appearance | Producer | Initial formulation | Initial status | Later transformations | Final status in `artifact_0007` | Transformation type |
|---|---|---|---|---|---|---|---|
| GDPR/CCPA | `artifact_0001` | `frame` / `framer` | "Compliance requirements: Must satisfy data privacy regulations (e.g., GDPR, CCPA)" | scenario / requirement hypothesis | Becomes compliance penalties, breaches, audit requirements, and then violations avoided by a toggle. | "GDPR/CCPA violations" solved with "0 compliance failures". | reformulation, amplification, mitigation-to-guarantee |
| healthcare/enterprise | `artifact_0001` | `frame` / `framer` | "enterprise, education..." and "healthcare, finance" | scenario | Narrowed into target segments, then mandatory enterprise-only toggle with healthcare as example. | Enterprise users, e.g. healthcare providers, are the only mandatory offline-toggle group. | narrowing, reformulation |
| `40% attrition` | `artifact_0004` for exact attrition claim | `role_reviews` / `operator` | "A default for all users would cause 40% attrition in low-end markets (per real-world tests)." | unsupported claim | Used by critic as proof for targeted rollout; preserved by final synthesis as risk solved by cloud fallback. | "40% attrition in low-end markets" appears as a concrete risk. | copy, amplification |
| `95%+ retention` | `artifact_0007` for retention metric | `final` / `synthesizer` | "95%+ retention (no config needed)" | unsupported claim | Nearest prior source is `artifact_0006`: "95%+ of users", not retention. | Presented as impact of cloud fallback. | migration of value, change of metric |
| `90%+ compliance risk prevention` | `artifact_0007` | `final` / `synthesizer` | "this pilot will prevent 90%+ of compliance risks" | unsupported claim | No earlier artifact contains this risk-prevention percentage. | Presented as evidence from Operator Report. | new invention |
| `92% confidence` | `artifact_0004` | `role_reviews` / `operator` | "Confidence: 92% (based on 12 real-world use cases, industry benchmarks, and compliance frameworks)" | unsupported claim | Repeated by critic; becomes "Validated by Operator Report (92% confidence)" in `artifact_0006`; final attributes it to real-world use cases and risk modeling. | Final confidence metadata. | copy, amplification |
| `Operator Report` | `artifact_0005` | `critique_reviews` / `critic` | "most recent and comprehensive review (Operator Report)" | unsupported claim | `artifact_0006` treats it as detailed analysis; final treats it as validated evidence. | Source authority for confidence and pilot justification. | artifact-to-authority transformation |
| `October 15, 2023` | `artifact_0004` | `role_reviews` / `operator` | "Date: 2023-10-15" | unsupported report metadata | Critic repeats approval by Alex Chen on October 15; final changes it into "Operator Report (Oct 15)". | Citation-like date for the Operator Report. | signature-to-source fusion |
| `October 26, 2023` | `artifact_0003` | `role_reviews` / `risk_reviewer` | "Date: October 26, 2023" | unsupported report metadata | `artifact_0006` treats it as approved decision date; final treats it as Risk Reviewer's approval. | Final approval date. | amplification |
| `Alex Chen` | `artifact_0004` | `role_reviews` / `operator` | "Operator Signature: Alex Chen | Product Operations Lead" | unsupported identity claim | `artifact_0005` repeats approval by Product Operations Lead Alex Chen; later artifacts drop the name but retain Operator Report authority. | Not present by name in final artifact. | dropped name, retained authority |
| `Approved by Risk Reviewer` | `artifact_0003` | `role_reviews` / `risk_reviewer` | "Approved by: Risk Reviewer" | unsupported self-approval claim | `artifact_0006` repeats it; final says the decision is based on Risk Reviewer's approval. | Final approval authority. | epistemic promotion |
| Survey deadline of 2 weeks | `artifact_0006` | `critique_reviews` / `risk_reviewer` | "Run targeted user surveys... Deadline: 2 weeks" | recommendation | Final preserves deadline and adds "fastest path to ROI" and "non-negotiable". | Critical next step and non-negotiable survey. | recommendation-to-imperative amplification |
| Pilot deadline of 4 weeks | `artifact_0006` | `critique_reviews` / `risk_reviewer` | "Pilot with one enterprise client... Deadline: 4 weeks" | recommendation | Final preserves deadline and adds Operator Report / 90% risk-prevention justification. | Critical next step backed by invented quantified prevention. | recommendation amplification, synthetic justification |

Note: `artifact_0002` contains "40% of Delibra's target clients", but the exact
`40% attrition` claim appears first in `artifact_0004`.

## Observed transformations

- Abusive reduction of the option space: the framer reduces the input to a
  binary choice, and later artifacts further narrow it to enterprise toggle vs
  targeted default.
- Transformation of hypotheses into facts: GDPR/CCPA and healthcare/enterprise
  begin as scenario examples, then become concrete violation and market
  requirements.
- Fabrication of statistics serving as proof: 40%, 68%, 70%, 92%, 95%, and 90%
  values are introduced without evidence and later reused as decision support.
- Correction of one unsupported claim by another: the risk reviewer challenges
  "all users prioritize privacy" using unsupported connectivity and behavior
  statistics.
- Numeric migration: `95%+ of users` becomes `95%+ retention`; `92% confidence`
  sits close to `92% retention` in `artifact_0005`, increasing metric ambiguity.
- Signature-to-approval transformation: report metadata such as "Approved by:
  Risk Reviewer" becomes final decision authority.
- Internal artifact-to-authority transformation: the operator review becomes an
  "Operator Report" and then a validated source.
- Mitigation-to-guarantee transformation: toggles and pilots become "0
  compliance failures" and "90%+ compliance risks" prevented.
- Recency/detail as implicit authority: `artifact_0005` calls the operator
  output the "most recent and comprehensive review"; later artifacts treat that
  as a reason to rely on it.
- Silent redefinition of `default`: all-user zero-config default, optional
  toggle, targeted segment default, and no default activation are used without a
  stable distinction.
- Premature closure: contradictory role recommendations are converted into a
  final approved decision rather than preserved as unresolved tension.
- Critique-as-synthesis: critique artifacts produce final-decision summaries
  instead of primarily weakening claims and preserving uncertainty.

## Provisional concepts

These are provisional vocabulary candidates from one experiment only. The
labels below are working terms for recurring patterns that may later be renamed,
merged, or rejected.

- `epistemic drift`: a claim's certainty changes as it moves across artifacts.
  Example: GDPR/CCPA begins as a compliance example and ends as violations
  prevented with 0 failures. Needs confirmation on other runs.
- `epistemic promotion`: a claim is upgraded from hypothesis, scenario, or
  generated text into decision evidence. Example: "Approved by: Risk Reviewer"
  becomes final approval authority. Needs confirmation on other runs.
- `documentary hallucination`: the model fabricates documentary scaffolding such
  as signatures, report names, dates, approvals, or confidence metadata.
  Example: "Alex Chen", "Operator Report", and dates. Needs confirmation on
  other runs.
- `synthetic justification`: later artifacts use generated prior claims to
  justify stronger conclusions. Example: the final artifact says the Operator
  Report shows the pilot will prevent 90%+ of compliance risks. Needs
  confirmation on other runs.
- `authority fabrication`: generated role metadata becomes an external-looking
  authority. Example: Risk Reviewer self-approval becomes final approval.
  Needs confirmation on other runs.
- `numeric migration`: a numeric value moves from one metric to another.
  Example: "95%+ of users" becomes "95%+ retention". Needs confirmation on
  other runs.

## Stage diagnosis

### Framing

The first unsupported expansions appear in the framing stage. They are not yet
the main failure: GDPR/CCPA, healthcare, enterprise, and low-connectivity
regions are plausible scenario axes. The risk is that the frame reduces the
option space too early and creates scenario slots that later roles fill with
unsupported specificity.

### Strategic review

The strategic review is where unsupported market facts and quantified
opportunity-cost claims first become prominent. It strengthens the
support-by-default side and introduces large claims without citations.

### Risk review

The risk review usefully challenges the strategist's direction, but it also
introduces its own unsupported statistics, a fabricated source label, and
approval metadata. This is where authority fabrication first becomes visible.

### Operator review

The operator review adds practical structure, but also a named signature, date,
confidence score, cost estimates, and "real-world tests". This is where an
internal role artifact most strongly takes the shape of an external report.

### Critique

The critique stage is the main laundering point in this run. It does not merely
criticize; it turns prior generated content into reports, proof, approvals, and
decision summaries. Contradictions between targeted default and no default
support are not preserved rigorously.

### Final synthesis

The final synthesis declares a final approved decision, closes the remaining
option space, and adds new unsupported certainty. It copies, transforms, and
amplifies prior claims while inventing at least one major quantified
justification: 90%+ compliance risk prevention.

## Provisional conclusion

In this precise configuration, `decision_review@0.1.0` executed with `qwen3:4b`
on a short and underspecified input did not produce a sufficiently grounded
decision analysis. The artifacts show progressive accumulation of unsupported
claims, promotion of those claims toward more certain statuses, and later use
of generated internal artifacts as sources of authority.

The technical runtime path passed. The semantic qualification for trustworthy
decision support failed for this run.

## Next experiments

These are experimental candidates, not an approved roadmap.

1. Run the same preset and same input with another local model.
2. Run the same preset and model with an input that provides explicit factual
   context, constraints, and known unknowns.
3. Repeat the same run to observe whether unsupported authority and numeric
   claims are stable.
4. Compare with a variant that explicitly requires unknowns to remain unknown.
5. Compare artifacts role by role to identify where each type of drift begins.
6. Test the framer and synthesizer separately.
7. Verify whether the roles produce genuinely differentiated cognition or
   mainly stylistic report variants.

## Relationship to other knowledge artifacts

This field note keeps contextual experimental evidence inside the existing
field-note structure. It is not a Knowledge Vault capture and not consolidated
method knowledge.

Several convergent field notes could later justify promotion into the Knowledge
Vault, for example as a durable principle about evidence preservation in
multi-step LLM workflows. That promotion would require independent experiments,
not just this run.

The possible need for a future Observatory-like capability is an architectural
signal, not a decision taken here. This note deliberately remains a documentary
artifact compatible with the current field-note convention.

Related local documentation:

- [Field Notes Index](INDEX.md)
- [Observed Frictions](FRICTIONS.md)
- [Local Runtime Experience Design Review](../design-reviews/local-runtime-experience.md)
