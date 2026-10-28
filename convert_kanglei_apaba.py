#!/usr/bin/env python3
"""
Convert text typed in the legacy "Kanglei Apaba" Meetei Mayek font into
real Unicode Meetei Mayek (U+ABC0-U+ABFF) UTF-8 text.

Accepts either a PDF or a plain .txt file as input; the input kind is
autodetected by sniffing the file (a leading "%PDF-" magic number), not by
trusting the file extension.

Background
----------
"Kanglei Apaba" (by IMMTRI, Imphal, 2003) is a pre-Unicode "ASCII hack" font:
it draws Meetei Mayek letterforms at ordinary Latin code points (a-z, A-Z, a
few digits and punctuation marks). A document built with this font contains
plain Latin text under the hood -- e.g. the heading "Khongjom Parba" is
literally stored as the bytes "SoZjoM prb". There is no ToUnicode CMap (in a
PDF) or other metadata tying those bytes back to the real Meetei Mayek
script, so ordinary text extraction (copy-paste, `pdftotext`, opening a .txt
export, etc.) produces Latin gibberish instead of Meetei Mayek.

This script:
  1. Autodetects whether the input is a PDF or plain text.
  2. For a PDF: sanity-checks that it embeds a font named "Kanglei Apaba",
     then extracts the raw text with `pdftotext -raw` (poppler-utils).
     For plain text: reads the file directly.
  3. Applies the character-substitution table below to turn the Latin
     stand-in bytes into real Unicode Meetei Mayek codepoints.
  4. Writes the result as UTF-8 text.

The substitution table was reverse-engineered by extracting the embedded
TrueType font from a sample PDF and shape-matching every glyph against Noto
Sans Meetei Mayek, then validated against known words/names that fell out of
decoding ("Khongjom Parba", "British", "Shastri", "Tokendrajit", "Binodini").
See README.md in this folder for the full methodology and glyph tables.

IMPORTANT: this mapping is specific to the "Kanglei Apaba" font. Other legacy
Meetei Mayek fonts (there were several competing ones) use different, mutually
incompatible keyboard layouts and will NOT convert correctly with this script.
A plain .txt input is assumed to already be Kanglei-Apaba-encoded Latin text
(e.g. exported from a word processor that had the font installed) -- there is
no font embedded in a .txt file to sanity-check against, so no such warning
is possible for that path.

Requirements
------------
- Python 3
- `pdftotext` from poppler-utils on PATH, only needed for PDF input
  (macOS: `brew install poppler`)

Usage
-----
    python3 convert_kanglei_apaba.py input.pdf
    python3 convert_kanglei_apaba.py input.txt
    python3 convert_kanglei_apaba.py input.pdf output.txt

If output.txt is omitted, it defaults to "<input stem> - unicode.txt" next
to the input file.
"""
import re
import subprocess
import sys
from pathlib import Path

# ASCII character -> Unicode Meetei Mayek codepoint.
# Grouped and commented by role; see README.md for the full derivation,
# confidence notes, and glyph comparison images.
MAPPING = {
    # --- Dependent vowel signs (superscript diacritics) ---
    'a': 0xABE5,  # ANAP    (aa)
    'e': 0xABE6,  # YENAP   (e)
    'i': 0xABE4,  # INAP    (i)
    'o': 0xABE3,  # ONAP    (o)
    'u': 0xABE8,  # UNAP    (u)
    'x': 0xABEA,  # NUNG    (anusvara / -ng nasalization)
    'E': 0xABE9,  # CHEINAP (ei)
    'O': 0xABE7,  # SOUNAP  (ou)  -- medium confidence, see README

    # --- Base consonants (lowercase = plain form) ---
    'b': 0xABD5,  # BA
    'c': 0xABC6,  # CHIL
    'd': 0xABD7,  # DIL
    'f': 0xABD0,  # PHAM
    'g': 0xABD2,  # GOK
    'h': 0xABCD,  # HUK
    'j': 0xABD6,  # JIL
    'k': 0xABC0,  # KOK
    'l': 0xABC2,  # LAI
    'm': 0xABC3,  # MIT
    'n': 0xABC5,  # NA
    'p': 0xABC4,  # PA
    'r': 0xABD4,  # RAI
    's': 0xABC1,  # SAM
    't': 0xABC7,  # TIL
    'w': 0xABCB,  # WAI
    'y': 0xABCC,  # YANG
    'z': 0xABC9,  # NGOU

    # --- Vowel-carrier base letters (uppercase of the matching vowel key) ---
    'A': 0xABD1,  # ATIYA (a)
    'I': 0xABCF,  # I     (ee)
    'U': 0xABCE,  # UN    (u)

    # --- Aspirated consonants / final ("lonsum") consonant forms (uppercase) ---
    'S': 0xABC8,  # KHOU        (aspirate of KOK)
    'Z': 0xABE1,  # NGOU_LONSUM (final -ng)
    'M': 0xABDD,  # MIT_LONSUM  (final -m)
    'K': 0xABDB,  # KOK_LONSUM  (final -k)
    'N': 0xABDF,  # NA_LONSUM   (final -n)
    'L': 0xABDC,  # LAI_LONSUM  (final -l)
    'P': 0xABDE,  # PA_LONSUM   (final -p)
    'T': 0xABE0,  # TIL_LONSUM  (final -t)
    'D': 0xABD9,  # DHOU        (aspirate of DIL)
    'G': 0xABD8,  # GHOU        (aspirate of GOK)
    'H': 0xABCA,  # THOU        (aspirate of TIL)

    # --- Conjunct / punctuation ---
    'C': 0xABED,  # APUN IYEK (consonant-cluster "killer" stroke, e.g. st/br/dr)
    '>': 0xABEB,  # CHEIKHEI  (sentence-final double danda)
    ',': 0xABEC,  # LUM IYEK  (tentative -- rare in sample text, low confidence)

    # --- Digits ---
    '1': 0xABF1,
    '8': 0xABF8,
    '9': 0xABF9,

    # --- Passthrough ---
    ' ': ord(' '),
    '\n': ord('\n'),
    '\t': ord('\t'),
}

# Characters Word's autocorrect already turned into real Unicode punctuation
# (curly quotes) before the PDF was made -- pass them through unchanged.
PASSTHROUGH_LITERAL = {'“', '”', '‘', '’'}


def sniff_input_kind(path):
    """Autodetect 'pdf' vs 'text' by magic number, ignoring the file extension."""
    with open(path, "rb") as f:
        head = f.read(5)
    return "pdf" if head.startswith(b"%PDF-") else "text"


def check_font(pdf_path):
    """Warn (but don't abort) if the PDF doesn't embed a 'Kanglei Apaba' font."""
    with open(pdf_path, "rb") as f:
        data = f.read()
    basefonts = re.findall(rb"/BaseFont\s*/([^\s/>\]]+)", data)
    names = sorted(set(b.decode("latin1", "replace").replace("#20", " ") for b in basefonts))
    if not any("Kanglei" in n for n in names):
        print(f"WARNING: no font named 'Kanglei Apaba' found in {pdf_path!r}.", file=sys.stderr)
        print(f"  Fonts found in this PDF: {names}", file=sys.stderr)
        print("  The mapping in this script is specific to Kanglei Apaba; "
              "output will be garbage for any other font.\n", file=sys.stderr)


def extract_raw_text_from_pdf(pdf_path):
    """Extract text in physical/typing order via poppler's pdftotext."""
    try:
        result = subprocess.run(
            ["pdftotext", "-raw", pdf_path, "-"],
            capture_output=True, check=True,
        )
    except FileNotFoundError:
        sys.exit(
            "Error: 'pdftotext' not found on PATH.\n"
            "Install poppler-utils, e.g. on macOS: brew install poppler"
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"pdftotext failed:\n{e.stderr.decode(errors='replace')}")
    return result.stdout.decode("utf-8", errors="replace")


def read_raw_text_from_txt(txt_path):
    """Read a plain-text file, tolerating either UTF-8 or Latin-1 source encoding."""
    data = Path(txt_path).read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1")


def load_input(path):
    """Autodetect input kind and return its raw (Kanglei-Apaba-encoded) text."""
    kind = sniff_input_kind(path)
    if kind == "pdf":
        check_font(path)
        return extract_raw_text_from_pdf(path)
    return read_raw_text_from_txt(path)


def convert(text):
    out = []
    unmapped = set()
    for ch in text:
        if ch in MAPPING:
            out.append(chr(MAPPING[ch]))
        elif ch in PASSTHROUGH_LITERAL:
            out.append(ch)
        else:
            out.append(ch)
            if ch.strip():
                unmapped.add(ch)
    return "".join(out), unmapped


def default_output_path(input_path):
    p = Path(input_path)
    return p.with_name(f"{p.stem} - unicode.txt")


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(f"Usage: {sys.argv[0]} input.pdf|input.txt [output.txt]")

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) == 3 else default_output_path(in_path)

    raw_text = load_input(in_path)
    converted_text, unmapped = convert(raw_text)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(converted_text)

    print(f"Wrote Unicode Meetei Mayek text to {out_path!r}")
    if unmapped:
        print(
            f"NOTE: {len(unmapped)} character(s) had no mapping and were "
            f"passed through as-is (likely source typos or unused keys): "
            f"{sorted(unmapped)}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
