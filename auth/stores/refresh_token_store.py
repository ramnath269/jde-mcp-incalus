import time
from threading import Lock

from auth.models import RefreshTokenEntry


class RefreshTokenStore:

    def __init__(self):
        self._store: dict[str, RefreshTokenEntry] = {}
        self._lock = Lock()

    def save(self, entry: RefreshTokenEntry) -> None:
        with self._lock:
            self._store[entry.refresh_token.token] = entry

    def get(self, token: str) -> RefreshTokenEntry | None:
        with self._lock:

            entry = self._store.get(token)

            if entry is None:
                return None

            if (
                entry.refresh_token.expires_at is not None
                and entry.refresh_token.expires_at < time.time()
            ):
                del self._store[token]
                return None

            return entry

    def delete(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)

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