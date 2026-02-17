"""
Auth middleware that decodes JWTs and attaches payload to request state.

Uses pure ASGI pattern to avoid anyio NoEventLoopError with BaseHTTPMiddleware.
"""
from __future__ import annotations

from typing import Callable, Any

from starlette.types import ASGIApp, Receive, Send, Scope

from auth.security import AuthError, decode_token


class AuthMiddleware:
    """Decode JWT from Authorization header and store payload in request.state.

    Pure ASGI middleware implementation to avoid anyio compatibility issues.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Initialize state if not present
        if "state" not in scope:
            scope["state"] = {}

        scope["state"]["token_payload"] = None
        scope["state"]["user"] = None
        scope["state"]["auth_error"] = None

        # Get headers from scope
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if token:
                try:
                    scope["state"]["token_payload"] = decode_token(token)
                except AuthError as exc:
                    scope["state"]["auth_error"] = exc.message

        await self.app(scope, receive, send)
