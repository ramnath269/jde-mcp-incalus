import logging
import time
from threading import Lock

from auth.models import RefreshTokenEntry

logger = logging.getLogger(__name__)


class RefreshTokenStore:

    def __init__(self):
        self._store: dict[str, RefreshTokenEntry] = {}
        self._lock = Lock()
        logger.debug("RefreshTokenStore initialized")

    def save(self, entry: RefreshTokenEntry) -> None:
        with self._lock:
            self._store[entry.refresh_token.token] = entry
        logger.debug(
            "Refresh token saved",
            extra={"token_prefix": entry.refresh_token.token[:8] + "...", "session_id": entry.session_id},
        )

    def get(self, token: str) -> RefreshTokenEntry | None:
        with self._lock:

            entry = self._store.get(token)

            if entry is None:
                logger.debug("Refresh token not found in store", extra={"token_prefix": token[:8] + "..."})
                return None

            if (
                entry.refresh_token.expires_at is not None
                and entry.refresh_token.expires_at < time.time()
            ):
                del self._store[token]
                logger.debug("Refresh token expired, deleted", extra={"token_prefix": token[:8] + "..."})
                return None

            logger.debug("Refresh token retrieved from store", extra={"session_id": entry.session_id})
            return entry

    def delete(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)
        logger.debug("Refresh token deleted", extra={"token_prefix": token[:8] + "..."})

    def cleanup(self) -> None:
        now = time.time()

        with self._lock:
            expired = [
                token
                for token, entry in self._store.items()
                if (
                    entry.refresh_token.expires_at is not None
                    and entry.refresh_token.expires_at < now
                )
            ]

            for token in expired:
                del self._store[token]

        if expired:
            logger.info("Cleaned up expired refresh tokens", extra={"count": len(expired)})