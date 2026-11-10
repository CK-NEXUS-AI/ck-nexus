#!/usr/bin/env python3
"""Render status-aware SVG badges from committed CK-NEXUS gate evidence."""

from __future__ import annotations

import html
from pathlib import Path

try:
    from .generate_update_report import group_states, load_gate_states
except ImportError:  # Support direct execution as a script.
    from generate_update_report import group_states, load_gate_states

ROOT = Path(__file__).resolve().parents[1]
WIDTH = 240
HEIGHT = 28
DARK = "#24292f"
COLORS = {
    "PASS": "#2ea043",
    "PASS_CANDIDATE": "#bf8700",
    "FAIL": "#cf222e",
    "BLOCKED": "#bf8700",
    "NOT_VERIFIED": "#6e7781",
    "NOT_STARTED": "#6e7781",
    "UNKNOWN": "#6e7781",
}


def render_svg(label: str, status: str, progress: int | None = None) -> str:
    normalized = status.upper()
    color = COLORS.get(normalized, COLORS["UNKNOWN"])
    if normalized == "PASS":
        display = "100%"
    elif normalized == "PASS_CANDIDATE":
        display = f"{progress if progress is not None else 75}%"
    elif normalized == "NOT_STARTED":
        display = "0%"
    else:
        display = normalized.replace("_", " ")
    safe_label = html.escape(label, quote=True)
    safe_display = html.escape(display, quote=True)
    label_width = 88
    status_width = WIDTH - label_width
    return f'''<svg
  xmlns="http://www.w3.org/2000/svg"
  width="{WIDTH}" height="{HEIGHT}"
  viewBox="0 0 {WIDTH} {HEIGHT}"
  role="img" aria-label="{safe_label}: {safe_display}">
  <title>{safe_label}: {safe_display}</title>
  <rect width="{WIDTH}" height="{HEIGHT}" rx="5" fill="{DARK}"/>
  <path d="M5 0h{label_width - 5}v28H5a5 5 0 0 1-5-5V5a5 5 0 0 1 5-5z"
        fill="{DARK}"/>
  <text x="{label_width / 2}" y="18" fill="#ffffff"
        font-family="Verdana,DejaVu Sans,sans-serif" font-size="10"
        text-anchor="middle">{safe_label}</text>
  <rect x="{label_width}" y="0" width="{status_width}"
        height="{HEIGHT}" rx="0" fill="{color}"/>
  <text x="{label_width + status_width / 2}" y="18" fill="#ffffff"
        font-family="Verdana,DejaVu Sans,sans-serif" font-size="11"
        font-weight="bold" text-anchor="middle">{safe_display}</text>
</svg>
'''


def main() -> int:
    output = ROOT / "docs" / "badges"
    output.mkdir(parents=True, exist_ok=True)
    gates = load_gate_states()
    groups = group_states(gates)
    for filename, label in (
        ("security.svg", "Security"),
        ("stability.svg", "Stability"),
        ("release.svg", "Release"),
        ("delivery.svg", "Delivery"),
    ):
        item = groups[label]
        path = output / filename
        path.write_text(
            render_svg(label, item["status"], item["progress"]),
            encoding="utf-8",
        )
        display = item["status"]
        if item["progress"] is not None:
            display += f" ({item['progress']}%)"
        print(f"WROTE {path.relative_to(ROOT)} [{display}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
