#!/bin/bash
set -euo pipefail
BASE=/home/kvm/.local/share/cknexus-webdesktop
mkdir -p "$BASE/logs"
cleanup() {
  set +e
  for p in "${CHROME_PID:-}" "${TUNNEL_PID:-}" "${PROXY_PID:-}" "${VNC_PID:-}" "${DESKTOP_PID:-}" "${XVFB_PID:-}"; do
    [ -n "$p" ] && kill "$p" 2>/dev/null || true
  done
  sleep 1
  for p in "${CHROME_PID:-}" "${TUNNEL_PID:-}" "${PROXY_PID:-}" "${VNC_PID:-}" "${DESKTOP_PID:-}" "${XVFB_PID:-}"; do
    [ -n "$p" ] && kill -9 "$p" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM
# Start an isolated virtual display, never touching the host desktop.
runuser -u kvm -- env HOME=/home/kvm XAUTHORITY="$BASE/Xauthority" XDG_RUNTIME_DIR=/tmp/cknexus-kvm-runtime Xvfb :1 -screen 0 1280x800x24 -nolisten tcp -auth "$BASE/Xauthority" > "$BASE/logs/xvfb.log" 2>&1 & XVFB_PID=$!
for i in $(seq 1 20); do DISPLAY=:1 XAUTHORITY="$BASE/Xauthority" runuser -u kvm -- xset -q >/dev/null 2>&1 && break; sleep 1; done
DISPLAY=:1 XAUTHORITY="$BASE/Xauthority" runuser -u kvm -- xset -q >/dev/null 2>&1 || { echo 'Xvfb failed'; exit 1; }
runuser -u kvm -- env HOME=/home/kvm DISPLAY=:1 XAUTHORITY="$BASE/Xauthority" XDG_RUNTIME_DIR=/tmp/cknexus-kvm-runtime fluxbox > "$BASE/logs/fluxbox.log" 2>&1 & DESKTOP_PID=$!
sleep 2
runuser -u kvm -- x11vnc -display :1 -auth "$BASE/Xauthority" -rfbauth "$BASE/vnc.passwd" -rfbport 5901 -localhost -forever -shared -noxdamage -repeat -o "$BASE/logs/x11vnc.log" > /dev/null 2>&1 & VNC_PID=$!
PYTHONPATH="$BASE" python3 -m websockify --web=/usr/share/novnc --web-auth --auth-plugin=auth_plugin.FileBasicAuth --auth-source="$BASE/web-auth.txt" 127.0.0.1:6081 127.0.0.1:5901 > "$BASE/logs/websockify.log" 2>&1 & PROXY_PID=$!
# Chrome is available from the desktop launcher and starts on demand to conserve RAM.
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:6081 > "$BASE/logs/cloudflared.log" 2>&1 & TUNNEL_PID=$!
echo "CK-NEXUS web desktop started; Quick Tunnel URL will be printed in logs."
wait "$TUNNEL_PID"
