import logging
from datetime import datetime, timedelta, UTC
from threading import Lock
from uuid import uuid4

from auth.models import UserSession

logger = logging.getLogger(__name__)

class SessionStore:

    SESSION_EXPIRY_HOURS = 8

    def __init__(self):
        self._store: dict[str, UserSession] = {}
        self._lock = Lock()
        logger.debug("SessionStore initialized")

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

        logger.info(
            "User session created",
            extra={"session_id": session.session_id, "username": session.username},
        )

        logger.debug(
            "Session object details",
            extra={
                "session_id": session.session_id,
                "username": session.username,
                "ais_token_prefix": session.ais_token[:16] + "...",
                "created_at": session.created_at.isoformat(),
                "last_access": session.last_access.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "ttl_seconds": int(session.expires_at.timestamp() - session.created_at.timestamp()),
            },
        )

        return session.session_id

    def get(self, session_id: str) -> UserSession | None:

      with self._lock:

          session = self._store.get(session_id)

          if session is None:
              logger.debug("Session not found", extra={"session_id": session_id})
              return None

          now = datetime.now(UTC)

          if session.expires_at < now:
              del self._store[session_id]
              logger.debug("Session expired, deleted", extra={"session_id": session_id})
              return None

          session.last_access = now

          logger.debug("Session retrieved", extra={"session_id": session_id, "username": session.username})
          return session

    def delete(self, session_id: str) -> None:

      with self._lock:
          self._store.pop(session_id, None)

      logger.debug("Session deleted", extra={"session_id": session_id})