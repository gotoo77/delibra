from __future__ import annotations

from dataclasses import dataclass

from delibra.core import Protocol, Run, RunStatus, StepDefinition, StepKind, Trace, TraceEventType
from delibra.core.json import JsonMutableObject
from delibra.protocol_validator import validate_protocol
from delibra.runtime.builders import (
    FixedClock,
    IdSequence,
    append_artifact,
    append_trace_event,
    create_artifact,
    create_run,
    create_trace,
    create_trace_event,
    transition_run,
)
from delibra.runtime.context import ExecutionContext
from delibra.runtime.llm import LLMClient, create_llm_request


@dataclass(frozen=True)
class EngineResult:
    run: Run
    trace: Trace


@dataclass(frozen=True)
class EngineIds:
    run_ids: IdSequence
    trace_ids: IdSequence
    artifact_ids: IdSequence
    event_ids: IdSequence
    request_message_ids: IdSequence


@dataclass(frozen=True)
class UnsupportedStepKindError(Exception):
    step_id: str
    kind: StepKind

    def __str__(self) -> str:
        return f"unsupported step kind for sequential engine: {self.step_id} ({self.kind.value})"


@dataclass(frozen=True)
class EngineExecutionError(Exception):
    result: EngineResult
    cause: Exception

    def __str__(self) -> str:
        return str(self.cause)


@dataclass(frozen=True)
class _StepRoleExecutionError(Exception):
    run: Run
    trace: Trace
    cause: Exception


def execute_prompt_synthesize_protocol(
    protocol: Protocol,
    input_ref: JsonMutableObject,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: FixedClock,
) -> EngineResult:
    return execute_protocol(
        protocol,
        input_ref,
        llm=llm,
        ids=ids,
        clock=clock,
    )


def execute_protocol(
    protocol: Protocol,
    input_ref: JsonMutableObject,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: FixedClock,
) -> EngineResult:
    validate_protocol(protocol)

    run = create_run(
        protocol,
        input_ref,
        run_ids=ids.run_ids,
        trace_ids=ids.trace_ids,
        clock=clock,
    )
    trace = create_trace(run)

    run = transition_run(run, RunStatus.VALIDATED, clock=clock)
    run = transition_run(run, RunStatus.RUNNING, clock=clock)
    context = ExecutionContext.from_run(run)

    for step in protocol.steps:
        run, trace, context = _execute_step(
            protocol,
            step,
            run,
            trace,
            context,
            llm=llm,
            ids=ids,
            clock=clock,
        )

    run = transition_run(run, RunStatus.COMPLETED, clock=clock)
    return EngineResult(run=run, trace=trace)


def _execute_step(
    protocol: Protocol,
    step: StepDefinition,
    run: Run,
    trace: Trace,
    context: ExecutionContext,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: FixedClock,
) -> tuple[Run, Trace, ExecutionContext]:
    trace = append_trace_event(
        trace,
        create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.STEP_STARTED,
            event_ids=ids.event_ids,
            clock=clock,
            step_id=step.id,
            payload={"step_id": step.id},
        ),
    )

    try:
        produced_artifact_ids: list[str] = []
        for role_id in _step_role_ids(step):
            run, trace, context, artifact_id = _execute_step_for_role(
                protocol,
                step,
                role_id,
                run,
                trace,
                context,
                llm=llm,
                ids=ids,
                clock=clock,
            )
            produced_artifact_ids.append(artifact_id)

        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.STEP_COMPLETED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload={"artifact_ids": produced_artifact_ids},
            ),
        )
    except _StepRoleExecutionError as exc:
        run = exc.run
        trace = exc.trace
        cause = exc.cause
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.STEP_FAILED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload={"step_id": step.id},
            ),
        )
        run = transition_run(run, RunStatus.FAILED, clock=clock)
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.RUN_FAILED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=None,
                payload={"step_id": step.id},
            ),
        )
        raise EngineExecutionError(EngineResult(run=run, trace=trace), cause) from cause
    except Exception as exc:
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.STEP_FAILED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload={"step_id": step.id},
            ),
        )
        run = transition_run(run, RunStatus.FAILED, clock=clock)
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.RUN_FAILED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=None,
                payload={"step_id": step.id},
            ),
        )
        raise EngineExecutionError(EngineResult(run=run, trace=trace), exc) from exc

    return run, trace, context


def _step_role_ids(step: StepDefinition) -> tuple[str, ...]:
    if step.kind in (StepKind.PROMPT, StepKind.SYNTHESIZE):
        if step.role is None:
            raise ValueError(f"single-role step {step.id} requires role")
        return (step.role,)
    if step.kind in (StepKind.FANOUT, StepKind.CRITICIZE):
        if not step.roles:
            raise ValueError(f"multi-role step {step.id} requires roles")
        return step.roles
    raise UnsupportedStepKindError(step.id, step.kind)


def _execute_step_for_role(
    protocol: Protocol,
    step: StepDefinition,
    role_id: str,
    run: Run,
    trace: Trace,
    context: ExecutionContext,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: FixedClock,
) -> tuple[Run, Trace, ExecutionContext, str]:
    try:
        resolved_inputs = context.resolve_step_inputs(step)
        role = protocol.roles[role_id]
        request = create_llm_request(
            step,
            role,
            message_ids=ids.request_message_ids,
            inputs={
                "user_input": None
                if resolved_inputs.user_input is None
                else dict(resolved_inputs.user_input),
                "artifact_ids": list(resolved_inputs.artifact_ids),
            },
        )
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.MESSAGE_SENT,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload={"message_id": request.message.id},
            ),
        )

        response = llm.generate(request)
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.MESSAGE_RECEIVED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload={"message_id": response.message.id},
            ),
        )

        artifact = create_artifact(
            step,
            producer_role_id=role.id,
            payload=response.payload,
            metadata=response.metadata,
            artifact_ids=ids.artifact_ids,
            clock=clock,
        )
        run = append_artifact(run, artifact)
        context = context.with_artifact(artifact)
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.ARTIFACT_CREATED,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload={
                    "artifact_id": artifact.id,
                    "output": artifact.output,
                    "kind": artifact.kind,
                    "producer_role_id": artifact.producer_role_id,
                },
            ),
        )
        return run, trace, context, artifact.id
    except Exception as exc:
        raise _StepRoleExecutionError(run, trace, exc) from exc


def default_engine_ids() -> EngineIds:
    return EngineIds(
        run_ids=IdSequence("run"),
        trace_ids=IdSequence("trace"),
        artifact_ids=IdSequence("artifact"),
        event_ids=IdSequence("evt"),
        request_message_ids=IdSequence("msg"),
    )


def deterministic_clock(size: int = 100) -> FixedClock:
    return FixedClock(
        tuple(f"2026-07-07T10:00:{index:02d}Z" for index in range(size))
    )
