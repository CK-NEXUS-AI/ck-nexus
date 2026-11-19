#!/usr/bin/env bash
set -euo pipefail
if [[ "${CKNEXUS_ENVIRONMENT:-}" != "staging" ]]; then
  echo '{"status":"BLOCKED","reason":"restore drill must run in isolated staging"}'
  exit 2
fi
if [[ "${CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE:-}" != "YES" ]]; then
  echo '{"status":"BLOCKED","reason":"set CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE=YES only in isolated staging"}'
  exit 2
fi
echo '{"status":"BLOCKED","reason":"Use a clean target VM/project for the destructive restore. The seller master intentionally refuses to destroy the current working environment."}'
exit 2
