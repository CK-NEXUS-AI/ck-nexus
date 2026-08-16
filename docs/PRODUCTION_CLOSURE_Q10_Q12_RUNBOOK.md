# CK-NEXUS Q10-Q12 Production Closure Operator Runbook

This runbook closes the three remaining P0 production gates without weakening the frozen release contract.

## Current frozen authorities

- Repository: `spinlnw10-art/ck-nexus`
- Current production-closure head: `a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53`
- Exact runtime/security scan source: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Exact source tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Application subject: `dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec`
- Frozen runtime/deployment subject: `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`

Do not replace the exact runtime/security source with a moving branch. If any runtime path changes, freeze a new subject and regenerate affected subject-bound evidence before production promotion.

## Common fail-closed preflight

```bash
git fetch --all --tags --prune

test "$(git show -s --format=%T 39f5c1adb9d761ab418cf088ff1f051b1ca731d1)" = \
  "0525195934f703a8becf8a39f6397b2411e0bb2e"

subject=$(git ls-tree -r 39f5c1adb9d761ab418cf088ff1f051b1ca731d1 -- \
  app creator_app services gateway orchestration idea_engine migrations deploy observability \
  Dockerfile docker-compose.prod.yml main.py pyproject.toml uv.lock | sha256sum | awk '{print $1}')

test "$subject" = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
echo "FROZEN SUBJECT PASS: $subject"
```

Any failure is a hard stop.

---

## Q10 — Codex Security Deep Security Scan

Dependency auditing is already PASS, but whole-gate Q10 remains `NOT_VERIFIED`. Only the native Codex Security Deep Security Scan satisfies this gate; Bandit, secret scan, `pip-audit`, ordinary CI, or manual review are not substitutes.

### Exact target

```bash
git checkout --detach 39f5c1adb9d761ab418cf088ff1f051b1ca731d1
test "$(git rev-parse HEAD)" = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
```

Use `evidence/q10/Q10_SCAN_REQUEST_FINAL_SUBJECT.json` as the machine-readable request. Scope is repository root (`.`).

Suggested Codex task:

```text
Run the native Codex Security Deep Security Scan repository-wide on this exact checkout.
Target commit: 39f5c1adb9d761ab418cf088ff1f051b1ca731d1
Target tree: 0525195934f703a8becf8a39f6397b2411e0bb2e
Frozen runtime subject: 89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52
Scope: .
Complete repeated discovery, canonical validation, attack-path analysis, canonical draft, coverage, completion, and generated report.md.
Do not substitute Bandit, pip-audit, secret scan, manual review, or ordinary CI.
```

Q10 can become PASS only after the workbench completes and the evidence includes all required fields:

```json
{
  "gate_result": "PASS",
  "codex_security_deep_scan": "PASS",
  "production_promotion_allowed": true,
  "codex_security_scan_id": "<sealed-scan-id>",
  "codex_security_report_sha256": "<sha256>",
  "codex_security_completed_at": "<RFC3339 timestamp>",
  "codex_security_target_sha": "39f5c1adb9d761ab418cf088ff1f051b1ca731d1",
  "codex_security_target_tree_sha": "0525195934f703a8becf8a39f6397b2411e0bb2e",
  "codex_security_release_subject_manifest_sha256": "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"
}
```

Compute the generated report digest with `sha256sum /path/to/report.md`. Never invent these values. If a valid finding requires a runtime fix, stop and rebaseline the runtime subject before continuing release closure.

---

## Q11 — Live OpenAI/provider smoke

Exact verifier branch: `verify/q11-final-subject`.
Fresh blocked run: `31950795711`.
The workflow is already bound to source `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`, tree `0525195934f703a8becf8a39f6397b2411e0bb2e`, and runtime subject `89f2925c...01a52`.

Create the GitHub Actions repository secret named exactly:

```text
OPENAI_API_KEY
```

Never place the secret in a commit, issue, PR comment, logs pasted into chat, or evidence JSON. Optionally configure the Actions variable `OPENAI_SMOKE_MODEL`.

Then rerun/dispatch `Verify Q11 final release subject` on `verify/q11-final-subject`.

PASS requires:
- `scripts/test_openai_live.py` exit code `0`;
- `credential_configured: true`;
- `credential_exposed: false`;
- `sentinel_observed: true` for `CK-NEXUS-P0-SMOKE-PASS`;
- `result: PASS`;
- `production_promotion_allowed: true`.

After PASS, use the generated artifact ID, server-side `sha256:` digest, run ID and exact subject when updating `evidence/Q11_OPENAI_LIVE.json`. Never edit a BLOCKED artifact into PASS.

---

## Q12 — delegated cgroup v2 on real Linux staging

Exact verifier branch: `verify/q12-final-subject`.
The real enforcement workflow is already `workflow_dispatch` only and uses:

```yaml
runs-on: [self-hosted, linux, cknexus-q12]
```

A separate hosted workflow may record a BLOCKED state, but it is not Q12 enforcement evidence.

### Required runner properties

- Linux with unified cgroup v2;
- runner/service identity is non-root;
- a real delegated writable cgroup subtree exists;
- `cpu`, `memory`, and `pids` are available in that subtree;
- repository Actions variable `CKNEXUS_AGNES_CGROUP_ROOT` points to that exact subtree;
- never use `/sys/fs/cgroup` itself as a fake delegation boundary and never use `chmod 777`.

A systemd deployment may use a service identity and controller delegation such as:

```ini
[Service]
User=cknexus
Group=cknexus
Delegate=cpu memory pids
```

The unit layout is host-specific. Verify as the actual runner/service identity:

```bash
test "$(id -u)" -ne 0
test -n "$CKNEXUS_AGNES_CGROUP_ROOT"
test "$CKNEXUS_AGNES_CGROUP_ROOT" != "/sys/fs/cgroup"
test -w "$CKNEXUS_AGNES_CGROUP_ROOT"
for c in cpu memory pids; do
  grep -qw "$c" "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.controllers" || exit 1
done
```

Then manually dispatch `.github/workflows/verify-q12-final-subject.yml` on branch `verify/q12-final-subject`.

The exact gate must observe:
- `cpu.max = 20000 100000`;
- `memory.max = 67108864`;
- `pids.max = 16`;
- child PID attached to the child `cgroup.procs`;
- raw gate status `PASS`;
- `actual_kernel_enforcement: true`;
- `production_promotion_allowed: true`.

After success, commit only normalized evidence generated from that exact self-hosted run with its artifact ID/digest and run ID.

---

## Final convergence

After legitimate Q10 + Q11 + Q12 PASS evidence is committed, run provenance against the current frozen subject:

```bash
GITHUB_REPOSITORY=spinlnw10-art/ck-nexus \
GITHUB_TOKEN="$GITHUB_TOKEN" \
python .github/release-tools/verify_release_evidence_provenance.py \
  --expected-subject 89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52 \
  --output release-evidence-provenance.json
```

Only provenance PASS authorizes the next step. Run `Final production package`; Production remains NO-GO until that workflow creates the checksummed production artifact and PR #14 is reviewed for merge.

Current reference preflight run `31951370404` is intentionally ineligible for exactly Q10, Q11 and Q12, with provenance 8/8 PASS and the package job skipped fail-closed.
