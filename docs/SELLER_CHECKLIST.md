# CK-NEXUS Seller Checklist

Use this checklist for each source-code sale or transfer. The repository can provide the technical package; transaction-specific legal and commercial fields are completed outside source control.

## Release identity

- [ ] Record exact branch, commit and tag.
- [ ] Record ZIP/bundle/wheel SHA-256 values.
- [ ] Verify the artifact was generated from a clean working tree.
- [ ] Verify internal `SHA256SUMS`.

## Technical acceptance

- [ ] Full dependency environment installed from the lock/declared extras.
- [ ] Full pytest suite PASS.
- [ ] Ruff PASS.
- [ ] Bandit PASS.
- [ ] pip-audit reviewed with no unaccepted high-impact finding.
- [ ] Secret scan PASS.
- [ ] Clean-machine installation PASS.
- [ ] Backup/restore rehearsal PASS where persistent production data is in scope.
- [ ] Live OpenAI/provider gate PASS using buyer/seller-authorized staging credentials.
- [ ] Production/staging infrastructure gates PASS for the exact release identity.

## Security and credentials

- [ ] No `.env.local`, API keys, OAuth tokens, private keys or production databases in the package.
- [ ] Credential Broker status is redacted.
- [ ] Provider credentials are buyer-provisioned after delivery.
- [ ] Default permissions and production fail-closed behavior reviewed.

## Commercial package

- [ ] Choose assignment vs perpetual source license in the executed schedule.
- [ ] Identify seller and buyer legal entities outside the repository.
- [ ] State price, currency, taxes and payment milestones.
- [ ] State acceptance period and rejection/remediation procedure.
- [ ] State support/warranty period and exclusions.
- [ ] Confirm third-party notices and dependency licenses.
- [ ] Define delivery channel and buyer backup responsibility.

## Final decision

Mark an artifact **SELLABLE** only when every technical P0 release gate required for the intended deployment posture is PASS. Otherwise label it **Development Candidate / NO-GO for Production claims**.
