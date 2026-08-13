from __future__ import annotations

import json
import os
import urllib.request


def post(url, data):
    req=urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type":"application/json","X-CK-NEXUS-Webhook-Token":os.environ["CKNEXUS_EMAIL_WEBHOOK_TOKEN"]}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r: return json.load(r)

def main():
    base=os.getenv("CKNEXUS_API_BASE","http://127.0.0.1:8000").rstrip("/")
    if not os.getenv("CKNEXUS_EMAIL_WEBHOOK_TOKEN"):
        print(json.dumps({"status":"BLOCKED","reason":"CKNEXUS_EMAIL_WEBHOOK_TOKEN missing"})); return 2
    fixtures=[
      ({"matched_alias":"security@example.com","subject":"hello","sender":"a@example.com","quarantined":False},"SECURITY"),
      ({"matched_alias":"billing@example.com","subject":"invoice","sender":"a@example.com","quarantined":False},"BILLING"),
      ({"matched_alias":"github@example.com","subject":"build","sender":"a@example.com","quarantined":False},"DEVOPS"),
      ({"matched_alias":"alerts@example.com","subject":"alert","sender":"a@example.com","quarantined":False},"SYSTEM_ALERT"),
      ({"matched_alias":"support@example.com","subject":"help","sender":"a@example.com","quarantined":False},"SUPPORT"),
      ({"matched_alias":"ai@example.com","subject":"generate","sender":"a@example.com","quarantined":False},"AI_REQUEST"),
      ({"matched_alias":None,"subject":"possible phishing breach","sender":"a@example.com","quarantined":False},"SECURITY"),
      ({"matched_alias":None,"subject":"payment failed","sender":"a@example.com","quarantined":False},"BILLING"),
      ({"matched_alias":None,"subject":"normal hello","sender":"a@example.com","quarantined":False},"UNKNOWN"),
      ({"matched_alias":"ai@example.com","subject":"hello","sender":"a@example.com","quarantined":True},"QUARANTINE"),
    ]
    results=[]
    for payload, expected in fixtures:
        got=post(base+"/api/email/route",payload); results.append({"expected":expected,"actual":got.get("category"),"pass":got.get("category")==expected})
    ok=all(x["pass"] for x in results)
    print(json.dumps({"status":"PASS" if ok else "FAIL","results":results},indent=2)); return 0 if ok else 1
if __name__=="__main__": raise SystemExit(main())
