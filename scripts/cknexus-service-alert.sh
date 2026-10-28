#!/usr/bin/env bash
set -Eeuo pipefail

unit="${1:-unknown.service}"
if [[ ! "$unit" =~ ^[A-Za-z0-9_.@:-]{1,200}$ ]]; then
  unit="invalid-unit-name"
fi
now="$(date +%s)"
logdir=/var/log/cknexus
state_dir=/run/cknexus-alert
install -d -o root -g root -m 0700 "$logdir" "$state_dir"
exec 9>"$state_dir/lock"
flock -x 9
state_file="$state_dir/$(printf '%s' "$unit" | sha256sum | cut -d' ' -f1)"
last=0
if [[ -r "$state_file" ]]; then read -r last < "$state_file" || last=0; fi
if [[ "$last" =~ ^[0-9]+$ ]] && (( now - last < 300 )); then
  logger -p daemon.warning -t cknexus-alert "suppressed duplicate failure alert unit=$unit window_seconds=300"
  exit 0
fi
printf '%s\n' "$now" > "$state_file"
chmod 0600 "$state_file"
message="unit=$unit result=failed timestamp=$(date -u +%FT%TZ)"
printf '%s\n' "$message" >> "$logdir/service-alerts.log"
chmod 0600 "$logdir/service-alerts.log"
logger -p daemon.err -t cknexus-alert "$message"
# Deliberately local-only: external webhooks are not configured in this deployment.
