from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol as TypingProtocol

from delibra.core import Role, StepDefinition
from delibra.core.json import JsonMutableObject
from delibra.runtime.builders import IdSequence


@dataclass(frozen=True)
class Message:
    id: str
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    message: Message
    step_id: str
    role_id: str
    inputs: JsonMutableObject


@dataclass(frozen=True)
class LLMResponse:
    message: Message
    payload: JsonMutableObject
    metadata: JsonMutableObject


class LLMClient(TypingProtocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        ...


@dataclass(frozen=True)
class MockLLMError(Exception):
    step_id: str
    role_id: str

    def __str__(self) -> str:
        return f"mock LLM error for step {self.step_id} role {self.role_id}"


@dataclass
class MockLLMClient:
    response_message_ids: IdSequence
    fail_for: tuple[tuple[str, str], ...] = ()

    def generate(self, request: LLMRequest) -> LLMResponse:
        if (request.step_id, request.role_id) in self.fail_for:
            raise MockLLMError(request.step_id, request.role_id)

        content = f"mock response for step {request.step_id} role {request.role_id}"
        return LLMResponse(
            message=Message(
                id=self.response_message_ids.next(),
                role="assistant",
                content=content,
            ),
            payload={"content": content},
            metadata={},
        )


def create_llm_request(
    step: StepDefinition,
    role: Role,
    *,
    message_ids: IdSequence,
    inputs: JsonMutableObject,
) -> LLMRequest:
    return LLMRequest(
        message=Message(
            id=message_ids.next(),
            role="user",
            content=_render_request_content(step, role),
        ),
        step_id=step.id,
        role_id=role.id,
        inputs=inputs,
    )


def _render_request_content(step: StepDefinition, role: Role) -> str:
    return "\n".join(
        (
            f"role:{role.id}",
            f"step:{step.id}",
            role.instruction,
            step.instruction,
        )
    )
