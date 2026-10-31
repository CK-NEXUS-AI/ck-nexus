# CK-NEXUS Q10-Q12 Production Closure Operator Runbook

This runbook closes the three remaining P0 production gates without weakening the frozen release contract.

## Frozen authorities

- Repository: `spinlnw10-art/ck-nexus`
- Production-closure head to security-scan: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Production-closure tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Frozen runtime source used by Q11/Q12 exact verifiers: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Frozen runtime source tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Frozen runtime/deployment subject: `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`

Do not replace any value above with `main`, a moving branch name, or a newer commit unless the entire subject-bound production evidence set is deliberately re-baselined.

## Common fail-closed preflight

From a clone with all objects fetched:

```bash
git fetch --all --tags --prune

test "$(git show -s --format=%T 39f5c1adb9d761ab418cf088ff1f051b1ca731d1)" = \
  "0525195934f703a8becf8a39f6397b2411e0bb2e"

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

## Q10 — Open-source layered security gate

### Required checks

Q10 uses a reproducible, multi-tool open-source security gate. The exact frozen source and runtime subject must pass all of the following:

1. Frozen dependency resolution: `uv lock --check` and `uv sync --all-extras --dev --frozen`.
2. Dependency vulnerability audit: `pip-audit` with no unaccepted vulnerability.
3. Static security analysis: Bandit over the applicable Python source.
4. Secret scanning: `scripts/secret_scan.py`.
5. Black-box security/policy regression: `scripts/security_attack_regression.py`.
6. Preserve scanner outputs, aggregate a canonical report, and record its SHA-256 plus the successful workflow run ID and completion timestamp.

A single scanner, a partial run, or a missing report is not a PASS. Any reportable finding must be triaged and resolved according to release policy. Any source remediation changes the subject and requires regenerating all subject-bound release evidence.

### Q10 acceptance

Q10 remains `NOT_VERIFIED` until all checks pass against the exact closure target and frozen runtime subject; the aggregate report exists and is hashed; provenance verifies the successful run and artifact; and `production_promotion_allowed` is true only in the resulting verified evidence. Until then, Production remains NO-GO.

## Q11 — Live OpenAI provider smoke

The exact verifier already exists on branch `verify/q11-final-subject` and checks out frozen source `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`. The test script is `scripts/test_openai_live.py` and requires the sentinel `CK-NEXUS-P0-SMOKE-PASS`.

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

After the secret exists, rerun the existing failed Q11 verifier run `31950795711` or trigger the verifier on `verify/q11-final-subject` without changing the frozen source SHA.

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
DelegateSubgroup=runner
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

Verify non-root write access, required controllers, and a usable delegated subtree:

```bash
test -w "$CKNEXUS_AGNES_CGROUP_ROOT"
for c in cpu memory pids; do
  grep -qw "$c" "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.controllers" || exit 1
done

# The delegated root must be free of internal processes before domain
# controllers can be enabled for child cgroups. DelegateSubgroup=runner
# keeps the service/runner process in a child subgroup.
test ! -s "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.procs"

printf '+cpu +memory +pids\n' >   "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.subtree_control"

for c in cpu memory pids; do
  grep -qw "$c" "$CKNEXUS_AGNES_CGROUP_ROOT/cgroup.subtree_control" || exit 1
done
```

A 2026-09-05 host-capability preflight on VPS `10616a96dd5c121bb`
(kernel 6.8, systemd 255) reproduced the failure with plain `Delegate=yes`
and then passed when `DelegateSubgroup=supervisor` was used and
`+cpu +memory +pids` were enabled in `cgroup.subtree_control`.
That preflight proves host capability only; it is not canonical Q12 evidence.

Checkout the frozen runtime source and run the exact gate:

```bash
git checkout --detach 39f5c1adb9d761ab418cf088ff1f051b1ca731d1
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
  --expected-subject 89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52 \
  --output release-evidence-provenance.json
```

Only a provenance `PASS` authorizes rerunning `Final production package`. Production is still NO-GO until that workflow actually creates the checksummed production artifact and PR #14 is reviewed for merge.

## Important development rule

Bug fixes and new features can continue on separate branches. If any fix changes a frozen runtime path, it must not be silently merged into the current production-closure line because the subject hash changes. Treat it as a new candidate subject and rerun every affected subject-bound gate.
