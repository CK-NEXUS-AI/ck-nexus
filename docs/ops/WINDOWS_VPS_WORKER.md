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
.\scripts\ops\windows_vps_worker.ps1 -InstallPythonToolchain
```

The bootstrap installs/enables OpenSSH Server, opens inbound TCP 22 in Windows Firewall, installs checksum-verified portable Node.js LTS under `C:\CKTools\node`, installs checksum-verified `uv` under `C:\CKTools\uv`, and installs Python 3.12 through `uv`.

For the first Desktop Commander enrollment, run the script without `-SkipRemoteAgent` and complete the device authorization in the browser. The authorization material stays in the local user profile and must not be copied into the repository.

After the device has been authorized once, make the agent restart automatically at Administrator logon:

```powershell
.\scripts\ops\windows_vps_worker.ps1 -SkipRemoteAgent -PersistRemoteAgent
```

`-PersistRemoteAgent` refuses to continue until `.desktop-commander-device\device.json` already exists. It registers the `CK-NEXUS-DesktopCommander` scheduled task and starts it immediately. This is intended to survive RDP disconnects; a full Windows logoff still terminates the interactive user session and the task starts again on the next logon.

## Verification

Do not retire Termux until all of the following are true:

1. the VPS appears as a separate Remote Desktop Commander device;
2. its device auth token is valid;
3. direct `ping` returns `pong`;
4. direct command execution succeeds on the VPS; and
5. the persistent agent task has been registered after enrollment.

## Security boundary

- install public keys through `C:\ProgramData\ssh\administrators_authorized_keys`
- verify key authentication before disabling password authentication
- never place API keys, passwords, passkeys, SSH private keys, or provider secrets in repository files
- keep the VPS development-only until independently verified
- use release checksums for portable Node.js/uv downloads
- revoke temporary SSH keys and destroy ephemeral VPS state when the lease ends

## Q12 limitation

Windows Server cannot satisfy the CK-NEXUS authoritative Q12 contract that requires Linux namespaces and delegated writable cgroup v2 controllers (`cpu`, `memory`, `pids`). Use an independently verified Linux/Ubuntu environment for Q12.
