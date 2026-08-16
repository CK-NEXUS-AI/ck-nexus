# Buyer Quick Start

Requirements: Python 3.11+.

## Linux/macOS

```bash
cp .env.example .env.local
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python main.py
```

## Windows PowerShell

```powershell
Copy-Item .env.example .env.local
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe main.py
```

Open `http://127.0.0.1:8000`.

The supplied example configuration enables Demo Mode (`CKNEXUS_MOCK_AI=true`) so evaluation can start without a live provider key.

## Live Mode

After Demo Mode works:

1. place your own `OPENAI_API_KEY` in `.env.local`;
2. set `CKNEXUS_MOCK_AI=false`;
3. select the desired allowed `OPENAI_MODEL`;
4. restart the application.

Do not commit `.env.local` or share credentials in screenshots/chat.

## Release verification

```bash
python scripts/release_check.py
```

Or run the documented compile/test/dependency checks individually. Live-provider checks require buyer-provisioned working credentials and are not represented as completed by this sale package.
