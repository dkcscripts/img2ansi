# img2ansi

Convert any image to ANSI 256-color block art in your terminal.

## How it works

Uses `▄` (U+2584 LOWER HALF BLOCK) and `▀` (U+2580 UPPER HALF BLOCK) with independent foreground/background colors to pack **two image rows into one terminal line**, doubling vertical resolution.

```
upper pixel → background color  ┐
                                ├─ one terminal cell
lower pixel → foreground color  ┘
```

Colors are mapped to the nearest **xterm-256** index via the 6×6×6 color cube (indices 16–231) and grayscale ramp (indices 232–255).

## Requirements

```bash
pip install Pillow
```

## Usage

```bash
# print to terminal
python img2ansi.py <image>

# also save raw ANSI to file
python img2ansi.py <image> --out output.ans

# custom blend color for semi-transparent pixels (feathered edges, drop shadows, etc.)
# no effect on images with hard-edged transparency (alpha is 0 or 255 only)
python img2ansi.py sprite.png --bg 30 30 46

# adjust alpha cutoff (default 128; lower = more pixels treated as opaque)
python img2ansi.py sprite.png --alpha-threshold 64
```

### Examples

```bash
python img2ansi.py photo.png
python img2ansi.py art.jpg --out art.ans
python img2ansi.py sprite.png --bg 30 30 46 --alpha-threshold 64
```

## Image sizing

The script uses the image **as-is** - one image pixel maps to one terminal character cell. For best results, resize your image to match your terminal width before converting:

```python
from PIL import Image
img = Image.open("photo.png").resize((80, 40))
img.save("photo_small.png")
```

Or with ImageMagick:

```bash
magick photo.png -resize 80x40! photo_small.png
```

## Transparency

Transparent pixels emit a plain space with **no color codes**, so your actual terminal background shows through naturally - no need to match `--bg` to your terminal theme.

Semi-transparent pixels (feathered edges, drop shadows) are composited against `--bg` before color mapping.

| upper pixel | lower pixel | output |
|---|---|---|
| opaque | opaque | `▄` bg=upper, fg=lower |
| opaque | transparent | `▀` fg=upper, terminal bg in lower half |
| transparent | opaque | `▄` fg=lower, terminal bg in upper half |
| transparent | transparent | ` ` space - terminal bg only |

## Output file

`--out FILE` saves the raw ANSI escape sequences to a file. Replay it anytime:

```bash
cat output.ans
```

---

## utf8_to_cp437.py

Convert UTF-8 text files to **CP437 encoding** for ANSI art editors (e.g., Moebius, ACiDDraw).

CP437 (Code Page 437) is the character encoding used by classic DOS and ANSI art systems. This script handles unmappable characters by replacing them with `?` and reports any conversions made.

### Usage

```bash
# Convert file (saves as .ans)
python utf8_to_cp437.py <input_file>

# Specify custom output file
python utf8_to_cp437.py <input_file> <output_file>
```

### Examples

```bash
python utf8_to_cp437.py notes.txt              # → notes.ans
python utf8_to_cp437.py text.txt output.ans   # → output.ans
```

The script warns about characters with no CP437 equivalent and logs the conversion summary (input character count, output byte count).
