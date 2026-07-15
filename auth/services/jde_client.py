import logging
import httpx

logger = logging.getLogger(__name__)


class JDEClient:

    def __init__(
        self,
        base_url: str
    ):
        self.base_url = base_url
        logger.debug("JDEClient initialized", extra={"base_url": base_url})

    async def request_token(
        self,
        username: str,
        password: str,
        environment: str
    ) -> dict:

        payload = {
            "username": username,
            "password": password,
            "environment": environment,
        }

        url = f"{self.base_url}/jderest/tokenrequest"
        logger.info(
            "Requesting JDE token",
            extra={"username": username, "environment": environment, "url": url},
        )

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                url,
                json=payload,
            )

        response.raise_for_status()

        json_response = response.json()
        logger.info(
            "JDE token request succeeded",
            extra={"username": username, "status_code": response.status_code},
        )

        return json_response