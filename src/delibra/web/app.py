from __future__ import annotations

import argparse
import asyncio
import json
import secrets
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from delibra import __version__
from delibra.app.analysis import analyze_run
from delibra.app.inputs import input_from_text
from delibra.app.local_runtime import LocalRuntimeIntent, assess_local_runtime
from delibra.app.models import ProviderConfig, ProviderId
from delibra.app.presets import PresetError, list_presets, load_preset
from delibra.app.run import RunProtocolApplicationRequest
from delibra.app.run_config import (
    SUPPORTED_PROVIDER_IDS,
    describe_presets,
    describe_provider_options,
)
from delibra.runtime import SUPPORTED_REQUESTED_LANGUAGE_VALUES
from delibra.web.execution_manager import ExecutionLimitError, ExecutionManager, WebExecution
from delibra.web.paths import (
    WebPathError,
    artifact_payload_text,
    discover_runs,
    persisted_run_by_key,
    payload_fields,
    payload_primary_text,
    prepare_experiments_root,
    resolve_web_output_paths,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_EXPERIMENTS_ROOT = "experiments"
MAX_FORM_BYTES = 128_000
CSRF_COOKIE = "delibra_csrf"
LANGUAGE_LABELS = {
    "auto": "Auto - detect from input",
    "fr": "Fran&ccedil;ais",
    "en": "English",
}
LANGUAGE_OPTIONS = tuple(
    {"value": value, "label": LANGUAGE_LABELS[value]}
    for value in SUPPORTED_REQUESTED_LANGUAGE_VALUES
)


@dataclass(frozen=True)
class WebSettings:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    experiments_root: Path = Path(DEFAULT_EXPERIMENTS_ROOT)


def create_app(
    *,
    experiments_root: str | Path = DEFAULT_EXPERIMENTS_ROOT,
    manager: ExecutionManager | None = None,
) -> FastAPI:
    settings = WebSettings(experiments_root=prepare_experiments_root(experiments_root))
    templates = _templates()
    app = FastAPI(title="Delibra Local Web UI")
    app.state.settings = settings
    app.state.manager = ExecutionManager(max_active=1) if manager is None else manager

    static_dir = files("delibra.web").joinpath("static")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        diagnostics = assess_local_runtime(LocalRuntimeIntent()).diagnostics
        return _html(
            request,
            templates,
            "home.html",
            {
                "diagnostics": diagnostics,
            },
        )

    @app.get("/runs/new", response_class=HTMLResponse)
    async def new_run(request: Request) -> Response:
        return _html(
            request,
            templates,
            "new_run.html",
            _new_run_context(),
        )

    @app.post("/runs")
    async def create_run(request: Request) -> Response:
        csrf_error = _validate_mutation_request(request)
        try:
            form = await _read_form(request)
        except ValueError as exc:
            context = _new_run_context()
            context["errors"].append(str(exc))
            return _html(request, templates, "new_run.html", context, status_code=400)
        csrf_error = csrf_error or _validate_csrf(form, request)
        context = _new_run_context(form=form)
        if csrf_error is not None:
            context["errors"].append(csrf_error)
            return _html(request, templates, "new_run.html", context, status_code=400)

        try:
            app_request = _build_run_request(settings.experiments_root, form)
            execution = app.state.manager.start(
                app_request,
                show_progress=form.get("show_progress") == "on",
            )
        except (ExecutionLimitError, PresetError, WebPathError, ValueError, TypeError, OSError) as exc:
            context["errors"].append(str(exc))
            return _html(request, templates, "new_run.html", context, status_code=400)

        return RedirectResponse(
            request.url_for("execution_detail", execution_id=execution.id),
            status_code=303,
        )

    @app.get("/executions/{execution_id}", response_class=HTMLResponse)
    async def execution_detail(request: Request, execution_id: str) -> Response:
        execution = app.state.manager.snapshot(execution_id)
        if execution is None:
            return _html(
                request,
                templates,
                "error.html",
                {"message": "execution not found"},
                status_code=404,
            )
        return _html(
            request,
            templates,
            "execution.html",
            {
                "execution": execution,
                "result_key": _result_key(settings.experiments_root, execution),
                "execution_terminal": _is_terminal_execution(execution),
            },
        )

    @app.get("/executions/{execution_id}/events")
    async def execution_events(execution_id: str) -> StreamingResponse:
        return StreamingResponse(
            _event_stream(app.state.manager, execution_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/runs", response_class=HTMLResponse)
    async def runs(request: Request) -> Response:
        return _html(
            request,
            templates,
            "runs.html",
            {"runs": discover_runs(settings.experiments_root)},
        )

    @app.get("/runs/{run_key:path}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_key: str) -> Response:
        try:
            persisted = persisted_run_by_key(settings.experiments_root, run_key)
        except WebPathError as exc:
            return _html(
                request,
                templates,
                "error.html",
                {"message": str(exc)},
                status_code=404,
            )

        assert persisted.run is not None
        analysis = analyze_run(persisted.run, persisted.trace)
        return _html(
            request,
            templates,
            "run_detail.html",
            {
                "persisted": persisted,
                "analysis": analysis,
                "steps": _step_groups(persisted.run.artifacts),
                "final_artifact": _final_artifact(persisted.run.artifacts),
                "payload_text": artifact_payload_text,
                "payload_primary_text": payload_primary_text,
                "payload_fields": payload_fields,
            },
        )

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="delibra web",
        description="Run the local Delibra web UI.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="host to bind; default 127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port to bind; default 8000")
    parser.add_argument(
        "--experiments-root",
        default=DEFAULT_EXPERIMENTS_ROOT,
        help="authorized root for run outputs and discovery; default experiments",
    )
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run(
        create_app(experiments_root=args.experiments_root),
        host=args.host,
        port=args.port,
    )
    return 0


def _templates() -> Jinja2Templates:
    template_dir = files("delibra.web").joinpath("templates")
    templates = Jinja2Templates(directory=str(template_dir))
    templates.env.filters["json_text"] = artifact_payload_text
    return templates


def _html(
    request: Request,
    templates: Jinja2Templates,
    template: str,
    context: dict[str, Any],
    *,
    status_code: int = 200,
) -> Response:
    token = request.cookies.get(CSRF_COOKIE)
    if token is None:
        token = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(
        request,
        template,
        {
            **context,
            "app_version": __version__,
            "csrf_token": token,
            "experiments_root": request.app.state.settings.experiments_root,
        },
        status_code=status_code,
    )
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=True,
        samesite="strict",
    )
    return response


def _new_run_context(
    *,
    form: dict[str, str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    presets = list_presets()
    diagnostics = assess_local_runtime(LocalRuntimeIntent()).diagnostics
    provider_options = describe_provider_options(diagnostics)
    return {
        "presets": presets,
        "preset_details": describe_presets(presets),
        "provider_options": provider_options,
        "language_options": LANGUAGE_OPTIONS,
        "form": form or {
            "preset": "",
            "provider": "mock",
            "model": "",
            "language": "auto",
            "input_text": "",
            "output_dir": "",
            "show_progress": "on",
        },
        "errors": [] if errors is None else errors,
    }


async def _read_form(request: Request) -> dict[str, str]:
    body = await request.body()
    if len(body) > MAX_FORM_BYTES:
        raise ValueError("form submission is too large")
    data = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in data.items()}


def _validate_mutation_request(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin is not None and origin != _request_origin(request):
        return "request origin is not allowed"
    referer = request.headers.get("referer")
    if origin is None and referer is not None and not referer.startswith(_request_origin(request) + "/"):
        return "request referer is not allowed"

    cookie_token = request.cookies.get(CSRF_COOKIE)
    return None if cookie_token is not None else "missing CSRF cookie"


def _validate_csrf(form: dict[str, str], request: Request) -> str | None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    form_token = form.get("csrf_token")
    if cookie_token is None or form_token is None:
        return "missing CSRF token"
    if not secrets.compare_digest(cookie_token, form_token):
        return "invalid CSRF token"
    return None


def _request_origin(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


def _build_run_request(root: Path, form: dict[str, str]) -> RunProtocolApplicationRequest:
    provider = _provider_from_form(form)
    preset_name = form.get("preset", "").strip()
    input_text = form.get("input_text", "")
    if input_text.strip() == "":
        raise ValueError("input text is required")
    if len(input_text) > 64_000:
        raise ValueError("input text is too long")

    protocol = load_preset(preset_name)
    output_paths = resolve_web_output_paths(root, form.get("output_dir", ""))
    language = _language_from_form(form)
    return RunProtocolApplicationRequest(
        protocol=protocol,
        input_ref=input_from_text(input_text),
        provider=provider,
        output_paths=output_paths,
        policy=None,
        language=language,
        progress=None,
    )


def _provider_from_form(form: dict[str, str]) -> ProviderConfig:
    provider = form.get("provider", "mock").strip()
    if provider not in SUPPORTED_PROVIDER_IDS:
        raise ValueError(f"unsupported provider: {provider}")
    model = form.get("model", "").strip()
    if provider in {"openai", "ollama"} and model == "":
        raise ValueError(f"model is required for {provider}")
    if len(model) > 120:
        raise ValueError("model is too long")
    return ProviderConfig(
        id=provider,  # type: ignore[arg-type]
        model=None if model == "" else model,
    )


def _language_from_form(form: dict[str, str]) -> str:
    language = form.get("language", "auto").strip()
    if language not in SUPPORTED_REQUESTED_LANGUAGE_VALUES:
        raise ValueError(f"unsupported language: {language}")
    return language


async def _event_stream(manager: ExecutionManager, execution_id: str):
    sequence = 0
    while True:
        execution = manager.snapshot(execution_id)
        if execution is None:
            yield _sse("missing", {"error": "execution not found"})
            return

        if execution.show_progress:
            for event in manager.events_after(execution_id, sequence):
                sequence = event.sequence
                yield _sse(
                    "progress",
                    {
                        "sequence": event.sequence,
                        "elapsed_seconds": round(event.elapsed_seconds, 2),
                        "type": event.event.type,
                        "step_id": event.event.step_id,
                        "step_kind": event.event.step_kind,
                        "role_id": event.event.role_id,
                        "artifact_id": event.event.artifact_id,
                        "artifact_count": event.event.artifact_count,
                    },
                )

        yield _sse(
            "status",
            {
                "status": execution.status,
                "elapsed_seconds": round(execution.elapsed_seconds, 2),
                "error": execution.error,
                "artifact_count": execution.artifact_count,
            },
        )
        if _is_terminal_execution(execution):
            return
        await asyncio.sleep(0.75)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _step_groups(artifacts) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_step: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        group = by_step.get(artifact.producer_step_id)
        if group is None:
            group = {"step_id": artifact.producer_step_id, "artifacts": []}
            by_step[artifact.producer_step_id] = group
            groups.append(group)
        group["artifacts"].append(artifact)
    return groups


def _final_artifact(artifacts):
    for artifact in reversed(artifacts):
        if artifact.kind == "synthesis" or "synthesis" in artifact.output:
            return artifact
    return artifacts[-1] if artifacts else None


def _result_key(root: Path, execution: WebExecution) -> str | None:
    if execution.run_path is None:
        return None
    try:
        return execution.run_path.parent.relative_to(root).as_posix() or "."
    except ValueError:
        return None


def _is_terminal_execution(execution: WebExecution) -> bool:
    return execution.status in {"completed", "failed"}
