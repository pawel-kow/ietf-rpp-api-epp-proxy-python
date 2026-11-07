class BodyBufferingMiddleware:
    """Hands the application only requests that arrived whole.

    The body of a request with one is read to its end before anything else runs. A client that
    disconnects first has its request dropped, so a half-received approve is never run. The
    application then sees an ordinary request with a `content-length` and no `transfer-encoding`,
    whatever the framing was and however late the body came.
    """

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _has_body(scope) -> bool:
        headers = dict(scope["headers"])
        return b"transfer-encoding" in headers or headers.get(b"content-length", b"0") != b"0"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self._has_body(scope):
            await self.app(scope, receive, send)
            return
        chunks = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        headers = [(name, value) for name, value in scope["headers"] if name not in (b"content-length", b"transfer-encoding")]
        headers.append((b"content-length", str(len(body)).encode()))
        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()  # what follows is the disconnect

        await self.app({**scope, "headers": headers}, replay, send)
