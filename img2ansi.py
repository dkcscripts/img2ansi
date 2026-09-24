#!/usr/bin/env python3
"""
img2ansi.py — Convert image to ANSI 256-color block art.

Uses ▄ (U+2584 LOWER HALF BLOCK) and ▀ (U+2580 UPPER HALF BLOCK) with
256-color fg/bg to pack 2 rows per terminal line, doubling vertical resolution.

Transparent pixels emit a plain space so the terminal background shows through.
Semi-transparent pixels are composited against --bg before color mapping.

Usage:
    python img2ansi.py <image>
    python img2ansi.py <image> --out result.ans
"""

import argparse
import sys
from PIL import Image

# Ensure stdout uses UTF-8 encoding for Unicode block characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# ---------------------------------------------------------------------------
# xterm-256 color mapping
# ---------------------------------------------------------------------------

# 6×6×6 cube: indices 16–231
# Cube level values: 0, 95, 135, 175, 215, 255
_CUBE_VALS = (0, 95, 135, 175, 215, 255)
# Breakpoints: midpoints between adjacent cube levels
_CUBE_BREAKS = (48, 115, 155, 195, 235)  # < break → lower index


def _cube_idx(v: int) -> int:
    for i, b in enumerate(_CUBE_BREAKS):
        if v < b:
            return i
    return 5


# Grayscale ramp: indices 232–255, values 8, 18, 28, …, 238
_GS_BASE = 8
_GS_STEP = 10
_GS_LEN  = 24  # 232..255


def rgb_to_256(r: int, g: int, b: int) -> int:
    """Map an (r,g,b) triple to the nearest xterm 256-color index (16–255)."""
    # --- 6×6×6 cube candidate ---
    ri, gi, bi = _cube_idx(r), _cube_idx(g), _cube_idx(b)
    cube_idx = 16 + 36 * ri + 6 * gi + bi
    cr, cg, cb = _CUBE_VALS[ri], _CUBE_VALS[gi], _CUBE_VALS[bi]
    cube_dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2

    # --- grayscale ramp candidate ---
    luma = (r * 299 + g * 587 + b * 114) // 1000
    gs_i = max(0, min(_GS_LEN - 1, round((luma - _GS_BASE) / _GS_STEP)))
    gs_idx = 232 + gs_i
    gs_val = _GS_BASE + gs_i * _GS_STEP
    gs_dist = (r - gs_val) ** 2 + (g - gs_val) ** 2 + (b - gs_val) ** 2

    return cube_idx if cube_dist <= gs_dist else gs_idx


# ---------------------------------------------------------------------------
# ANSI escape helpers
# ---------------------------------------------------------------------------

RESET       = "\033[0m"
LOWER_HALF  = "\u2584"  # ▄  fills lower half of cell
UPPER_HALF  = "\u2580"  # ▀  fills upper half of cell


def _fg(idx: int) -> str:
    return f"\033[38;5;{idx}m"


def _bg(idx: int) -> str:
    return f"\033[48;5;{idx}m"


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def _composite(img: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    """Alpha-composite image onto a solid bg; return RGB."""
    if img.mode not in ("RGBA", "LA", "PA"):
        return img.convert("RGB")
    rgba = img.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (*bg, 255))
    background.paste(rgba, mask=rgba.split()[3])
    return background.convert("RGB")


def image_to_ansi(
    img: Image.Image,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    alpha_threshold: int = 128,
) -> str:
    """
    Convert a PIL Image to an ANSI-escaped string.

    Two image rows are packed into one terminal line using half-block chars:
      ▄ (U+2584): bg = upper pixel color, fg = lower pixel color
      ▀ (U+2580): fg = upper pixel color, lower half = terminal background
      ▄ (no bg) : fg = lower pixel color, upper half = terminal background
      ' '       : both pixels transparent — terminal background shows through

    Partial alpha (0 < a < alpha_threshold) is composited against bg_color.
    Fully transparent pixels (a < alpha_threshold) let the terminal bg bleed in.
    """
    has_alpha = img.mode in ("RGBA", "LA", "PA")
    rgba  = img.convert("RGBA") if has_alpha else None
    rgb   = _composite(img, bg_color)          # colors for opaque pixels

    w, h  = rgb.size
    px    = rgb.load()
    apx   = rgba.load() if rgba else None
    out_lines: list[str] = []

    def is_opaque(x: int, y: int) -> bool:
        if apx is None:
            return True
        return apx[x, y][3] >= alpha_threshold

    for y in range(0, h, 2):
        chars: list[str] = []
        for x in range(w):
            upper_vis = is_opaque(x, y)
            lower_vis = is_opaque(x, y + 1) if y + 1 < h else False

            if upper_vis and lower_vis:
                # normal: bg=upper, fg=lower, ▄
                r1, g1, b1 = px[x, y]
                r2, g2, b2 = px[x, y + 1]
                chars.append(
                    f"{_bg(rgb_to_256(r1, g1, b1))}"
                    f"{_fg(rgb_to_256(r2, g2, b2))}"
                    f"{LOWER_HALF}"
                )
            elif upper_vis:
                # only upper visible: ▀ with fg=upper, terminal bg for lower
                r1, g1, b1 = px[x, y]
                chars.append(f"{_fg(rgb_to_256(r1, g1, b1))}{UPPER_HALF}")
            elif lower_vis:
                # only lower visible: ▄ with fg=lower, terminal bg for upper
                r2, g2, b2 = px[x, y + 1]
                chars.append(f"{_fg(rgb_to_256(r2, g2, b2))}{LOWER_HALF}")
            else:
                # both transparent: plain space, terminal bg shows
                chars.append(" ")

        out_lines.append("".join(chars) + RESET)

    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an image to ANSI 256-color block art."
    )
    parser.add_argument("image", help="Path to input image (any format Pillow supports)")
    parser.add_argument(
        "--bg",
        metavar=("R", "G", "B"),
        nargs=3,
        type=int,
        default=[0, 0, 0],
        help="Blend color for semi-transparent pixels (alpha >= threshold but < 255), as R G B (default: 0 0 0). No effect on fully opaque or fully transparent pixels.",
    )
    parser.add_argument(
        "--alpha-threshold",
        metavar="N",
        type=int,
        default=128,
        help="Alpha cutoff 0-255: pixels below this are transparent (default: 128)",
    )
    parser.add_argument(
        "--out",
        metavar="FILE",
        help="Also save raw ANSI output to FILE (printed to stdout regardless)",
    )
    args = parser.parse_args()

    try:
        img = Image.open(args.image)
    except FileNotFoundError:
        print(f"Error: file not found — {args.image}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error opening image: {exc}", file=sys.stderr)
        sys.exit(1)

    result = image_to_ansi(img, bg_color=tuple(args.bg), alpha_threshold=args.alpha_threshold)

    # Always print to stdout
    print(result)

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(result + "\n")
            print(f"[saved → {args.out}]", file=sys.stderr)
        except OSError as exc:
            print(f"Error writing output: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
