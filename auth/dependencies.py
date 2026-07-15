import logging
from auth.stores.oauth_request_store import OAuthRequestStore
from auth.stores.session_store import SessionStore
from auth.stores.authorization_code_store import AuthorizationCodeStore
from auth.stores.access_token_store import AccessTokenStore
from auth.stores.refresh_token_store import RefreshTokenStore
from auth.services.jde_auth_service import JDEAuthService
from auth.jde_oauth_provider import JDEOAuthProvider
from auth.services.jde_client import JDEClient
import os

logger = logging.getLogger(__name__)

oauth_request_store = OAuthRequestStore()
session_store = SessionStore()
authorization_code_store = AuthorizationCodeStore()
access_token_store = AccessTokenStore()
refresh_token_store = RefreshTokenStore()

jde_base_url = os.environ.get("JDE_BASE_URL", "https://aoctest.webine3.com/aoc-mcp")
logger.info("Initializing JDEClient", extra={"base_url": jde_base_url})
jde_client = JDEClient(base_url=jde_base_url)

auth_service = JDEAuthService(jde_client=jde_client, session_store=session_store)

provider = JDEOAuthProvider(
    auth_service=auth_service,
    oauth_request_store=oauth_request_store,
    authorization_code_store=authorization_code_store,
    session_store=session_store,
    access_token_store=access_token_store,
    refresh_token_store=refresh_token_store,
)
logger.info("JDEOAuthProvider initialized")