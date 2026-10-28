# Kanglei Apaba → Unicode Meetei Mayek Converter

_Mostly written by Anthropic Claude, but I contributed quite a bit._

Converts PDFs or plain `.txt` files that were typed in the legacy
**"Kanglei Apaba"** Meetei Mayek font into real Unicode Meetei Mayek
(block **U+ABC0–U+ABFF**). Input kind (PDF vs. plain text) is autodetected
by sniffing the file's contents, not by trusting its extension.

Worked example in this repository:
- Input: [`docs/my inspiration & khongjom parva.pdf`](docs/my%20inspiration%20&%20khongjom%20parva.pdf)
- Output: [`docs/khongjom parva - unicode.txt`](docs/khongjom%20parva%20-%20unicode.txt)

## The problem

The PDF looks like Meetei Mayek script when opened, but it isn't Unicode text —
it's ordinary Latin text (produced by Word 2010) styled with an embedded font
called **Kanglei Apaba** (by IMMTRI, Imphal, dated 2003). That font is a
pre-Unicode "ASCII hack": it redraws ordinary Latin letters, a handful of
digits, and a few punctuation marks as Meetei Mayek glyphs. Nothing about the
underlying character codes changes — the heading that displays as **"Khongjom
Parba"** is literally stored in the PDF as the bytes `SoZjoM prb`.

Because there's no `ToUnicode` CMap connecting those bytes to the real Meetei
Mayek code points, any standard text extraction (copy-paste, `pdftotext`,
search, screen readers, indexing, etc.) produces Latin gibberish instead of
usable Meetei Mayek text. This is the same class of problem as legacy
"typewriter" fonts for Devanagari (Kruti Dev, Chanakya) or Bengali — visually
correct, structurally invalid.

## How the mapping was reverse-engineered

1. **Identify the font.** `pdffonts` on the PDF showed an embedded TrueType
   font `ABCDEE+Kanglei Apaba` with WinAnsi encoding and no `ToUnicode` map —
   i.e. glyphs sitting at ordinary Latin code points with no way to recover
   their real identity from the PDF alone.

2. **Extract the embedded font.** The font file itself is a normal PDF object
   (`/FontFile2`). Pulling it out (`qpdf --show-object=N --filtered-stream-data`)
   and loading it with `fontTools` gave direct access to the real glyph
   outlines the font draws for each Latin key — e.g. what shape actually gets
   drawn when the document says `S`, `o`, `Z`, etc.

3. **Automated shape matching.** Every mapped ASCII character was rendered in
   Kanglei Apaba, and every candidate Unicode Meetei Mayek letter/vowel
   sign/digit was rendered in Google's **Noto Sans Meetei Mayek** (a real
   Unicode font). Each pair of glyph bitmaps was compared pixel-by-pixel
   (after cropping/centering/scaling to 64×64) to find the best-matching
   Unicode target for every Kanglei Apaba key. See:
   - [`assets/kanglei_apaba_glyphs.png`](assets/kanglei_apaba_glyphs.png) — every mapped ASCII key rendered in Kanglei Apaba
   - [`assets/unicode_reference_glyphs.png`](assets/unicode_reference_glyphs.png) — the Unicode Meetei Mayek reference chart rendered the same way

4. **Validation against known plaintext (the crib).** Shape matching alone is
   imprecise for visually similar letter/final-form pairs. The decisive
   confirmation came from decoding actual words in the document and checking
   they were real: the heading decoded to **"Khongjom Parba"** — an exact
   match for the PDF's filename and the title of a well-known Manipuri ballad
   about the 1891 Battle of Khongjom (Anglo-Manipur War). The body text
   likewise decoded proper nouns correctly: **"British"**, **"Shastri"**,
   **"Tokendrajit"** (Tikendrajit, the historical Manipuri prince), and
   **"Binodini"**. That's strong, specific, checkable confirmation that the
   mapping is right, not just plausible.

5. **One character (`C`) turned out to be a diacritic, not a letter.** It
   didn't fit any single consonant, but it consistently sat between two
   consonants in loanwords requiring clusters: `sastCriy` → "shastri",
   `bCritis` → "british", `tokeNdCrajiT` → "tokendrajit". That's the
   signature of **APUN IYEK** (U+ABED), the Meetei Mayek "killer stroke" that
   suppresses a consonant's inherent vowel to form a cluster (st, br, dr).

The resulting scheme is a clean, mnemonic keyboard layout, once decoded:

- Lowercase vowel keys `a e i o u` → the five basic vowel signs.
- Uppercase of those same keys `A I U` → the "vowel-carrier" base letters
  used to spell a vowel at the start of a word (there's no `O`/`E` carrier
  needed the same way, since Meetei Mayek only has dedicated carrier letters
  for a/i/u).
- Lowercase consonant keys → base consonant letters, chosen mnemonically
  (`k`=KOK, `p`=PA, `s`=SAM, `r`=RAI, `t`=TIL, `l`=LAI, `n`=NA, `m`=MIT, `j`=JIL,
  `y`=YANG, `w`=WAI, `h`=HUK, `c`=CHIL, `d`=DIL, `f`=PHAM(pha), `z`=NGOU(nga),
  `g`=GOK, `b`=BA).
- Uppercase consonant keys → either the aspirated counterpart (`S`=KHOU/kha,
  `D`=DHOU/dha, `G`=GHOU/gha, `H`=THOU/tha) or the "lonsum" (word/syllable
  -final) form of the same consonant (`K`=KOK final, `Z`=NGOU final, `M`=MIT
  final, `N`=NA final, `L`=LAI final, `P`=PA final, `T`=TIL final).
- `C` → APUN IYEK, the consonant-cluster killer stroke.
- `>` → CHEIKHEI, the Meetei sentence-final double danda (used exactly where
  you'd expect a full stop in the source text).
- `1`, `8`, `9` → the matching Meetei Mayek digits (the only digits that
  happened to appear in the sample document; the mapping table includes only
  what was actually observed, see caveats below).

## Full character mapping table

| Key | Unicode | Name | Role | Confidence |
|---|---|---|---|---|
| `a` | U+ABE5 | ANAP | vowel sign "aa" | high |
| `e` | U+ABE6 | YENAP | vowel sign "e" | high |
| `i` | U+ABE4 | INAP | vowel sign "i" | high |
| `o` | U+ABE3 | ONAP | vowel sign "o" | high (resolved via crib; near-tie with ANAP on raw shape score) |
| `u` | U+ABE8 | UNAP | vowel sign "u" | high |
| `x` | U+ABEA | NUNG | anusvara / -ng nasalization | high |
| `E` | U+ABE9 | CHEINAP | vowel sign "ei" | high |
| `O` | U+ABE7 | SOUNAP | vowel sign "ou" | **medium** (weak raw shape score; based on mnemonic + convention from other Meetei fonts) |
| `b` | U+ABD5 | BA | consonant "ba" | high |
| `c` | U+ABC6 | CHIL | consonant "ca" | high |
| `d` | U+ABD7 | DIL | consonant "da" | high |
| `f` | U+ABD0 | PHAM | consonant "pha" | high |
| `g` | U+ABD2 | GOK | consonant "ga" | high (resolved via crib: common "-gi" genitive suffix) |
| `h` | U+ABCD | HUK | consonant "ha" | high |
| `j` | U+ABD6 | JIL | consonant "ja" | high (confirmed via crib) |
| `k` | U+ABC0 | KOK | consonant "ka" | high |
| `l` | U+ABC2 | LAI | consonant "la" | high |
| `m` | U+ABC3 | MIT | consonant "ma" | high |
| `n` | U+ABC5 | NA | consonant "na" | high |
| `p` | U+ABC4 | PA | consonant "pa" | high (confirmed via crib) |
| `r` | U+ABD4 | RAI | consonant "ra" | high (confirmed via crib) |
| `s` | U+ABC1 | SAM | consonant "sa" | high |
| `t` | U+ABC7 | TIL | consonant "ta" | medium-high |
| `w` | U+ABCB | WAI | consonant "wa" | high (mnemonic w→wai; near-tie with CHIL on raw shape score) |
| `y` | U+ABCC | YANG | consonant "ya" | high |
| `z` | U+ABC9 | NGOU | consonant "nga" | medium-high |
| `A` | U+ABD1 | ATIYA | vowel-carrier "a" | high |
| `I` | U+ABCF | I | vowel-carrier "ee" | high |
| `U` | U+ABCE | UN | vowel-carrier "u" | high |
| `S` | U+ABC8 | KHOU | aspirate of KOK ("kha") | high (confirmed via crib) |
| `Z` | U+ABE1 | NGOU LONSUM | final "-ng" | high (confirmed via crib) |
| `M` | U+ABDD | MIT LONSUM | final "-m" | high (confirmed via crib) |
| `K` | U+ABDB | KOK LONSUM | final "-k" | high |
| `N` | U+ABDF | NA LONSUM | final "-n" | high |
| `L` | U+ABDC | LAI LONSUM | final "-l" | medium (raw shape score slightly favored BHAM; overridden by mnemonic pairing with `l`) |
| `P` | U+ABDE | PA LONSUM | final "-p" | high |
| `T` | U+ABE0 | TIL LONSUM | final "-t" | high |
| `D` | U+ABD9 | DHOU | aspirate of DIL ("dha") | high |
| `G` | U+ABD8 | GHOU | aspirate of GOK ("gha") | high |
| `H` | U+ABCA | THOU | aspirate of TIL ("tha") | high |
| `C` | U+ABED | APUN IYEK | consonant-cluster killer stroke | high (confirmed via crib: "shastri", "british", "tokendrajit") |
| `>` | U+ABEB | CHEIKHEI | sentence-final double danda | medium-high |
| `,` | U+ABEC | LUM IYEK | (tentative) | **low** — rare in the sample text |
| `1` | U+ABF1 | digit 1 | | high |
| `8` | U+ABF8 | digit 8 | | high |
| `9` | U+ABF9 | digit 9 | | high |

Digits 0, 2–7 and several punctuation/symbol keys (`!`, `"`, `F`, `J`, `Q`, `R`,
`V`, `W`, `X`, `Y`, `q`, `v`) either don't appear in the font at all (no glyph
defined — confirmed via the font's cmap) or never appeared in the sample
document, so they aren't in the table. If you run this on a PDF that uses one
of those keys, the script will pass it through unchanged and flag it as
unmapped — treat that as a signal to extend the table (see "Extending the
mapping" below), not as something safe to ignore.

A stray uppercase `B` in the sample document (`Bbinodini`) did not decode to
anything sensible and is almost certainly a typo in the original Word
document (the name "Binodini" already decodes correctly elsewhere without
it). The script passes unmapped characters through unchanged and reports them
as a warning so you can spot cases like this.

## Files in this repository

- `convert_kanglei_apaba.py` — the converter (see Usage below).
- `assets/kanglei_apaba_glyphs.png` — every ASCII key rendered in Kanglei Apaba.
- `assets/unicode_reference_glyphs.png` — Unicode Meetei Mayek reference chart (Noto Sans Meetei Mayek), same layout, for visual comparison.
- `assets/sample_output_render.png` — the converted output re-rendered in a real Unicode Meetei Mayek font, as a sanity check.
- `docs/my inspiration & khongjom parva.pdf` — the original sample PDF.
- `docs/khongjom parva - unicode.txt` — its converted output.
- `docs/meetei-mayek-kb-for-mac-os.png`, `docs/meetei-mayek-kb-select-mac-os.png` — screenshots of the Meetei Mayek keyboard input source on macOS.
- `LICENSE` — MIT License.

## Usage

Requires Python 3. `pdftotext` (from poppler-utils) is only needed for PDF
input:

```bash
brew install poppler   # if not already installed
```

Run:

```bash
python3 convert_kanglei_apaba.py "input.pdf"                  # -> "input - unicode.txt"
python3 convert_kanglei_apaba.py "input.txt"                  # -> "input - unicode.txt"
python3 convert_kanglei_apaba.py "input.pdf" "output.txt"     # explicit output path
```

The output path is optional; if omitted it defaults to
`"<input stem> - unicode.txt"` next to the input file.

The input kind is **autodetected** by reading the file's first bytes (a
leading `%PDF-` magic number means PDF; anything else is treated as plain
text) — so a PDF with a `.txt` extension or a text file with a `.pdf`
extension is still handled correctly.

The script will:
1. For a PDF: warn (but not stop) if it doesn't appear to embed a font named
   "Kanglei Apaba" — the mapping is specific to that font and will produce
   garbage for any other legacy Meetei font. Then extract the raw text with
   `pdftotext -raw`.
2. For plain text: read the file directly (UTF-8, falling back to Latin-1),
   on the assumption it's already Kanglei-Apaba-encoded Latin text (e.g.
   exported from a word processor that had the font installed). There's no
   embedded font to sanity-check in a `.txt` file, so no such warning is
   possible on this path — double-check the source yourself.
3. Substitute characters per the table above.
4. Write UTF-8 Unicode Meetei Mayek text to the output path.
5. Print a warning listing any characters it didn't know how to convert.

To read/verify the output, open it in an editor/viewer with a Unicode Meetei
Mayek font installed, e.g. **Noto Sans Meetei Mayek**
(https://fonts.google.com/noto/specimen/Noto+Sans+Meetei+Mayek).

## Caveats / where to double-check

- This mapping was derived from **one sample document**. It covers every
  character that document actually used, plus everything visible in the
  font's glyph set, but a longer or different document could exercise keys
  we never saw (the unused digits/punctuation above).
- A few assignments (`O`→SOUNAP, `L`→LAI LONSUM, `,`→LUM IYEK) rested more on
  mnemonic convention than on strong shape-match or crib evidence. If output
  looks wrong specifically around long "ou" vowels, a final "-l", or commas,
  those are the first places to check.
- Ideally, have a Meithei/Manipuri reader skim the converted output for
  sense, especially in a new document with vocabulary not covered by this
  sample.

## Extending the mapping

If you run this on another Kanglei Apaba PDF and get unmapped-character
warnings:

1. Note which characters are unmapped and roughly where they occur in the
   source PDF.
2. Extract the embedded font (`qpdf --show-object=<N> --filtered-stream-data
   input.pdf > font.ttf`, where `<N>` is the object number found via
   `grep -o '/FontFile2 [0-9]* 0 R' input.pdf`) and inspect it with
   `fontTools` (`ttx -l font.ttf`, or render specific characters with Pillow's
   `ImageFont.truetype`) to see what glyph shape that key actually draws.
3. Compare against `assets/unicode_reference_glyphs.png` (or the official
   Unicode Meetei Mayek chart at https://www.unicode.org/charts/PDF/UABC0.pdf)
   to identify the matching letter/sign.
4. Add the new key → codepoint pair to `MAPPING` in
   `convert_kanglei_apaba.py`, with a comment noting the Unicode letter name
   and how confident the assignment is.
5. Re-run the script and sanity check the new output the same way we did
   here — decode a distinctive word or proper noun you can independently
   verify (a title, a name, a place) rather than trusting shape-matching
   alone.
