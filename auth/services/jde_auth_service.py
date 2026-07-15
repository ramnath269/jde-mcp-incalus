import logging
from auth.stores.session_store import SessionStore
from auth.services.jde_client import JDEClient
from auth.models import AuthenticationResult

logger = logging.getLogger(__name__)

class JDEAuthService:

    def __init__(
        self,
        jde_client: JDEClient,
        session_store: SessionStore
    ):
        self.jde_client = jde_client
        self.session_store = session_store

    async def authenticate(
        self,
        username: str,
        password: str,
        environment: str
    ) -> AuthenticationResult:

        logger.info(
            "Authenticating user with JDE",
            extra={"username": username, "environment": environment},
        )

        response = await self.jde_client.request_token(
            username,
            password,
            environment,
        )

        ais_token = response["userInfo"]["token"]

        username = response["username"]

        session_id = self.session_store.create(
            username=username,
            ais_token=ais_token,
        )

        logger.info(
            "JDE authentication successful",
            extra={"username": username, "session_id": session_id, "environment": environment},
        )

        return AuthenticationResult(
            session_id=session_id,
            username=username,
            environment=environment,
            ais_token=ais_token
        )