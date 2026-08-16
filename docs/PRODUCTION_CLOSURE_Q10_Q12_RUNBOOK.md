# CK-NEXUS Q10-Q12 Production Closure Operator Runbook

This runbook closes the three remaining P0 production gates without weakening the frozen release contract.

## Frozen authorities

- Repository: `spinlnw10-art/ck-nexus`
- Production-closure head to security-scan: `512837c8b1a3e6e8e844252a1b0781d8de011b07`
- Production-closure tree: `43f9cb9691a0d028a1ef396a0a475c5cd80c4a99`
- Frozen runtime source used by Q11/Q12 exact verifiers: `4cf17cd3befaafeaf64cd4c149739133aa220f73`
- Frozen runtime source tree: `dfe3888bb6adc9aebbb0351efe4a06006f4e0a48`
- Frozen runtime/deployment subject: `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f`

Do not replace any value above with `main`, a moving branch name, or a newer commit unless the entire subject-bound production evidence set is deliberately re-baselined.

## Common fail-closed preflight

From a clone with all objects fetched:

```bash
git fetch --all --tags --prune

test "$(git show -s --format=%T 512837c8b1a3e6e8e844252a1b0781d8de011b07)" = \
  "43f9cb9691a0d028a1ef396a0a475c5cd80c4a99"

test "$(git show -s --format=%T 4cf17cd3befaafeaf64cd4c149739133aa220f73)" = \
  "dfe3888bb6adc9aebbb0351efe4a06006f4e0a48"

subject=$(git ls-tree -r 4cf17cd3befaafeaf64cd4c149739133aa220f73 -- \
  app creator_app services gateway orchestration idea_engine migrations deploy observability \
  Dockerfile docker-compose.prod.yml main.py pyproject.toml uv.lock | sha256sum | awk '{print $1}')

test "$subject" = "96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f"
echo "FROZEN SUBJECT PASS: $subject"
```

Any failure is a hard stop.

---

## Q10 — Codex Security Deep Security Scan

### Why this is still blocked

`pip-audit` is only the dependency component. Q10 whole-gate PASS requires the native Codex Security **Deep Security Scan**, including repeated discovery, validation, attack-path analysis, canonical completion, and generated report. Bandit, secret scanning, dependency scanning, or ordinary CI are not substitutes.

### Exact scan target

Checkout the exact production-closure head before opening the repository in Codex Security:

```bash
git checkout --detach 512837c8b1a3e6e8e844252a1b0781d8de011b07
test "$(git rev-parse HEAD)" = "512837c8b1a3e6e8e844252a1b0781d8de011b07"
```

Use `evidence/q10/Q10_SCAN_REQUEST_FINAL_SUBJECT.json` as the machine-readable request. Scan scope must be repository root (`.`).

Suggested Codex task text:

```text
Run the native Codex Security Deep Security Scan repository-wide on this exact checkout.
Target commit: 512837c8b1a3e6e8e844252a1b0781d8de011b07
Target tree: 43f9cb9691a0d028a1ef396a0a475c5cd80c4a99
Frozen runtime subject: 96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f
Scope: .
Do not substitute Bandit, pip-audit, secret scan, manual review, or ordinary CI.
Complete repeated discovery, canonical validation, attack-path analysis, canonical draft, completion, coverage, and generated report.md.
```

### Q10 acceptance

Q10 remains blocked until all of these are true:

1. Codex Security completion succeeds and generated `report.md` exists.
2. Coverage is not falsely represented as complete when discovery did not complete.
3. Every reportable finding is validated. Findings requiring remediation must be fixed before release.
4. If a remediation changes any frozen runtime path, stop: the runtime subject changes and subject-bound Q10-Q16 evidence must be regenerated.
5. Capture the Codex Security scan ID, completion timestamp, and SHA-256 of the generated report.

Compute the report digest:

```bash
sha256sum /path/to/codex-security/report.md
```

The committed `evidence/Q10_DEPENDENCY_AUDIT.json` may be promoted to whole-gate PASS only after adding at minimum:

```json
{
  "gate_result": "PASS",
  "codex_security_deep_scan": "PASS",
  "production_promotion_allowed": true,
  "codex_security_scan_id": "<sealed-scan-id>",
  "codex_security_report_sha256": "<sha256>",
  "codex_security_completed_at": "<RFC3339 timestamp>",
  "codex_security_target_sha": "512837c8b1a3e6e8e844252a1b0781d8de011b07",
  "codex_security_target_tree_sha": "43f9cb9691a0d028a1ef396a0a475c5cd80c4a99",
  "codex_security_release_subject_manifest_sha256": "96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f"
}
```

Do not invent these fields before the workbench produces them.

---

## Q11 — Live OpenAI provider smoke

The exact verifier already exists on branch `verify/q11-final-subject` and checks out frozen source `4cf17cd3befaafeaf64cd4c149739133aa220f73`. The test script is `scripts/test_openai_live.py` and requires the sentinel `CK-NEXUS-P0-SMOKE-PASS`.

### Secure secret setup

In GitHub repository settings, create an Actions repository secret named exactly:

```text
OPENAI_API_KEY
```

Never put the key in a commit, issue, PR comment, shell history pasted into chat, or evidence JSON. Optionally create an Actions variable:

```text
OPENAI_SMOKE_MODEL
```

If unset, the verifier falls back to the model configured by the script.

### Execute

After the secret exists, rerun the existing failed Q11 verifier run `31818698368` or trigger the verifier on `verify/q11-final-subject` without changing the frozen source SHA.

PASS requires:

- exit code `0` from `scripts/test_openai_live.py`;
- `credential_configured: true`;
- `credential_exposed: false`;
- `sentinel_observed: true`;
- `result: PASS`;
- `production_promotion_allowed: true`.

After a successful run, download/read the generated `Q11_OPENAI_LIVE.json`, obtain the GitHub artifact ID and server-side `sha256:` digest, then commit the normalized evidence to `evidence/Q11_OPENAI_LIVE.json` on the production-closure line. Never hand-edit a BLOCKED run into PASS.

---

## Q12 — delegated cgroup v2 on real Linux staging

The GitHub-hosted verifier proved that seeing cgroup v2 controllers is not enough. Q12 requires a writable delegated subtree owned by the **non-root CK-NEXUS service identity** with `cpu`, `memory`, and `pids` available.

### Recommended staging topology

Use a Linux VPS or self-hosted runner registered with a dedicated service account. The runner/service account must not be root. A systemd service/scope should delegate the controllers:

```ini
[Service]
User=cknexus
Group=cknexus
Delegate=cpu memory pids
```

The exact unit layout depends on the host. Do not make `/sys/fs/cgroup` globally writable and do not use `chmod 777` as a workaround.

### Host preflight as the non-root service identity

```bash
id -u
test "$(id -u)" -ne 0
stat -fc %T /sys/fs/cgroup
cat /sys/fs/cgroup/cgroup.controllers
```

Identify the actual delegated service subtree, for example:

```bash
cat /proc/self/cgroup
```

Set only the real delegated root returned by the service-manager layout:

```bash
export CKNEXUS_ENVIRONMENT=staging
export CKNEXUS_AGNES_CGROUP_ROOT=/sys/fs/cgroup/<actual-delegated-subtree>
```

Verify non-root write access and required controllers:

```bash
test -w "$CKNEXUS_AGNES_CGROUP_ROOT"
for c in cpu memory pids; do
  grep -qw "$c" "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.controllers" || exit 1
done
```

Checkout the frozen runtime source and run the exact gate:

```bash
git checkout --detach 4cf17cd3befaafeaf64cd4c149739133aa220f73
CKNEXUS_ENVIRONMENT=staging \
CKNEXUS_AGNES_CGROUP_ROOT="$CKNEXUS_AGNES_CGROUP_ROOT" \
python3 scripts/agnes_cgroup_v2_staging_gate.py | tee Q12_CGROUP_RAW.json
```

PASS must observe exactly:

- `cpu.max = 20000 100000`
- `memory.max = 67108864`
- `pids.max = 16`
- child PID attached in `cgroup.procs`
- result `PASS`

For GitHub provenance, run this through a self-hosted GitHub Actions runner on the allowed verifier branch `verify/q12-final-subject`. Before doing that, adapt its verifier workflow from `ubuntu-24.04` to the dedicated self-hosted runner label and remove the hosted-runner `sudo mkdir/chown` probe. The gate itself must run as the non-root delegated identity.

After success, normalize the generated Q12 evidence with the workflow run ID, artifact ID, server-side artifact digest, exact release subject, environment class, and raw gate observations; then commit it to `evidence/Q12_CGROUP_V2.json`.

---

## Final convergence after Q10 + Q11 + Q12 PASS

On the production-closure branch, require all three evidence files to claim PASS legitimately, then run:

```bash
GITHUB_REPOSITORY=spinlnw10-art/ck-nexus \
GITHUB_TOKEN="$GITHUB_TOKEN" \
python .github/release-tools/verify_release_evidence_provenance.py \
  --expected-subject 96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f \
  --output release-evidence-provenance.json
```

Only a provenance `PASS` authorizes rerunning `Final production package`. Production is still NO-GO until that workflow actually creates the checksummed production artifact and PR #14 is reviewed for merge.

## Important development rule

Bug fixes and new features can continue on separate branches. If any fix changes a frozen runtime path, it must not be silently merged into the current production-closure line because the subject hash changes. Treat it as a new candidate subject and rerun every affected subject-bound gate.
