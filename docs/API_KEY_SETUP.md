# CK-NEXUS API Key Setup

## Current entry point

On the VPS, run `sudo api`. The command presents a provider menu and accepts secrets only through a hidden terminal prompt. Do not paste keys into ChatGPT, Qwen, n8n, tickets, or logs.

The exact command matcher is `is_api_command(text)`: it accepts only `Api` after trimming surrounding whitespace, case-insensitively. It is unit-tested. This matcher is not yet connected to the Qwen/n8n chat workflow, because the repaired workflow JSON was not available in the repository; chat cannot safely open an interactive SSH terminal by itself.

## Provider policy

- Qwen / DashScope updates `/etc/cknexus/qwen.env` and uses `DASHSCOPE_API_KEY`.
- Gemini updates `/etc/cknexus/gemini.env` and uses `GEMINI_API_KEY`.
- OpenAI Admin preserves the existing `/root/.openai_admin_key` location and requires the `sk-admin-` prefix.
- OpenAI standard, separate Model Studio, and custom OpenAI-compatible setup are blocked until the service's actual EnvironmentFile/provider mapping is verified. Model Studio is additionally blocked by the current `free-only` systemd drop-in.
- Ollama local is shown as normally not requiring a key.

Existing environment files are backed up before edits; the new file is written atomically with root ownership and mode 0600. The service restart is opt-in, and no live API request is made automatically.

## Verification

Run `.venv/bin/python -m pytest -q tests/test_api_key_setup.py` and `git diff --check`. No real API key is entered by tests.
