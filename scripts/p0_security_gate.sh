#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
status=0

if command -v gitleaks >/dev/null 2>&1; then
  if gitleaks detect --source . --no-banner; then
    echo '[PASS] gitleaks'
  else
    echo '[FAIL] gitleaks'
    status=1
  fi
else
  echo '[BLOCKED] gitleaks command not installed'
  status=2
fi

python - <<'PY'
from scripts.release_check import scan_secrets
result = scan_secrets()
print(f"[{'PASS' if result.passed else 'FAIL'}] internal secret scan: {result.detail}")
raise SystemExit(0 if result.passed else 1)
PY

if python -m bandit --version >/dev/null 2>&1; then
  python -m bandit -q -r creator_app services main.py || status=1
else
  echo '[BLOCKED] bandit module not installed'
  [[ "$status" -eq 1 ]] || status=2
fi

if python -m pip_audit --version >/dev/null 2>&1; then
  python -m pip_audit || status=1
else
  echo '[BLOCKED] pip-audit module not installed'
  [[ "$status" -eq 1 ]] || status=2
fi

exit "$status"
