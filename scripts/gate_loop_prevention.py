from __future__ import annotations
import json, os, urllib.request

def post(url,data):
    req=urllib.request.Request(url,data=json.dumps(data).encode(),headers={"Content-Type":"application/json","X-CK-NEXUS-Webhook-Token":os.environ["CKNEXUS_EMAIL_WEBHOOK_TOKEN"]},method="POST")
    with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
def main():
    base=os.getenv("CKNEXUS_API_BASE","http://127.0.0.1:8000").rstrip("/")
    if not os.getenv("CKNEXUS_EMAIL_WEBHOOK_TOKEN"):
        print('{"status":"BLOCKED","reason":"missing webhook token"}'); return 2
    cases=[
      ({"headers":{"Auto-Submitted":"auto-replied"},"system_addresses":[]},False),
      ({"headers":{"X-CK-NEXUS-Loop":"evt"},"system_addresses":[]},False),
      ({"headers":{"Precedence":"bulk"},"system_addresses":[]},False),
      ({"headers":{"From":"mailer-daemon@example.com"},"system_addresses":[]},False),
      ({"headers":{"From":"system@example.com"},"system_addresses":["system@example.com"]},False),
      ({"headers":{"From":"human@example.com","Auto-Submitted":"no"},"system_addresses":[]},True),
    ]
    results=[]
    for payload,expected in cases:
        got=post(base+"/api/email/loop-check",payload); actual=bool(got.get("allow_automatic_reply")); results.append({"expected":expected,"actual":actual,"pass":actual==expected,"reason":got.get("reason")})
    ok=all(r["pass"] for r in results); print(json.dumps({"status":"PASS" if ok else "FAIL","results":results},indent=2)); return 0 if ok else 1
if __name__=="__main__": raise SystemExit(main())
