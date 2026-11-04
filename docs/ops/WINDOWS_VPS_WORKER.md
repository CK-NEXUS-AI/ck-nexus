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
.\scripts\ops\windows_vps_worker.ps1 -InstallPythonToolchain -InstallGitToolchain
```

The bootstrap installs/enables OpenSSH Server, opens inbound TCP 22 in Windows Firewall, installs checksum-verified portable Node.js LTS under `C:\CKTools\node`, checksum-verified `uv` under `C:\CKTools\uv`, Python 3.12 through `uv`, and checksum-verified MinGit under `C:\CKTools\git`.

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
4. direct command execution succeeds on the VPS;
5. Python 3.12, uv, Node.js/npm, and Git report expected versions; and
6. the persistent agent task has been registered after enrollment and survives the next logon/reconnect cycle.

Current live VPS evidence collected during development:

- Node.js `v24.19.0`
- npm `11.17.0`
- uv `0.12.5`
- CPython `3.12.14`
- MinGit `2.55.0.windows.5`
- MinGit release SHA-256 matched GitHub release asset digest before extraction

These are development-worker facts only and are not production release evidence.

## Security boundary

- install public keys through `C:\ProgramData\ssh\administrators_authorized_keys`
- verify key authentication before disabling password authentication
- never place API keys, passwords, passkeys, SSH private keys, or provider secrets in repository files
- keep the VPS development-only until independently verified
- require release SHA-256 verification for portable Node.js/uv/Git downloads
- revoke temporary SSH keys and destroy ephemeral VPS state when the lease ends

## Q12 limitation

Windows Server cannot satisfy the CK-NEXUS authoritative Q12 contract that requires Linux namespaces and delegated writable cgroup v2 controllers (`cpu`, `memory`, `pids`). Use an independently verified Linux/Ubuntu environment for Q12.
