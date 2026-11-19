#!/usr/bin/env bash
R=/root/ck-nexus
mask() { sed -E 's#(https?://)[^/@ ]+@#\1***@#g; s#(gh[pousr]_|github_pat_)[A-Za-z0-9_]+#\1***#g'; }

echo "=== 1) Git repo ==="
git -C $R remote -v | mask
git -C $R branch -vv | head -5 | mask
git -C $R fetch --dry-run 2>&1 | mask | head -5
git -C $R rev-list --left-right --count origin/main...main 2>/dev/null | awk '{print "behind="$1" ahead="$2}'
echo "dirty: $(git -C $R status --porcelain | wc -l) ไฟล์"
git -C $R stash list | head -3
git -C $R log origin/main..main --oneline | head -8

echo; echo "=== 2) GitHub auth ==="
command -v gh >/dev/null && gh auth status 2>&1 | mask || echo "ไม่มี gh CLI"
git config --global --get credential.helper
ls -l ~/.git-credentials ~/.config/gh/hosts.yml 2>/dev/null | awk '{print $1,$3,$9}'
ls -l ~/.ssh/*.pub 2>/dev/null | awk '{print $9}'

echo; echo "=== 3) Actions runner ==="
systemctl is-active actions.runner.spinlnw10-art-ck-nexus.cknexus-q12.service
journalctl -u actions.runner.spinlnw10-art-ck-nexus.cknexus-q12.service -n 8 --no-pager | cut -c1-140 | mask
du -sh /opt/actions-runner/_work 2>/dev/null

echo; echo "=== 4) ความเสี่ยง secret ก่อน push ==="
cd $R
git ls-files -o -m --exclude-standard | grep -Ei '\.env$|\.pem$|\.key$|secret|credential|token' | head
git ls-files -o -m --exclude-standard -z | xargs -0 grep -IlE 'sk-[A-Za-z0-9._-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|LTAI[A-Za-z0-9]{12,}' 2>/dev/null | head
echo "--- .gitignore ครอบ .env/evidence? ---"
git check-ignore -v .env evidence/ 2>&1 | head -3

echo; echo "=== 5) สคริปต์ที่ใช้ GitHub ==="
grep -nE 'GITHUB_TOKEN|GH_TOKEN|ghp_|github_pat_' /root/github-manager.sh 2>/dev/null | mask | head -5
