#!/usr/bin/env python3
"""Allowlist-only exporter for CK-NEXUS n8n health evidence."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
SECTIONS = {"n8n":{"service","version","healthz_http_status"},"database":{"present","integrity_check","table_counts"},"backup_timer":{"active","enabled"},"cloud_inventory_snapshot":{"age_seconds","sha256_match","workflow_count","note"},"filesystem_root":{"used_percent","total_bytes","free_bytes"}}
TOP = {"schema","generated_at_utc","scope"}
def sanitize(raw):
    if not isinstance(raw,dict): raise ValueError("input must be a JSON object")
    out={k:raw[k] for k in TOP if k in raw}
    for section,allow in SECTIONS.items():
        obj=raw.get(section,{})
        out[section]={k:obj[k] for k in sorted(allow) if isinstance(obj,dict) and k in obj}
    out["exported_at_utc"]=datetime.now(timezone.utc).isoformat()
    return out
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("input",type=Path); ap.add_argument("output_dir",type=Path); args=ap.parse_args()
    safe=sanitize(json.loads(args.input.read_text(encoding="utf-8"))); args.output_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); target=args.output_dir/f"n8n-health-{stamp}.json"
    target.write_text(json.dumps(safe,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.chmod(target,0o600)
    digest=hashlib.sha256(target.read_bytes()).hexdigest(); manifest=target.with_suffix(".sha256")
    manifest.write_text(f"{digest}  {target.name}\n",encoding="utf-8"); os.chmod(manifest,0o600)
    print(json.dumps({"status":"written","report":str(target),"sha256":digest,"fields":sorted(safe)}))
if __name__=="__main__": main()
