from datetime import timedelta
import os


class AuthConfig:
    # OAuth Server
    ISSUER = os.getenv("OAUTH_ISSUER", "http://localhost:8000")

    AUTHORIZE_ENDPOINT = "/oauth/authorize"
    TOKEN_ENDPOINT = "/oauth/token"
    REGISTER_ENDPOINT = "/oauth/register"

    # Static OAuth Client (Claude Desktop)
    CLIENT_ID = "claude-desktop"

    REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"

    # Supported scopes
    SCOPES = [
        "openid",
        "profile",
        "mcp",
    ]

    # Token lifetimes
    OAUTH_REQUEST_EXPIRY = timedelta(minutes=5)
    AUTHORIZATION_CODE_EXPIRY = timedelta(minutes=5)
    SESSION_EXPIRY = timedelta(hours=8)

    ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
    REFRESH_TOKEN_EXPIRY = timedelta(hours=8)
    LOGIN_URL = "http://localhost:5173/login"