"""Loopback-only development proxy with strict request and response validation."""

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

MAX_BODY_BYTES = 1_048_576
MAX_TARGET_LENGTH = 8_192
SAFE_RESPONSE_HEADERS = {
    "cache-control",
    "content-encoding",
    "content-length",
    "content-type",
    "etag",
    "expires",
    "last-modified",
    "set-cookie",
    "vary",
}


def validated_origin_target(raw_target: str) -> str | None:
    """Return a normalized origin-form request target, or None for unsafe input."""
    if (
        not isinstance(raw_target, str)
        or not raw_target
        or len(raw_target) > MAX_TARGET_LENGTH
        or "\\" in raw_target
        or any(ord(char) < 32 or ord(char) == 127 for char in raw_target)
    ):
        return None
    parsed = urlsplit(raw_target)
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or not parsed.path.startswith("/")
        or parsed.path.startswith("//")
    ):
        return None
    decoded_path = unquote(parsed.path)
    if (
        decoded_path.startswith("//")
        or "\\" in decoded_path
        or any(ord(char) < 32 or ord(char) == 127 for char in decoded_path)
    ):
        return None
    safe_path = quote(decoded_path, safe="/:@!$&'()*+,;=-._~")
    try:
        query_items = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=100)
    except ValueError:
        return None
    safe_query = urlencode(query_items, doseq=True)
    return safe_path + ("?" + safe_query if safe_query else "")


def safe_response_headers(headers: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Keep only expected headers and reject CR/LF injection from upstream."""
    safe: list[tuple[str, str]] = []
    for name, value in headers:
        if name.lower() not in SAFE_RESPONSE_HEADERS:
            continue
        if any(char in name or char in value for char in ("\r", "\n")):
            continue
        safe.append((name, value))
    return safe


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def f(self):
        if self.headers.get("X-CK-NEXUS-Mode", "") != "SANDBOX":
            self.send_error(403, "sandbox mode required")
            return

        target = validated_origin_target(self.path)
        if target is None:
            self.send_error(400, "invalid request target")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "invalid content length")
            return
        if length < 0 or length > MAX_BODY_BYTES:
            self.send_error(413, "request body too large")
            return

        content_type = self.headers.get("Content-Type", "application/json")
        if "\r" in content_type or "\n" in content_type or len(content_type) > 128:
            self.send_error(400, "invalid content type")
            return

        body = self.rfile.read(length) if length else None
        connection = http.client.HTTPConnection("127.0.0.1", 5691, timeout=30)
        try:
            connection.request(
                self.command,
                target,
                body=body,
                headers={
                    "X-CK-NEXUS-Mode": "SANDBOX",
                    "Content-Type": content_type,
                },
            )
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status)
            for name, value in safe_response_headers(response.getheaders()):
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)
        except (OSError, http.client.HTTPException):
            self.send_error(502, "upstream unavailable")
        finally:
            connection.close()

    def do_GET(self):
        self.f()

    def do_POST(self):
        self.f()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 5690), H).serve_forever()
