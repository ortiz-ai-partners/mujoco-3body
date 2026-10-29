"""Build the report PDF (説明資料_PAI最終課題_83485.pdf) from report/src/report.html with headless Chrome or Edge.

    python report/build_report.py --youtube https://youtu.be/XXXX        -> report/説明資料_PAI最終課題_83485.pdf
    python report/build_report.py --png out/report_pages                 -> also one PNG per page (needs pypdfium2)

The HTML is the source; {{YOUTUBE}} is replaced by --youtube (a placeholder line until the video is public).
Images are referenced relative to report/src/ (the figures in report/, the video stills in report/src/stills/).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src" / "report.html"
OUT = HERE / "説明資料_PAI最終課題_83485.pdf"
BROWSERS = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--youtube", default="（YouTube の URL は公開後に記入）", help="the video's URL")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--png", type=Path, help="also write one PNG per page into this folder (needs pypdfium2)")
    args = ap.parse_args()

    html = SRC.read_text(encoding="utf-8").replace("{{YOUTUBE}}", args.youtube)
    build = SRC.with_name("_build.html")
    build.write_text(html, encoding="utf-8")
    browser = next((b for b in BROWSERS if b.exists()), None) or shutil.which("chrome") or shutil.which("msedge")
    if browser is None:
        sys.exit("no Chrome or Edge found")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(browser), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
           "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000",
           f"--print-to-pdf={args.out}", build.as_uri()]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    build.unlink(missing_ok=True)
    if res.returncode != 0 or not args.out.exists():
        sys.exit(f"browser failed ({res.returncode}): {res.stderr[-800:]}")
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.2f} MB)")
    if args.png:
        import pypdfium2 as pdfium
        args.png.mkdir(parents=True, exist_ok=True)
        pdf = pdfium.PdfDocument(str(args.out))
        for i in range(len(pdf)):
            pdf[i].render(scale=1.6).to_pil().save(args.png / f"page{i + 1:02d}.png")
        print(f"{len(pdf)} pages -> {args.png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
