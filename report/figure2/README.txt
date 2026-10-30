Submitted video timeline (2:57)

Run:
  python -m pip install Pillow
  python render.py

Output: ../timeline_ortiz.png, i.e. report/timeline_ortiz.png, 7200 x 3600 pixels (2:1), 300 dpi metadata.
Both ribbons use one linear scale from 0 to 177 video seconds.
No facial ribbon is drawn before 0:18 or after 2:54.

Typography:
Only BIZ UDPGothic Regular and Bold, included in ../fonts/ (report/fonts/).
Title and the face-ribbon heading: Bold. All other text: Regular.
Smallest text: 56 output pixels. Ribbon height: 112 output pixels.
Labels in narrow face cells use line breaks without changing the text.
Fullwidth U+FF1E/U+FF1C characters are retained in the face labels.

Font source: https://github.com/google/fonts/tree/main/ofl/bizudpgothic
SIL Open Font License 1.1: ../fonts/OFL.txt
