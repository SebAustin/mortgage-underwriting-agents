"""Build a Devpost image gallery: curated frames fitted to a 3:2 canvas on brand bg.

Each source image (16:9 scene frame or a real UI screenshot) is contained — never cropped —
on an 1800x1200 (3:2) background matching the deck palette, then saved as an optimized PNG
(well under Devpost's 5 MB limit). Output: devpost/gallery/NN_name.png.
"""

from __future__ import annotations

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "devpost", "gallery")
BG = (11, 14, 20)  # #0b0e14
SIZE = (1800, 1200)  # 3:2

# (source path relative to repo root, output name) — story order.
GALLERY = [
    ("video/frames/01_title.png", "01_overview"),
    ("video/frames/03_architecture.png", "02_architecture"),
    ("video/frames/04_clean.png", "03_clean_approve_run"),
    ("video/frames/05_borderline.png", "04_borderline_conditional_run"),
    ("video/frames/06_hitl.png", "05_human_gate_decision_support"),
    ("video/assets/shots/case_gate_a_vp.png", "06_loan_officer_desk_ui"),
    ("video/frames/07_durable.png", "07_durable_human_in_the_loop"),
    ("video/frames/08_fraud.png", "08_fraud_aml_escalation"),
    ("video/frames/09_cloud.png", "09_same_code_on_uipath"),
    ("video/frames/10_closing.png", "10_built_with_claude_code"),
]


def fit(src: str, dst: str) -> tuple[int, int]:
    img = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", SIZE, BG)
    scaled = img.copy()
    scaled.thumbnail(SIZE, Image.LANCZOS)  # contain, preserve aspect
    x = (SIZE[0] - scaled.width) // 2
    y = (SIZE[1] - scaled.height) // 2
    canvas.paste(scaled, (x, y))
    canvas.save(dst, "PNG", optimize=True)
    return os.path.getsize(dst), 0


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for rel, name in GALLERY:
        src = os.path.join(ROOT, rel)
        dst = os.path.join(OUT, f"{name}.png")
        size, _ = fit(src, dst)
        print(f"  {name:38} {size/1024:6.0f} KB")
    print(f"\n{len(GALLERY)} images → {OUT}")


if __name__ == "__main__":
    main()
