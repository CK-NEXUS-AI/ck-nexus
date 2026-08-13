from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .arbitration import Proposal
from .authority import PolicyDenied
from .identity import IdentityError


class AuthorityHTTPServer(ThreadingHTTPServer):
    def __init__(self, addr, handler, *, authority, identity_verifier, arbiter):
        super().__init__(addr, handler); self.authority=authority; self.identity_verifier=identity_verifier; self.arbiter=arbiter

class Handler(BaseHTTPRequestHandler):
    server: AuthorityHTTPServer
    def _json(self,status,body):
        raw=json.dumps(body,separators=(",",":"),default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def _body(self):
        n=int(self.headers.get("Content-Length","0"))
        if n>1024*1024: raise ValueError("request too large")
        return json.loads(self.rfile.read(n) or b"{}")
    def _identity(self):
        value=self.headers.get("Authorization","")
        if not value.startswith("Bearer "): raise IdentityError("missing bearer service token")
        return self.server.identity_verifier.verify(value[7:])
    def do_POST(self):
        try:
            ident=self._identity(); body=self._body()
            if self.path=="/v1/enforce":
                out=self.server.authority.enforce(ident,body["capabilityId"],body.get("params",{}),body.get("ctx",{})); return self._json(200,out)
            if self.path=="/v1/grants/consume":
                ok=self.server.authority.consume_grant(ident,body["executionGrant"],body.get("params",{})); return self._json(200 if ok else 403,{"ok":ok})
            if self.path=="/v1/evidence/seed":
                if ident.role!="admin": return self._json(403,{"error":"ADMIN_REQUIRED"})
                self.server.authority.store.seed_evidence(ref=body["ref"],kind=body["kind"],digest=body["digest"],task_id=body.get("taskId"),quality=body.get("quality",1.0),verified=body.get("verified",True)); return self._json(200,{"ok":True})
            if self.path=="/v1/budget/top-up":
                # Administrative mutation is represented as a capability and still passes the same authority.
                self.server.authority.enforce(ident,"system.budget.top_up",{"taskId":body["taskId"],"amount":body["amount"]},{"taskId":body.get("adminTaskId","admin")})
                remaining=self.server.authority.store.top_up(body["taskId"],int(body["amount"]),self.server.authority.default_budget); return self._json(200,{"ok":True,"remaining":remaining})
            if self.path=="/v1/resolve":
                proposals=[Proposal(**p) for p in body["proposals"]]; out=self.server.arbiter.resolve(body["decisionId"],body["domain"],proposals,high_risk=body.get("highRisk",False)); return self._json(200,out)
            return self._json(404,{"error":"NOT_FOUND"})
        except IdentityError as e: self._json(401,{"error":"IDENTITY_DENIED","message":str(e)})
        except PolicyDenied as e: self._json(403,{"error":e.code,"message":str(e)})
        except (KeyError,ValueError,TypeError,json.JSONDecodeError) as e: self._json(400,{"error":"BAD_REQUEST","message":str(e)})
        except Exception: self._json(500,{"error":"INTERNAL"})
    def do_GET(self):
        try:
            ident=self._identity()
            if self.path=="/health": return self._json(200,{"status":"ok","policySha256":self.server.authority.policy_sha256})
            if self.path.startswith("/v1/transcript"):
                if ident.role!="admin": return self._json(403,{"error":"ADMIN_REQUIRED"})
                # Deliberately no raw-secret-bearing fields; audit payloads only contain hashes/IDs.
                import json as _json
                with self.server.authority.store._db() as db:
                    rows=db.execute("SELECT seq,previous_hash,entry_hash,payload,created_at FROM audit ORDER BY seq").fetchall()
                return self._json(200,{"entries":[{"seq":r[0],"previous_hash":r[1],"entry_hash":r[2],"payload":_json.loads(r[3]),"created_at":r[4]} for r in rows]})
            return self._json(404,{"error":"NOT_FOUND"})
        except IdentityError as e: self._json(401,{"error":"IDENTITY_DENIED","message":str(e)})
    def log_message(self,fmt,*args): pass
