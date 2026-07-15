import logging
from dataclasses import dataclass
from datetime import datetime
from dataclasses import dataclass
from mcp.server.auth.provider import RefreshToken, AccessToken, AuthorizationCode

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class AccessTokenEntry:
    access_token: AccessToken
    session_id: str

@dataclass
class RefreshTokenEntry:
    refresh_token: RefreshToken
    session_id: str

@dataclass(slots=True)
class OAuthRequest:
    request_id: str
    client_id: str
    redirect_uri: str
    state: str
    code_challenge: str
    created_at: datetime
    expires_at: datetime

@dataclass(slots=True)
class UserSession:
    session_id: str
    username: str
    ais_token: str
    created_at: datetime
    last_access: datetime
    expires_at: datetime

@dataclass(slots=True)
class AuthenticationResult:
    session_id: str
    username: str
    environment: str
    ais_token: str

@dataclass(slots=True)
class JDEAuthorizationCode:
    code: str
    session_id: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    scopes: list[str]
    expires_at: datetime

@dataclass(slots=True)
class JDEAccessToken:
    token: str
    session_id: str
    username: str
    scopes: list[str]
    expires_at: datetime

@dataclass(slots=True)
class JDERefreshToken:
    token: str
    session_id: str
    expires_at: datetime

@dataclass(slots=True)
class AuthorizationCodeEntry:
    authorization_code: AuthorizationCode
    session_id: str