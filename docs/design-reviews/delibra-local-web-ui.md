# Delibra Local Web UI Design Review

## Status

This document is a design review, not an accepted architecture decision.

It records the boundary for a first local web UI tranche. Normative decisions
must still be accepted through ADRs, architecture documentation, or the
implementation itself.

## Purpose

The user problem is not to replace `delibra run`.

The problem is:

> A user wants to discover Delibra presets, configure one explicit local run,
> watch progress, and inspect durable artifacts without remembering CLI flags.

The web UI is therefore a local product adapter above Delibra application
capabilities. It should make the existing artifact-first runtime easier to use
while preserving the CLI as a peer adapter.

## Identity Constraints

Delibra remains:

> an artifact-first derivation runtime with durable provenance

The web UI must not make provider names, models, sessions, browser state,
progress timings, or form state durable domain objects. Durable state remains
`run.json`, `trace.json`, and artifacts already contained in `Run`.

## CLI / Web Relationship

The target relationship is:

```text
                    +-- CLI
                    |
Application capabilities
                    |
                    +-- Local Web UI
```

The rejected relationship is:

```text
Web UI
  -> build shell command
  -> execute python3 -m delibra ...
  -> parse stdout/stderr
```

The CLI already delegates much of its behavior to `delibra.app` modules:

- `presets.py` lists and loads presets.
- `inputs.py` resolves text, file, and JSON inputs.
- `output_paths.py` validates output paths and follows the existing symlink
  policy.
- `providers.py` builds runtime `LLMClient` instances.
- `storage.py` writes and reads canonical run and trace JSON.
- `inspection.py` and `analysis.py` return structured views used by CLI
  renderers.
- `local_runtime.py` and `local_diagnostics.py` expose provider diagnostics.

The CLI still owns argument parsing and textual rendering. Those should stay in
`cli.py`.

## Current Coupling

The main run flow is still assembled in `cli._run`:

1. resolve and prepare output paths;
2. load protocol or preset;
3. resolve input;
4. load optional policy;
5. build provider client;
6. execute protocol;
7. write outputs, including partial failed outputs.

That sequence is application behavior, not CLI-specific behavior. A small
`delibra.app.run` service can extract it without moving CLI rendering or
argparse concerns.

Provider selection is mostly reusable, but `ProviderConfig` currently contains
only `id`, and real providers read model names from environment variables. The
web form needs per-run model selection, especially for Ollama, without changing
global `OLLAMA_MODEL`. A minimal extension is to add optional model/base URL
fields to application `ProviderConfig` and let `build_llm_client` overlay those
values on environment-derived configuration without mutating `os.environ`.

## Web Module Boundary

A small `delibra.web` package is appropriate:

- imports FastAPI/Jinja2 and owns HTTP concerns;
- owns CSRF/session cookies, form validation, execution ids, and SSE;
- calls `delibra.app` services for presets, providers, storage, inspection,
  analysis, diagnostics, and run execution;
- never imports into `core` or `runtime`;
- never defines new durable models.

No FastAPI or Jinja2 import should appear in `delibra.core`,
`delibra.runtime`, or `delibra.app`.

## Long-Running Runs

HTTP request handlers should not synchronously execute the protocol. The first
tranche can use an in-memory execution manager:

- POST validates the form;
- creates an ephemeral execution id;
- starts a background task;
- redirects to `/executions/{id}`;
- progress events are appended in memory from structured
  `EngineProgressEvent` callbacks;
- completion points to persisted `run.json` and `trace.json`.

This state is explicitly ephemeral. If the server restarts, active executions
are lost. Completed runs remain discoverable from persisted files.

Concurrency should be deliberately narrow. The first tranche should allow one
active run at a time and reject additional submissions clearly. This is simple,
testable, and avoids shared mutable provider configuration.

## Progress Transport

The runtime already emits structured `EngineProgressEvent` values. The web UI
should use those directly.

Server-Sent Events are a proportional fit for a one-way progress stream. HTMX
polling would be acceptable, but SSE is small enough here and avoids repeated
HTML polling handlers. WebSockets, token streaming, brokers, queues, and
distributed workers are non-goals.

The first tranche does not implement `Last-Event-ID` resume semantics. A
reconnected browser receives current execution status and any progress events
still retained in the bounded in-memory log. The retained progress log is capped
to avoid unbounded memory growth.

## Durable vs Ephemeral State

Durable:

- `run.json`;
- `trace.json`;
- artifacts inside `run.json`;
- existing Delibra protocol and trace semantics.

Ephemeral:

- web execution id;
- in-memory status and event list;
- observed elapsed time;
- form errors;
- CSRF token and session cookie;
- active-task bookkeeping.

The first tranche should not add a database, task persistence, or a new file
format.

## Run Discovery

`Runs` should discover directories below `experiments-root` containing both
`run.json` and `trace.json`.

The directory path is a navigation label only. Provider, model, protocol,
status, and input are not inferred from directory names. They must come from
persisted files or remain unknown.

Discovery should be bounded by a configurable maximum number of visited
directories. Invalid pairs should be listed with diagnostics and never modified.

## Path Confinement

The server should listen on `127.0.0.1` by default and require an
`experiments-root`.

Every user-provided output path in the web form should be relative to that root.
Absolute paths and normalized escapes through `..` must be rejected. Existing
symlink handling should remain coherent with `output_paths.py`: a symlinked
root may be usable, while a symlink under the root that resolves outside is
rejected.

The web UI should not expose arbitrary file browsing.

Result pages should display run and trace locations as labels relative to the
configured experiments root rather than absolute filesystem paths.

## Providers and Secrets

Provider ids should come from application configuration, not duplicated template
lists. The first tranche can support `mock`, `openai`, and `ollama`, matching the
current CLI.

Secrets remain environment configuration. The UI must not display API keys or
sensitive environment values. For OpenAI, the form may accept a model name, but
the API key still comes from `OPENAI_API_KEY`. For Ollama, the form must accept
an explicit model such as `mistral` or `qwen3:4b` and must not mutate
`OLLAMA_MODEL`.

Provider diagnostics can reuse passive local diagnostics. The web UI must not
install runtimes, download models, or change system configuration.

## Local Security

Localhost still has risk because another browser page can attempt requests to a
local service.

Minimum controls for this tranche:

- bind to `127.0.0.1` by default;
- reject unsafe output paths;
- execute no shell commands;
- avoid command interpolation entirely;
- escape model output by default;
- use a CSRF token stored in an HTTP-only same-site cookie and required in POST
  forms;
- reject unsafe `Origin` and `Referer` headers on mutating requests;
- keep the CSRF cookie without `Secure` by default because the server is served
  over local HTTP, not HTTPS;
- cap form field sizes;
- show errors without tracebacks or secrets.

This is not a multi-user authentication system.

If `Origin` and `Referer` are both absent, the CSRF token remains the active
protection. If either header is present and points outside the current local
origin, the mutating request is rejected.

## Rendering

Server-rendered HTML with Jinja2 is sufficient. HTMX is not required for the
first tranche if SSE plus small local JavaScript covers progress updates.

Artifact payloads should render as escaped preformatted JSON/text. Model output
must not be rendered as raw HTML or automatically linkified. Markdown rendering
is out of scope until a sanitization policy is explicit and tested.

## Stack Choice

FastAPI, Jinja2, server-rendered HTML, SSE, local CSS, and minimal JavaScript
fit the current repository:

- no existing frontend stack exists;
- Python remains the only runtime;
- no Node.js, bundler, SPA, or separate API client is needed;
- FastAPI gives straightforward local routing and background tasks;
- Jinja2 keeps templates inspectable and boring.

Added dependencies should be limited to `fastapi`, `uvicorn`, and `jinja2`.
Form bodies can be parsed from URL-encoded request bodies to avoid adding
`python-multipart`.

Alternatives considered:

- CLI subprocess backend: rejected because it makes the CLI an implicit backend
  and requires stdout/stderr parsing.
- Flask: viable, but FastAPI has better built-in streaming response ergonomics
  and typed request handling.
- SPA frontend: rejected as disproportionate for the first local tranche.
- HTMX polling only: viable fallback, but SSE is small and maps directly to
  structured progress events.

## Non-Goals

- Remote public server.
- User accounts or full authentication.
- Multi-user permissions.
- Database.
- Persistent web task queue or resume after restart.
- Celery, Redis, brokers, or WebSockets.
- React, Vue, Angular, Node.js, npm, or a bundler.
- Protocol editing.
- Preset creation.
- Provider installation or model download.
- Secret storage.
- Graphical DelObs or semantic comparison.
- Markdown-to-HTML model output rendering.

## Smallest Useful Vertical Slice

The smallest useful tranche is:

1. `python3 -m delibra web --host 127.0.0.1 --port 8000 --experiments-root experiments`.
2. Home page with Delibra identity, New run, Runs, and provider diagnostics.
3. New run form:
   - preset from `list_presets`;
   - provider from application provider ids;
   - explicit model for real providers;
   - text input;
   - relative output subdirectory;
   - progress enabled by default.
4. POST creates one background execution and redirects.
5. Execution page shows status and structured progress via SSE.
6. Completed execution links to persisted result.
7. Result page loads `run.json` and `trace.json`, shows summary, steps,
   artifacts, provenance, payloads, metadata, and simple mechanical analysis
   when available.
8. Runs page discovers persisted run/trace pairs below `experiments-root`.

## Established Decisions for Implementation

The boundary is sufficiently clear for a first tranche:

- implement `python3 -m delibra web`;
- keep the CLI;
- add `delibra.web` as an adapter package;
- extract a minimal application run service;
- extend `ProviderConfig` for explicit per-run model configuration;
- use FastAPI/Jinja2/SSE;
- keep execution state in memory;
- support one active run;
- discover only persisted `run.json` / `trace.json` pairs under
  `experiments-root`;
- add tests for provider config, path confinement, run discovery, and CLI web
  command availability.

## Stop Criteria Before Extension

Stop after the first tranche unless observed use demonstrates pressure for:

- multiple active runs;
- persistent execution state;
- richer provider setup flows;
- Markdown rendering;
- graphical comparison;
- protocol editing;
- more general web APIs.

Any of those would need a separate design review or ADR depending on how close
it gets to durable state, provider boundaries, or runtime semantics.
