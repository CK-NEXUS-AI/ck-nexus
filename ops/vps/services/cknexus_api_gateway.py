#!/usr/bin/python3
"""CK-NEXUS API Gateway with Qwen integration."""
import json, os, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("CK_GATEWAY_PORT", "8790"))
SCANNER_HEALTH = "http://127.0.0.1:8787/health"
QWEN_KEY   = os.environ.get("DASHSCOPE_API_KEY", "").strip()
QWEN_BASE  = os.environ.get("DASHSCOPE_BASE_URL", "").rstrip("/")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen3.6-plus").strip()
QWEN_OK    = bool(QWEN_KEY and QWEN_BASE)
MAX_BODY   = 65536

def respond(h, status, payload):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.send_header("Cache-Control", "no-store")
    h.send_header("X-Content-Type-Options", "nosniff")
    h.end_headers()
    h.wfile.write(body)

def qwen_chat(payload, timeout=30):
    req = urllib.request.Request(
        QWEN_BASE + "/chat/completions",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {QWEN_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

class Handler(BaseHTTPRequestHandler):
    server_version = "CKNEXUS-Gateway"
    sys_version = ""

    def do_GET(self):
        p = self.path.split("?", 1)[0]
        if p == "/health":
            return respond(self, 200, {"service": "cknexus-api-gateway", "status": "ok", "port": PORT})
        if p == "/v1/status":
            return respond(self, 200, {
                "service": "cknexus-api-gateway", "status": "ok",
                "upstream_integrations": "configured" if QWEN_OK else "not_configured",
                "production_ready": False,
                "qwen": {"configured": QWEN_OK, "model": QWEN_MODEL},
            })
        if p == "/v1/services":
            svcs = [{"name": "scanner", "base_url": "http://127.0.0.1:8787",
                     "routes": ["GET /v1/scanner/health"]}]
            if QWEN_OK:
                svcs.append({"name": "qwen", "base_url": QWEN_BASE,
                             "routes": ["GET /v1/qwen/health", "POST /v1/qwen/chat"]})
            return respond(self, 200, {"services": svcs, "arbitrary_proxying": False})
        if p == "/v1/scanner/health":
            req = urllib.request.Request(SCANNER_HEALTH, headers={"Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=2) as u:
                    return respond(self, 200 if 200 <= u.status < 300 else 502,
                                   {"service": "scanner", "reachable": True, "upstream_status": u.status})
            except Exception as e:
                return respond(self, 502, {"service": "scanner", "reachable": False, "error": type(e).__name__})
        if p == "/v1/qwen/health":
            if not QWEN_OK:
                return respond(self, 503, {"service": "qwen", "configured": False})
            try:
                r = qwen_chat({"model": QWEN_MODEL, "messages": [{"role":"user","content":"ping"}], "max_tokens": 3, "enable_thinking": False}, 15)
                return respond(self, 200, {"service": "qwen", "configured": True, "healthy": True,
                                           "model": QWEN_MODEL, "usage": r.get("usage", {})})
            except Exception as e:
                return respond(self, 502, {"service": "qwen", "configured": True, "healthy": False, "error": type(e).__name__})
        return respond(self, 404, {"error": "route_not_found"})

    def do_POST(self):
        p = self.path.split("?", 1)[0]
        if p != "/v1/qwen/chat":
            return respond(self, 405, {"error": "method_not_allowed"})
        if not QWEN_OK:
            return respond(self, 503, {"error": "qwen_not_configured"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            return respond(self, 400, {"error": "invalid_length"})
        if n <= 0 or n > MAX_BODY:
            return respond(self, 400, {"error": "body_size"})
        try:
            payload = json.loads(self.rfile.read(n))
        except Exception:
            return respond(self, 400, {"error": "invalid_json"})
        if not isinstance(payload, dict) or "messages" not in payload:
            return respond(self, 400, {"error": "missing_messages"})
        payload.setdefault("model", QWEN_MODEL)
        payload.setdefault("max_tokens", 512)
        try:
            return respond(self, 200, qwen_chat(payload, 60))
        except urllib.error.HTTPError as e:
            try: b = json.loads(e.read())
            except Exception: b = {}
            return respond(self, 502, {"error": "upstream", "status": e.code, "body": b})
        except Exception as e:
            return respond(self, 502, {"error": type(e).__name__})

    def do_PUT(self):    return respond(self, 405, {"error": "method_not_allowed"})
    def do_PATCH(self):  return respond(self, 405, {"error": "method_not_allowed"})
    def do_DELETE(self): return respond(self, 405, {"error": "method_not_allowed"})
    def log_message(self, *a): print("cknexus-api-gateway: request handled", flush=True)

if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
