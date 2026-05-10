from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from phone_mem.web_lab.inspector import MemoryInspector
from phone_mem.web_lab.schemas import error_payload, ok_payload
from phone_mem.web_lab.state import LabState


MODULE_DIR = Path(__file__).parent
TEMPLATE_PATH = MODULE_DIR / "templates" / "index.html"
STATIC_DIR = MODULE_DIR / "static"


def create_app(state: LabState | None = None) -> FastAPI:
    lab_state = state or LabState.create()
    owns_state = state is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> object:
        try:
            yield
        finally:
            if owns_state:
                lab_state.close()

    app = FastAPI(title="Phone Mem Python Web Lab", lifespan=lifespan)
    app.state.lab_state = lab_state
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        html = TEMPLATE_PATH.read_text(encoding="utf-8")
        metadata = lab_state.metadata()
        rendered = (
            html.replace("{{ model }}", metadata["model"])
            .replace("{{ provider_status }}", metadata["provider_status"])
            .replace("{{ db_path }}", metadata["db_path"])
            .replace("{{ caller }}", metadata["caller"])
            .replace("{{ source_app }}", metadata["source_app"])
        )
        return HTMLResponse(rendered)

    @app.get("/api/metadata")
    def metadata() -> dict[str, Any]:
        return lab_state.metadata()

    @app.post("/api/chat")
    def chat(body: dict[str, Any]) -> Any:
        message = str(body.get("message", "")).strip()
        if not message:
            return JSONResponse(
                {"ok": False, "error": {"type": "ValidationError", "message": "message is required"}},
                status_code=400,
            )
        try:
            response = lab_state.run_chat_turn(message)
        except Exception as exc:
            return JSONResponse(error_payload(exc), status_code=502)
        return ok_payload(
            text=response.text,
            evidence_event_ids=response.evidence_event_ids,
            captured_event_ids=response.captured_event_ids,
            memory_context=response.memory_context,
            tool_results=response.tool_results,
            turn=lab_state.turn_snapshots[-1].to_dict(),
        )

    @app.get("/api/turns")
    def turns() -> dict[str, Any]:
        return lab_state.snapshots_payload()

    @app.get("/api/memories")
    def memories(include_deleted: bool = False) -> dict[str, Any]:
        return _inspector(lab_state).list_memories(include_deleted=include_deleted)

    @app.get("/api/search")
    def search(query: str, top_k: int = 5) -> dict[str, Any]:
        return _inspector(lab_state).search(query, top_k=top_k)

    @app.get("/api/context")
    def context(query: str, max_tokens: int = 160) -> dict[str, Any]:
        return _inspector(lab_state).preview_context(query, max_tokens=max_tokens)

    @app.get("/api/explain/{event_id}")
    def explain(event_id: str) -> Any:
        return _route_payload(_inspector(lab_state).explain(event_id))

    @app.post("/api/correct/{event_id}")
    def correct(event_id: str, body: dict[str, Any]) -> Any:
        replacement_text = str(body.get("replacement_text", "")).strip()
        if not replacement_text:
            return JSONResponse(
                {
                    "ok": False,
                    "error": {
                        "type": "ValidationError",
                        "message": "replacement_text is required",
                    },
                },
                status_code=400,
            )
        return _route_payload(_inspector(lab_state).correct(event_id, replacement_text))

    @app.post("/api/delete/{event_id}")
    def delete(event_id: str, body: dict[str, Any]) -> Any:
        reason = str(body.get("reason", "")).strip()
        if not reason:
            return JSONResponse(
                {"ok": False, "error": {"type": "ValidationError", "message": "reason is required"}},
                status_code=400,
            )
        return _route_payload(_inspector(lab_state).delete(event_id, reason=reason))

    @app.get("/api/audit")
    def audit() -> dict[str, Any]:
        return _inspector(lab_state).audit()

    @app.get("/api/metrics")
    def metrics() -> dict[str, Any]:
        return _inspector(lab_state).metrics()

    @app.get("/api/maintenance/reflect")
    def reflect() -> dict[str, Any]:
        return _inspector(lab_state).reflect()

    @app.get("/api/maintenance/defrag")
    def defrag() -> dict[str, Any]:
        return _inspector(lab_state).defrag()

    @app.get("/api/maintenance/schema-diff")
    def schema_diff() -> dict[str, Any]:
        return _inspector(lab_state).schema_diff()

    return app


def _inspector(state: LabState) -> MemoryInspector:
    return MemoryInspector(state)


def _route_payload(payload: dict[str, Any]) -> Any:
    if payload.get("ok") is False:
        return JSONResponse(payload, status_code=404)
    return payload
