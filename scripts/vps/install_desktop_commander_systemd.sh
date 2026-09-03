#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="desktop-commander-remote"
PACKAGE="@wonderwhy-er/desktop-commander@0.2.47"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[ "${EUID}" -eq 0 ] || fail "run as root on the VPS"
command -v systemctl >/dev/null 2>&1 || fail "systemd/systemctl is required"
command -v node >/dev/null 2>&1 || fail "Node.js is required"
command -v npx >/dev/null 2>&1 || fail "npx is required"

NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
[ "$NODE_MAJOR" -ge 18 ] || fail "Node.js 18+ is required"

NPX_PATH="$(command -v npx)"
HOME_DIR="/root"

cat >"$UNIT_PATH" <<EOF
[Unit]
Description=Remote Desktop Commander device agent for CK-NEXUS VPS
Documentation=https://github.com/desktop-commander/remote-desktop-commander
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$HOME_DIR
Environment=HOME=$HOME_DIR
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$NPX_PATH --yes $PACKAGE remote
Restart=always
RestartSec=5s
KillSignal=SIGINT
TimeoutStopSec=30s
NoNewPrivileges=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
LockPersonality=true
RestrictRealtime=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

sleep 3
printf 'service_enabled=%s\n' "$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null || true)"
printf 'service_active=%s\n' "$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || true)"
printf 'node=%s\n' "$(node --version)"
printf 'npx=%s\n' "$NPX_PATH"
printf 'desktop_commander_package=%s\n' "$PACKAGE"

if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  printf 'Recent service log follows (pairing codes/credentials must not be copied into evidence):\n' >&2
  journalctl -u "$SERVICE_NAME" -n 20 --no-pager >&2 || true
  exit 2
fi

printf 'RESULT=PASS\n'
printf 'NOTE=The agent now survives SSH/Termux disconnects and starts after reboot.\n'
