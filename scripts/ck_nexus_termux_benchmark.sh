#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

MODEL="${1:-qwen2.5:0.5b}"
ROUNDS="${ROUNDS:-5}"
PORT="${PORT:-8000}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
CK_NEXUS_URL="${CK_NEXUS_URL:-http://127.0.0.1:${PORT}/api/runs}"
PROMPT="${PROMPT:-สวัสดีครับ ช่วยสรุปข้อดีของการรัน AI บนมือถือใน 2 ประโยค}"
RESULTS="${RESULTS:-$HOME/ck_nexus_bench}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$RESULTS/$RUN_ID"
mkdir -p "$RUN_DIR"

OLLAMA_PID=""
CK_PID=""

cleanup() {
  if [ -n "$CK_PID" ]; then
    kill "$CK_PID" 2>/dev/null || true
    wait "$CK_PID" 2>/dev/null || true
  fi
  if [ -n "$OLLAMA_PID" ]; then
    kill "$OLLAMA_PID" 2>/dev/null || true
    wait "$OLLAMA_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command not found: $1" >&2
    exit 2
  }
}

require_command curl
require_command ollama
require_command python
require_command awk
require_command sort
require_command sha256sum
require_command git

if [ "$ROUNDS" -lt 3 ]; then
  echo "ROUNDS must be at least 3 for claim evidence" >&2
  exit 2
fi

if curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  echo "ollama is already running; stop it before this benchmark to keep process measurements isolated" >&2
  exit 2
fi

if curl -fsS "http://127.0.0.1:${PORT}/health/live" >/dev/null 2>&1; then
  echo "CK-NEXUS is already running on port ${PORT}; stop it before this benchmark" >&2
  exit 2
fi

process_rss_kib() {
  local pid="$1"
  awk '/^VmRSS:/{print $2; found=1} END{if(!found) print 0}' "/proc/$pid/status" 2>/dev/null || echo 0
}

ollama_rss_kib() {
  ps -eo rss,args 2>/dev/null | awk '
    BEGIN { total=0 }
    tolower($0) ~ /ollama/ && $0 !~ /awk/ { total += $1 }
    END { print total+0 }
  '
}

system_mem_used_mib() {
  awk '
    /^MemTotal:/ { total=$2 }
    /^MemAvailable:/ { available=$2 }
    END { if (total > 0) printf "%.2f", (total-available)/1024; else print "0" }
  ' /proc/meminfo
}

mem_total_kib() {
  awk '/^MemTotal:/{print $2; exit}' /proc/meminfo
}

android_property() {
  local key="$1"
  if command -v getprop >/dev/null 2>&1; then
    getprop "$key" 2>/dev/null || true
  fi
}

wait_http() {
  local url="$1"
  local attempts="${2:-30}"
  local i
  for i in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

latency_stats() {
  local file="$1"
  local avg median count worst
  count="$(wc -l < "$file" | tr -d ' ')"
  avg="$(awk '{sum+=$1} END {if(NR) printf "%.2f", sum/NR; else print "0"}' "$file")"
  median="$(sort -n "$file" | awk '
    { values[NR]=$1 }
    END {
      if (NR == 0) { print "0"; exit }
      if (NR % 2 == 1) { printf "%.2f", values[(NR+1)/2] }
      else { printf "%.2f", (values[NR/2] + values[NR/2+1]) / 2 }
    }
  ')"
  worst="$(sort -n "$file" | tail -n 1)"
  printf '%s,%s,%s,%s\n' "$count" "$avg" "$median" "$worst"
}

http_post_timed() {
  local url="$1"
  local payload_file="$2"
  local output_file="$3"
  local timing_file="$4"
  local status
  status="$(curl -sS -o "$output_file" -w '%{http_code} %{time_total}' \
    -H 'Content-Type: application/json' \
    --data-binary "@$payload_file" \
    "$url")"
  printf '%s\n' "$status" > "$timing_file"
  case "$status" in
    2??\ *) return 0 ;;
    *)
      echo "request failed: $url status=$status" >&2
      cat "$output_file" >&2 || true
      return 1
      ;;
  esac
}

SUBJECT_COMMIT="$(git rev-parse HEAD)"
MEM_TOTAL_KIB="$(mem_total_kib)"
ANDROID_RELEASE="$(android_property ro.build.version.release)"
ANDROID_SDK="$(android_property ro.build.version.sdk)"
DEVICE_MODEL="$(android_property ro.product.model)"
DEVICE_MANUFACTURER="$(android_property ro.product.manufacturer)"

printf '%s\n' "CK-NEXUS Termux benchmark" > "$RUN_DIR/README.txt"
printf 'run_id=%s\nmodel=%s\nrounds=%s\nport=%s\nsubject_commit=%s\n' \
  "$RUN_ID" "$MODEL" "$ROUNDS" "$PORT" "$SUBJECT_COMMIT" >> "$RUN_DIR/README.txt"
uname -a > "$RUN_DIR/uname.txt"
cat /proc/meminfo > "$RUN_DIR/meminfo_before.txt"
python --version > "$RUN_DIR/python_version.txt" 2>&1
ollama --version > "$RUN_DIR/ollama_version.txt" 2>&1 || true

echo "stage=baseline"
BASELINE_SYSTEM_USED_MIB="$(system_mem_used_mib)"
echo "baseline_system_used_mib=$BASELINE_SYSTEM_USED_MIB"

echo "stage=ollama_start"
ollama serve > "$RUN_DIR/ollama_serve.log" 2>&1 &
OLLAMA_PID=$!
wait_http "$OLLAMA_URL/api/tags" 30 || {
  echo "ollama did not become ready" >&2
  exit 1
}

ollama pull "$MODEL" > "$RUN_DIR/ollama_pull.log" 2>&1
python - "$MODEL" "$PROMPT" > "$RUN_DIR/ollama_payload.json" <<'PY'
import json
import sys
model, prompt = sys.argv[1], sys.argv[2]
print(json.dumps({"model": model, "prompt": prompt, "stream": False}, ensure_ascii=False))
PY

http_post_timed "$OLLAMA_URL/api/generate" "$RUN_DIR/ollama_payload.json" \
  "$RUN_DIR/ollama_warmup.json" "$RUN_DIR/ollama_warmup_timing.txt"
sleep 2

OLLAMA_ONLY_RSS_KIB="$(ollama_rss_kib)"
OLLAMA_ONLY_SYSTEM_USED_MIB="$(system_mem_used_mib)"
echo "ollama_only_rss_kib=$OLLAMA_ONLY_RSS_KIB"

: > "$RUN_DIR/ollama_latency_ms.txt"
i=1
while [ "$i" -le "$ROUNDS" ]; do
  http_post_timed "$OLLAMA_URL/api/generate" "$RUN_DIR/ollama_payload.json" \
    "$RUN_DIR/ollama_round_${i}.json" "$RUN_DIR/ollama_round_${i}_timing.txt"
  awk '{printf "%.3f\n", $2*1000}' "$RUN_DIR/ollama_round_${i}_timing.txt" >> "$RUN_DIR/ollama_latency_ms.txt"
  i=$((i+1))
done

IFS=',' read -r OLLAMA_COUNT OLLAMA_AVG_MS OLLAMA_MEDIAN_MS OLLAMA_WORST_MS <<EOF
$(latency_stats "$RUN_DIR/ollama_latency_ms.txt")
EOF

echo "stage=ck_nexus_start"
export CKNEXUS_OLLAMA_ENABLED=true
export OLLAMA_BASE_URL="$OLLAMA_URL"
export OLLAMA_MODEL="$MODEL"
export CKNEXUS_PROVIDER_LOCAL_FIRST=true
export CKNEXUS_PROVIDER_ALLOW_CLOUD=false
export CKNEXUS_MOCK_AI=false
export CKNEXUS_ACCESS_TOKEN=""
export CKNEXUS_DATABASE_PATH="$RUN_DIR/cknexus.db"
export CKNEXUS_RUNTIME_BINDING_ENABLED=false
export CKNEXUS_CONNECTOR_FABRIC_ENABLED=false
export CKNEXUS_EMAIL_GATEWAY_ENABLED=false
export PORT

python main.py > "$RUN_DIR/ck_nexus.log" 2>&1 &
CK_PID=$!
wait_http "http://127.0.0.1:${PORT}/health/live" 30 || {
  echo "CK-NEXUS did not become ready" >&2
  cat "$RUN_DIR/ck_nexus.log" >&2 || true
  exit 1
}

curl -fsS "http://127.0.0.1:${PORT}/api/status" > "$RUN_DIR/ck_nexus_status.json"
python - "$PROMPT" > "$RUN_DIR/ck_payload.json" <<'PY'
import json
import sys
prompt = sys.argv[1]
print(json.dumps({
    "agent_id": "content-strategist",
    "prompt": prompt,
    "session_id": "termux-benchmark",
    "audience": "ผู้ชมทั่วไป",
    "platform": "mobile",
    "tone": "เป็นธรรมชาติ",
    "language": "ไทย"
}, ensure_ascii=False))
PY

http_post_timed "$CK_NEXUS_URL" "$RUN_DIR/ck_payload.json" \
  "$RUN_DIR/ck_warmup.json" "$RUN_DIR/ck_warmup_timing.txt"
sleep 2

CK_RSS_KIB="$(process_rss_kib "$CK_PID")"
OLLAMA_WITH_CK_RSS_KIB="$(ollama_rss_kib)"
COMBINED_RSS_KIB=$((CK_RSS_KIB + OLLAMA_WITH_CK_RSS_KIB))
INCREMENTAL_COMBINED_KIB=$((COMBINED_RSS_KIB - OLLAMA_ONLY_RSS_KIB))
CK_SYSTEM_USED_MIB="$(system_mem_used_mib)"

: > "$RUN_DIR/ck_latency_ms.txt"
i=1
while [ "$i" -le "$ROUNDS" ]; do
  http_post_timed "$CK_NEXUS_URL" "$RUN_DIR/ck_payload.json" \
    "$RUN_DIR/ck_round_${i}.json" "$RUN_DIR/ck_round_${i}_timing.txt"
  awk '{printf "%.3f\n", $2*1000}' "$RUN_DIR/ck_round_${i}_timing.txt" >> "$RUN_DIR/ck_latency_ms.txt"
  i=$((i+1))
done

IFS=',' read -r CK_COUNT CK_AVG_MS CK_MEDIAN_MS CK_WORST_MS <<EOF
$(latency_stats "$RUN_DIR/ck_latency_ms.txt")
EOF

LATENCY_OVERHEAD_AVG_MS="$(awk -v ck="$CK_AVG_MS" -v ol="$OLLAMA_AVG_MS" 'BEGIN {printf "%.2f", ck-ol}')"

cat /proc/meminfo > "$RUN_DIR/meminfo_after.txt"

python - "$RUN_DIR/summary.json" <<PY
import json
from pathlib import Path

summary = {
    "schema": "ck-nexus.termux-benchmark.v2",
    "claim_id": "CLAIM-MOBILE-001",
    "claim_status": "MEASURED_NOT_VERIFIED",
    "run_id": "$RUN_ID",
    "subject_commit": "$SUBJECT_COMMIT",
    "model": "$MODEL",
    "rounds": int("$ROUNDS"),
    "device": {
        "mem_total_kib": int("$MEM_TOTAL_KIB"),
        "android_release": "$ANDROID_RELEASE",
        "android_sdk": "$ANDROID_SDK",
        "manufacturer": "$DEVICE_MANUFACTURER",
        "model": "$DEVICE_MODEL",
    },
    "endpoints": {
        "ollama": "$OLLAMA_URL/api/generate",
        "ck_nexus": "$CK_NEXUS_URL",
    },
    "layers_completed": ["local_api", "integrated_local_provider"],
    "memory": {
        "baseline_system_used_mib": float("$BASELINE_SYSTEM_USED_MIB"),
        "ollama_only_rss_kib": int("$OLLAMA_ONLY_RSS_KIB"),
        "ollama_only_system_used_mib": float("$OLLAMA_ONLY_SYSTEM_USED_MIB"),
        "ck_nexus_process_rss_kib": int("$CK_RSS_KIB"),
        "ollama_with_ck_rss_kib": int("$OLLAMA_WITH_CK_RSS_KIB"),
        "combined_rss_kib": int("$COMBINED_RSS_KIB"),
        "incremental_combined_rss_kib": int("$INCREMENTAL_COMBINED_KIB"),
        "ck_stage_system_used_mib": float("$CK_SYSTEM_USED_MIB"),
    },
    "latency_ms": {
        "ollama_direct_average": float("$OLLAMA_AVG_MS"),
        "ollama_direct_median": float("$OLLAMA_MEDIAN_MS"),
        "ollama_direct_worst_case": float("$OLLAMA_WORST_MS"),
        "ck_nexus_average": float("$CK_AVG_MS"),
        "ck_nexus_median": float("$CK_MEDIAN_MS"),
        "ck_nexus_worst_case": float("$CK_WORST_MS"),
        "average_overhead": float("$LATENCY_OVERHEAD_AVG_MS"),
    },
    "measurement_method": "Visible process VmRSS plus /proc/meminfo system memory; latency from curl time_total after warm-up.",
    "limitations": [
        "Process RSS is not Android PSS and must not be presented as full-device memory consumption.",
        "Ollama RSS is summed from visible processes whose command contains ollama.",
        "The CK-NEXUS process RSS excludes Ollama model-process memory.",
        "Termux and Android may restrict visibility of process metrics under /proc.",
        "A single device run cannot establish performance for all Android 4 GB devices.",
        "This run does not by itself prove network-off offline behavior.",
        "Promotion to VERIFIED requires independent review and any additional protocol layers required by the claim scope.",
    ],
}
Path("$RUN_DIR/summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

(
  cd "$RUN_DIR"
  sha256sum summary.json uname.txt meminfo_before.txt meminfo_after.txt \
    ollama_latency_ms.txt ck_latency_ms.txt ck_nexus_status.json > SHA256SUMS
)

echo "stage=summary"
cat "$RUN_DIR/summary.json"
echo "evidence_dir=$RUN_DIR"
echo "summary_sha256=$(sha256sum "$RUN_DIR/summary.json" | awk '{print $1}')"
