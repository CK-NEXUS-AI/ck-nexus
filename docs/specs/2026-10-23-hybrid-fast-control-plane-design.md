# CK-NEXUS Hybrid Fast Control Plane — Design

**Date:** 2026-10-23
**Status:** Approved by execution instruction `เริ่ม` after selecting Hybrid Fast Mode (C)

## Intent

ลด latency ของ CK-NEXUS control plane โดยให้ deterministic checks และ actions ที่ปลอดภัยทำงานก่อน AI diagnosis และใช้ parallel execution เฉพาะงานที่เป็นอิสระ โดยไม่เพิ่ม concurrency จนทำให้ VPS ที่มี RAM ~1.9 GiB เกิด memory pressure เพิ่มขึ้น

## Goals

- ลดเวลาจาก detection → verified result สำหรับ known failures
- ลดการเรียก Qwen เมื่อ rule-based diagnosis ตัดสินได้
- ทำ health/status checks ที่เป็นอิสระแบบ bounded parallelism
- มี cache เฉพาะข้อมูลที่ปลอดภัยและมี TTL ชัดเจน
- ป้องกัน retry storm และ resource exhaustion
- คง fail-closed execution, evidence และ verification boundaries
- รักษา dirty worktree และไฟล์ที่ผู้ใช้แก้ไว้เดิม

## Non-goals

- ไม่สร้าง execution engine ใหม่
- ไม่ให้ LLM สร้าง shell command แล้วนำไป execute โดยตรง
- ไม่เพิ่ม public network exposure
- ไม่แก้ Qwen credential ในงานนี้
- ไม่ start `ck-auditor` จนกว่าจะวิเคราะห์ exit 137/OOM เพิ่มเติม

## Architecture

```text
Detector
  ↓
Fast Policy / Known-Failure Rules
  ├── known + safe → deterministic ACTION_ID → verify
  └── unknown/complex → bounded AI diagnosis → policy mapping
                                      ↓
                             deterministic ACTION_ID
                                      ↓
                               health verification
                                      ↓
                         evidence / escalation
```

Parallelism applies only to independent read-only detection/health checks. Remediation remains serialized per resource and bounded by existing watchdog/action limits.

## Resource policy

- Default control-plane concurrency: 2 on this VPS class; never exceed 3 without explicit capacity evidence.
- Health probes should have short timeouts and no duplicate retries.
- Cache only read-only health/capability results; default TTL 5 seconds.
- Failed or mutating operations are not served from cache.
- Qwen is diagnosis-only; its output must map to a predefined action identifier.

## Acceptance criteria

1. Existing control-plane behavior remains green.
2. Independent health probes can execute concurrently with bounded concurrency.
3. Known failure rules bypass AI diagnosis.
4. Unknown failures fall back to diagnosis without executing model-generated shell text.
5. Cache expires correctly and never serves stale mutation results.
6. Concurrency never exceeds the configured budget.
7. No secret is included in results/evidence.
8. Existing dirty changes remain untouched.
