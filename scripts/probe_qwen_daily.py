#!/usr/bin/env python3
"""Run at most one authenticated, low-token Qwen probe per UTC day."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.collect_dev_status import probe_qwen_daily  # noqa: E402

if __name__ == "__main__":
    result = probe_qwen_daily()
    print(result["status"])
