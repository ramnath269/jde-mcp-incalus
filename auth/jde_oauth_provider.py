from __future__ import annotations
import logging
import time
import secrets
import base64
import hashlib
from datetime import UTC, datetime
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

logger = logging.getLogger(__name__)


class JDEOAuthProvider(OAuthAuthorizationServerProvider):
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
        logger.debug("JDEOAuthProvider instantiated")


    async def get_client(
        self,
        client_id: str,
    ) -> OAuthClientInformationFull | None:

        if client_id == AuthConfig.CLIENT_ID:
            logger.debug("Client lookup succeeded", extra={"client_id": client_id})
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

        if client_id == AuthConfig.INSPECTOR_CLIENT_ID:
            logger.debug("Client lookup succeeded", extra={"client_id": client_id})
            return OAuthClientInformationFull(
                client_id=AuthConfig.INSPECTOR_CLIENT_ID,
                client_name="MCP Inspector",
                redirect_uris=[
                    AuthConfig.INSPECTOR_REDIRECT_URI,
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

        logger.warning("Client lookup failed: unknown client", extra={"client_id": client_id})
        return None

    @staticmethod
    def verify_pkce(
        code_verifier: str,
        code_challenge: str,
        method: str,
    ) -> bool:

        if method == "plain":
            result = code_verifier == code_challenge
            logger.debug("PKCE verification (plain)", extra={"result": result})
            return result

        if method != "S256":
            logger.warning("Unsupported PKCE method", extra={"method": method})
            return False

        digest = hashlib.sha256(
            code_verifier.encode()
        ).digest()

        calculated = (
            base64.urlsafe_b64encode(digest)
            .decode()
            .rstrip("=")
        )

        result = secrets.compare_digest(
            calculated,
            code_challenge,
        )
        logger.debug("PKCE verification (S256)", extra={"result": result})
        return result

    @staticmethod
    def generate_token(length: int = 48) -> str:
        token = secrets.token_urlsafe(length)
        logger.debug("Token generated", extra={"length": length})
        return token

    @classmethod
    def access_token_expiry(cls) -> datetime:
        expiry = datetime.now(UTC) + AuthConfig.ACCESS_TOKEN_EXPIRY
        logger.debug("Access token expiry calculated", extra={"expires_at": expiry.isoformat()})
        return expiry

    @classmethod
    def refresh_token_expiry(cls) -> datetime:
        expiry = datetime.now(UTC) + AuthConfig.REFRESH_TOKEN_EXPIRY
        logger.debug("Refresh token expiry calculated", extra={"expires_at": expiry.isoformat()})
        return expiry

    @classmethod
    def authorization_code_expiry(cls) -> datetime:
        expiry = datetime.now(UTC) + AuthConfig.AUTHORIZATION_CODE_EXPIRY
        logger.debug("Authorization code expiry calculated", extra={"expires_at": expiry.isoformat()})
        return expiry

    async def register_client(
        self,
        client_info: OAuthClientInformationFull,
    ) -> None:
        logger.warning("Dynamic Client Registration attempted but disabled")
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

        logger.info(
            "Authorization request created",
            extra={"request_id": request_id, "client_id": client.client_id},
        )

        query = urlencode(
            {
                "request_id": request_id,
            }
        )

        login_url = AuthConfig.LOGIN_URL

        redirect = f"{login_url}?{query}"
        logger.debug("Authorization redirect URL built", extra={"redirect_url": redirect})
        return redirect

    async def load_authorization_request(
        self,
        request_id: str,
    ):

        request = self._oauth_request_store.get(
            request_id
        )

        if request is None:
            logger.warning("Authorization request not found", extra={"request_id": request_id})
            raise TokenError(
                TokenErrorCode.INVALID_REQUEST,
                "Unknown authorization request."
            )

        logger.debug("Authorization request loaded", extra={"request_id": request_id})
        return request

    async def load_session(
        self,
        session_id: str,
    ):

        session = self._session_store.get(
            session_id
        )

        if session is None:
            logger.warning("Session not found", extra={"session_id": session_id})
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "User session not found."
            )

        logger.debug("Session loaded", extra={"session_id": session_id, "username": session.username})
        return session

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:

        entry = self._authorization_code_store.get(authorization_code)

        if entry is None:
            logger.warning("Authorization code not found", extra={"code": authorization_code[:8] + "..."})
            return None

        code = entry.authorization_code

        if code.client_id != client.client_id:
            logger.warning(
                "Authorization code client_id mismatch",
                extra={"expected": code.client_id, "got": client.client_id},
            )
            return None

        logger.debug("Authorization code loaded successfully", extra={"code": authorization_code[:8] + "..."})
        return code

    async def create_authorization_code(
        self,
        request_id: str,
        session_id: str,
    ) -> str:

        request = self._oauth_request_store.get(request_id)

        if request is None:
            logger.warning("create_authorization_code: request not found", extra={"request_id": request_id})
            raise TokenError(
                TokenErrorCode.INVALID_REQUEST,
                "Unknown authorization request.",
            )

        session = self._session_store.get(session_id)

        if session is None:
            logger.warning("create_authorization_code: session not found", extra={"session_id": session_id})
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

        logger.info(
            "Authorization code created",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "username": session.username,
                "code": code[:8] + "...",
            },
        )

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

      access_token_ttl = int(AuthConfig.ACCESS_TOKEN_EXPIRY.total_seconds())
      refresh_token_ttl = int(AuthConfig.REFRESH_TOKEN_EXPIRY.total_seconds())

      access_token_string = secrets.token_urlsafe(48)
      refresh_token_string = secrets.token_urlsafe(48)

      access_token = AccessToken(
          token=access_token_string,
          client_id=client.client_id,
          scopes=scopes,
          expires_at=now + access_token_ttl,
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
          expires_at=now + refresh_token_ttl,
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

      logger.info(
          "Tokens issued",
          extra={
              "session_id": session_id,
              "subject": subject,
              "scopes": scopes,
              "access_token_ttl": access_token_ttl,
              "refresh_token_ttl": refresh_token_ttl,
          },
      )

      return OAuthToken(
          access_token=access_token_string,
          refresh_token=refresh_token_string,
          expires_in=access_token_ttl,
          scope=" ".join(scopes),
      )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:

        logger.info(
            "Exchanging authorization code for tokens",
            extra={"code": authorization_code.code[:8] + "...", "client_id": client.client_id},
        )

        #
        # Load AuthorizationCodeEntry
        #
        code_entry = self._authorization_code_store.get(
            authorization_code.code
        )

        if code_entry is None:
            logger.warning("exchange_authorization_code: code entry not found")
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
            logger.warning(
                "exchange_authorization_code: session expired",
                extra={"session_id": code_entry.session_id},
            )
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Session expired."
            )

        self._authorization_code_store.delete(
            authorization_code.code
        )

        logger.debug(
            "Authorization code consumed, issuing tokens",
            extra={"session_id": session.session_id, "username": session.username},
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
            logger.debug("Access token not found or expired")
            return None

        logger.debug("Access token loaded", extra={"subject": entry.access_token.subject})
        return entry.access_token


    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:

        entry = self._refresh_token_store.get(refresh_token)

        if entry is None:
            logger.debug("Refresh token not found or expired")
            return None

        if entry.refresh_token.client_id != client.client_id:
            logger.warning(
                "Refresh token client_id mismatch",
                extra={"expected": entry.refresh_token.client_id, "got": client.client_id},
            )
            return None

        logger.debug("Refresh token loaded", extra={"subject": entry.refresh_token.subject})
        return entry.refresh_token

    async def revoke_token(
        self,
        token: AccessToken | RefreshToken,
    ) -> None:

        if isinstance(token, AccessToken):

            entry = self._access_token_store.get(token.token)

            if entry is None:
                logger.warning("revoke_token: access token not found")
                return

            self._access_token_store.delete(token.token)
            logger.info("Access token revoked", extra={"subject": token.subject})
            return

        entry = self._refresh_token_store.get(token.token)

        if entry is None:
            logger.warning("revoke_token: refresh token not found")
            return

        self._refresh_token_store.delete(token.token)
        logger.info("Refresh token revoked", extra={"token": token.token[:8] + "..."})

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:

        logger.info(
            "Exchanging refresh token",
            extra={"token": refresh_token.token[:8] + "...", "client_id": client.client_id},
        )

        entry = self._refresh_token_store.get(refresh_token.token)

        if entry is None:
            logger.warning("exchange_refresh_token: refresh token not found")
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Invalid refresh token.",
            )

        session = self._session_store.get(entry.session_id)

        if session is None:
            logger.warning(
                "exchange_refresh_token: session expired",
                extra={"session_id": entry.session_id},
            )
            raise TokenError(
                TokenErrorCode.INVALID_GRANT,
                "Session expired.",
            )

        requested_scopes = scopes or refresh_token.scopes

        self._refresh_token_store.delete(
            refresh_token.token
        )

        logger.debug(
            "Old refresh token consumed, issuing new tokens",
            extra={"session_id": session.session_id, "username": session.username},
        )

        return self._issue_tokens(
            client=client,
            session_id=session.session_id,
            subject=session.username,
            scopes=requested_scopes,
        )