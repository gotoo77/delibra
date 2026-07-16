# Comparative Qualification Field Note

## Experiment identity

This note compares two completed experimental runs of the same protocol and the
same user input.

| Field | Configuration A | Configuration B |
|---|---|---|
| Protocol | `decision_review@0.1.0` | `decision_review@0.1.0` |
| Provider | `ollama`, from captured execution context | `openai`, from captured execution context |
| Model | `qwen3:4b`, from captured execution context | `gpt-5.5`, from captured execution context |
| Input | `Should Delibra support local LLMs by default?` | `Should Delibra support local LLMs by default?` |
| Run file | `local_first.run.json` | `gpt55_decision.run.json` |
| Trace file | `local_first.trace.json` | `gpt55_decision.trace.json` |
| Run date | 2026-07-16T10:47:49Z | 2026-07-16T11:34:01Z |
| Artifacts | 7 | 7 |
| Trace events | 38 | 38 |
| Run status | `completed` | `completed` |

The protocol and input were intentionally identical. The provider and model
differed. This note compares observed behavior only; it does not rank models,
claim causality, or generalize beyond these two runs.

## Qualification scope

This is a comparative qualification note about:

`decision_review@0.1.0 + fixed input + two provider/model configurations`

It does not establish that:

- either model is globally better or worse;
- either provider is globally better or worse;
- the observed differences are caused only by the model;
- the same differences will reproduce with other prompts, seeds, model
  versions, provider settings, or protocol variants.

## Recommendation on artifact type

This should be documented as a Comparative Qualification Field Note, not as a
second independent Experimental Qualification Field Note.

Reasons:

- The second run used the same protocol and same input as the first run.
- The new knowledge is primarily relational: which behaviors changed when the
  provider/model configuration changed.
- The existing field-note convention tracks observed patterns across notes. A
  comparative note preserves the pairwise evidence without duplicating the full
  single-run provenance already captured in `0006`.
- The comparison is still field evidence, not a consolidated Knowledge Vault
  claim and not an architecture decision.

## Observations

### Common execution facts

- Both runs completed.
- Both produced 7 artifacts.
- Both produced 38 trace events.
- Both used `decision_review@0.1.0`.
- Both used the exact same input text.
- Both produced a final recommendation rather than refusing to decide.

### Configuration A observed behavior

Configuration A is documented in detail in
[0006-local-ollama-decision-review-qualification.md](0006-local-ollama-decision-review-qualification.md).

Observed behaviors in Configuration A included:

- unsupported numbers introduced across role reviews;
- report-like metadata such as named signatures, dates, confidence values, and
  approvals;
- transformation of an operator role artifact into an "Operator Report";
- promotion of self-approval text into decision authority;
- migration from `95%+ of users` to `95%+ retention`;
- invention of `90%+ compliance risk prevention` in the final synthesis;
- critique artifacts behaving partly as decision summaries.

### Configuration B observed behavior

Configuration B produced a more explicitly option-preserving analysis in the
inspected artifacts:

- `artifact_0001` framed three options: local by default, local but not by
  default, and no local support for now.
- `artifact_0002` recommended Option B, while describing it as provisional:
  "at least for now" and "until local-model quality, setup complexity, and user
  demand are better validated."
- `artifact_0003` framed local-by-default as high risk "unless Delibra's
  product is explicitly designed around heterogeneous model quality, degraded
  capability modes, and heavy configuration variability."
- `artifact_0004` recommended defaulting to reliable cloud providers while
  designing a local/self-hosted integration path.
- `artifact_0005` criticized premature convergence on Option B and introduced
  missing options such as hybrid default, segment-specific defaults,
  OpenAI-compatible endpoints only, and certified local model profiles.
- `artifact_0006` split the ambiguous question into three decisions:
  architecture, product default, and commercial/support commitment.
- `artifact_0007` preserved that split in the final recommendation.

Configuration B still added information not present in the user input, including
lists of possible runtimes, markets, risks, and product options. In the observed
artifacts, those additions were generally framed as considerations, risks,
options, or assumptions rather than dated facts, external reports, approvals, or
validated statistics.

## Phenomena Comparison

| Phenomenon from Configuration A | Configuration B observation | Comparative status |
|---|---|---|
| Unsupported precise percentages become decision evidence. | No comparable invented percentages were observed in B's final synthesis. | disappeared in this pair |
| Named signatures and fabricated identities. | No named person comparable to `Alex Chen` was observed. | disappeared in this pair |
| Approval metadata becomes authority. | No "Approved by" decision authority was observed. | disappeared in this pair |
| Internal artifact becomes authoritative report. | No "Operator Report" equivalent was observed. | disappeared in this pair |
| Numeric migration between metrics. | No equivalent migration such as users to retention was observed. | disappeared in this pair |
| Mitigations become guarantees. | B discusses risks and support boundaries; no `0 compliance failures` or `90%+ prevention` style guarantee was observed. | weakened or absent |
| Critique behaves as synthesis. | B's critique artifacts still summarize, but `artifact_0005` and `artifact_0006` also reopen options and challenge convergence. | weakened |
| The meaning of `default` shifts. | B explicitly splits default into product default, architecture, and support commitment. | remained as a topic, but clarified |
| Option space closes prematurely. | B's final still recommends Option B, but preserves sub-decisions and support boundaries. | weakened |
| Scenario dimensions become considerations. | B introduces privacy, enterprise, public sector, governance, runtime, and support considerations. | remained |
| Additional options appear during critique. | B adds hybrid, segment-specific, endpoint-only, and certified-profile options in critique. | newly appeared |
| Architecture/product/support split. | B explicitly separates architecture, product default, and commercial/support commitment. | newly appeared |

## Artifact-Level Comparison

### Framing

Configuration A reduced the decision to two options: support local LLMs by
default, or do not support them by default and require cloud models exclusively.

Configuration B framed three options and treated "support local LLMs, but not
by default" as distinct from both local-by-default and no local support.

Observation: in this pair, Configuration B preserved a wider initial option
space.

### Strategic review

Configuration A selected support-by-default for review and introduced precise
strategic claims such as market percentages, compliance fines, and timelines.

Configuration B recommended Option B, but used scoped language such as
"at least for now" and "until local-model quality, setup complexity, and user
demand are better validated."

Observation: in this pair, B's strategic review used fewer precise unsupported
claims and more validation-bound language.

### Risk review

Configuration A introduced risk pressure but also fabricated external-looking
statistics, a "2023 Global Connectivity Report", and approval metadata.

Configuration B identified risks around model quality, support burden, UX,
reliability, security, and product trust. It did not introduce comparable
approval metadata or dated authority in the inspected artifact.

Observation: risk framing remained in both runs, but documentary hallucination
was observed in A and not observed in B.

### Operator review

Configuration A produced operational structure but also added a named operator,
date, confidence score, costs, and "real-world tests".

Configuration B produced operational structure around support burden,
configuration scope, endpoint compatibility, documentation, QA, and support
commitments without a named signature or confidence score.

Observation: both runs used operational reasoning; A added report-like
authority metadata, while B did not in the inspected artifact.

### Critique

Configuration A's critique stage transformed prior generated content into
authority and decision proof. It named an "Operator Report" and treated prior
material as validated.

Configuration B's critique stage challenged premature convergence, identified
missing options, and split the decision into smaller decisions.

Observation: in this pair, the critique stage is the clearest behavioral
difference. A laundered generated claims; B reopened the decision frame.

### Final synthesis

Configuration A produced a final approved decision with unsupported quantified
claims, authority references, deadlines, and guarantees.

Configuration B produced a final recommendation for cloud default plus
local/self-hosted advanced support. It preserved the architecture/product
default/commercial-support split.

Observation: both final artifacts decide. A's final artifact amplified
unsupported authority and numbers; B's final artifact retained more of the
uncertainty and boundary-setting introduced by critique.

## Observations vs Hypotheses

### Observations

- The same protocol and input produced different artifact behavior across the
  two provider/model configurations.
- Configuration A showed unsupported authority, dates, percentages, and report
  labels propagating into the final synthesis.
- Configuration B did not show the same authority/date/percentage propagation
  pattern in the inspected artifacts.
- Configuration B introduced and preserved a decomposition of the decision into
  architecture, product default, and commercial/support commitment.
- Both configurations added content beyond the user input.
- Both configurations reached a recommendation.

### Provisional hypotheses

These hypotheses require more runs before they can be trusted.

- Some model/provider configurations may preserve uncertainty better than
  others for this protocol.
- The same protocol may be sensitive to model behavior around role metadata,
  report formatting, and executive-synthesis style.
- Short and underspecified inputs may expose differences in how models fill
  missing context.
- Critique-stage behavior may be a useful qualification target for multi-role
  protocols.

None of these hypotheses should be treated as causal conclusions from this
two-run comparison.

## Relationship to Field Note 0006

Field Note 0006 remains the detailed single-run provenance record for
Configuration A.

This note adds a comparative layer:

- which phenomena from 0006 disappeared in Configuration B;
- which weakened;
- which remained;
- which newly appeared.

It does not replace 0006 and does not revise its claims.

## Qualification Verdict

For this pair of runs, a comparative note is the most appropriate artifact.

The comparison suggests that the failure mode observed in Configuration A is
not an unavoidable consequence of the `decision_review@0.1.0` protocol alone,
because the same protocol and input produced different behavior in
Configuration B.

That statement is intentionally limited. It does not identify the cause of the
difference. The provider, model, provider settings, runtime behavior, and other
uncontrolled factors differ between the two configurations.

## Next Experiments

These are candidates, not an approved roadmap.

1. Repeat Configuration A to test stability of authority and numeric drift.
2. Repeat Configuration B to test stability of uncertainty preservation.
3. Run the same protocol/input with a third model.
4. Run both configurations with richer factual input to see whether unsupported
   elaboration weakens.
5. Compare only the critique stage across configurations.
6. Compare final synthesis behavior when prior artifacts contain explicit
   unknowns and evidence labels.

## Relationship to Other Knowledge Artifacts

This note remains a Field Note. It is not a Knowledge Vault capture, ADR,
architecture decision, or Observatory subsystem.

If multiple comparative notes converge, the repeated pattern could later justify
a more durable Knowledge Vault capture about evidence preservation in multi-step
LLM protocols. That threshold has not been met by this pair alone.
