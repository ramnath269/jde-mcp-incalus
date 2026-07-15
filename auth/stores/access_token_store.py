from datetime import UTC, datetime
from threading import Lock
import time
from auth.models import AccessTokenEntry
from mcp.server.auth.provider import AccessToken


class AccessTokenStore:
    _store: dict[str, AccessTokenEntry]
    def __init__(self):
        self._store: dict[str, AccessTokenEntry] = {}
        self._lock = Lock()

    def save(self, entry: AccessTokenEntry) -> None:
        with self._lock:
            self._store[entry.access_token.token] = entry

    def get(self, token: str) -> AccessTokenEntry | None:
        with self._lock:
            entry = self._store.get(token)

            if entry is None:
                return None

            if (
                entry.access_token.expires_at is not None
                and entry.access_token.expires_at < time.time()
            ):
                del self._store[token]
                return None

            return entry

    def delete(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)

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