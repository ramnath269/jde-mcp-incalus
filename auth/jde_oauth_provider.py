from __future__ import annotations
import time
import secrets
import base64
import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    OAuthClientInformationFull,
    RefreshToken,
    OAuthToken,
    TokenError,
    TokenErrorCode,
)

from auth.services.jde_auth_service import JDEAuthService
from auth.stores.authorization_code_store import AuthorizationCodeStore, AuthorizationCodeEntry
from auth.stores.oauth_request_store import OAuthRequestStore
from auth.stores.session_store import SessionStore
from auth.stores.access_token_store import AccessTokenStore, AccessTokenEntry
from auth.stores.refresh_token_store import RefreshTokenStore, RefreshTokenEntry
from auth.config import AuthConfig

ACCESS_TOKEN_TTL = 3600          # 1 hour
REFRESH_TOKEN_TTL = 30 * 86400   # 30 days


class JDEOAuthProvider(OAuthAuthorizationServerProvider):
    AUTH_CODE_LIFETIME = timedelta(minutes=10)
    ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
    REFRESH_TOKEN_LIFETIME = timedelta(days=30)
    def __init__(
        self,
        auth_service: JDEAuthService,
        oauth_request_store: OAuthRequestStore,
        authorization_code_store: AuthorizationCodeStore,
        session_store: SessionStore,
        access_token_store: AccessTokenStore,
        refresh_token_store: RefreshTokenStore,
    ):
        self.auth_service = auth_service
        self._oauth_request_store = oauth_request_store
        self._authorization_code_store = authorization_code_store
        self._session_store = session_store
        self._access_token_store = access_token_store
        self._refresh_token_store = refresh_token_store


    async def get_client(
        self,
        client_id: str,
    ) -> OAuthClientInformationFull | None:

        if client_id != AuthConfig.CLIENT_ID:
            return None

        return OAuthClientInformationFull(
            client_id=AuthConfig.CLIENT_ID,
            client_name="Claude Desktop",
            redirect_uris=[
                AuthConfig.REDIRECT_URI,
            ],
            grant_types=[
                "authorization_code",
                "refresh_token",
            ],
            response_types=[
                "code",
            ],
            scope=" ".join(AuthConfig.SCOPES),
            token_endpoint_auth_method="none",
        )

    @staticmethod
    def verify_pkce(
        code_verifier: str,
        code_challenge: str,
        method: str,
    ) -> bool:

        if method == "plain":
            return code_verifier == code_challenge

        if method != "S256":
            return False

        digest = hashlib.sha256(
            code_verifier.encode()
        ).digest()

        calculated = (
            base64.urlsafe_b64encode(digest)
            .decode()
            .rstrip("=")
        )

        return secrets.compare_digest(
            calculated,
            code_challenge,
        )

    @staticmethod
    def generate_token(length: int = 48) -> str:
        return secrets.token_urlsafe(length)

    @classmethod
    def access_token_expiry(cls) -> datetime:
        return datetime.now(UTC) + cls.ACCESS_TOKEN_LIFETIME

    @classmethod
    def refresh_token_expiry(cls) -> datetime:
        return datetime.now(UTC) + cls.REFRESH_TOKEN_LIFETIME

    @classmethod
    def authorization_code_expiry(cls) -> datetime:
        return datetime.now(UTC) + cls.AUTH_CODE_LIFETIME

    async def register_client(
        self,
        client_info: OAuthClientInformationFull,
    ) -> None:
        raise NotImplementedError(
            "Dynamic Client Registration is disabled."
        )

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:

        request_id = self._oauth_request_store.create(
            client_id=client.client_id,
            redirect_uri=str(params.redirect_uri),
            state=params.state,
            code_challenge=params.code_challenge,
        )

        query = urlencode(
            {
                "request_id": request_id,
            }
        )

        login_url = AuthConfig.LOGIN_URL

        return f"{login_url}?{query}"

    async def load_authorization_request(
        self,
        request_id: str,
    ):

        request = self._oauth_request_store.get(
            request_id
        )

        if request is None:
            raise TokenError(
                TokenErrorCode.INVALID_REQUEST,
                "Unknown authorization request."
            )

        return request

    async def load_session(
        self,
        session_id: str,
    ):

        session = self._session_store.get(
            session_id
        )

        if session is None:
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "User session not found."
            )

        return session

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:

        entry = self._authorization_code_store.get(authorization_code)

        if entry is None:
            return None

        code = entry.authorization_code

        if code.client_id != client.client_id:
            return None

        return code

    async def create_authorization_code(
        self,
        request_id: str,
        session_id: str,
    ) -> str:

        request = self._oauth_request_store.get(request_id)

        if request is None:
            raise TokenError(
                TokenErrorCode.INVALID_REQUEST,
                "Unknown authorization request.",
            )

        session = self._session_store.get(session_id)

        if session is None:
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Session expired.",
            )

        code = secrets.token_urlsafe(32)

        authorization_code = AuthorizationCode(
            code=code,
            scopes=AuthConfig.SCOPES,
            expires_at=self.authorization_code_expiry().timestamp(),
            client_id=request.client_id,
            code_challenge=request.code_challenge,
            redirect_uri=request.redirect_uri,
            redirect_uri_provided_explicitly=True,
            subject=session.username,
        )

        self._authorization_code_store.save(
            AuthorizationCodeEntry(
                authorization_code=authorization_code,
                session_id=session.session_id,
            )
        )

        self._oauth_request_store.delete(request_id)

        query = urlencode(
            {
                "code": code,
                "state": request.state,
            }
        )

        return f"{request.redirect_uri}?{query}"
    
    def _issue_tokens(
      self,
      *,
      client: OAuthClientInformationFull,
      session_id: str,
      subject: str,
      scopes: list[str],
  ) -> OAuthToken:

      now = int(time.time())

      access_token_string = secrets.token_urlsafe(48)
      refresh_token_string = secrets.token_urlsafe(48)

      access_token = AccessToken(
          token=access_token_string,
          client_id=client.client_id,
          scopes=scopes,
          expires_at=now + ACCESS_TOKEN_TTL,
          subject=subject,
          claims={
              "jde": {
                  "session_id": session_id,
              }
          },
      )

      refresh_token = RefreshToken(
          token=refresh_token_string,
          client_id=client.client_id,
          scopes=scopes,
          expires_at=now + REFRESH_TOKEN_TTL,
          subject=subject,
      )

      self._access_token_store.save(
          AccessTokenEntry(
              access_token=access_token,
              session_id=session_id,
          )
      )

      self._refresh_token_store.save(
          RefreshTokenEntry(
              refresh_token=refresh_token,
              session_id=session_id,
          )
      )

      return OAuthToken(
          access_token=access_token_string,
          refresh_token=refresh_token_string,
          expires_in=ACCESS_TOKEN_TTL,
          scope=" ".join(scopes),
      )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:

        #
        # Load AuthorizationCodeEntry
        #
        code_entry = self._authorization_code_store.get(
            authorization_code.code
        )

        if code_entry is None:
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Authorization code is invalid."
            )

        #
        # Load authenticated session
        #
        session = self._session_store.get(
            code_entry.session_id
        )

        if session is None:
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Session expired."
            )

        self._authorization_code_store.delete(
            authorization_code.code
        )

        return self._issue_tokens(
            client=client,
            session_id=session.session_id,
            subject=session.username,
            scopes=authorization_code.scopes,
        )
    
    async def load_access_token(
        self,
        token: str,
    ) -> AccessToken | None:

        entry = self._access_token_store.get(token)

        if entry is None:
            return None

        return entry.access_token


    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:

        entry = self._refresh_token_store.get(refresh_token)

        if entry is None:
            return None

        if entry.refresh_token.client_id != client.client_id:
            return None

        return entry.refresh_token

    async def revoke_token(
        self,
        token: AccessToken | RefreshToken,
    ) -> None:

        if isinstance(token, AccessToken):

            entry = self._access_token_store.get(token.token)

            if entry is None:
                return

            self._access_token_store.delete(token.token)

            return

        entry = self._refresh_token_store.get(token.token)

        if entry is None:
            return

        self._refresh_token_store.delete(token.token)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:

        entry = self._refresh_token_store.get(refresh_token.token)

        if entry is None:
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Invalid refresh token.",
            )

        session = self._session_store.get(entry.session_id)

        if session is None:
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Session expired.",
            )

        requested_scopes = scopes or refresh_token.scopes

        self._refresh_token_store.delete(
            refresh_token.token
        )

        return self._issue_tokens(
            client=client,
            session_id=session.session_id,
            subject=session.username,
            scopes=requested_scopes,
        )