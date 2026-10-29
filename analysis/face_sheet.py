"""The 11 faces as they appear in the video, with their names and the situations that bring them out (report
figure 6).  Renders each expression through the face camera at twice the monitor's size and lays them out in
a grid with Japanese labels.

    python analysis/face_sheet.py            -> report/faces_sheet_ja.png
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mujoco                                       # noqa: E402
import numpy as np                                  # noqa: E402
from PIL import Image, ImageDraw, ImageFont          # noqa: E402

import crab_face                                    # noqa: E402
from v6_common import _FONTS, course_builder        # noqa: E402
from v6_robots import build_arena                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 2 * crab_face.PIP_W, 2 * crab_face.PIP_H      # 480 x 240
ORDER = ["neutral", "serious", "happy", "cross", "sweat", "troubled_sweat", "troubled", "relief", "sparkle", "shock", "spiral"]
WHEN = {
    "neutral": ["戯れ・待機・移動（救助の外）", "様子見で「渡れる」が中くらい"],
    "serious": ["自分が坂を登る・ジャンプする", "手の成功確率が 2 本の線の間"],
    "happy": ["坂に挑むパッカンを応援（登っている間）", "手の成功確率がにっこりの線以上", "様子見で渡れる 60% 以上／祝賀ダンス"],
    "cross": ["パッカンを押している（順調）"],
    "sweat": ["押している：力 0.7 以上", "または接触 5 秒超"],
    "troubled_sweat": ["押している：止まる＋転ぶ 40% 以上", "転ぶ 30% 以上、または進みなし 3 秒"],
    "troubled": ["登れないパッカンを見ている（足踏み・後ずさり・座る）", "直前の押しが止まった・転ばせた", "手の成功確率が困りの線以下／渡れる 30% 以下"],
    "relief": ["手がうまく終わった直後の 2 秒", "（座れた・頂に届いた・立てた・渡った）"],
    "sparkle": ["パッカンが渡り切った（祝賀ダンスまで）"],
    "shock": ["パッカンが転んだ直後の 1.5 秒"],
    "spiral": ["自分が転んだ（傾き 50° 超）"],
}


def main():
    app, slope_assembly, _ = course_builder()
    xml = slope_assembly.assembly_xml(app.ROOT / "scene_fork_tracks.xml")
    model, data = build_arena(xml, md_pose=(4.0, 0.6, -math.pi / 2), jp_pose=(4.6, 1.2, math.pi), timestep=0.005, face=True)
    face = crab_face.FaceDriver(model, "jp-")
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=H, width=W)
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0
    pics = {}
    for e in ORDER:
        model.geom_matid[face.gid] = face.mat[e]
        renderer.update_scene(data, camera=face.cam_name, scene_option=opt)
        pics[e] = Image.fromarray(renderer.render().copy())
    renderer.close()

    font_path = next((p for p in _FONTS if p.exists()), None)
    f_title = ImageFont.truetype(str(font_path), 34)
    f_name = ImageFont.truetype(str(font_path), 28)
    f_key = ImageFont.truetype(str(font_path), 17)
    f_when = ImageFont.truetype(str(font_path), 18)
    cols, rows = 3, 4
    pad, text_h = 28, 120
    cw, ch = W + pad, H + text_h + pad
    canvas = Image.new("RGB", (cols * cw + pad, rows * ch + pad + 90), (248, 249, 252))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 24), "跳跳の表情 11 種 — 表示パネルの描画と、その顔が出る場面（crab_face.py の 17 規則）", font=f_title, fill=(30, 40, 60))
    for i, e in enumerate(ORDER):
        r, c = divmod(i, cols)
        x0, y0 = pad + c * cw, 90 + pad + r * ch
        d.rounded_rectangle([x0 - 8, y0 - 8, x0 + W + 8, y0 + H + text_h + 8], radius=12, fill=(255, 255, 255), outline=(200, 206, 216))
        canvas.paste(pics[e], (x0, y0))
        d.text((x0 + 4, y0 + H + 10), crab_face.JA[e], font=f_name, fill=(30, 40, 60))
        nw = d.textbbox((0, 0), crab_face.JA[e], font=f_name)[2]
        d.text((x0 + 4 + nw + 12, y0 + H + 20), e, font=f_key, fill=(120, 128, 140))
        for k, line in enumerate(WHEN[e]):
            d.text((x0 + 4, y0 + H + 48 + k * 23), line, font=f_when, fill=(60, 70, 90))
    # the twelfth cell: a legend
    r, c = divmod(len(ORDER), cols)
    x0, y0 = pad + c * cw, 90 + pad + r * ch
    d.rounded_rectangle([x0 - 8, y0 - 8, x0 + W + 8, y0 + H + text_h + 8], radius=12, fill=(240, 244, 250), outline=(200, 206, 216))
    legend = ["顔は跳跳の前面パネル（10.7 × 3.9 cm）に描画した板で、", "顔カメラ（パネルの 30 cm 前）から見た絵。",
              "どの顔を出すかは 2 つ目の AI（気分ネット）の確率と", "計測値（接触力・押している時間・進み・転倒・傾き）", "から 17 の規則で決める。描画のみで物理には戻らない。",
              "キラキラは公式の目アニメ（dance 用）の星型を借用。"]
    for k, line in enumerate(legend):
        d.text((x0 + 8, y0 + 16 + k * 28), line, font=f_when, fill=(60, 70, 90))
    out = os.path.join(ROOT, "report", "faces_sheet_ja.png")
    canvas.save(out)
    print("wrote", out, canvas.size)


if __name__ == "__main__":
    main()
