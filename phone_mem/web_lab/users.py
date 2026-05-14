from __future__ import annotations

import logging
import os
import secrets
import shutil
from pathlib import Path
from typing import Any

from phone_mem.web_lab.state import LabState

logger = logging.getLogger(__name__)

DEFAULT_USERS_DIR = Path(".phone-mem-lab") / "users"
DEFAULT_SESSION_SECRET_ENV = "PHONE_MEM_SESSION_SECRET"


def get_session_secret() -> str:
    """Return session secret from env or a generated fallback."""
    secret = os.environ.get(DEFAULT_SESSION_SECRET_ENV)
    if secret:
        return secret
    return secrets.token_urlsafe(32)


class UserLabStateManager:
    """Manages per-user LabState instances with isolated SQLite databases."""

    def __init__(
        self,
        *,
        users_dir: str | Path | None = None,
        model: str | None = None,
        thinking: dict[str, Any] | None = None,
    ) -> None:
        self.users_dir = Path(users_dir or DEFAULT_USERS_DIR)
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.thinking = thinking
        self._states: dict[str, LabState] = {}

    def _user_db_path(self, username: str) -> Path:
        safe_name = "".join(c for c in username if c.isalnum() or c in "-_").lower()
        if not safe_name:
            safe_name = "default"
        return self.users_dir / safe_name / "memory.sqlite3"

    def get_or_create(self, username: str) -> LabState:
        if username in self._states:
            return self._states[username]
        db_path = self._user_db_path(username)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        state = LabState.create(
            db_path=db_path,
            caller=username,
            source_app="web_lab",
            model=self.model,
            thinking=self.thinking,
        )
        self._states[username] = state
        logger.info("Created LabState for user %r at %s", username, db_path)
        return state

    def get(self, username: str) -> LabState | None:
        return self._states.get(username)

    def delete_user(self, username: str) -> bool:
        """Delete a user's data directory and remove cached state."""
        db_path = self._user_db_path(username)
        user_dir = db_path.parent
        if username in self._states:
            try:
                self._states[username].close()
            except Exception:
                logger.exception("Error closing LabState for user %r", username)
            del self._states[username]
        if user_dir.exists():
            try:
                shutil.rmtree(user_dir)
                logger.info("Deleted user data for %r at %s", username, user_dir)
                return True
            except Exception:
                logger.exception("Failed to delete user data for %r", username)
                return False
        return False

    def list_users(self) -> list[str]:
        """List existing users by directory names."""
        users = []
        for entry in self.users_dir.iterdir():
            if entry.is_dir() and (entry / "memory.sqlite3").exists():
                users.append(entry.name)
        return sorted(users)

    def close_all(self) -> None:
        for username, state in list(self._states.items()):
            try:
                state.close()
            except Exception:
                logger.exception("Error closing LabState for user %r", username)
        self._states.clear()
