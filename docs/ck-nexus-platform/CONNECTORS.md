# Connector and Tool Registry

สถานะหมายถึงสิ่งที่ตรวจพบใน session/catalog ณ 2026-10-31 ไม่ใช่การรับประกันว่า account ทุกตัวพร้อมใช้งานในอนาคต

| Connector/tool | สถานะ | ใช้ทำอะไร | ระดับเริ่มต้น | ห้ามทำจนกว่าจะอนุมัติ |
|---|---|---|---|---|
| GitHub builtin | enabled | repo, branch, commit, PR, checks, evidence | read-only | merge, delete, protection mutation |
| Browser / Pinterest | available | อ่านหน้าเว็บและภาพอ้างอิง | read-only | login/post/download ที่มีสิทธิ์ภายนอก |
| ConnectorFabric MCP/OpenAPI | code-ready | discovery, schema, risk, authorization | fail-closed | active write |
| n8n / n8n API | catalog disabled/unverified | workflows/executions | read-only plan | create/run/activate |
| triggers | runtime available | event discovery, fixed trigger, execution, dry-run | inspect/dry-run | create live trigger |
| manus-tasks | runtime available | task/project handoff | current task | สร้าง task ใหม่โดยไม่ร้องขอ |
| Tailscale | catalog disabled | device/network access | diagnostics | SSH/stop/restart |
| Playwright | catalog disabled | browser test | not enabled | enable/login/side effects |
| Slack/Sentry | catalog disabled | notification/observability | not enabled | send or change incident data |
| OpenAI connector | catalog disabled | external model API | not enabled | add key or send data |

## Activation protocol

`REGISTERED -> DISCOVERED -> SCHEMA_VERIFIED -> ACTIVE_READ_ONLY -> ACTIVE_WRITE`

Write activation requires schema hash, risk review, explicit approval, credential lease, idempotency and evidence. Unknown-risk tools block write activation. Never copy secrets into this file.

## Tool routing

- Repository facts: GitHub connector/`gh`
- Public research: web search/fetch/browser
- Code changes: local isolated branch/worktree
- Execution: AGNES dispatcher only
- Workflow automation: n8n adapter only after live contract verification
- Event automation: triggers only after owner, scope, cadence, failure action and disable path are documented
