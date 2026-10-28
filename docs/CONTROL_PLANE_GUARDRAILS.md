# CK-NEXUS Control Plane Guardrails

## Installed guardrails

- `scripts/cknexus-emergency-stop.sh` / `/usr/local/sbin/cknexus-emergency-stop`: defaults to `--dry-run`; `--confirm` stops only the Auto-Developer and Auto-GitOps timers/services. It preserves n8n, the UI, monitoring, backups, and the task database.
- `scripts/cknexus-service-alert.sh` / `/usr/local/sbin/cknexus-service-alert`: writes root-only local alerts and deduplicates repeats per unit for five minutes.
- `ops/vps/systemd/cknexus-alert@.service`: systemd alert template.
- `ops/vps/systemd/*.service.d/90-cknexus-alert.conf`: `OnFailure` hooks for Intelligence, Auto-Developer, and Auto-GitOps.
- `creator_app/n8n_intelligence/client.py`: bounded retry/backoff with jitter; deterministic HTTP 401/403 is not retried.
- `creator_app/n8n_intelligence/circuit_breaker.py`: persistent circuit state with a single Half-Open probe, immediate auth-failure cooldown, and threshold-based transient cooldown. State and lock files are mode 0600.
- `scripts/cknexus-github-gitops-configure` / `/usr/local/sbin/cknexus-github-gitops-configure`: hidden-input GitHub token setup that validates identity/repository access and atomically writes a root-only EnvironmentFile.
- `creator_app/n8n_intelligence/judgment_gate.py`: deterministic Allow/Edit/Escalate/Deny gate with TRACE levels; unsafe paths are denied and auth failures escalate.
- `creator_app/n8n_intelligence/auto_gitops.py`: invokes the judgment gate before staging/committing; retains its existing path allowlist, secret scan, isolated worktree and remote-SHA verification.
- `creator_app/n8n_intelligence/gitops_controller.py`: creates idempotent draft GitHub PRs for already-published verified branches only; it does not commit, push, merge, or deploy.
- `ops/vps/scripts/cknexus_n8n_auto_gitops.py`: optionally opens draft PRs for published evidence when `GITHUB_TOKEN` and `GITHUB_REPO` are provided by a secure runtime environment.

## Emergency stop

Preview actions first:

```bash
/usr/local/sbin/cknexus-emergency-stop --dry-run
```

Apply the stop only when required:

```bash
/usr/local/sbin/cknexus-emergency-stop --confirm
```

The script intentionally does not update task rows to `halted`: the current `control_plane_tasks.state` constraint permits only `queued`, `running`, `completed`, and `failed`. Do not bypass that constraint with ad-hoc SQL. A future task-cancellation feature must add an explicit, tested state transition and migration.

## Current limitations

- Alerts are local-only (journal and `/var/log/cknexus/service-alerts.log`); no outbound webhook is configured.
- n8n API authentication still returns HTTP 401. Alerting and retries do not repair an invalid key.
- Circuit breaker persistence, DLQ, authenticated Pause/Resume/Kill API, and human approval/merge enforcement are not yet implemented.
- Draft PR creation is wired but has **not been live-verified**; the current systemd unit does not configure `GITHUB_TOKEN` or `GITHUB_REPO`. Do not put tokens directly in a unit file or repository. Configure them through a root-readable environment file, then verify against GitHub without exposing the value.
- Auto-GitOps never merges or deploys. Repository branch protection and required approvals must be configured on GitHub; the controller only opens a draft PR.
