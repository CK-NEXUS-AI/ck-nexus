#!/data/data/com.termux/files/usr/bin/bash
set -u -o pipefail

EXPECTED_HEAD="d7af1ade0df944ed3843781a13f598fe06528695"
CONTAINER="ck-nexus-debian12"
STAMP="$(date +%Y%m%d-%H%M%S)"

SRC="$(find "$HOME" -maxdepth 3 -type d -path "$HOME/ck-nexus-canonical-r28-*/source" 2>/dev/null | sort | tail -1)"
if [ -z "$SRC" ] || [ ! -d "$SRC/.git" ]; then
  echo "CANONICAL_SOURCE=NOT_FOUND"
  exit 1
fi

HEAD="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || true)"
echo "CANONICAL_SOURCE=$SRC"
echo "CANONICAL_HEAD=$HEAD"
if [ "$HEAD" != "$EXPECTED_HEAD" ]; then
  echo "CANONICAL_IDENTITY=FAIL"
  exit 1
fi
echo "CANONICAL_IDENTITY=PASS"

WORK="$HOME/ck-nexus-linux-verify-$STAMP"
EVIDENCE="$HOME/ck-nexus-linux-evidence-$STAMP"
RUNNER="$HOME/ck-nexus-linux-inner-$STAMP.sh"
mkdir -p "$WORK" "$EVIDENCE"

# Fresh copy without the Android virtualenv. Preserve the refreshed candidate uv.lock.
(
  cd "$SRC" || exit 1
  tar --exclude='./.venv' --exclude='./.pytest_cache' --exclude='./.ruff_cache' -cf - .
) | (
  cd "$WORK" || exit 1
  tar -xf -
)

COPY_HEAD="$(git -C "$WORK" rev-parse HEAD 2>/dev/null || true)"
if [ "$COPY_HEAD" != "$EXPECTED_HEAD" ]; then
  echo "VERIFY_COPY_IDENTITY=FAIL"
  exit 1
fi
echo "VERIFY_COPY_IDENTITY=PASS"

pkg install -y proot-distro git coreutils tar >/dev/null 2>&1 || {
  echo "PROOT_DISTRO_TOOLCHAIN=BLOCKED"
  exit 1
}
echo "PROOT_DISTRO_TOOLCHAIN=PASS"

if proot-distro list -q 2>/dev/null | grep -Fxq "$CONTAINER"; then
  echo "DEBIAN_CONTAINER=ALREADY_PRESENT"
else
  echo "DEBIAN_CONTAINER=INSTALLING"
  if ! proot-distro install debian:12 --name "$CONTAINER" --architecture aarch64; then
    echo "DEBIAN_CONTAINER=BLOCKED"
    exit 1
  fi
  echo "DEBIAN_CONTAINER=INSTALLED"
fi

cat > "$RUNNER" <<'INNER'
#!/bin/bash
set -u -o pipefail

S(){ printf '%s\n' "$1" | tee -a /evidence/STATUS.txt; }

S "PRODUCTION_STATUS=NO-GO"
S "ENVIRONMENT=DEBIAN12_LINUX_AARCH64_PROOT"
S "SAFETY=no_push,no_repo_create,no_delete_user_data,no_deploy,no_external_message"

export DEBIAN_FRONTEND=noninteractive
export UV_INDEX_URL="https://pypi.org/simple"
export PIP_INDEX_URL="https://pypi.org/simple"
export DB_CONNECT_TIMEOUT="${DB_CONNECT_TIMEOUT:-5}"
export DB_COMMAND_TIMEOUT="${DB_COMMAND_TIMEOUT:-10}"
export DB_POOL_ACQUIRE_TIMEOUT="${DB_POOL_ACQUIRE_TIMEOUT:-5}"
export REDIS_CONNECT_TIMEOUT="${REDIS_CONNECT_TIMEOUT:-5}"
export REDIS_SOCKET_TIMEOUT="${REDIS_SOCKET_TIMEOUT:-5}"

apt-get update > /evidence/apt-update.txt 2>&1 || {
  S "APT_UPDATE=BLOCKED"
  tail -40 /evidence/apt-update.txt
  exit 1
}
S "APT_UPDATE=PASS"

apt-get install -y \
  python3 python3-venv python3-pip git ca-certificates \
  build-essential pkg-config libpq-dev \
  postgresql postgresql-client redis-server \
  > /evidence/apt-install.txt 2>&1 || {
    S "LINUX_TOOLCHAIN=BLOCKED"
    tail -50 /evidence/apt-install.txt
    exit 1
  }
S "LINUX_TOOLCHAIN=PASS"

python3 -m venv /opt/cknexus-tools >/dev/null 2>&1 || true
/opt/cknexus-tools/bin/pip install -U pip uv > /evidence/uv-install.txt 2>&1 || {
  S "UV_INSTALL=BLOCKED"
  tail -40 /evidence/uv-install.txt
  exit 1
}
UV=/opt/cknexus-tools/bin/uv
"$UV" --version | tee /evidence/uv-version.txt
S "UV_INSTALL=PASS"

cd /workspace || exit 1

HEAD="$(git rev-parse HEAD 2>/dev/null || true)"
printf 'HEAD=%s\n' "$HEAD" > /evidence/source-head.txt
if [ "$HEAD" != "d7af1ade0df944ed3843781a13f598fe06528695" ]; then
  S "SOURCE_IDENTITY=FAIL"
  exit 1
fi
S "SOURCE_IDENTITY=PASS"

sha256sum pyproject.toml uv.lock > /evidence/dependency-before.sha256

if "$UV" lock --refresh > /evidence/uv-lock-refresh.txt 2>&1; then
  S "UV_LOCK_REFRESH=PASS"
else
  S "UV_LOCK_REFRESH=BLOCKED_OR_FAIL"
  tail -60 /evidence/uv-lock-refresh.txt
  exit 1
fi

if "$UV" lock --check > /evidence/uv-lock-check.txt 2>&1; then
  S "UV_LOCK_CHECK=PASS"
else
  S "UV_LOCK_CHECK=FAIL_CLOSED"
  tail -60 /evidence/uv-lock-check.txt
  exit 1
fi

python3 - <<'PY' > /evidence/required-packages.txt
from pathlib import Path
import tomllib
required={"asyncpg","psycopg","redis","aiosqlite"}
data=tomllib.loads(Path("uv.lock").read_text())
present={str(x.get("name","")).lower() for x in data.get("package",[])}
missing=sorted(required-present)
print("missing=" + (",".join(missing) if missing else "none"))
raise SystemExit(1 if missing else 0)
PY
PKG_RC=$?
cat /evidence/required-packages.txt
if [ "$PKG_RC" -eq 0 ]; then
  S "REQUIRED_LOCK_PACKAGES=PASS"
else
  S "REQUIRED_LOCK_PACKAGES=FAIL_CLOSED"
  exit 1
fi

if "$UV" sync --all-extras --dev --frozen > /evidence/uv-sync.txt 2>&1; then
  S "UV_FROZEN_SYNC=PASS"
else
  S "UV_FROZEN_SYNC=BLOCKED_OR_FAIL"
  tail -70 /evidence/uv-sync.txt
  exit 1
fi

if "$UV" run --frozen python - <<'PY' > /evidence/imports.txt 2>&1
import asyncpg, psycopg, redis, aiosqlite
print("asyncpg", asyncpg.__version__)
print("psycopg", psycopg.__version__)
print("redis", redis.__version__)
PY
then
  cat /evidence/imports.txt
  S "DEPENDENCY_IMPORTS=PASS"
else
  cat /evidence/imports.txt
  S "DEPENDENCY_IMPORTS=FAIL_CLOSED"
  exit 1
fi

DEP_FAIL=0
for gate in scripts/gate_lock_consistency.py scripts/gate_dependency_closure.py scripts/gate_trusted_toolchain.py; do
  name="$(basename "$gate" .py)"
  if [ ! -f "$gate" ]; then
    S "$name=NOT_PRESENT"
    DEP_FAIL=1
    continue
  fi
  if "$UV" run --frozen python "$gate" > "/evidence/$name.txt" 2>&1; then
    S "$name=PASS"
  else
    S "$name=FAIL_CLOSED"
    tail -35 "/evidence/$name.txt"
    DEP_FAIL=1
  fi
done

if [ "$DEP_FAIL" -eq 0 ]; then
  S "DEPENDENCY_CLOSURE=PASS_LINUX_CANDIDATE"
else
  S "DEPENDENCY_CLOSURE=FAIL_CLOSED"
  exit 1
fi

# Focused regression around dependency/runtime binding behavior.
if "$UV" run --frozen pytest -q \
  tests/test_dependency_closure_gate.py \
  tests/test_trusted_toolchain_gate.py \
  tests/test_r26_runtime_binding.py \
  > /evidence/focused-tests.txt 2>&1; then
  S "FOCUSED_DEPENDENCY_RUNTIME_TESTS=PASS"
else
  S "FOCUSED_DEPENDENCY_RUNTIME_TESTS=FAIL"
  tail -60 /evidence/focused-tests.txt
  exit 1
fi

# ---------- Local ephemeral PostgreSQL + Redis binding ----------
PGVER="$(find /usr/lib/postgresql -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -1)"
PGBIN="/usr/lib/postgresql/$PGVER/bin"
PGDATA="/tmp/cknexus-pgdata-$$"
PGPORT=55432
REDIS_PORT=56379
REDIS_PID="/tmp/cknexus-redis-$$.pid"

cleanup(){
  redis-cli -p "$REDIS_PORT" shutdown nosave >/dev/null 2>&1 || true
  if [ -n "${PGBIN:-}" ] && [ -d "${PGDATA:-/nonexistent}" ]; then
    runuser -u postgres -- "$PGBIN/pg_ctl" -D "$PGDATA" -m fast -w stop >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

install -d -o postgres -g postgres "$PGDATA"
if ! runuser -u postgres -- "$PGBIN/initdb" -D "$PGDATA" --auth-local=trust --auth-host=trust \
     > /evidence/postgres-initdb.txt 2>&1; then
  S "POSTGRES_LOCAL_INIT=BLOCKED"
  tail -50 /evidence/postgres-initdb.txt
  exit 1
fi
S "POSTGRES_LOCAL_INIT=PASS"

if ! runuser -u postgres -- "$PGBIN/pg_ctl" -D "$PGDATA" \
     -o "-h 127.0.0.1 -p $PGPORT" -w start \
     > /evidence/postgres-start.txt 2>&1; then
  S "POSTGRES_LOCAL_START=BLOCKED"
  tail -50 /evidence/postgres-start.txt
  exit 1
fi
S "POSTGRES_LOCAL_START=PASS"

if ! "$PGBIN/psql" -h 127.0.0.1 -p "$PGPORT" -U postgres -d postgres -v ON_ERROR_STOP=1 \
     > /evidence/postgres-bootstrap.txt 2>&1 <<'SQL'
CREATE ROLE cknexus LOGIN;
CREATE DATABASE cknexus OWNER cknexus;
SQL
then
  S "POSTGRES_LOCAL_BOOTSTRAP=FAIL"
  tail -50 /evidence/postgres-bootstrap.txt
  exit 1
fi
S "POSTGRES_LOCAL_BOOTSTRAP=PASS"

if ! redis-server \
     --port "$REDIS_PORT" \
     --bind 127.0.0.1 \
     --protected-mode yes \
     --save "" \
     --appendonly no \
     --daemonize yes \
     --pidfile "$REDIS_PID" \
     --dir /tmp \
     > /evidence/redis-start.txt 2>&1; then
  S "REDIS_LOCAL_START=BLOCKED"
  cat /evidence/redis-start.txt
  exit 1
fi

if redis-cli -h 127.0.0.1 -p "$REDIS_PORT" ping | grep -q '^PONG$'; then
  S "REDIS_LOCAL_START=PASS"
else
  S "REDIS_LOCAL_START=FAIL"
  exit 1
fi

export DATABASE_URL="postgresql://cknexus@127.0.0.1:${PGPORT}/cknexus"
export REDIS_URL="redis://127.0.0.1:${REDIS_PORT}/0"
export DB_POOL_MIN=1
export DB_POOL_MAX=3
export REDIS_SOCKET_TIMEOUT=3
export REDIS_MAX_CONNECTIONS=5
export RUNTIME_BINDING_FAIL_FAST=true

if "$UV" run --frozen python creator_app/runtime_binding.py --verify \
   > /evidence/runtime-binding.txt 2>&1; then
  cat /evidence/runtime-binding.txt
  S "POSTGRES_REDIS_APPLICATION_BINDING=PASS_LOCAL_LINUX"
else
  cat /evidence/runtime-binding.txt
  S "POSTGRES_REDIS_APPLICATION_BINDING=FAIL_CLOSED"
  exit 1
fi

# Static deployment checks are evidence only; they are not staging/TLS proof.
if "$UV" run --frozen python scripts/gate_r26_runtime_tls.py > /evidence/r26-static-gate.txt 2>&1; then
  S "R26_RUNTIME_TLS_STATIC_GATE=PASS"
else
  S "R26_RUNTIME_TLS_STATIC_GATE=FAIL"
fi

# Detect known production hardening gaps in the recovered canonical R28 source.
HARDEN_FAIL=0
if grep -q 'COPY gateway ./gateway' Dockerfile && \
   grep -q 'COPY orchestration ./orchestration' Dockerfile && \
   grep -q 'COPY idea_engine ./idea_engine' Dockerfile; then
  S "DOCKER_PACKAGE_INCLUSION=PASS"
else
  S "DOCKER_PACKAGE_INCLUSION=FAIL_CANDIDATE_PATCH_REQUIRED"
  HARDEN_FAIL=1
fi

if grep -q '/health/ready' docker-compose.prod.yml; then
  S "COMPOSE_READINESS_ENDPOINT=PASS"
else
  S "COMPOSE_READINESS_ENDPOINT=FAIL_CANDIDATE_PATCH_REQUIRED"
  HARDEN_FAIL=1
fi

if grep -q 'DB_CONNECT_TIMEOUT' creator_app/runtime_binding.py && \
   grep -q 'REDIS_CONNECT_TIMEOUT' creator_app/runtime_binding.py && \
   grep -q 'DB_POOL_ACQUIRE_TIMEOUT' creator_app/runtime_binding.py && \
   grep -q 'DB_COMMAND_TIMEOUT' creator_app/runtime_binding.py; then
  S "RUNTIME_CONNECT_TIMEOUTS=PASS"
else
  S "RUNTIME_CONNECT_TIMEOUTS=FAIL_CANDIDATE_PATCH_REQUIRED"
  HARDEN_FAIL=1
fi

sha256sum pyproject.toml uv.lock > /evidence/dependency-after.sha256
git diff --check > /evidence/git-diff-check.txt 2>&1
GIT_DIFF_RC=$?
git diff -- uv.lock > /evidence/uv-lock-linux-candidate.diff 2>/dev/null || true
[ "$GIT_DIFF_RC" -eq 0 ] && S "GIT_DIFF_CHECK=PASS" || S "GIT_DIFF_CHECK=FAIL"

if [ "$HARDEN_FAIL" -eq 0 ]; then
  S "DEPLOYMENT_HARDENING_STATIC=PASS"
else
  S "DEPLOYMENT_HARDENING_STATIC=FAIL_CANDIDATE_PATCH_REQUIRED"
fi

S "GITHUB_REMOTE_SOURCE_AUTHORITY=BLOCKED_REPOSITORY_NOT_CREATED"
S "GITHUB_PUSH=NOT_PERFORMED"
S "POSTGRES_REDIS_STAGING=NOT_VERIFIED"
S "TLS_STAGING=NOT_VERIFIED"
S "CLEAN_MACHINE_DEPLOYMENT=NOT_VERIFIED"
S "SECURITY_RECOVERY_STAGING=NOT_VERIFIED"
S "COMMERCIAL_READINESS=NO-GO"
S "PRODUCTION_STATUS=NO-GO"

echo "========================================"
cat /evidence/STATUS.txt
echo "========================================"
INNER
chmod 700 "$RUNNER"

proot-distro login \
  --bind "$WORK:/workspace" \
  --bind "$EVIDENCE:/evidence" \
  --bind "$RUNNER:/runner.sh" \
  --work-dir /workspace \
  "$CONTAINER" -- bash /runner.sh
RC=$?

ARCHIVE="$HOME/storage/downloads/CK-NEXUS-R33-LINUX-RUNTIME-EVIDENCE-$STAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$EVIDENCE" . 2>/dev/null || true
if [ -f "$ARCHIVE" ]; then
  sha256sum "$ARCHIVE" | tee "$EVIDENCE/evidence-archive.sha256"
  echo "EVIDENCE_ARCHIVE=$ARCHIVE"
fi

echo "LINUX_VERIFY_SOURCE=$WORK"
echo "EVIDENCE_DIR=$EVIDENCE"
echo "NO GITHUB CREATE/PUSH, NO USER-DATA DELETE, NO PRODUCTION DEPLOY"
exit "$RC"
