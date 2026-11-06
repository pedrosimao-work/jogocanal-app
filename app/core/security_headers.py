from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeaders:
    """Pure ASGI middleware; no buffering or sync adaptation of request handling."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "same-origin"
                headers["X-Frame-Options"] = "DENY"
                if scope.get("path", "").startswith("/admin"):
                    headers["Cache-Control"] = "no-store"
                    headers["Content-Security-Policy"] = (
                        "default-src 'self'; style-src 'self'; img-src 'self' data:; "
                        "script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
                    )
            await send(message)

        await self.app(scope, receive, secure_send)
