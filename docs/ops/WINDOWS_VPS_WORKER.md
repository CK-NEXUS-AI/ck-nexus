# CK-NEXUS Windows VPS Worker

This worker is a development execution plane only. It is not Q12 Linux sandbox evidence and does not change Production NO-GO status.

## Purpose

- offload development workloads from Termux/mobile
- provide key-based remote administration
- host the Remote Desktop Commander device agent
- run repeatable build, test, packaging, and preview workloads

## Bootstrap

Run PowerShell as Administrator:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\ops\windows_vps_worker.ps1
```

The script installs/enables OpenSSH Server, opens inbound TCP 22 in Windows Firewall, installs a portable Node.js LTS runtime under `C:\CKTools\node`, and starts the Desktop Commander device authorization flow.

## Security boundary

- install public keys through `C:\ProgramData\ssh\administrators_authorized_keys`
- verify key authentication before disabling password authentication
- never place API keys, passwords, passkeys, or provider secrets in repository files
- keep the VPS development-only until independently verified
- revoke temporary SSH keys and destroy ephemeral VPS state when the lease ends

## Q12 limitation

Windows Server cannot satisfy the CK-NEXUS authoritative Q12 contract that requires Linux namespaces and delegated writable cgroup v2 controllers (`cpu`, `memory`, `pids`). Use an independently verified Linux/Ubuntu environment for Q12.
