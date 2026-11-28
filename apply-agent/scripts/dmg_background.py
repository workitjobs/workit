"""Draw the DMG window's background (KAN-950): assets/dmg-background.png and its @2x copy, white fading to a faint
violet, with WorkIt's violet arrow between the app's icon and Applications where build_app.DMG_LAYOUT puts them.

    uv run --no-project --with pillow python scripts/dmg_background.py      (from apply-agent/)

Run it after a change to DMG_LAYOUT, and commit both pictures. Pillow draws them here only, so it is no dependency of
Apply's. It draws at four times the size and scales down, for smooth edges.
"""

import build_app as build  # DMG_LAYOUT and the pictures' path, kept in one place
from PIL import Image, ImageDraw

SCALE = 4
TOP, BOTTOM = (255, 255, 255), (243, 240, 250)  # white to a faint violet
BRAND = (109, 63, 216)  # WorkIt's violet, --color-brand (#6d3fd8)
LENGTH, HEAD, WIDTH = 72, 22, 9  # the arrow, in points: short and thick (the user's pick, 2026-11-27)


def main() -> None:
    (_, (width, height)), places = build.DMG_LAYOUT["window_rect"], build.DMG_LAYOUT["icon_locations"]
    (left, y), (right, _) = sorted(places.values())
    image = Image.new("RGB", (width * SCALE, height * SCALE))
    draw = ImageDraw.Draw(image)
    for row in range(height * SCALE):
        share = row / (height * SCALE - 1)
        draw.line([(0, row), (width * SCALE, row)],
                  fill=tuple(round(top + (bottom - top) * share) for top, bottom in zip(TOP, BOTTOM)))

    def stroke(*points: tuple[float, float]) -> None:
        drawn = [(x * SCALE, y * SCALE) for x, y in points]
        thick = WIDTH * SCALE
        draw.line(drawn, fill=BRAND, width=thick, joint="curve")
        for x, y in drawn:  # round ends
            draw.ellipse([x - thick / 2, y - thick / 2, x + thick / 2, y + thick / 2], fill=BRAND)

    tip = (left + right + LENGTH) / 2  # centred between the two icons
    stroke((tip - LENGTH, y), (tip - 2, y))
    stroke((tip - HEAD, y - HEAD), (tip, y), (tip - HEAD, y + HEAD))
    picture = build.ROOT / build.DMG_BACKGROUND
    image.resize((width * 2, height * 2), Image.LANCZOS).save(picture.with_name(f"{picture.stem}@2x.png"), optimize=True)
    image.resize((width, height), Image.LANCZOS).save(picture, optimize=True)
    print(f"Drew {picture} and its @2x copy.")


if __name__ == "__main__":
    main()
