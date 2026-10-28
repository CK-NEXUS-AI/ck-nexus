#!/usr/bin/env bash
set -Eeuo pipefail

# Safe emergency stop: halt autonomous writers while preserving n8n, monitoring,
# backups, the read-only workflows UI, and task database contents.
MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--confirm" ]]; then
  echo "Usage: $0 [--dry-run|--confirm]" >&2
  exit 2
fi

UNITS=(
  cknexus-n8n-auto-developer.timer
  cknexus-n8n-auto-gitops.timer
  cknexus-n8n-auto-developer.service
  cknexus-n8n-auto-gitops.service
)

printf 'mode=%s action=stop_autonomous_writers timestamp=%s\n' "$MODE" "$(date -u +%FT%TZ)"
for unit in "${UNITS[@]}"; do
  if systemctl cat "$unit" >/dev/null 2>&1; then
    state="$(systemctl is-active "$unit" 2>/dev/null || true)"
    printf 'unit=%s state=%s planned_action=%s\n' "$unit" "${state:-unknown}" "$([[ "$MODE" == "--confirm" ]] && echo stop || echo no_change)"
    if [[ "$MODE" == "--confirm" ]]; then
      systemctl stop "$unit"
    fi
  else
    printf 'unit=%s state=not-installed planned_action=skip\n' "$unit"
  fi
done

if [[ "$MODE" == "--confirm" ]]; then
  install -d -o root -g root -m 0700 /var/log/cknexus
  printf 'timestamp=%s actor=uid:%s action=emergency_stop result=completed units=%s\n' \
    "$(date -u +%FT%TZ)" "$(id -u)" "${UNITS[*]}" >> /var/log/cknexus/emergency-stop.log
  chmod 0600 /var/log/cknexus/emergency-stop.log
  echo 'Emergency stop applied to autonomous writer services and timers.'
  echo 'Task database was not modified; n8n, UI, monitoring, and backup services were preserved.'
else
  echo 'Dry run only. Re-run with --confirm to stop the listed autonomous writer services and timers.'
fi
