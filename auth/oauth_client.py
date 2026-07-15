# auth/oauth_client.py

from mcp.server.auth.provider import OAuthClientInformationFull

CLAUDE_CLIENT = OAuthClientInformationFull(
    client_id="claude-desktop",
    redirect_uris=[
        "http://localhost:33418/oauth/callback"
    ],
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="none",
)