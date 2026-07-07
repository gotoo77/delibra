from __future__ import annotations

import unittest
from math import inf
from types import MappingProxyType

from delibra.core import (
    Artifact,
    Run,
    RunStatus,
    Trace,
    TraceEvent,
    TraceEventType,
)


ARTIFACT_JSON = {
    "id": "artifact_0001",
    "kind": "framing",
    "output": "framing",
    "producer_step_id": "frame",
    "producer_role_id": "framer",
    "payload": {
        "content": "The input describes a request validation change.",
        "structured": {"left_as": "opaque json"},
    },
    "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop",
    },
    "created_at": "2026-07-07T10:00:05Z",
}

TRACE_EVENT_JSON = {
    "id": "evt_0001",
    "type": "ArtifactCreated",
    "timestamp": "2026-07-07T10:00:05Z",
    "run_id": "run_0001",
    "step_id": "frame",
    "payload": {
        "artifact_id": "artifact_0001",
        "output": "framing",
        "kind": "framing",
        "producer_role_id": "framer",
    },
}

TRACE_JSON = {
    "id": "trace_0001",
    "run_id": "run_0001",
    "events": [TRACE_EVENT_JSON],
}

RUN_JSON = {
    "id": "run_0001",
    "protocol": {
        "id": "code_review",
        "version": "0.1.0",
    },
    "status": "completed",
    "input": {
        "kind": "file",
        "source": "pr.diff",
        "hash": "sha256:abc123",
    },
    "artifacts": [ARTIFACT_JSON],
    "trace_id": "trace_0001",
    "started_at": "2026-07-07T10:00:00Z",
    "completed_at": "2026-07-07T10:00:21Z",
}


class DurableExecutionModelTests(unittest.TestCase):
    def test_artifact_serializes_to_canonical_json(self) -> None:
        artifact = Artifact(
            id="artifact_0001",
            kind="framing",
            output="framing",
            producer_step_id="frame",
            producer_role_id="framer",
            payload={
                "content": "The input describes a request validation change.",
                "structured": {"left_as": "opaque json"},
            },
            metadata={
                "model": "gpt-5-mini",
                "finish_reason": "stop",
            },
            created_at="2026-07-07T10:00:05Z",
        )

        self.assertEqual(artifact.to_json(), ARTIFACT_JSON)

    def test_artifact_deserializes_from_canonical_json(self) -> None:
        artifact = Artifact.from_json(ARTIFACT_JSON)

        self.assertEqual(artifact.to_json(), ARTIFACT_JSON)

    def test_artifact_payload_is_opaque_immutable_json(self) -> None:
        artifact = Artifact.from_json(ARTIFACT_JSON)

        self.assertIsInstance(artifact.payload, MappingProxyType)
        self.assertEqual(
            artifact.payload["structured"],
            {"left_as": "opaque json"},
        )
        with self.assertRaises(TypeError):
            artifact.payload["content"] = "changed"

    def test_artifact_payload_rejects_non_json_values(self) -> None:
        invalid_values = [
            {"not-json"},
            b"bytes",
            bytearray(b"bytes"),
            object(),
            ("tuple",),
            inf,
        ]

        for value in invalid_values:
            with self.subTest(value=type(value).__name__):
                artifact_json = {
                    **ARTIFACT_JSON,
                    "payload": {"invalid": value},
                }
                with self.assertRaisesRegex(TypeError, "JSON-compatible"):
                    Artifact.from_json(artifact_json)

    def test_artifact_metadata_rejects_non_json_values(self) -> None:
        artifact_json = {
            **ARTIFACT_JSON,
            "metadata": {"invalid": bytearray(b"bytes")},
        }

        with self.assertRaisesRegex(TypeError, "JSON-compatible"):
            Artifact.from_json(artifact_json)

    def test_artifact_kind_accepts_structural_string_without_domain_parsing(self) -> None:
        artifact_json = {**ARTIFACT_JSON, "kind": "custom_structural_kind"}

        artifact = Artifact.from_json(artifact_json)

        self.assertEqual(artifact.kind, "custom_structural_kind")

    def test_trace_event_serializes_to_canonical_json(self) -> None:
        event = TraceEvent(
            id="evt_0001",
            type=TraceEventType.ARTIFACT_CREATED,
            timestamp="2026-07-07T10:00:05Z",
            run_id="run_0001",
            step_id="frame",
            payload={
                "artifact_id": "artifact_0001",
                "output": "framing",
                "kind": "framing",
                "producer_role_id": "framer",
            },
        )

        self.assertEqual(event.to_json(), TRACE_EVENT_JSON)

    def test_trace_event_deserializes_from_canonical_json(self) -> None:
        event = TraceEvent.from_json(TRACE_EVENT_JSON)

        self.assertEqual(event.type, TraceEventType.ARTIFACT_CREATED)
        self.assertEqual(event.to_json(), TRACE_EVENT_JSON)

    def test_trace_serializes_to_canonical_json(self) -> None:
        trace = Trace(
            id="trace_0001",
            run_id="run_0001",
            events=(TraceEvent.from_json(TRACE_EVENT_JSON),),
        )

        self.assertEqual(trace.to_json(), TRACE_JSON)

    def test_trace_deserializes_from_canonical_json(self) -> None:
        trace = Trace.from_json(TRACE_JSON)

        self.assertEqual(trace.to_json(), TRACE_JSON)

    def test_trace_rejects_duplicate_event_ids(self) -> None:
        duplicate_event = {
            **TRACE_EVENT_JSON,
            "type": "StepCompleted",
            "payload": {},
        }
        trace_json = {
            **TRACE_JSON,
            "events": [TRACE_EVENT_JSON, duplicate_event],
        }

        with self.assertRaisesRegex(ValueError, "Trace.events.id"):
            Trace.from_json(trace_json)

    def test_trace_rejects_events_for_another_run(self) -> None:
        trace_json = {
            **TRACE_JSON,
            "events": [{**TRACE_EVENT_JSON, "run_id": "run_other"}],
        }

        with self.assertRaisesRegex(ValueError, "trace run_id"):
            Trace.from_json(trace_json)

    def test_run_serializes_to_canonical_json(self) -> None:
        run = Run(
            id="run_0001",
            protocol={
                "id": "code_review",
                "version": "0.1.0",
            },
            status=RunStatus.COMPLETED,
            input={
                "kind": "file",
                "source": "pr.diff",
                "hash": "sha256:abc123",
            },
            artifacts=(Artifact.from_json(ARTIFACT_JSON),),
            trace_id="trace_0001",
            started_at="2026-07-07T10:00:00Z",
            completed_at="2026-07-07T10:00:21Z",
        )

        self.assertEqual(run.to_json(), RUN_JSON)

    def test_run_deserializes_from_canonical_json(self) -> None:
        run = Run.from_json(RUN_JSON)

        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertEqual(run.to_json(), RUN_JSON)

    def test_run_can_deserialize_null_completed_at(self) -> None:
        run_json = {**RUN_JSON, "status": "running", "completed_at": None}

        run = Run.from_json(run_json)

        self.assertEqual(run.status, RunStatus.RUNNING)
        self.assertIsNone(run.completed_at)
        self.assertEqual(run.to_json(), run_json)

    def test_run_rejects_duplicate_artifact_ids(self) -> None:
        duplicate_artifact = {
            **ARTIFACT_JSON,
            "kind": "review",
            "output": "reviews",
        }
        run_json = {
            **RUN_JSON,
            "artifacts": [ARTIFACT_JSON, duplicate_artifact],
        }

        with self.assertRaisesRegex(ValueError, "Run.artifacts.id"):
            Run.from_json(run_json)

    def test_run_protocol_ref_requires_exact_id_and_version(self) -> None:
        missing_version = {
            **RUN_JSON,
            "protocol": {"id": "code_review"},
        }
        extra_description = {
            **RUN_JSON,
            "protocol": {
                "id": "code_review",
                "version": "0.1.0",
                "description": "not part of the run protocol ref",
            },
        }

        with self.assertRaisesRegex(ValueError, "protocol missing fields"):
            Run.from_json(missing_version)
        with self.assertRaisesRegex(ValueError, "protocol unknown fields"):
            Run.from_json(extra_description)

    def test_run_status_parses_valid_values(self) -> None:
        self.assertEqual(RunStatus.parse("created"), RunStatus.CREATED)
        self.assertEqual(RunStatus.parse("validated"), RunStatus.VALIDATED)
        self.assertEqual(RunStatus.parse("running"), RunStatus.RUNNING)
        self.assertEqual(RunStatus.parse("completed"), RunStatus.COMPLETED)
        self.assertEqual(RunStatus.parse("failed"), RunStatus.FAILED)
        self.assertEqual(RunStatus.parse("cancelled"), RunStatus.CANCELLED)

    def test_run_status_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown run status"):
            RunStatus.parse("done")

    def test_trace_event_type_parses_valid_values(self) -> None:
        self.assertEqual(TraceEventType.parse("RunCreated"), TraceEventType.RUN_CREATED)
        self.assertEqual(
            TraceEventType.parse("RunValidated"), TraceEventType.RUN_VALIDATED
        )
        self.assertEqual(TraceEventType.parse("RunStarted"), TraceEventType.RUN_STARTED)
        self.assertEqual(TraceEventType.parse("StepStarted"), TraceEventType.STEP_STARTED)
        self.assertEqual(TraceEventType.parse("MessageSent"), TraceEventType.MESSAGE_SENT)
        self.assertEqual(
            TraceEventType.parse("MessageReceived"), TraceEventType.MESSAGE_RECEIVED
        )
        self.assertEqual(
            TraceEventType.parse("ArtifactCreated"),
            TraceEventType.ARTIFACT_CREATED,
        )
        self.assertEqual(
            TraceEventType.parse("StepCompleted"), TraceEventType.STEP_COMPLETED
        )
        self.assertEqual(TraceEventType.parse("StepFailed"), TraceEventType.STEP_FAILED)
        self.assertEqual(
            TraceEventType.parse("RunCompleted"), TraceEventType.RUN_COMPLETED
        )
        self.assertEqual(TraceEventType.parse("RunFailed"), TraceEventType.RUN_FAILED)
        self.assertEqual(
            TraceEventType.parse("RunCancelled"), TraceEventType.RUN_CANCELLED
        )

    def test_trace_event_type_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown trace event type"):
            TraceEventType.parse("ArtifactUpdated")


if __name__ == "__main__":
    unittest.main()
