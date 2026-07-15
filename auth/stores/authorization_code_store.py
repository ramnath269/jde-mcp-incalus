import logging
from datetime import datetime, UTC
from threading import Lock

from mcp.server.auth.provider import AuthorizationCode

from auth.models import AuthorizationCodeEntry

logger = logging.getLogger(__name__)


class AuthorizationCodeStore:

    def __init__(self):
        self._store: dict[str, AuthorizationCodeEntry] = {}
        self._lock = Lock()
        logger.debug("AuthorizationCodeStore initialized")

    def save(
        self,
        entry: AuthorizationCodeEntry,
    ) -> None:

        with self._lock:
            self._store[entry.authorization_code.code] = entry

        logger.debug(
            "Authorization code saved",
            extra={"code_prefix": entry.authorization_code.code[:8] + "...", "session_id": entry.session_id},
        )

    def get(
        self,
        code: str,
    ) -> AuthorizationCodeEntry | None:

        with self._lock:

            entry = self._store.get(code)

            if entry is None:
                logger.debug("Authorization code not found in store", extra={"code_prefix": code[:8] + "..."})
                return None

            now = datetime.now(UTC).timestamp()

            if entry.authorization_code.expires_at < now:
                del self._store[code]
                logger.debug("Authorization code expired, deleted", extra={"code_prefix": code[:8] + "..."})
                return None

            logger.debug("Authorization code retrieved from store", extra={"code_prefix": code[:8] + "..."})
            return entry

    def delete(
        self,
        code: str,
    ) -> None:

        with self._lock:
            self._store.pop(code, None)

        logger.debug("Authorization code deleted", extra={"code_prefix": code[:8] + "..."})

    def cleanup(self) -> None:

        now = datetime.now(UTC).timestamp()

        with self._lock:

            expired = [
                code
                for code, entry in self._store.items()
                if entry.authorization_code.expires_at < now
            ]

            for code in expired:
                del self._store[code]

        if expired:
            logger.info("Cleaned up expired authorization codes", extra={"count": len(expired)})