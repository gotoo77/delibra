from __future__ import annotations

import json
import sys

from delibra.core import TraceEventType
from delibra.protocol_loader import load_protocol_yaml
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
)


def run_lot5_smoke(protocol_path: str) -> dict[str, object]:
    protocol = load_protocol_yaml(protocol_path)
    validate_protocol(protocol)

    clock = FixedClock(
        (
            "2026-07-07T10:00:00Z",
            "2026-07-07T10:00:01Z",
            "2026-07-07T10:00:02Z",
            "2026-07-07T10:00:03Z",
        )
    )
    run_ids = IdSequence("run")
    trace_ids = IdSequence("trace")
    artifact_ids = IdSequence("artifact")
    event_ids = IdSequence("evt")

    run = create_run(
        protocol,
        {"kind": "text", "content": "Why protect oceans?"},
        run_ids=run_ids,
        trace_ids=trace_ids,
        clock=clock,
    )
    trace = create_trace(run)
    trace = append_trace_event(
        trace,
        create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.RUN_CREATED,
            event_ids=event_ids,
            clock=clock,
            step_id=None,
            payload={"run_id": run.id},
        ),
    )

    step = protocol.steps[0]
    artifact = create_artifact(
        step,
        producer_role_id=step.role or "",
        payload={"content": "The topic asks why oceans should be protected."},
        metadata={},
        artifact_ids=artifact_ids,
        clock=clock,
    )
    run = append_artifact(run, artifact)
    trace = append_trace_event(
        trace,
        create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.ARTIFACT_CREATED,
            event_ids=event_ids,
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

    return {
        "run": run.to_json(),
        "trace": trace.to_json(),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m delibra.runtime.smoke path/to/protocol.yaml", file=sys.stderr)
        return 2
    print(json.dumps(run_lot5_smoke(args[0]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

