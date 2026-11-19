#!/usr/bin/env bash
cd /root/ck-nexus || exit 1

# venv ใต้ /opt เพื่อให้ผ่าน sandbox guard
if [ ! -x /opt/pyvenv/bin/python ]; then
  /usr/bin/python3 -m venv /opt/pyvenv
  /opt/pyvenv/bin/pip install -q -e . pytest 2>&1 | tail -3
fi
PY=/opt/pyvenv/bin/python

echo "=== A) ของคุณ (HEAD) ==="
$PY -m pytest -q 2>&1 | grep -E '^FAILED|passed|failed' | sort > /tmp/mine.txt
tail -12 /tmp/mine.txt

echo; echo "=== B) origin/main ==="
rm -rf /tmp/ck-base; git worktree prune
git worktree add -f /tmp/ck-base origin/main >/dev/null 2>&1
( cd /tmp/ck-base && /opt/pyvenv/bin/pip install -q -e . 2>&1 | tail -1
  $PY -m pytest -q 2>&1 | grep -E '^FAILED|passed|failed' | sort > /tmp/base.txt )
tail -12 /tmp/base.txt
git worktree remove --force /tmp/ck-base

echo; echo "=== C) ล้มเฉพาะของคุณ (ใหม่) ==="
comm -13 <(grep ^FAILED /tmp/base.txt) <(grep ^FAILED /tmp/mine.txt)
echo "(ว่าง = ไม่มีเทสต์ใหม่ที่ล้ม)"
