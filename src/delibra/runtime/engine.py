from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from delibra.core import (
    Protocol,
    Run,
    RunStatus,
    StepDefinition,
    StepKind,
    Trace,
    TraceEventType,
    USER_INPUT_RESERVED_ID,
)
from delibra.core.json import JsonMutableObject
from delibra.protocol_validator import validate_protocol
from delibra.runtime.builders import (
    Clock,
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
from delibra.runtime.llm import LLMClient, LLMRequest, create_llm_request
from delibra.runtime.policy import (
    ExecutionPolicy,
    PolicyDecision,
    PolicyDecisionAction,
    PolicyState,
    decide_before_call,
    default_execution_policy,
    default_policy_state,
)


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
class EngineProgressEvent:
    type: str
    run_id: str
    protocol_id: str
    protocol_version: str
    step_id: str | None = None
    step_kind: str | None = None
    role_id: str | None = None
    artifact_id: str | None = None
    artifact_count: int | None = None


ProgressCallback = Callable[[EngineProgressEvent], None]


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


@dataclass(frozen=True)
class _PolicyCancelled(Exception):
    run: Run
    trace: Trace


def execute_protocol(
    protocol: Protocol,
    input_ref: JsonMutableObject,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: Clock,
    policy: ExecutionPolicy | None = None,
    progress: ProgressCallback | None = None,
) -> EngineResult:
    validate_protocol(protocol)
    policy = default_execution_policy() if policy is None else policy

    run = create_run(
        protocol,
        input_ref,
        run_ids=ids.run_ids,
        trace_ids=ids.trace_ids,
        clock=clock,
    )
    trace = create_trace(run)
    trace = _append_run_created_event(trace, run, ids=ids, clock=clock)

    run = transition_run(run, RunStatus.VALIDATED, clock=clock)
    run = transition_run(run, RunStatus.RUNNING, clock=clock)
    _emit_progress(
        progress,
        "run_started",
        run,
        artifact_count=len(run.artifacts),
    )
    trace = _append_policy_applied_event(trace, run, policy, ids=ids, clock=clock)
    context = ExecutionContext.from_run(run)
    policy_state = default_policy_state()

    try:
        for step in protocol.steps:
            run, trace, context, policy_state = _execute_step(
                protocol,
                step,
                run,
                trace,
                context,
                policy,
                policy_state,
                llm=llm,
                ids=ids,
                clock=clock,
                progress=progress,
            )
    except _PolicyCancelled as exc:
        return EngineResult(run=exc.run, trace=exc.trace)

    run = transition_run(run, RunStatus.COMPLETED, clock=clock)
    _emit_progress(
        progress,
        "run_completed",
        run,
        artifact_count=len(run.artifacts),
    )
    return EngineResult(run=run, trace=trace)


def _append_run_created_event(
    trace: Trace,
    run: Run,
    *,
    ids: EngineIds,
    clock: Clock,
) -> Trace:
    return append_trace_event(
        trace,
        create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.RUN_CREATED,
            event_ids=ids.event_ids,
            clock=clock,
            step_id=None,
            payload={},
        ),
    )


def _append_policy_applied_event(
    trace: Trace,
    run: Run,
    policy: ExecutionPolicy,
    *,
    ids: EngineIds,
    clock: Clock,
) -> Trace:
    return append_trace_event(
        trace,
        create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.POLICY_APPLIED,
            event_ids=ids.event_ids,
            clock=clock,
            step_id=None,
            payload={
                "policy_id": policy.id,
                "mode": policy.mode.value,
                "unit": policy.unit,
            },
        ),
    )


def _execute_step(
    protocol: Protocol,
    step: StepDefinition,
    run: Run,
    trace: Trace,
    context: ExecutionContext,
    policy: ExecutionPolicy,
    policy_state: PolicyState,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: Clock,
    progress: ProgressCallback | None,
) -> tuple[Run, Trace, ExecutionContext, PolicyState]:
    _emit_progress(
        progress,
        "step_started",
        run,
        step_id=step.id,
        step_kind=step.kind.value,
        artifact_count=len(run.artifacts),
    )
    resolved_inputs = context.resolve_step_inputs(step)
    trace = append_trace_event(
        trace,
        create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.STEP_STARTED,
            event_ids=ids.event_ids,
            clock=clock,
            step_id=step.id,
            payload={
                "step_id": step.id,
                "inputs": list(step.inputs),
                "resolved_artifact_ids": list(resolved_inputs.artifact_ids),
            },
        ),
    )

    try:
        produced_artifact_ids: list[str] = []
        for role_id in _step_role_ids(step):
            run, trace, context, policy_state, artifact_id = _execute_step_for_role(
                protocol,
                step,
                role_id,
                run,
                trace,
                context,
                policy,
                policy_state,
                llm=llm,
                ids=ids,
                clock=clock,
                progress=progress,
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
        _emit_progress(
            progress,
            "step_completed",
            run,
            step_id=step.id,
            step_kind=step.kind.value,
            artifact_count=len(produced_artifact_ids),
        )
    except _PolicyCancelled:
        raise
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
        _emit_progress(
            progress,
            "run_failed",
            run,
            step_id=step.id,
            step_kind=step.kind.value,
            artifact_count=len(run.artifacts),
        )
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
        _emit_progress(
            progress,
            "run_failed",
            run,
            step_id=step.id,
            step_kind=step.kind.value,
            artifact_count=len(run.artifacts),
        )
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

    return run, trace, context, policy_state


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
    policy: ExecutionPolicy,
    policy_state: PolicyState,
    *,
    llm: LLMClient,
    ids: EngineIds,
    clock: Clock,
    progress: ProgressCallback | None,
) -> tuple[Run, Trace, ExecutionContext, PolicyState, str]:
    try:
        _emit_progress(
            progress,
            "role_started",
            run,
            step_id=step.id,
            step_kind=step.kind.value,
            role_id=role_id,
            artifact_count=len(run.artifacts),
        )
        resolved_inputs = context.resolve_step_inputs(step)
        role = protocol.roles[role_id]
        request = create_llm_request(
            step,
            role,
            message_ids=ids.request_message_ids,
            inputs={
                USER_INPUT_RESERVED_ID: None
                if resolved_inputs.user_input is None
                else _json_mutable_value(resolved_inputs.user_input),
                "artifact_ids": list(resolved_inputs.artifact_ids),
                "artifacts": _resolve_input_artifacts(run, resolved_inputs.artifact_ids),
            },
        )
        decision_result = decide_before_call(
            policy,
            policy_state,
            step_id=step.id,
            role_id=role.id,
            input_chars=_estimated_request_chars(request),
        )
        policy_state = decision_result.state
        trace = append_trace_event(
            trace,
            create_trace_event(
                run_id=run.id,
                event_type=TraceEventType.POLICY_DECISION,
                event_ids=ids.event_ids,
                clock=clock,
                step_id=step.id,
                payload=_policy_decision_payload(decision_result.decision),
            ),
        )
        if decision_result.decision.action is PolicyDecisionAction.CANCEL_RUN:
            trace = append_trace_event(
                trace,
                create_trace_event(
                    run_id=run.id,
                    event_type=TraceEventType.BUDGET_EXCEEDED,
                    event_ids=ids.event_ids,
                    clock=clock,
                    step_id=step.id,
                    payload=_budget_exceeded_payload(decision_result.decision),
                ),
            )
            run = transition_run(run, RunStatus.CANCELLED, clock=clock)
            _emit_progress(
                progress,
                "run_cancelled",
                run,
                step_id=step.id,
                step_kind=step.kind.value,
                role_id=role.id,
                artifact_count=len(run.artifacts),
            )
            raise _PolicyCancelled(run=run, trace=trace)
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
        _emit_progress(
            progress,
            "role_completed",
            run,
            step_id=step.id,
            step_kind=step.kind.value,
            role_id=role_id,
            artifact_id=artifact.id,
            artifact_count=len(run.artifacts),
        )
        return run, trace, context, policy_state, artifact.id
    except _PolicyCancelled:
        raise
    except Exception as exc:
        raise _StepRoleExecutionError(run, trace, exc) from exc


def _emit_progress(
    progress: ProgressCallback | None,
    event_type: str,
    run: Run,
    *,
    step_id: str | None = None,
    step_kind: str | None = None,
    role_id: str | None = None,
    artifact_id: str | None = None,
    artifact_count: int | None = None,
) -> None:
    if progress is None:
        return
    protocol = run.protocol
    progress(
        EngineProgressEvent(
            type=event_type,
            run_id=run.id,
            protocol_id=protocol["id"],
            protocol_version=protocol["version"],
            step_id=step_id,
            step_kind=step_kind,
            role_id=role_id,
            artifact_id=artifact_id,
            artifact_count=artifact_count,
        )
    )


def _resolve_input_artifacts(run: Run, artifact_ids: tuple[str, ...]) -> list[JsonMutableObject]:
    artifacts_by_id = {artifact.id: artifact for artifact in run.artifacts}
    return [artifacts_by_id[artifact_id].to_json() for artifact_id in artifact_ids]


def _json_mutable_value(value):
    if isinstance(value, Mapping):
        return {key: _json_mutable_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_mutable_value(item) for item in value]
    return value


def _estimated_request_chars(request: LLMRequest) -> int:
    return len(
        json.dumps(
            {
                "message_content": request.message.content,
                "inputs": request.inputs,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _policy_decision_payload(decision: PolicyDecision) -> JsonMutableObject:
    return {
        "step_id": decision.step_id,
        "role_id": decision.role_id,
        "action": decision.action.value,
        "reason": decision.reason,
        "estimated_input_units": decision.estimated_input_units,
        "reserved_output_units": decision.reserved_output_units,
        "estimated_total_units": decision.estimated_total_units,
        "run_budget_remaining": decision.run_budget_remaining,
        "step_budget_remaining": decision.step_budget_remaining,
        "route_id": decision.route_id,
        "unit": decision.unit,
    }


def _budget_exceeded_payload(decision: PolicyDecision) -> JsonMutableObject:
    return {
        "step_id": decision.step_id,
        "role_id": decision.role_id,
        "reason": decision.reason,
        "estimated_total_units": decision.estimated_total_units,
        "run_budget_remaining": 0
        if decision.run_budget_remaining is None
        else decision.run_budget_remaining,
        "step_budget_remaining": 0
        if decision.step_budget_remaining is None
        else decision.step_budget_remaining,
        "unit": decision.unit,
    }


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
