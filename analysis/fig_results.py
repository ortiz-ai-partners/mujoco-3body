"""Report figure 3: the manager AI's evaluation, drawn from the evaluation files (no hand-copied numbers).

    python analysis/fig_results.py            -> report/results_managers.png (+ report/results_managers.html)

Left: the duck-rescue task over the 30 shared seeds of evaluation v4 (success and summit reached, per method).
Right, top: success / failure of each method against the fixed rule on the same seed (the 2x2 counts, as a table).
Right, bottom: the whole story with construction, from analysis/fullrun_stats.py (out/fullrun_stats/<name>/summary.json).
Laid out in HTML in BIZ UDPGothic (the report's typeface) and screenshotted with headless Chrome or Edge at 2x.
"""
from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "out" / "manager_runs"
FULL = ROOT / "out" / "fullrun_stats"
OUT_PNG = ROOT / "report" / "results_managers.png"
OUT_HTML = ROOT / "report" / "results_managers.html"
BROWSERS = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]
W, H = 1360, 700
METHODS = [("固定ルール", "baselines_v4/eval_rule.json"),
           ("PPO v2.2", "ppo2_v22_v4/eval_ppo.json"),
           ("表形式 Q", "tabq2_small_v4/eval_tabq.json"),
           ("PPO 中規模", "ppo2_medium2_v4/eval_ppo.json"),
           ("ランダム", "baselines_v4/eval_random.json")]
NOTE = {"PPO v2.2": "継続学習、提出動画で使用", "PPO 中規模": "継続学習の前"}
FULL_RUNS = [("PPO v2.2", "ppo2_v22", "提出動画と同じ支配人"), ("固定ルール", "rule", "比較")]
INK, SUB, MUTED, LINE, SURF, CARD = "#1d2430", "#556070", "#7a8494", "#dfe4ea", "#f6f8fa", "#ffffff"
DARK, LIGHT = "#2f8f86", "#a9d6cf"            # one hue, two steps: success / summit reached

CSS = """
* { box-sizing: border-box; }
body { margin: 0; width: %(W)dpx; height: %(H)dpx; background: %(SURF)s; font-family: "BIZ UDPGothic", sans-serif; color: %(INK)s; }
.wrap { padding: 28px 36px; }
h1 { font-size: 31px; margin: 0 0 6px; letter-spacing: .01em; }
.sub { font-size: 16px; color: %(SUB)s; margin: 0 0 18px; }
.grid { display: grid; grid-template-columns: 1.08fr 1fr; gap: 22px; }
.card { background: %(CARD)s; border: 1px solid %(LINE)s; border-radius: 10px; padding: 18px 22px; }
h2 { font-size: 21px; margin: 0 0 10px; }
.legend { font-size: 15px; color: %(SUB)s; margin: 0 0 12px; }
.legend i { display: inline-block; width: 22px; height: 12px; border-radius: 0 3px 3px 0; vertical-align: -1px; margin: 0 6px 0 0; }
.legend b { font-weight: normal; margin-right: 22px; }
.row { display: grid; grid-template-columns: 170px 1fr 118px; align-items: center; height: 56px; }
.lab { font-size: 18px; font-weight: bold; line-height: 1.15; }
.lab span { display: block; font-size: 12.5px; font-weight: normal; color: %(MUTED)s; }
.track { position: relative; height: 24px; border-left: 1px solid #b9c2cd;
         background: repeating-linear-gradient(90deg, transparent 0 calc(100%% / 3 - 1px), %(LINE)s calc(100%% / 3 - 1px) calc(100%% / 3)); }
.bar { position: absolute; left: 0; top: 0; height: 24px; background: %(DARK)s; border-radius: 0 4px 4px 0; }
.bar.back { background: %(LIGHT)s; }
.val { font-size: 17px; padding-left: 12px; font-variant-numeric: tabular-nums; }
.val b { font-size: 21px; }
.val span { display: block; font-size: 12.5px; color: %(MUTED)s; }
.axis { display: grid; grid-template-columns: 170px 1fr 118px; font-size: 13px; color: %(MUTED)s; margin-top: 4px; }
.axis div:nth-child(2) { display: flex; justify-content: space-between; }
table { border-collapse: collapse; width: 100%%; font-size: 17px; font-variant-numeric: tabular-nums; }
th { font-size: 14px; color: %(SUB)s; font-weight: normal; text-align: right; padding: 4px 8px; border-bottom: 1px solid %(LINE)s; }
th:first-child, td:first-child { text-align: left; }
td { text-align: right; padding: 6px 8px; border-bottom: 1px solid %(LINE)s; }
td:first-child { font-weight: bold; }
.small { font-size: 13px; color: %(MUTED)s; margin: 8px 0 0; line-height: 1.5; }
.right { display: grid; grid-template-rows: auto 1fr; gap: 22px; }
.detail { font-size: 13px; color: %(MUTED)s; margin: -6px 0 6px 170px; }
.pending { font-size: 16px; color: %(MUTED)s; }
.notes { font-size: 13.5px; color: %(SUB)s; margin: 16px 2px 0; line-height: 1.6; }
"""


def load(rel):
    return {r["seed"]: r for r in json.load(open(RUNS / rel, encoding="utf-8"))}


def bar_row(label, note, n_main, n_back, total, value_text):
    w_main = 100 * n_main / total
    back = "" if n_back is None else f'<div class="bar back" style="width:{100 * n_back / total:.2f}%"></div>'
    return (f'<div class="row"><div class="lab">{html.escape(label)}<span>{html.escape(note)}</span></div>'
            f'<div class="track">{back}<div class="bar" style="width:{w_main:.2f}%"></div></div>'
            f'<div class="val">{value_text}</div></div>')


def main():
    evals = {name: load(rel) for name, rel in METHODS}
    rule = evals["固定ルール"]
    seeds = sorted(rule)
    total = len(seeds)
    rows_a, rows_b = [], []
    for name, _ in METHODS:
        e = evals[name]
        ok = sum(e[s]["success"] for s in seeds)
        top = sum(e[s]["landed"] for s in seeds)
        rows_a.append(bar_row(name, NOTE.get(name, ""), ok, top, total, f"<b>{ok}</b> / {total}<span>天面 {top}</span>"))
        if name != "固定ルール":
            def cell(a, b):
                return sum(1 for s in seeds if rule[s]["success"] == a and e[s]["success"] == b)
            rows_b.append(f"<tr><td>{html.escape(name)}</td><td>{cell(True, True)}</td><td>{cell(True, False)}</td>"
                          f"<td>{cell(False, True)}</td><td>{cell(False, False)}</td></tr>")
    scenes = sorted({rule[s]["scenario"] for s in seeds})

    rows_c, n_full, yaws, build_ok = [], None, {}, {}
    for label, folder, note in FULL_RUNS:
        p = FULL / folder / "summary.json"
        if not p.exists():
            rows_c.append(f'<div class="row"><div class="lab">{label}<span>{note}</span></div><div class="pending">未集計</div></div>')
            continue
        sm = json.load(open(p, encoding="utf-8"))
        n_full = sm["runs"]
        runs = sm["per_run"].values()
        built = [r for r in runs if r["bz"]]
        n_course = sum(1 for r in built if r["course_disturbed"])
        n_rescue = sum(1 for r in built if not r["course_disturbed"] and not r["success"])
        rows_c.append(bar_row(label, note, sm["success"], None, sm["runs"], f'<b>{sm["success"]}</b> / {sm["runs"]}'))
        rows_c.append(f'<div class="detail">失敗の内訳：施工で停止 {sm["runs"] - len(built)}・部材の移動 {n_course}・救助の失敗 {n_rescue}</div>')
        yaws.update({int(k): v for k, v in sm.get("bz_yaw_deg", {}).items()})
        build_ok.update({int(k): r["bz"] for k, r in sm["per_run"].items()})

    yaw_note = ""
    if yaws:
        cw = [s for s, y in yaws.items() if y <= -1.0]
        yaw_note = (f"施工で止まった回は両方式で同じシード。BZ が右回りに 1° 以上ずれて始めた {len(cw)} 回は"
                    f"{'すべて' if all(not build_ok[s] for s in cw) else str(sum(not build_ok[s] for s in cw)) + ' 回が'}施工で止まった。")
    css = CSS % dict(W=W, H=H, SURF=SURF, INK=INK, SUB=SUB, MUTED=MUTED, LINE=LINE, CARD=CARD, DARK=DARK, LIGHT=LIGHT)
    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>{css}</style></head><body><div class="wrap">
<h1>支配人 AI の評価 ― パッカンの救助タスクと、施工を含む 3 体の通し</h1>
<p class="sub">新コース（峠の継ぎ目 1 cm）。救助タスクは坂の足元などで止まったパッカンを跳跳の助けで渡らせる部分（施工は含まない）、通しは施工からゴールまで。</p>
<div class="grid">
 <div class="card">
  <h2>パッカンの救助タスクの成功数（同じ {total} シード）</h2>
  <p class="legend"><i style="background:{DARK}"></i><b>救助の成功</b><i style="background:{LIGHT}"></i><b>天面到達</b></p>
  {"".join(rows_a)}
  <div class="axis"><div></div><div><span>0</span><span>10</span><span>20</span><span>30</span></div><div></div></div>
  <p class="small">各方式を各シードで 1 回、方策は決定的。30 試行で出た開始場面は 7 種のうち {len(scenes)} 種（天面で転倒・坂の途中で転倒は出ていない）。</p>
 </div>
 <div class="right">
  <div class="card">
   <h2>固定ルールとの成否の対応（同じ {total} シード）</h2>
   <table><tr><th>方式</th><th>両方成功</th><th>ルールだけ成功</th><th>方策だけ成功</th><th>両方失敗</th></tr>{"".join(rows_b)}</table>
   <p class="small">途中の接触や姿勢も変わるため、判断とスキルの寄与は切り分けていない。</p>
  </div>
  <div class="card">
   <h2>施工を含む 3 体の通しの成功数（各 {n_full or "—"} 回）</h2>
   {"".join(rows_c)}
   <p class="small">描画なしで通しを実行。回ごとに開始位置をずらす（BZ ±2 cm・±2°、パッカンと跳跳 ±5 cm・±10°）。
   成功＝3 体とも渡り切り、コースの部材が 4 cm 以上動かない。{yaw_note}</p>
  </div>
 </div>
</div>
<p class="notes">出所：救助タスクは同一シード評価（評価 v4）の記録、通しは通しの集計スクリプトの出力。図は評価の記録から直接描いた（手で写した数値はない）。</p>
</div></body></html>"""
    OUT_HTML.write_text(page, encoding="utf-8")
    browser = next((b for b in BROWSERS if b.exists()), None)
    if browser is None:
        sys.exit("no Chrome or Edge found")
    res = subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                          f"--window-size={W},{H}", "--default-background-color=ffffffff", "--virtual-time-budget=5000",
                          f"--screenshot={OUT_PNG}", OUT_HTML.as_uri()], capture_output=True, text=True)
    print(f"wrote {OUT_PNG} (rc={res.returncode})")
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
