from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from phone_mem.web_lab.inspector import MemoryInspector
from phone_mem.web_lab.schemas import error_payload, ok_payload
from phone_mem.web_lab.state import LabState
from phone_mem.web_lab.users import UserLabStateManager, get_session_secret

logger = logging.getLogger(__name__)

MODULE_DIR = Path(__file__).parent
TEMPLATE_PATH = MODULE_DIR / "templates" / "index.html"
STATIC_DIR = MODULE_DIR / "static"


def create_app(
    state: LabState | None = None,
    *,
    model: str | None = None,
    thinking: dict[str, Any] | None = None,
) -> FastAPI:
    if state is not None:
        return _create_single_user_app(state)

    manager = UserLabStateManager(model=model, thinking=thinking)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> object:
        try:
            yield
        finally:
            manager.close_all()

    app = FastAPI(title="Phone Mem Python Web Lab", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=get_session_secret(),
        session_cookie="phone_mem_session",
        max_age=7 * 24 * 60 * 60,
    )
    app.state.user_manager = manager
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def _current_state(request: Request) -> LabState:
        username = request.session.get("username")
        logger.debug(
            "_current_state: raw_cookies=%r session=%r username=%r",
            dict(request.cookies),
            dict(request.session),
            username,
        )
        if not username:
            raise RuntimeError("Not authenticated")
        return manager.get_or_create(username)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        html = TEMPLATE_PATH.read_text(encoding="utf-8")
        username = request.session.get("username")
        if username:
            try:
                lab_state = manager.get_or_create(username)
                metadata = lab_state.metadata()
            except Exception:
                metadata = {
                    "caller": username,
                    "source_app": "web_lab",
                    "model": "unknown",
                    "provider_status": "unknown",
                    "db_path": "",
                }
            rendered = (
                html.replace("{{ model }}", metadata.get("model", "unknown"))
                .replace("{{ provider_status }}", metadata.get("provider_status", "unknown"))
                .replace("{{ db_path }}", metadata.get("db_path", ""))
                .replace("{{ caller }}", metadata.get("caller", username))
                .replace("{{ source_app }}", metadata.get("source_app", "web_lab"))
            )
        else:
            rendered = (
                html.replace("{{ model }}", "—")
                .replace("{{ provider_status }}", "—")
                .replace("{{ db_path }}", "—")
                .replace("{{ caller }}", "—")
                .replace("{{ source_app }}", "—")
            )
        return HTMLResponse(rendered)

    @app.get("/api/me")
    def me(request: Request) -> dict[str, Any]:
        username = request.session.get("username")
        return {"ok": True, "username": username, "authenticated": bool(username)}

    @app.get("/api/debug/session")
    def debug_session(request: Request) -> dict[str, Any]:
        return {
            "ok": True,
            "raw_cookies": dict(request.cookies),
            "session_data": dict(request.session),
            "username": request.session.get("username"),
        }

    @app.post("/api/login")
    async def login(request: Request) -> Any:
        body = await request.json()
        username = str(body.get("username", "")).strip()
        if not username:
            return JSONResponse(
                {"ok": False, "error": {"type": "ValidationError", "message": "username is required"}},
                status_code=400,
            )
        request.session["username"] = username
        manager.get_or_create(username)
        return ok_payload(username=username)

    @app.post("/api/logout")
    def logout(request: Request) -> Any:
        request.session.pop("username", None)
        return ok_payload()

    @app.get("/api/metadata")
    def metadata(request: Request) -> Any:
        try:
            return _current_state(request).metadata()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.post("/api/chat")
    async def chat(request: Request) -> Any:
        try:
            lab_state = _current_state(request)
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )
        body = await request.json()
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
    def turns(request: Request) -> Any:
        try:
            return _current_state(request).snapshots_payload()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.post("/api/chat/refresh")
    def refresh_chat(request: Request) -> Any:
        try:
            return ok_payload(**_current_state(request).clear_chat_history(), turns=[])
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/memories")
    def memories(request: Request, include_deleted: bool = False) -> Any:
        try:
            return _inspector(_current_state(request)).list_memories(include_deleted=include_deleted)
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/search")
    def search(request: Request, query: str, top_k: int = 5) -> Any:
        try:
            return _inspector(_current_state(request)).search(query, top_k=top_k)
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/context")
    def context(request: Request, query: str, max_tokens: int = 160) -> Any:
        try:
            return _inspector(_current_state(request)).preview_context(query, max_tokens=max_tokens)
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/explain/{event_id}")
    def explain(request: Request, event_id: str) -> Any:
        try:
            return _route_payload(_inspector(_current_state(request)).explain(event_id))
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.post("/api/correct/{event_id}")
    async def correct(request: Request, event_id: str) -> Any:
        try:
            lab_state = _current_state(request)
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )
        body = await request.json()
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
    async def delete(request: Request, event_id: str) -> Any:
        try:
            lab_state = _current_state(request)
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )
        body = await request.json()
        reason = str(body.get("reason", "")).strip()
        if not reason:
            return JSONResponse(
                {"ok": False, "error": {"type": "ValidationError", "message": "reason is required"}},
                status_code=400,
            )
        return _route_payload(_inspector(lab_state).delete(event_id, reason=reason))

    @app.get("/api/audit")
    def audit(request: Request) -> Any:
        try:
            return _inspector(_current_state(request)).audit()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/metrics")
    def metrics(request: Request) -> Any:
        try:
            return _inspector(_current_state(request)).metrics()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/maintenance/reflect")
    def reflect(request: Request) -> Any:
        try:
            return _inspector(_current_state(request)).reflect()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/maintenance/defrag")
    def defrag(request: Request) -> Any:
        try:
            return _inspector(_current_state(request)).defrag()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    @app.get("/api/maintenance/schema-diff")
    def schema_diff(request: Request) -> Any:
        try:
            return _inspector(_current_state(request)).schema_diff()
        except RuntimeError as exc:
            return JSONResponse(
                {"ok": False, "error": {"type": "AuthenticationError", "message": str(exc)}},
                status_code=401,
            )

    return app


def _create_single_user_app(state: LabState) -> FastAPI:
    """Legacy single-user mode used by tests."""
    owns_state = False

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> object:
        try:
            yield
        finally:
            nonlocal owns_state
            if owns_state:
                state.close()

    app = FastAPI(title="Phone Mem Python Web Lab", lifespan=lifespan)
    app.state.lab_state = state
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    lab_state = state

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

    @app.post("/api/chat/refresh")
    def refresh_chat() -> dict[str, Any]:
        return ok_payload(**lab_state.clear_chat_history(), turns=[])

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
