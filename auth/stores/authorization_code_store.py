from datetime import datetime, UTC
from threading import Lock

from mcp.server.auth.provider import AuthorizationCode

from auth.models import AuthorizationCodeEntry


class AuthorizationCodeStore:

    def __init__(self):
        self._store: dict[str, AuthorizationCodeEntry] = {}
        self._lock = Lock()

    def save(
        self,
        entry: AuthorizationCodeEntry,
    ) -> None:

        with self._lock:
            self._store[entry.authorization_code.code] = entry

    def get(
        self,
        code: str,
    ) -> AuthorizationCodeEntry | None:

        with self._lock:

            entry = self._store.get(code)

            if entry is None:
                return None

            now = datetime.now(UTC).timestamp()

            if entry.authorization_code.expires_at < now:
                del self._store[code]
                return None

            return entry

    def delete(
        self,
        code: str,
    ) -> None:

        with self._lock:
            self._store.pop(code, None)

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