#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="/data/data/com.termux/files/home/cknexus-pr365-archive-fix"
source "/data/data/com.termux/files/home/.config/agnes/providers/load_key.sh" groq
export GROQ_API_KEY="$API_KEY"
export PROVIDER=groq
export PYTHONPATH="/data/data/com.termux/files/home/.cache/cknexus-q11-python"
unset API_KEY
exec python3 "$REPO/scripts/test_openai_live.py"
