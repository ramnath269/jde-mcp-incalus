# auth/oauth_client.py

import logging

from mcp.server.auth.provider import OAuthClientInformationFull

logger = logging.getLogger(__name__)

CLAUDE_CLIENT = OAuthClientInformationFull(
    client_id="claude-desktop",
    redirect_uris=[
        "http://localhost:33418/oauth/callback"
    ],
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="none",
)

logger.info(
    "Claude OAuth client configured",
    extra={
        "client_id": CLAUDE_CLIENT.client_id,
        "redirect_uris": CLAUDE_CLIENT.redirect_uris,
    },
)