from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BG = "#090b0b"
SURFACE = "#151917"
LINE = "#38403b"
TEXT = "#f4f7f4"
MUTED = "#9da8a1"
ACCENT = "#b8ff65"


def font(size: int, bold: bool = False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def rounded_box(draw: ImageDraw.ImageDraw, box, title: str, subtitle: str, accent=False):
    fill = "#1b211d" if accent else SURFACE
    outline = ACCENT if accent else LINE
    draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=3)
    x1, y1, _, _ = box
    draw.text((x1 + 26, y1 + 25), title, fill=ACCENT if accent else TEXT, font=font(28, True))
    draw.multiline_text((x1 + 26, y1 + 72), subtitle, fill=MUTED, font=font(18), spacing=7)


def arrow(draw: ImageDraw.ImageDraw, start, end):
    draw.line([start, end], fill=ACCENT, width=5)
    x, y = end
    draw.polygon([(x, y), (x - 16, y - 10), (x - 16, y + 10)], fill=ACCENT)


def interactions():
    image = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(image)
    draw.text((72, 54), "CK-NEXUS Creator Edition", fill=TEXT, font=font(42, True))
    draw.text((72, 112), "Agent interactions — direct menu selection", fill=MUTED, font=font(22))

    rounded_box(
        draw,
        (80, 300, 360, 520),
        "Creator",
        "Select agent\nWrite brief\nReview output",
        accent=True,
    )
    rounded_box(
        draw,
        (510, 180, 870, 640),
        "CK-NEXUS",
        "FastAPI gateway\nValidation & limits\nCreator service\nLocal run history",
    )
    rounded_box(draw, (1020, 120, 1500, 290), "Content Strategist", "Ideas, hooks, plan")
    rounded_box(draw, (1020, 330, 1500, 500), "Script Writer", "Ready-to-record script")
    rounded_box(draw, (1020, 540, 1500, 710), "Repurpose / Review", "Platform variants & QA")

    arrow(draw, (360, 410), (510, 410))
    arrow(draw, (870, 270), (1020, 205))
    arrow(draw, (870, 410), (1020, 415))
    arrow(draw, (870, 550), (1020, 625))
    draw.text(
        (72, 812),
        "Only the selected specialist runs — predictable cost and latency.",
        fill=ACCENT,
        font=font(20, True),
    )
    image.save(DOCS / "agent-interactions.png", optimize=True)


def sequence():
    image = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(image)
    draw.text((72, 54), "CK-NEXUS Creator Edition", fill=TEXT, font=font(42, True))
    draw.text((72, 112), "Generation sequence", fill=MUTED, font=font(22))

    columns = [(100, "Browser"), (500, "FastAPI"), (900, "Agent SDK"), (1300, "SQLite")]
    for x, title in columns:
        draw.text((x, 185), title, fill=TEXT, font=font(24, True))
        draw.line((x + 65, 230, x + 65, 785), fill=LINE, width=3)

    events = [
        (280, 165, 565, "POST creative brief"),
        (370, 565, 965, "Run selected specialist"),
        (465, 965, 1365, "Persist session memory"),
        (560, 965, 565, "Final Markdown"),
        (655, 565, 1365, "Save run history"),
        (750, 565, 165, "Return result + run ID"),
    ]
    for y, x1, x2, label in events:
        direction = 1 if x2 > x1 else -1
        draw.line((x1, y, x2, y), fill=ACCENT, width=4)
        tip = [(x2, y), (x2 - 15 * direction, y - 9), (x2 - 15 * direction, y + 9)]
        draw.polygon(tip, fill=ACCENT)
        center = min(x1, x2) + abs(x2 - x1) / 2
        box = draw.textbbox((0, 0), label, font=font(17))
        draw.rectangle(
            (center - (box[2] - box[0]) / 2 - 8, y - 31, center + (box[2] - box[0]) / 2 + 8, y - 7),
            fill=BG,
        )
        draw.text((center, y - 29), label, anchor="ma", fill=MUTED, font=font(17))

    image.save(DOCS / "agent-sequence.png", optimize=True)


if __name__ == "__main__":
    DOCS.mkdir(parents=True, exist_ok=True)
    interactions()
    sequence()
    print("Generated docs/agent-interactions.png and docs/agent-sequence.png")
