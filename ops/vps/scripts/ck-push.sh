#!/usr/bin/env bash
set -u
cd /root/ck-nexus || exit 1

echo "=== 1) สถานะ ==="
git status -sb | head -5
git log --oneline -3

echo; echo "=== 2) ตรวจ secret ใน commit ที่จะ push (แสดงแค่ชื่อไฟล์) ==="
git diff origin/main..HEAD -U0 | grep -E '^\+' | grep -E 'sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|LTAI[A-Za-z0-9]{12,}|BEGIN (RSA|OPENSSH|EC) PRIVATE' \
  && { echo "!! พบ pattern คล้าย secret หยุด push"; exit 1; } || echo "สะอาด"

echo; echo "=== 3) เทสต์ ==="
if [ -f uv.lock ] || grep -q '\[tool.uv\]\|dependency-groups' pyproject.toml 2>/dev/null; then
  uv run --with pytest pytest -q -x 2>&1 | tail -15
else
  python3 -m venv /root/.venvs/ck-test 2>/dev/null
  /root/.venvs/ck-test/bin/pip install -q -e . pytest 2>&1 | tail -3
  /root/.venvs/ck-test/bin/python -m pytest -q -x 2>&1 | tail -15
fi
rc=${PIPESTATUS[0]}
echo "pytest exit=$rc"
[ "$rc" -ne 0 ] && { echo "!! เทสต์ไม่ผ่าน ไม่ push (ส่งผลมาให้ดู)"; exit 1; }

echo; echo "=== 4) push ==="
git push origin main || { echo "push ไม่ผ่าน (อาจติด branch protection) → ใช้: git switch -c feat/control-plane && git push -u origin feat/control-plane"; exit 1; }

echo; echo "=== 5) ตรวจหลัง push ==="
git status -sb | head -3
python3 /root/ck-nexus/scripts/ck-health.py 2>&1 | grep -E 'WARN|FAIL|PASS' | head -15
df -h / | tail -1
