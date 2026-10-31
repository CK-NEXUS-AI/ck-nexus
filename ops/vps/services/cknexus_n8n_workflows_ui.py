#!/usr/bin/env python3
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "100.117.205.112"
PORT = 8791
BASE = "https://xtzsfd91.rpcld.co/api/v1"
KEY_FILE = Path("/root/.config/n8n/api_key")
HTML = Path("/root/ck-nexus/creator_app/web/n8n-workflows.html")
REQUEST_TIMEOUT = 10
MAX_WORKFLOW_PAGES = 20
ALLOWED_READ_PATHS = {"workflows", "executions"}


class N8NAPIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.safe_message = message


def n8n_request(method, path, payload=None):
    """Call only verified n8n API v1 read endpoints; never expose upstream details."""
    method = str(method).upper()
    if method != "GET" or payload is not None:
        raise N8NAPIError(501, "วิธีเรียก API นี้ยังไม่รองรับ")
    parsed = urllib.parse.urlsplit("/" + str(path).lstrip("/"))
    endpoint = parsed.path.strip("/")
    parts = endpoint.split("/")
    allowed_endpoint = endpoint in ALLOWED_READ_PATHS or (
        len(parts) == 2
        and parts[0] == "workflows"
        and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", parts[1]))
    )
    if not allowed_endpoint or ".." in parsed.path.split("/") or parsed.fragment:
        raise N8NAPIError(501, "ปลายทาง API นี้ยังไม่ได้รับการยืนยัน")
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    if any(k not in ("limit", "cursor", "excludePinnedData") for k, _ in query):
        raise N8NAPIError(400, "พารามิเตอร์ API ไม่ถูกต้อง")
    try:
        key = KEY_FILE.read_text().strip()
    except OSError:
        raise N8NAPIError(503, "ยังอ่านการตั้งค่าเชื่อมต่อ n8n ไม่ได้") from None
    if not key:
        raise N8NAPIError(503, "ยังไม่ได้ตั้งค่า API key ของ n8n")
    url = BASE.rstrip("/") + "/" + endpoint
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(
        url,
        headers={
            "X-N8N-API-KEY": key,
            "Accept": "application/json",
            "User-Agent": "CK-NEXUS-WorkflowsUI/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read()
        data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        status = exc.code
        safe = {
            401: "การยืนยันตัวตนกับ n8n ไม่ผ่าน",
            403: "ไม่มีสิทธิ์อ่านข้อมูลจาก n8n",
            404: "ไม่พบปลายทาง n8n ที่ร้องขอ",
        }.get(status, "n8n ตอบกลับข้อผิดพลาด")
        raise N8NAPIError(status if status in (401, 403, 404) else 502, safe) from None
    except (TimeoutError, urllib.error.URLError):
        raise N8NAPIError(504, "n8n ไม่ตอบสนองภายในเวลาที่กำหนด") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise N8NAPIError(502, "n8n ส่งข้อมูล JSON ที่ไม่ถูกต้อง") from None
    except OSError:
        raise N8NAPIError(502, "เชื่อมต่อ n8n ไม่สำเร็จ") from None
    if (
        not isinstance(data, dict)
        or (endpoint == "workflows" and not isinstance(data.get("data"), list))
        or (endpoint.startswith("workflows/") and not isinstance(data.get("nodes"), list))
        or (endpoint == "executions" and not isinstance(data.get("data"), list))
    ):
        raise N8NAPIError(502, "รูปแบบข้อมูลจาก n8n ไม่ตรงตามสัญญา API")
    return data


def list_workflows():
    rows = []
    cursor = None
    seen_cursors = set()
    for _ in range(MAX_WORKFLOW_PAGES):
        params = [("limit", "100")]
        if cursor:
            params.append(("cursor", cursor))
        data = n8n_request("GET", "workflows?" + urllib.parse.urlencode(params))
        rows.extend(data["data"])
        cursor = data.get("nextCursor")
        if not cursor:
            return rows, None
        if not isinstance(cursor, str) or cursor in seen_cursors:
            raise N8NAPIError(502, "ข้อมูลแบ่งหน้าจาก n8n ไม่ถูกต้อง")
        seen_cursors.add(cursor)
    raise N8NAPIError(502, "รายการ workflow มีหน้ามากเกินขีดจำกัดที่ปลอดภัย")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Avoid logging request headers or credentials.
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def send_bytes(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index.html"):
            try:
                body = HTML.read_bytes()
            except Exception:
                self.send_bytes(500, b"UI file missing", "text/plain; charset=utf-8")
                return
            self.send_bytes(200, body, "text/html; charset=utf-8")
            return
        if self.path == "/api/workflows":
            try:
                rows, _ = list_workflows()
                safe = []
                for w in rows:
                    if not isinstance(w, dict):
                        continue
                    safe.append(
                        {
                            "id": str(w.get("id", "")),
                            "name": str(w.get("name") or "Untitled workflow"),
                            "active": bool(w.get("active", False)),
                            "createdAt": w.get("createdAt"),
                            "updatedAt": w.get("updatedAt"),
                            "tags": [
                                t.get("name", "")
                                for t in (w.get("tags") or [])
                                if isinstance(t, dict)
                            ],
                        }
                    )
                out = json.dumps(
                    {"ok": True, "count": len(safe), "workflows": safe, "nextCursor": None},
                    ensure_ascii=False,
                ).encode()
                self.send_bytes(200, out, "application/json; charset=utf-8")
            except N8NAPIError as e:
                code = e.status if e.status in (400, 401, 403, 404, 501, 504) else 502
                self.send_bytes(
                    code,
                    json.dumps({"ok": False, "error": e.safe_message}, ensure_ascii=False).encode(),
                    "application/json; charset=utf-8",
                )
            except Exception:
                self.send_bytes(
                    502,
                    json.dumps(
                        {"ok": False, "error": "โหลดรายการ workflow ไม่สำเร็จ"}, ensure_ascii=False
                    ).encode(),
                    "application/json; charset=utf-8",
                )
            return
        if self.path.startswith("/api/workflows/") and self.path.endswith("/diagram"):
            workflow_id = self.path[len("/api/workflows/") : -len("/diagram")].strip("/")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", workflow_id):
                self.send_bytes(
                    400,
                    json.dumps(
                        {"ok": False, "error": "Workflow ID ไม่ถูกต้อง"}, ensure_ascii=False
                    ).encode(),
                    "application/json; charset=utf-8",
                )
                return
            try:
                rows, _ = list_workflows()
                item = next(
                    (
                        w
                        for w in rows
                        if isinstance(w, dict) and str(w.get("id", "")) == workflow_id
                    ),
                    None,
                )
                if item is None:
                    self.send_bytes(
                        404,
                        json.dumps(
                            {"ok": False, "error": "ไม่พบ Workflow"}, ensure_ascii=False
                        ).encode(),
                        "application/json; charset=utf-8",
                    )
                    return
                if not bool(item.get("active", False)):
                    self.send_bytes(
                        403,
                        json.dumps(
                            {"ok": False, "error": "หน้านี้แสดงเฉพาะ Workflow ที่เปิดใช้งาน"},
                            ensure_ascii=False,
                        ).encode(),
                        "application/json; charset=utf-8",
                    )
                    return
                detail = n8n_request("GET", "workflows/" + workflow_id + "?excludePinnedData=true")
                wf = detail.get("data", detail)
                nodes = []
                for node in wf.get("nodes") or []:
                    if not isinstance(node, dict):
                        continue
                    pos = node.get("position") if isinstance(node.get("position"), list) else [0, 0]
                    nodes.append(
                        {
                            "id": str(node.get("id", "")),
                            "name": str(node.get("name") or node.get("type") or "Node"),
                            "type": str(node.get("type") or "unknown"),
                            "position": [pos[0], pos[1]],
                        }
                    )
                connections = (
                    wf.get("connections") if isinstance(wf.get("connections"), dict) else {}
                )
                safe_connections = {}
                for source, outputs in connections.items():
                    if not isinstance(outputs, dict):
                        continue
                    edges = []
                    for connection_type, groups in outputs.items():
                        if not isinstance(groups, list):
                            continue
                        for group_index, group in enumerate(groups):
                            if not isinstance(group, list):
                                continue
                            for edge in group:
                                if isinstance(edge, dict) and edge.get("node"):
                                    edges.append(
                                        {
                                            "target": str(edge["node"]),
                                            "type": str(edge.get("type") or connection_type),
                                            "index": int(edge.get("index") or 0),
                                            "output": group_index,
                                        }
                                    )
                    if edges:
                        safe_connections[str(source)] = edges
                out = json.dumps(
                    {
                        "ok": True,
                        "workflow": {
                            "id": workflow_id,
                            "name": str(wf.get("name") or item.get("name") or "Workflow"),
                            "nodes": nodes,
                            "connections": safe_connections,
                        },
                    },
                    ensure_ascii=False,
                ).encode()
                self.send_bytes(200, out, "application/json; charset=utf-8")
            except N8NAPIError as e:
                code = e.status if e.status in (400, 401, 403, 404, 501, 504) else 502
                self.send_bytes(
                    code,
                    json.dumps({"ok": False, "error": e.safe_message}, ensure_ascii=False).encode(),
                    "application/json; charset=utf-8",
                )
            except Exception:
                self.send_bytes(
                    502,
                    json.dumps(
                        {"ok": False, "error": "โหลดรายละเอียดแผนผังไม่สำเร็จ"}, ensure_ascii=False
                    ).encode(),
                    "application/json; charset=utf-8",
                )
            return
        if self.path == "/api/health":
            self.send_bytes(
                200, b'{"ok":true,"service":"CK-NEXUS n8n Workflows UI"}', "application/json"
            )
            return
        self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
