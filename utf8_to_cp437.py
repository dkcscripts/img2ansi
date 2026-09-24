#!/usr/bin/env python3
"""
Convert a UTF-8 text file to CP437 encoding (for ANSI art editors like Moebius).
Usage: python utf8_to_cp437.py <input_file> [output_file]
"""

import sys
import os


def convert(input_path, output_path=None):
    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".ans"

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for unmappable characters
    bad = []
    for i, ch in enumerate(content):
        try:
            ch.encode("cp437")
        except (UnicodeEncodeError, ValueError):
            bad.append((i, repr(ch), hex(ord(ch))))

    if bad:
        print(f"Warning: {len(bad)} character(s) have no CP437 equivalent and will be replaced with '?':")
        for pos, ch, code in bad[:20]:
            print(f"  pos {pos}: {ch} ({code})")
        if len(bad) > 20:
            print(f"  ... and {len(bad) - 20} more")

    encoded = content.encode("cp437", errors="replace")

    with open(output_path, "wb") as f:
        f.write(encoded)

    print(f"Input : {input_path} ({len(content)} chars)")
    print(f"Output: {output_path} ({len(encoded)} bytes)")
    if not bad:
        print("All characters mapped cleanly to CP437.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utf8_to_cp437.py <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else None
    convert(input_file, output_file)
