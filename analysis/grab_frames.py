"""Grab frames from an mp4 at given times (seconds) -> PNGs next to the given prefix."""
import sys
from pathlib import Path

video, prefix, *times = sys.argv[1:]
times = [float(x) for x in times]
try:
    import imageio.v3 as iio
    import numpy as np
    from PIL import Image
    meta = iio.immeta(video, plugin="pyav")
    fps = float(meta.get("fps", 30.0))
    wanted = {int(round(tt * fps)): tt for tt in times}
    for i, frame in enumerate(iio.imiter(video, plugin="pyav")):
        if i in wanted:
            Image.fromarray(np.asarray(frame)).save(f"{prefix}_{wanted[i]:05.1f}s.png")
            del wanted[i]
            if not wanted:
                break
    print("done imageio", fps)
except Exception as exc:  # fall back to OpenCV
    print("imageio failed:", exc)
    import cv2
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    for tt in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(tt * fps)))
        ok, frame = cap.read()
        if ok:
            cv2.imwrite(f"{prefix}_{tt:05.1f}s.png", frame)
    print("done cv2", fps)
