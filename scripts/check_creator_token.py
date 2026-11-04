#!/usr/bin/env python3
"""Fail Creator App startup if its bearer token is missing or blank."""
from __future__ import annotations

import os
import sys

if __name__ == "__main__":
    sys.exit(0 if os.getenv("CKNEXUS_ACCESS_TOKEN", "").strip() else 1)
