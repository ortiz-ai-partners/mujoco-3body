"""Smoke test of the crab's face (crab_face.py): the seven expressions on the display panel, seen from in front of the
crab by a story-style camera and by the face monitor (the inset at the bottom-left).  No physics is stepped.

    python v7_test_face.py            -> out/face_test/face_<expression>.png and out/face_test/faces_sheet.png

Checks by eye: the face is on the front plate, upright and not mirrored (the sweat drop sits at the viewer's right),
the monitor frames the whole panel, and the two renderers (the story's and the monitor's) coexist.
"""
from __future__ import annotations

import math

import imageio
import mujoco
import numpy as np

import crab_face
from v6_common import OUT_DIR, VIDEO_H, VIDEO_W, Captioner, course_builder
from v6_robots import build_arena

JP_POSE = (4.6, 1.2, math.pi)          # the story's park spot: the crab faces -x


def main():
    app, slope_assembly, _tracks = course_builder()
    xml = slope_assembly.assembly_xml(app.ROOT / "scene_fork_tracks.xml")
    model, data = build_arena(xml, md_pose=(4.0, 0.6, -math.pi / 2), jp_pose=JP_POSE, timestep=0.005, face=True)
    face = crab_face.FaceDriver(model, "jp-")
    mujoco.mj_forward(model, data)
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "jp-base_link")
    print(f"ngeom={model.ngeom} ncam={model.ncam} face geom {face.gid} cam {face.cam_name} "
          f"fovy={model.cam_fovy[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, face.cam_name)]:.1f}")
    out = OUT_DIR / "face_test"
    out.mkdir(parents=True, exist_ok=True)
    renderer = mujoco.Renderer(model, height=VIDEO_H, width=VIDEO_W)
    pip = mujoco.Renderer(model, height=crab_face.PIP_H, width=crab_face.PIP_W)
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0
    cap = Captioner()
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    p = data.xpos[bid]
    cam.lookat[:] = [p[0], p[1], p[2] + 0.02]
    cam.distance, cam.azimuth, cam.elevation = 0.7, 0.0, -12.0     # from -x, looking +x: the crab's front
    pics = []
    for e in crab_face.EXPRESSIONS:
        face.expr, face.reason = e, "テスト"
        model.geom_matid[face.gid] = face.mat[e]
        renderer.update_scene(data, cam, opt)
        frame = renderer.render()
        pip.update_scene(data, camera=face.cam_name, scene_option=opt)
        small = pip.render().copy()
        pics.append((e, small))
        # the story's widest caption (RESCUE), so the monitor goes below it; the smoke test also shows a jump-cut notice
        img = cap.draw(frame, "v7 | 支配人AI〈アイランドマスター〉が次の一手を選ぶ ― 手助けは跳跳、物理のみ",
                       [f"face test | {e}（{crab_face.JA[e]}）", "跳跳の表示パネル（描画のみ・物理に影響なし）"],
                       footer="sim 123.4 s   x2",
                       inset={"pic": small, "above": "AI 成功91% 止6% 転3% 空0%｜渡65%",
                              "bars": [("成", 0.91), ("止", 0.06), ("転", 0.03), ("空", 0.0)],
                              "below": "力 0.7  接触 12 秒", "reason": face.label()},
                       notice="≫ 省略（sim 22→54 s）：BZ が空荷で保管場所へ戻る" if e == "sweat" else None)
        imageio.imwrite(out / f"face_{e}.png", img)
        if e == "neutral":                                        # and once beside a short caption
            img = cap.draw(frame, "v7 face test | short title", ["跳跳の表示パネル"], footer="crab_face.py",
                           inset={"pic": small, "above": "跳跳の顔（表示パネル・描画のみ）", "reason": face.label()})
            imageio.imwrite(out / "face_neutral_short_title.png", img)
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (crab_face.PIP_W, (crab_face.PIP_H + 24) * len(pics)), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, (e, small) in enumerate(pics):
        d.text((6, i * (crab_face.PIP_H + 24) + 5), e, fill=(220, 220, 220))
        sheet.paste(Image.fromarray(small), (0, i * (crab_face.PIP_H + 24) + 22))
    sheet.save(out / "faces_sheet.png")
    renderer.close()
    pip.close()
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
