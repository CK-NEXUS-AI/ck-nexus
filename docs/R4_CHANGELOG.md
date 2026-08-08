# R4 Integration Hub Changelog

- Added unified Integration Hub status API.
- Added Slack authentication status check.
- Added Google Drive API access status check.
- Added n8n Public API access status check.
- Added OpenAI configuration gate status without exposing keys.
- Expanded Full System Demo SYSTEM matrix for GitHub, Slack, Drive, n8n, and OpenAI.
- Replaced stale unverified default OpenAI model with `gpt-5-mini`; environment override remains supported.
- Added GitHub Actions CI: compile, Ruff, Bandit, secret scan, pytest.
- Added weekly/manual dependency audit workflow.
- Added tracked-file secret scanner.
- Preserved Release Candidate / NO-GO production language until P0 runtime evidence passes.
- Updated official GitHub Actions workflow dependencies to checkout v6 and setup-python v6.
