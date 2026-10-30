Figure 1 — MuJoCo system overview

Reproduce:
  python -m pip install Pillow
  python render.py

Output: ../system_overview_ortiz.png, i.e. report/system_overview_ortiz.png (7200 x 4800, 3:2).
All headings use BIZ UDPGothic Bold; all body text uses BIZ UDPGothic Regular.
The original, unmodified Google Fonts TTF files are in ../fonts/ (report/fonts/).
Their SIL Open Font License is included as ../fonts/OFL.txt.
Source: https://github.com/google/fonts/tree/main/ofl/bizudpgothic

Rendering notes:
- Text is drawn to the full canvas without line-height clipping.
- 2x rendering preserves the font's thin, low-position underscore.
- BIZ UDPGothic lacks U+21C6 (⇆). The renderer mirrors the same font's
  U+21C4 glyph (⇄) to create the required symbol without a fallback font.
- No other font is used. Robot icons and arrows are drawn geometrically.
