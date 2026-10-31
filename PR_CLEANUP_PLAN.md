# CK-NEXUS PR Cleanup Plan

สถานะจัดทำเมื่อ 2026-10-31 จาก `main` baseline `bff3ef06b6e243226c36aafb03855125b5022311` ตรวจพบ 198 open PRs โดย 172 เป็น draft แผนนี้เป็น **คำแนะนำเท่านั้น** ยังไม่มีคำสั่ง `gh pr close` หรือ `gh pr merge` ถูกเรียกใช้

## กฎก่อนดำเนินการ

1. ห้าม merge หรือ close โดยอาศัยชื่อ PR อย่างเดียว ต้องตรวจ diff กับ latest `main`, owner, dependency impact, checks และ whether another PR already contains the same change
2. ต้องหยุด autonomous timers ก่อน review queue เพื่อป้องกัน PR ใหม่เข้ามาระหว่าง cleanup
3. ต้อง merge security/dependency fixes แบบทีละ PR และรัน clean CI หลังแต่ละกลุ่ม
4. PR ที่เป็น draft หรือมี production/security claim แต่ไม่มี evidence ต้องคงไว้เป็น draft หรือปิดพร้อมเหตุผล ไม่ควร merge เพื่อให้จำนวนลดลง

## Merge-first candidates — ตรวจแล้วจึง merge

- **#300** MCP 1.30.0 dependency update: `gh pr merge 300 --squash --delete-branch=false`
- **#301** certifi update: `gh pr merge 301 --squash --delete-branch=false`
- **#302** opentelemetry-api update: `gh pr merge 302 --squash --delete-branch=false`
- **#311** filelock update: `gh pr merge 311 --squash --delete-branch=false`
- **#315** secret scanner token-boundary fix: `gh pr merge 315 --squash --delete-branch=false`
- **#313** deterministic Ruff/quality fixes: `gh pr merge 313 --squash --delete-branch=false`

คำสั่งข้างต้นต้องรันหลัง `gh pr checks <number> --watch` ผ่าน, `uv lock --check` ผ่าน, `pip-audit` ไม่พบ vulnerability และ review diff โดยมนุษย์แล้วเท่านั้น หาก branch protection ถูกเปิดใช้ก่อน merge ให้ใช้ required checks ของ ruleset เป็นตัวตัดสิน ไม่ใช่ local result อย่างเดียว

## Likely duplicate or superseded auto-proactive PRs — close only after diff confirmation

PR เหล่านี้เป็น daily auto-fix task ที่เกิดจาก proactive seeder และมีรูปแบบซ้ำกัน ควรตรวจว่าไม่มี unique security fix ก่อน close:

- #306 — `gh pr close 306 --comment "Superseded by consolidated audit remediation; no unique accepted change."`
- #307 — `gh pr close 307 --comment "Superseded by consolidated audit remediation; no unique accepted change."`
- #308 — `gh pr close 308 --comment "Superseded by consolidated audit remediation; no unique accepted change."`
- #309 — `gh pr close 309 --comment "Superseded by consolidated audit remediation; no unique accepted change."`
- #310 — `gh pr close 310 --comment "Superseded by consolidated audit remediation; no unique accepted change."`
- #312 — `gh pr close 312 --comment "Superseded by consolidated audit remediation; no unique accepted change."`
- #319 — `gh pr close 319 --comment "Autonomous task held while governance and release gates are remediated."`

ห้ามปิด PR เหล่านี้เพียงเพราะเป็น auto-generated; ใช้ `gh pr diff <number>` และ `git diff main...<head>` ตรวจ unique changes ก่อนทุกครั้ง

## Defer / triage queue

PR ที่เหลือประมาณ 181 รายการยังไม่มีหลักฐานพอให้ merge หรือ close จากการตรวจรอบนี้ ให้จัดกลุ่มเป็น:

- dependency/security
- test/CI/release gate
- production evidence/governance
- feature/architecture
- documentation/research
- duplicate/abandoned

คำสั่งสร้าง inventory ล่าสุด:

```bash
gh pr list -R CK-NEXUS-AI/ck-nexus --state open --limit 500 \
  --json number,title,isDraft,headRefName,updatedAt,url \
  --jq 'sort_by(.updatedAt) | reverse'
```

คำสั่งตรวจ duplicate ที่ปลอดภัยกว่าใช้ keyword เป็นเพียง shortlist ไม่ใช่คำตัดสิน:

```bash
gh pr list -R CK-NEXUS-AI/ck-nexus --state open --limit 500 \
  --search 'auto-fix OR proactive OR Dependabot OR security OR lint' \
  --json number,title,isDraft,headRefName,url
```

## เป้าหมายหลัง cleanup

ลด open PR ให้เหลือเฉพาะงานที่มี owner, acceptance criteria, current CI evidence และ target release เดียว ปิด autonomous PR generation จนกว่า `main` มี branch protection และ release gate จะผ่านแบบทำซ้ำได้
