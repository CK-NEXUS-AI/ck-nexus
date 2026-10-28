# n8n API key rotation and automatic adoption

## Boundary

n8n's public REST API does not provide a documented endpoint to create or revoke its own API keys. Create a replacement in the n8n UI under **Settings → n8n API**. Do not confuse the n8n public API key with `N8N_ENCRYPTION_KEY` or an arbitrary `N8N_API_KEY` environment variable.

## Safe adoption

Run as root on the VPS:

```bash
/usr/local/sbin/cknexus-n8n-key-rotate
```

Paste the replacement key only at the hidden terminal prompt. The helper first calls the local API at `127.0.0.1:5678` and checks for HTTP 200 plus the expected workflow-list response. It changes nothing if validation fails. On success it atomically writes `/root/.config/n8n/api_key` with root ownership and mode 0600 and keeps a root-only backup. The workflows gateway reads this file on each request, so adoption requires no restart.

Check the installed key without modifying files:

```bash
/usr/local/sbin/cknexus-n8n-key-rotate --check
```

After verifying the consumers work, revoke the old key manually in **Settings → n8n API**. The helper deliberately does not revoke keys, because a bad rotation could lock out every consumer. External Cloudflare 403 responses are a separate routing/access issue; successful local validation does not imply the external endpoint is fixed.

## Verified limits

This automates validation, secure replacement, propagation to file-based consumers, rollback on post-write failure, and health checks. It does not autonomously issue a new native n8n key or revoke the old one; n8n's documented workflow for those actions is in the UI.
