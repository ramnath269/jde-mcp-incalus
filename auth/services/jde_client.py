import httpx


class JDEClient:

    def __init__(
        self,
        base_url: str
    ):
        self.base_url = base_url

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

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                f"{self.base_url}/jderest/tokenrequest",
                json=payload,
            )

        response.raise_for_status()

        return response.json()