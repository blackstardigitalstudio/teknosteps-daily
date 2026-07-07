# -*- coding: utf-8 -*-
import os, subprocess, sys, random
import seo_youtube
BASE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
video = os.path.join(BASE, "teknosteps_scimmia_kling_1h.mp4")
short = os.path.join(BASE, "short_monkey_kling.mp4")
df = os.path.join(BASE, "_desc_scimmia.txt")
title, desc, tags = seo_youtube.build("monkey")
open(df, "w", encoding="utf-8").write(desc)
print("[RE-UPLOAD] " + title, flush=True)
r = subprocess.run([PY, "youtube_upload.py", "--video", video, "--title", title,
     "--description-file", df, "--tags", tags, "--thumbnail", "scimmia-thumbnail.png",
     "--token", "token_ch3.json", "--privacy", "public"], cwd=BASE)
if r.returncode != 0:
    sys.exit("[X] upload video fallito di nuovo")
if os.path.exists(short):
    subprocess.run([PY, "youtube_upload.py", "--video", short, "--short", "--token", "token_ch3.json",
         "--title", "This monkey is ON BEAT #shorts", "--tags", tags, "--privacy", "public"], cwd=BASE)
print("[OK] Monkey ripubblicato.", flush=True)
