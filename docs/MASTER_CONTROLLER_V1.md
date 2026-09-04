# CK-NEXUS Master Controller V1

Status: DEVELOPMENT / IMPLEMENTED_NOT_VERIFIED

## Purpose

Provide one small planning layer over existing CK-NEXUS capabilities instead of
building a second control plane.

The controller reuses:

- Unified Control Surface
- AGNES planning and policy
- GitHub source/PR/CI workflows
- VPS and Docker execution lane
- Web research
- File/content research
- Gmail reviewer intake
- Evidence generation

## Command

After installation:

```text
ck-nexus-control
```

defaults to the logical command:

```text
CK-NEXUS RUN
```

A specific request can be planned with:

```text
ck-nexus-control ตรวจสอบ Q10 บน VPS
```

The command prints a deterministic JSON plan. V1 is planner-only; it does not
perform external side effects.

## Routing lanes

- `github`
- `vps_docker`
- `web_research`
- `file_content`
- `gmail`
- `agnes`
- `evidence`

Every plan includes the Evidence lane.

## Safety

- unavailable required lanes block automatic execution;
- external-write and Production-class intents require a human gate;
- `production_effect` is always false in V1;
- Q10/Q11/Q12 authority is unchanged;
- no merge, deployment, payment, credential exposure, or self-approval is added.

## Completion criteria

V1 development implementation is complete when:

1. planner and CLI exist;
2. routing and fail-closed tests pass;
3. CK-NEXUS CI passes on the exact head;
4. Security Attack Regression passes on the exact head;
5. PR is ready for independent review.

Independent review and canonical adoption remain separate gates.
