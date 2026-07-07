# Delibra Implementation Backlog v0.1

This backlog prepares an implementation faithful to [Delibra Core Model v0.1](../core-model-v0.1.md).

The core RFC is considered frozen. Implementation work must not introduce core entities, primitives, or durable concepts absent from the RFC.

## Ground Rules

- Each lot must produce executable software.
- Each lot must be testable.
- Each lot should fit in roughly half a day to two days.
- Each lot should minimize architectural risk.
- Do not introduce `Claim`, `Evidence`, `Critique`, or `Decision` as core entities.
- Do not make `Message` part of the durable core.
- Do not add primitives beyond `prompt`, `fanout`, `criticize`, and `synthesize`.
- Do not add workflow-engine features such as branching, loops, gates, votes, tools, shell, MCP, or memory.

## Spike 0: In-Memory Artifact Derivation Prototype

### Goal

Prove in 1-2 hours that the artifact-first model is pleasant to implement.

This spike should validate the shape of:

- an in-memory protocol;
- a minimal `ExecutionContext`;
- derived artifacts;
- a minimal trace.

### Constraints

- No CLI.
- No YAML.
- No provider.
- No full serialization.
- No rendering.
- No heavy tests.
- Only an in-memory protocol, minimal `ExecutionContext`, derived artifacts, and minimal trace.

### Expected Output

- A disposable prototype.
- A short note saying whether the model holds.
- A list of frictions found.

### Acceptance Criteria

- The prototype demonstrates `Artifact -> StepDefinition -> Artifact` derivation in memory.
- Inputs resolve through `produces.output`, not `step.id`.
- Artifacts are created, not mutated.
- Trace is represented as an event stream.
- The result is explicitly treated as disposable.

### Tests To Write

- None required beyond a tiny executable smoke path.

### Dependencies

- Core model RFC.

### Risks

- Accidentally turning the spike into production code.
- Spending more than two hours polishing infrastructure.
- Drawing conclusions from a prototype that ignores the core invariants.

## Lot 1: Project Skeleton And CLI Stub

### Objective

Create the minimal executable project with a CLI entrypoint and no real Delibra behavior yet.

The executable should start, print help, and expose placeholder commands that fail with clear "not implemented" messages.

### Files Concerned

- Project manifest and lockfile for the chosen language.
- CLI entrypoint.
- Minimal test configuration.
- `README.md` if needed for local run instructions.

### Acceptance Criteria

- `delibra --help` runs successfully.
- `delibra validate --help` runs successfully.
- `delibra run --help` runs successfully.
- Commands that are not implemented fail cleanly without stack traces.
- No core model behavior is implemented yet.

### Tests To Write

- CLI smoke test for `--help`.
- CLI smoke test for `validate --help`.
- CLI smoke test for `run --help`.
- Test that unimplemented commands return a non-zero status with a readable error.

### Dependencies

- Language and CLI framework selected.

### Risks

- Choosing a CLI framework that makes tests or later structured errors awkward.
- Starting to implement runtime behavior before the project skeleton is stable.

## Lot 2.1: Durable Execution Model

### Objective

Implement the durable execution data structures from the RFC without protocol parsing or execution logic.

This lot should model:

- `Run`
- `Artifact`
- `Trace`
- `TraceEvent`
- enums for run status and trace event type

### Files Concerned

- Durable execution model module.
- Serialization module if separated.
- Unit tests for execution model serialization.

### Acceptance Criteria

- `Run`, `Artifact`, `Trace`, and `TraceEvent` serialize to the canonical JSON shapes from the RFC.
- `Run`, `Artifact`, `Trace`, and `TraceEvent` deserialize from canonical JSON where appropriate.
- `Message` is not included in durable core types.
- No provider, engine, or CLI business logic is mixed into core types.
- `Artifact.payload` is represented as opaque JSON.
- `Artifact.kind` is not interpreted as a domain-specific type.

### Tests To Write

- Serialization snapshot for `Run`.
- Serialization snapshot for `Artifact`.
- Serialization snapshot for `Trace`.
- Serialization snapshot for `TraceEvent`.
- Enum parsing tests for valid and invalid run statuses.
- Enum parsing tests for valid and invalid trace event types.

### Dependencies

- Lot 1.

### Risks

- Adding convenience fields not present in the RFC.
- Encoding provider-specific details into `Artifact.metadata`.
- Letting the core model become aware of execution mechanics too early.
- Adding `Message` as a durable core type.

## Lot 2.2: Static Protocol Model

### Objective

Implement the static protocol data structures from the RFC without YAML parsing or execution logic.

This lot should model:

- `Protocol`
- `Role`
- `StepDefinition`
- `Produces`
- enum for step kind

### Files Concerned

- Static protocol model module.
- Serialization module if separated.
- Unit tests for protocol model serialization.

### Acceptance Criteria

- `Protocol`, `Role`, `StepDefinition`, and `Produces` serialize to the canonical JSON shapes from the RFC.
- `Protocol`, `Role`, `StepDefinition`, and `Produces` deserialize from canonical JSON where appropriate.
- `StepDefinition.id` identifies the operation.
- `Produces.output` identifies the logical value produced.
- `StepDefinition.inputs` are modeled as references to `user_input` or prior `produces.output` values.
- No provider, engine, CLI, or runtime behavior is mixed into static protocol types.

### Tests To Write

- Serialization snapshot for `Protocol`.
- Serialization snapshot for `Role`.
- Serialization snapshot for `StepDefinition`.
- Serialization snapshot for `Produces`.
- Enum parsing tests for valid and invalid step kinds.

### Dependencies

- Lot 1.

### Risks

- Resolving inputs by `step.id` instead of `produces.output`.
- Treating artifact `kind` as a domain-specific taxonomy.
- Adding future workflow concepts to the static model.

## Lot 3: Protocol YAML Parsing And Canonical JSON

### Objective

Load a protocol YAML file and normalize it into the canonical internal `Protocol` model.

This lot only parses and serializes. It does not validate all semantic rules yet.

### Files Concerned

- Protocol loader.
- YAML parsing module.
- CLI `validate` command wired to parsing only.
- Test fixtures under test data.

### Acceptance Criteria

- A valid protocol YAML file can be loaded.
- The loaded protocol can be emitted as canonical JSON.
- YAML role map entries are normalized to roles with explicit `id`.
- Unknown top-level parse failures produce readable errors.
- `delibra validate --protocol path/to/protocol.yaml` runs and reports parse success.

### Tests To Write

- Parse the RFC example protocol YAML.
- Assert normalized role ids.
- Assert canonical JSON output shape.
- Invalid YAML returns a structured parse error.
- Missing file returns a readable CLI error.

### Dependencies

- Lot 2.2.

### Risks

- Conflating YAML input shape with canonical JSON too tightly.
- Silently accepting malformed YAML.
- Making validation rules implicit in parser behavior rather than explicit in the validator.

## Lot 4: Protocol Validation

### Objective

Implement strict RFC validation for `Protocol`.

Validation must reject unsupported fields or behavior instead of guessing intent.

### Files Concerned

- Protocol validator.
- Validation error types.
- CLI `validate` command.
- Validation test fixtures.

### Acceptance Criteria

- Valid protocol YAML passes validation.
- `produces.output` is required and unique.
- `inputs` may reference only `user_input` or previous `produces.output` values.
- Future output references are rejected.
- Missing roles are rejected.
- Primitive-specific `role` and `roles` rules are enforced.
- Unsupported step kinds are rejected.
- Unknown fields are rejected if the chosen parser supports strict mode.
- `synthesize` must be the final step for v0.1.

### Tests To Write

- Valid code-review-style protocol passes.
- Duplicate step ids fail.
- Duplicate `produces.output` values fail.
- Unknown input output fails.
- Future input output fails.
- `prompt` with `roles` fails.
- `fanout` without `roles` fails.
- `criticize` with `role` fails.
- `synthesize` not last fails.
- Unknown primitive fails.

### Dependencies

- Lot 3.

### Risks

- Over-validating artifact `kind` values as domain semantics.
- Under-validating references and allowing runtime failures that should be compile-time protocol errors.
- Accidentally adding workflow concepts to solve validation edge cases.

## Lot 5: Run, Trace, And Artifact Builders

### Objective

Create deterministic builders for `Run`, `Artifact`, `Trace`, and `TraceEvent`.

This lot produces executable behavior through tests and a small internal smoke path, but still does not call an LLM.

### Files Concerned

- Run creation module.
- Artifact creation module.
- Trace event append module.
- Id generation abstraction.
- Clock abstraction.
- Unit tests.

### Acceptance Criteria

- A new run can be created for a validated protocol and input reference.
- Run lifecycle transitions are enforced.
- Trace events are append-only.
- Artifact creation records `kind`, `output`, `producer_step_id`, and `producer_role_id`.
- Deterministic ids and timestamps are possible in tests.
- Failed runs can retain partial artifacts.

### Tests To Write

- Create run in `created` status.
- Transition `created -> validated -> running -> completed`.
- Reject transition from terminal status back to `running`.
- Create artifact matching producer step `produces`.
- Reject artifact with wrong `kind` or `output`.
- Append trace events in order.
- Failed run retains existing artifacts.

### Dependencies

- Lot 2.1.
- Lot 4.

### Risks

- Letting `Run` become a mutable execution context.
- Making trace a free-form log instead of typed events.
- Generating non-deterministic ids in tests.

## Lot 6: ExecutionContext And Input Resolution

### Objective

Implement the engine's ephemeral `ExecutionContext`.

It should resolve step `inputs` into artifact ids using an output index.

### Files Concerned

- Engine context module.
- Input resolution module.
- Unit tests.

### Acceptance Criteria

- `ExecutionContext` can be created from a running `Run`.
- `user_input` resolves to the original run input reference.
- Produced artifacts are indexed by `Artifact.output`.
- Inputs such as `framing` or `reviews` resolve to artifact ids.
- Missing outputs produce structured engine errors.
- `ExecutionContext` is not serialized as durable core output.

### Tests To Write

- Empty context resolves `user_input`.
- Index one artifact under `framing`.
- Resolve multiple artifacts under `reviews`.
- Missing output fails.
- Context can be rebuilt from a run's artifacts.

### Dependencies

- Lot 5.

### Risks

- Duplicating durable state between `Run` and `ExecutionContext`.
- Making `ExecutionContext` part of canonical output.
- Resolving inputs by `step.id` instead of `produces.output`.

## Lot 7: Mock LLM Interface And Engine Message Boundary

### Objective

Introduce the model-agnostic LLM interface and mock implementation.

`Message` remains engine-only and is not added to durable core.

### Files Concerned

- LLM request/response interface.
- Engine-only message model.
- Mock LLM client.
- Tests for deterministic mock behavior.

### Acceptance Criteria

- Engine can request generated content through an abstract LLM interface.
- Mock client returns deterministic content based on step and role.
- Trace events may reference `message_id`.
- Durable `Run` and `Artifact` do not embed engine `Message`.
- No real provider is introduced.

### Tests To Write

- Mock returns deterministic response for a step/role.
- Engine records `MessageSent` and `MessageReceived` trace events with message ids.
- Message content is not present in core `Run` JSON.
- Provider errors from mock can be simulated.

### Dependencies

- Lot 6.

### Risks

- Leaking provider-specific request shapes into core.
- Treating LLM messages as durable deliberation outputs.
- Adding real provider complexity too early.

## Lot 8: Sequential Engine For `prompt` And `synthesize`

### Objective

Implement sequential execution for single-role primitives:

- `prompt`
- `synthesize`

Both create exactly one artifact.

### Files Concerned

- Engine executor.
- Primitive handlers for `prompt` and `synthesize`.
- Trace integration.
- CLI `run` command wired to mock provider for these primitives.

### Acceptance Criteria

- A protocol containing `prompt` then `synthesize` executes with the mock provider.
- Each step emits `StepStarted`, message events, `ArtifactCreated`, and `StepCompleted`.
- Produced artifacts use the declared `produces.output` and `produces.kind`.
- Final run status is `completed`.
- CLI can run the sample protocol with mock provider and write run JSON and trace JSON.

### Tests To Write

- Execute a two-step protocol with mock provider.
- Assert artifact count and fields.
- Assert trace event order.
- Assert final run status.
- Assert CLI output files are created.

### Dependencies

- Lot 7.

### Risks

- Baking prompt-construction policy into the core model.
- Creating artifacts from raw provider data without enforcing core artifact shape.
- Making CLI own execution logic.

## Lot 9: Sequential Engine For `fanout` And `criticize`

### Objective

Implement multi-role primitives:

- `fanout`
- `criticize`

Both execute sequentially in v0.1 and produce one artifact per role.

### Files Concerned

- Primitive handlers for `fanout` and `criticize`.
- Engine executor updates.
- Tests with the full code-review protocol shape.

### Acceptance Criteria

- `fanout` produces one artifact per role under one output.
- `criticize` produces one artifact per role under one output.
- Execution is sequential even though the semantic operation is fanout-like.
- If one role fails, the run fails and retains prior artifacts.
- Trace records partial artifacts and failure events.

### Tests To Write

- Execute full four-step protocol with mock provider.
- Assert `reviews` output has three artifacts.
- Assert `critiques` output has three artifacts.
- Simulate failure on second fanout role and assert partial run.
- Assert no synthetic failure artifact is created.

### Dependencies

- Lot 8.

### Risks

- Accidentally introducing real parallelism before deterministic behavior is stable.
- Treating `criticize` as a debate or workflow rather than a multi-role artifact derivation.
- Losing partial artifacts on failure.

## Lot 10: Canonical Run And Trace File Output

### Objective

Stabilize CLI output for run JSON and trace JSON.

This lot makes the executable useful for local inspection with the mock provider.

### Files Concerned

- CLI `run` output handling.
- JSON writer.
- Filesystem output validation.
- Integration tests.

### Acceptance Criteria

- `delibra run --protocol protocol.yaml --input input.txt --provider mock --run-out run.json --trace-out trace.json` works.
- `run.json` contains canonical `Run`.
- `trace.json` contains canonical `Trace`.
- Existing output file behavior is explicit and tested.
- Write failures produce readable errors.
- No repository files are modified except explicit output paths.

### Tests To Write

- Run command writes both output files.
- Output JSON parses back into core models.
- Missing input file fails.
- Non-writable output path fails.
- Existing output path behavior matches documented CLI behavior.

### Dependencies

- Lot 9.

### Risks

- Writing implicit files without user request.
- Mixing trace into run JSON.
- Adding rendering behavior before canonical JSON is stable.

## Lot 11: Markdown Rendering From Run JSON

### Objective

Add a simple Markdown renderer derived from canonical run artifacts.

The renderer must not introduce new semantic entities or interpret artifact payloads deeply.

### Files Concerned

- Markdown renderer.
- CLI output option for Markdown.
- Renderer tests.

### Acceptance Criteria

- Markdown output lists artifacts grouped by output and kind.
- Markdown includes protocol id/version, run id, status, and timestamps.
- Markdown renders `payload.content` when present.
- Markdown does not require specialized `Claim`, `Evidence`, `Critique`, or `Decision` structures.
- Markdown is derived from `Run`, not from provider messages.

### Tests To Write

- Render successful run to Markdown.
- Render failed run with partial artifacts.
- Render artifact without `payload.content` gracefully.
- Snapshot test for stable Markdown output.

### Dependencies

- Lot 10.

### Risks

- Making Markdown renderer smarter than the core model.
- Introducing domain-specific rendering rules too early.
- Treating final synthesis as a special `Decision` entity.

## Lot 12: Official v0.1 Presets And Fixtures

### Objective

Add official MVP protocol fixtures aligned with the RFC.

At minimum:

- `code_review`
- `design_review`

These are presets as data, not core behavior.

### Files Concerned

- Preset YAML files.
- Example input files.
- Preset validation tests.
- Documentation references.

### Acceptance Criteria

- Both preset YAML files validate.
- Both presets execute successfully with mock provider.
- Presets use only structural artifact kinds.
- Presets do not add unsupported primitives or fields.
- Presets are discoverable by CLI if preset discovery is in scope for this lot; otherwise they are runnable by path.

### Tests To Write

- Validate `code_review` preset.
- Validate `design_review` preset.
- Execute both with mock provider.
- Snapshot run JSON for both presets.
- Snapshot Markdown for both presets if Lot 11 is complete.

### Dependencies

- Lot 10 for JSON-only presets.
- Lot 11 if Markdown snapshots are included.

### Risks

- Letting presets smuggle domain concepts into core.
- Making preset discovery too complex.
- Overfitting the engine to the official presets.

## Lot 13: Documentation And Local Developer Workflow

### Objective

Document how to validate and run protocols locally with the mock provider.

This lot should make the current executable understandable without adding behavior.

### Files Concerned

- `README.md`
- `docs/README.md`
- CLI usage documentation.
- Example command snippets.

### Acceptance Criteria

- Documentation explains core model reference.
- Documentation shows `validate` usage.
- Documentation shows `run` usage with mock provider.
- Documentation states v0.1 non-goals.
- Documentation states that `core-model-v0.1.md` is frozen.

### Tests To Write

- Optional documentation command smoke test if the project has doc-test tooling.
- Otherwise no automated test required beyond keeping commands aligned with CLI tests.

### Dependencies

- Lots 10-12.

### Risks

- Documenting future behavior as if it exists.
- Duplicating the RFC instead of referencing it.
- Making the README broader than the implemented MVP.

## Lot 14: Real Provider Boundary, Without Changing Core

### Objective

Add the first real LLM provider behind the existing LLM interface.

This lot must not change the durable core model.

### Files Concerned

- Provider implementation.
- Provider configuration.
- Provider error mapping.
- Optional integration test guarded by environment configuration.

### Acceptance Criteria

- Real provider implements the same LLM interface as mock.
- CLI can select mock or real provider explicitly.
- Missing API configuration fails with a clear error.
- Provider errors become engine errors and trace failure events.
- Durable `Run`, `Artifact`, and `Trace` schemas do not change.

### Tests To Write

- Unit test provider request mapping where possible.
- Missing API key error test.
- Mock remains default for deterministic tests.
- Optional ignored integration test for real provider.

### Dependencies

- Lot 10 minimum.
- Lot 12 recommended.

### Risks

- Letting provider capabilities reshape the core model.
- Making network tests mandatory.
- Leaking provider response structure into durable core artifacts.

## Lot 15: v0.1 Hardening Pass

### Objective

Stabilize the MVP before any new conceptual expansion.

This is a cleanup and risk-reduction lot only.

### Files Concerned

- Error handling.
- Validation coverage.
- CLI UX.
- Test fixtures.
- Documentation corrections.

### Acceptance Criteria

- All validation errors are readable.
- All command failures exit non-zero.
- All official presets validate and execute with mock provider.
- Failed runs retain partial artifacts and trace failures.
- No extra primitives, core entities, or workflow features have been introduced.
- Documentation and implementation agree on canonical field names.

### Tests To Write

- Regression tests for discovered edge cases.
- Snapshot refresh only when output changes are intentional.
- CLI failure matrix for common user errors.
- Full mock end-to-end test.

### Dependencies

- Lots 1-14 as applicable.

### Risks

- Slipping feature work into hardening.
- Changing the frozen core model instead of fixing implementation drift.
- Treating provider output quality as a core-model issue.
