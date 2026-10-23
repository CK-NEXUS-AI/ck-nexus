#!/usr/bin/env bash
set -u
cd /root/ck-nexus || exit 1
PY=/opt/pyvenv/bin/python
exec > >(tee /root/ck-next-$(date +%Y%m%d-%H%M).log) 2>&1

echo "=== 0) กันพลาด ==="
git branch -f backup/pre-push-$(date +%Y%m%d) HEAD
git status -sb | head -3
$PY -c "import creator_app; print('editable ->', creator_app.__file__)"
git diff origin/main HEAD --stat -- scripts/n8n_evidence_export.py | tail -1 || true

echo; echo "=== 1) dependency ของ JWKS/OMNI ==="
for m in jwt cryptography httpx; do
  if $PY -c "import $m" 2>/dev/null; then echo "ok   $m"; else echo "MISSING $m"; fi
done

echo; echo "=== 2) สาเหตุที่เทสต์ล้ม (ดู error แรก) ==="
$PY -m pytest -x -q --tb=short -p no:cacheprovider \
  tests/test_device_bridge_jwt_jwks_verifier.py 2>&1 | tail -30
$PY -m pytest -x -q --tb=short -p no:cacheprovider \
  tests/test_omni_runtime_production_gate.py \
  tests/test_agnes_execution_kernel_phase2.py::test_runtime_fails_closed_without_omni_context_factory 2>&1 | tail -30

echo; echo "=== 3) เทียบกับ origin/main ==="
$PY -m pytest -q -p no:cacheprovider 2>&1 | grep -E '^FAILED|passed|failed' | sort > /tmp/mine.txt
tail -1 /tmp/mine.txt
if [ -s /tmp/base.txt ]; then
  comm -13 <(grep ^FAILED /tmp/base.txt) <(grep ^FAILED /tmp/mine.txt) > /tmp/new-fail.txt
  echo "เทสต์ที่ล้มใหม่: $(wc -l < /tmp/new-fail.txt)"; head -20 /tmp/new-fail.txt
else
  echo "ไม่มี /tmp/base.txt → ไม่ push"; exit 1
fi

echo; echo "=== 4) push (เป็น branch เท่านั้น ไม่แตะ main) ==="
if [ ! -s /tmp/new-fail.txt ]; then
  git push -u origin HEAD:refs/heads/feat/control-plane \
    && echo "ไปเปิด PR: https://github.com/CK-NEXUS-AI/ck-nexus/compare/feat/control-plane"
else
  echo "!! ยังมีเทสต์ล้มใหม่ → ไม่ push ส่งผลข้อ 2 มาให้ดู"
fi

echo; echo "=== 5) rclone (ทำท้ายสุด) ==="
command -v rclone >/dev/null || curl -fsSL https://rclone.org/install.sh | bash
rclone version | head -1
cat <<'TXT'
ขั้นต่อไป (ทำเอง ต้องใช้เบราว์เซอร์):
 1. เครื่องคุณ:  ssh -L 53682:localhost:53682 root@162.35.28.151
 2. ใน session นั้น:  rclone authorize "onedrive"
 3. เปิดลิงก์ที่ได้ในเบราว์เซอร์เครื่องคุณ แล้วเอา token ไปใส่ rclone config
 4. mount ด้วย: --vfs-cache-mode writes --buffer-size 8M (RAM เหลือน้อย)
TXT
df -h / | tail -1; free -h | head -2
