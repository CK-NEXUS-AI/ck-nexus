# CK-NEXUS GitHub Baseline

Repository target: `spinlnw10-art/ck-nexus`

Authoritative baseline tag: `v0.2.0-p0-rc`
Source-content commit before GitHub push tooling: `7a0070d761a4808795e3fc3788be5d39e9d33cca`

The final delivered baseline commit is whatever the signed/annotated tag resolves to:

```bash
git rev-parse v0.2.0-p0-rc^{}
```

The repository did not exist at baseline-preparation time. Create the empty GitHub repository first, then run:

```bash
export GITHUB_TOKEN='...'
./scripts/github/push_ck_nexus.sh
```

The token is read only from the process environment and is not written into the Git remote URL or source tree.
