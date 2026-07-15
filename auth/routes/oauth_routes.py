from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from auth.dependencies import (
    provider,
    auth_service,
)


async def oauth_callback(request: Request):
    request_id = request.query_params["request_id"]
    session_id = request.query_params["session_id"]

    redirect_url = await provider.create_authorization_code(
        request_id,
        session_id,
    )

    return RedirectResponse(redirect_url)


async def oauth_login(request: Request):
    body = await request.json()

    request_id = body["request_id"]
    username = body["username"]
    password = body["password"]
    environment = body["environment"]

    session = await auth_service.authenticate(
        username,
        password,
        environment,
    )

    # session_id = session_store.create(session)

    redirect_url = await provider.create_authorization_code(
        request_id,
        session.session_id,
    )

    return JSONResponse(
    {
        "redirect_url": redirect_url,
    }
)