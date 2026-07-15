from datetime import datetime, timedelta, UTC
from threading import Lock
from uuid import uuid4

from auth.models import UserSession

class SessionStore:

    SESSION_EXPIRY_HOURS = 8

    def __init__(self):
        self._store: dict[str, UserSession] = {}
        self._lock = Lock()

    def create(
        self,
        username: str,
        ais_token: str
    ) -> str:

        now = datetime.now(UTC)

        session = UserSession(
            session_id=uuid4().hex,
            username=username,
            ais_token=ais_token,
            created_at=now,
            last_access=now,
            expires_at=now + timedelta(hours=self.SESSION_EXPIRY_HOURS)
        )

        with self._lock:
            self._store[session.session_id] = session

        return session.session_id

    def get(self, session_id: str) -> UserSession | None:

      with self._lock:

          session = self._store.get(session_id)

          if session is None:
              return None

          now = datetime.now(UTC)

          if session.expires_at < now:
              del self._store[session_id]
              return None

          session.last_access = now

          return session

    def delete(self, session_id: str) -> None:

      with self._lock:
          self._store.pop(session_id, None)