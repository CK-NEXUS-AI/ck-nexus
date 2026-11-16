from __future__ import annotations

import os
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

UPSTREAM = "http://127.0.0.1:8000"
MAX_BODY_BYTES = 65_536
ALLOWED_METHODS = ["GET", "POST", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Correlation-ID"]


def _allowed_origins() -> list[str]:
    origins = [
        item.strip().rstrip("/")
        for item in os.getenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    ]
    if not origins or "*" in origins:
        raise RuntimeError("Chat ingress requires explicit HTTPS origins; wildcard is forbidden.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError("Chat ingress origins must be exact HTTPS origins.")
    return origins


def create_app(
    *,
    transport_factory: Callable[[], httpx.AsyncBaseTransport] | None = None,
) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        expose_headers=["X-Correlation-ID"],
        max_age=600,
    )

    async def forward(request: Request, method: str, path: str, body: bytes = b"") -> Response:
        headers: dict[str, str] = {}
        for name in ("authorization", "content-type", "x-correlation-id"):
            value = request.headers.get(name)
            if value:
                headers[name] = value
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(100.0, connect=5.0),
                trust_env=False,
                transport=transport_factory() if transport_factory else None,
            ) as client:
                upstream = await client.request(
                    method,
                    f"{UPSTREAM}{path}",
                    headers=headers,
                    content=body,
                )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Chat backend timed out.") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Chat backend is unavailable.") from exc

        response_headers = {"Cache-Control": "no-store"}
        for name in ("content-type", "x-correlation-id"):
            value = upstream.headers.get(name)
            if value:
                response_headers[name] = value
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
        )

    @app.get("/api/chat/status")
    async def chat_status(request: Request) -> Response:
        return await forward(request, "GET", "/api/chat/status")

    @app.post("/api/chat")
    async def chat(request: Request) -> Response:
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Chat request is too large.")
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Chat request is too large.")
        return await forward(request, "POST", "/api/chat", body)

    return app
