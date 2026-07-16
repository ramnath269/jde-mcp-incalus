import logging
from datetime import UTC, datetime
from threading import Lock
import time
from auth.models import AccessTokenEntry
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger(__name__)


class AccessTokenStore:
    def __init__(self):
        self._store: dict[str, AccessTokenEntry] = {}
        self._lock = Lock()
        logger.debug("AccessTokenStore initialized")

    def save(self, entry: AccessTokenEntry) -> None:
        with self._lock:
            self._store[entry.access_token.token] = entry
        logger.debug(
            "Access token saved",
            extra={"token_prefix": entry.access_token.token[:8] + "...", "subject": entry.access_token.subject},
        )

        logger.debug(
            "Access token object details",
            extra={
                "token_prefix": entry.access_token.token[:8] + "...",
                "session_id": entry.session_id,
                "subject": entry.access_token.subject,
                "client_id": entry.access_token.client_id,
                "scopes": entry.access_token.scopes,
                "expires_at": entry.access_token.expires_at,
                "ttl_seconds": int(entry.access_token.expires_at - time.time()) if entry.access_token.expires_at else None,
                "claims": entry.access_token.claims,
            },
        )

    def get(self, token: str) -> AccessTokenEntry | None:
        with self._lock:
            entry = self._store.get(token)

            if entry is None:
                logger.debug("Access token not found in store", extra={"token_prefix": token[:8] + "..."})
                return None

            if (
                entry.access_token.expires_at is not None
                and entry.access_token.expires_at < time.time()
            ):
                del self._store[token]
                logger.debug("Access token expired, deleted", extra={"token_prefix": token[:8] + "..."})
                return None

            logger.debug("Access token retrieved from store", extra={"subject": entry.access_token.subject})
            return entry

    def delete(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)
        logger.debug("Access token deleted", extra={"token_prefix": token[:8] + "..."})

    def cleanup(self) -> None:
        now = datetime.now(UTC).timestamp()

        with self._lock:
            expired = [
                token
                for token, access_token in self._store.items()
                if (
                    access_token.expires_at is not None
                    and access_token.expires_at < now
                )
            ]

            for token in expired:
                del self._store[token]

        if expired:
            logger.info("Cleaned up expired access tokens", extra={"count": len(expired)})