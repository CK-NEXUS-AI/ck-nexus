---
name: termux-rescue
description: Use when configuring or troubleshooting the CK-NEXUS Termux SSH recovery path and reverse SSH tunnel.
---

# Termux rescue path

1. Inspect SSH aliases and effective configuration with secrets redacted. Never display private-key contents.
2. Pin and verify host keys; do not disable StrictHostKeyChecking or use password authentication as a shortcut.
3. Use a dedicated least-privilege rescue key and a dedicated Termux SSH account. Restrict authorized_keys options where compatible with the chosen tunnel.
4. Use runit/autossh or an equivalent supervisor with bounded connection timeouts, ServerAliveInterval, ServerAliveCountMax, and ExitOnForwardFailure.
5. Bind reverse-forwarded ports to loopback only; never expose the rescue port publicly.
6. Verify local sshd listener, tunnel process, remote loopback listener, authenticated read-only command, reconnect after tunnel drop, and boot persistence.
7. Termux:Boot only runs after the companion app is installed and Android permits it. Do not claim reboot persistence based solely on a boot script file existing.
8. Never run destructive commands through the rescue path. Record test time, endpoint, exit status, and logs without secrets.
