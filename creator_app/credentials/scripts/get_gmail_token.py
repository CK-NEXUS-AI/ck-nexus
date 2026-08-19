#!/usr/bin/env python3
"""Gmail OAuth2 Refresh Token Helper.

This script guides you through obtaining a Gmail Refresh Token step by step,
without sending your credentials to anyone.

Usage:
  python creator_app/credentials/scripts/get_gmail_token.py

The script will:
1. Display the Google OAuth consent URL
2. You open it in a browser and grant access
3. You paste the authorization code back
4. Script exchanges it for tokens (client-side only)
5. Outputs GOOGLE_REFRESH_TOKEN for your .env file

No credentials are stored or transmitted to any third party.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


def main() -> int:
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables first.")
        print()
        print("Get them from: https://console.cloud.google.com/apis/credentials")
        return 1

    redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "response_type": "code",
    }

    auth_url = f"{GOOGLE_AUTH_BASE}?{urllib.parse.urlencode(params)}"

    print("=" * 60)
    print("📧 Gmail OAuth2 — Get Refresh Token")
    print("=" * 60)
    print()
    print("Step 1: Open this URL in your browser:")
    print()
    print(f"   {auth_url}")
    print()
    print("Step 2: Sign in with your Gmail account (spinlnw10@gmail.com)")
    print("        and grant the requested permissions.")
    print()
    print("Step 3: Copy the authorization code and paste it below.")
    print()

    code = input("Authorization code: ").strip()
    if not code:
        print("❌ No code entered. Exiting.")
        return 1

    print()
    print("Step 4: Exchanging code for tokens...")
    print()

    data = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            token_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        print(f"❌ Token exchange failed: HTTP {exc.code}")
        print(f"   Response: {error_body}")
        return 1

    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        print("❌ No refresh token returned. Try granting consent again.")
        if "warning" in token_data:
            print(f"   Warning: {token_data['warning']}")
        return 1

    access_token = token_data.get("access_token", "")
    expires_in = token_data.get("expires_in", 3600)

    print("✅ Success! Tokens obtained.")
    print()
    print("Add these to your .env file:")
    print()
    print(f"   GOOGLE_REFRESH_TOKEN={refresh_token}")
    print()
    print(f"   Access token (short-lived, {expires_in}s):")
    print(f"   {access_token}")
    print()
    print("ℹ️  The refresh token is what you need. The access token expires and")
    print("   will be refreshed automatically by the Gmail connector.")
    print()

    env_path = Path(".env")
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")
        if "GOOGLE_REFRESH_TOKEN=" not in existing:
            with env_path.open("a", encoding="utf-8") as f:
                f.write(f"\nGOOGLE_REFRESH_TOKEN={refresh_token}\n")
            print(f"✅ Added GOOGLE_REFRESH_TOKEN to {env_path}")
        else:
            print(f"⚠️  {env_path} already has GOOGLE_REFRESH_TOKEN. Update manually if needed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
