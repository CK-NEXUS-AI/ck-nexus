#!/usr/bin/python3
"""Bounded CK-NEXUS heartbeat watchdog. Never reads or prints credentials."""
import json, subprocess, time
from pathlib import Path

CONTAINERS = ("ck-sentinel", "ck-ops", "ck-auditor")
STATE = Path("/var/lib/cknexus-watchdog/state.json")
STALE_SECONDS = 180
WINDOW_SECONDS = 3600
MAX_RESTARTS = 2

def run(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)

def log(msg):
    print("cknexus-watchdog: " + msg, flush=True)

def main():
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        state = {"restarts": []}
    now = time.time()
    history = [t for t in state.get("restarts", []) if isinstance(t, (int, float)) and now-t < WINDOW_SECONDS]
    for name in CONTAINERS:
        p = run(["docker", "inspect", "--format", "{{.State.Status}}", name])
        if p.returncode != 0:
            log(f"{name}: inspect failed; no action")
            continue
        status = p.stdout.strip()
        stale_reason = None
        if status != "running":
            stale_reason = "container_not_running"
        else:
            hb = run(["docker", "exec", name, "cat", "/data/heartbeat.json"], timeout=5)
            if hb.returncode != 0:
                stale_reason = "heartbeat_missing"
            else:
                try:
                    data = json.loads(hb.stdout)
                    age = now - float(data["ts"])
                    if age > STALE_SECONDS:
                        stale_reason = f"heartbeat_stale_{int(age)}s"
                    if data.get("has_key") is False:
                        log(f"{name}: heartbeat fresh but provider key missing; agent remains idle (no secret inspected)")
                except Exception:
                    stale_reason = "heartbeat_invalid"
        if stale_reason:
            if len(history) >= MAX_RESTARTS:
                log(f"{name}: {stale_reason}; restart suppressed by rate limit ({len(history)}/{MAX_RESTARTS} per hour)")
                continue
            log(f"{name}: {stale_reason}; attempting bounded restart")
            rp = run(["docker", "restart", "--time", "10", name], timeout=30)
            if rp.returncode == 0:
                history.append(now)
                log(f"{name}: restart command succeeded")
            else:
                log(f"{name}: restart failed (exit {rp.returncode})")
    STATE.write_text(json.dumps({"restarts": history, "checked_at": now}, indent=2) + "\n")
    STATE.chmod(0o600)

if __name__ == "__main__":
    main()
