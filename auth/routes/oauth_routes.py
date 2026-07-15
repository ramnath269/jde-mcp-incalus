import logging
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from auth.dependencies import (
    provider,
    auth_service,
)

logger = logging.getLogger(__name__)


async def oauth_callback(request: Request):
    request_id = request.query_params["request_id"]
    session_id = request.query_params["session_id"]

    logger.info(
        "OAuth callback received",
        extra={"request_id": request_id, "session_id": session_id},
    )

    redirect_url = await provider.create_authorization_code(
        request_id,
        session_id,
    )

    logger.debug("OAuth callback redirecting", extra={"redirect_url": redirect_url})
    return RedirectResponse(redirect_url)


async def oauth_login(request: Request):
    body = await request.json()

    request_id = body["request_id"]
    username = body["username"]
    password = body["password"]
    environment = body["environment"]

    logger.info(
        "OAuth login attempt",
        extra={"request_id": request_id, "username": username, "environment": environment},
    )

    session = await auth_service.authenticate(
        username,
        password,
        environment,
    )

    logger.info(
        "OAuth login successful",
        extra={"request_id": request_id, "session_id": session.session_id, "username": username},
    )

    redirect_url = await provider.create_authorization_code(
        request_id,
        session.session_id,
    )

    return JSONResponse(
    {
        "redirect_url": redirect_url,
    }
)