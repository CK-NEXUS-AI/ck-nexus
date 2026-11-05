"""Legacy DevX proxy disabled until an authenticated upstream contract exists.

The live VPS has no listener on ports 5690/5691 and no systemd unit references
this proxy. Do not restore generic path/header forwarding without a reviewed
route allowlist and authenticated upstream contract.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _disabled(self):
        self.send_error(410, "legacy development proxy disabled")

    def do_GET(self):
        self._disabled()

    def do_POST(self):
        self._disabled()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 5690), H).serve_forever()
