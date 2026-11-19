from __future__ import annotations
import json, sys
from pathlib import Path
ALLOWED={"NOT_ASSESSED","GAP","IMPLEMENTED","VERIFIED","BLOCKED"}
REQUIRED={f"CKAI-{i:02d}" for i in range(1,19)}
def validate(path: str) -> list[str]:
    data=json.loads(Path(path).read_text())
    errors=[]; controls=data.get("controls",[]); ids={c.get("id") for c in controls}
    missing=sorted(REQUIRED-ids)
    if missing: errors.append("missing controls: "+", ".join(missing))
    for c in controls:
        cid=c.get("id","<missing>"); state=c.get("state")
        if state not in ALLOWED: errors.append(f"{cid}: invalid state {state}")
        if not c.get("owner"): errors.append(f"{cid}: owner required")
        if state in {"IMPLEMENTED","VERIFIED"} and not c.get("evidence"):
            errors.append(f"{cid}: evidence required for {state}")
        if state=="VERIFIED" and not c.get("independent_verification"):
            errors.append(f"{cid}: independent verification required")
    if data.get("status")=="VERIFIED" and any(c.get("state")!="VERIFIED" for c in controls):
        errors.append("profile VERIFIED requires every control VERIFIED")
    return errors
if __name__=="__main__":
    p=sys.argv[1] if len(sys.argv)>1 else "config/ai_assurance_controls.json"
    errs=validate(p)
    print("PASS" if not errs else "FAIL\n"+"\n".join(errs))
    raise SystemExit(0 if not errs else 1)
