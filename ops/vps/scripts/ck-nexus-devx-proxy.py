import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def f(self):
        if self.headers.get("X-CK-NEXUS-Mode", "") != "SANDBOX":
            self.send_response(403)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n) if n else None
        c = http.client.HTTPConnection("127.0.0.1", 5691, timeout=100)
        h = {
            "X-CK-NEXUS-Mode": "SANDBOX",
            "Content-Type": self.headers.get("Content-Type", "application/json"),
        }
        c.request(self.command, self.path, body=body, headers=h)
        r = c.getresponse()
        data = r.read()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection"):
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)
        c.close()

    def do_GET(self):
        self.f()

    def do_POST(self):
        self.f()


ThreadingHTTPServer(("0.0.0.0", 5690), H).serve_forever()
