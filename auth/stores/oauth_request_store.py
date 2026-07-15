from datetime import datetime, timedelta
from threading import Lock
from uuid import uuid4

from auth.models import OAuthRequest

class OAuthRequestStore:

    REQUEST_EXPIRY_MINUTES = 5

    def __init__(self):
        self._store: dict[str, OAuthRequest] = {}
        self._lock = Lock()
    
    def create(
        self,
        client_id: str,
        redirect_uri: str,
        state: str,
        code_challenge: str,
    ) -> str:

      now = datetime.utcnow()

      request = OAuthRequest(
          request_id=uuid4().hex,
          client_id=client_id,
          redirect_uri=redirect_uri,
          state=state,
          code_challenge=code_challenge,
          created_at=now,
          expires_at=now + timedelta(minutes=self.REQUEST_EXPIRY_MINUTES)
      )

      with self._lock:
          self._store[request.request_id] = request

      return request.request_id
    
    def get(self, request_id: str) -> OAuthRequest | None:

      with self._lock:
          request = self._store.get(request_id)

      if request is None:
          return None

      if request.expires_at < datetime.utcnow():
          self.delete(request_id)
          return None

      return request
    
    def delete(self, request_id: str) -> None:

      with self._lock:
          self._store.pop(request_id, None)

    def cleanup(self):

      now = datetime.utcnow()

      with self._lock:

          expired = [
              key
              for key, value in self._store.items()
              if value.expires_at < now
          ]

          for key in expired:
              del self._store[key]