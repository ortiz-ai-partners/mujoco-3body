表情の規則 — 再描画用ソース

実行方法（Python 3）
  python -m pip install Pillow
  python render.py

出力: ../face_rules_chart_ortiz.png（report/face_rules_chart_ortiz.png）
寸法: 6400 × 8000 px（4:5）、RGB、300 dpi

文字は同梱した BIZ UDPGothic のみを使用。
問いと顔の名前: Bold。条件と規則番号: Regular。
最小文字サイズは問いの文字サイズの 70% 以上。
絵文字は使わず、顔は名前と規則番号で表示。
17 本の規則番号、様子を見る手の 3 分岐をコード内で検査。

../fonts/（report/fonts/）のフォントは Google Fonts より。
https://github.com/google/fonts/tree/main/ofl/bizudpgothic
SIL Open Font License 1.1。ライセンス全文は ../fonts/OFL.txt。
