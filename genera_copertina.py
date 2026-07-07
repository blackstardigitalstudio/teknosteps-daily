# -*- coding: utf-8 -*-
"""
TeknoSteps - Genera copertine YouTube 1280x720 SEMPRE DIVERSE (Made in Italy).
Ogni run pesca: sfondo (pavimento) diverso, titolo, sotto-barra e tagline diversi,
restando coerente col brand (nero + verde neon). Cosi i video non sembrano ripetitivi.

Uso:
  python genera_copertina.py                       # variante casuale
  python genera_copertina.py --seed 7              # variante riproducibile
  python genera_copertina.py --out cover2.png
"""
import argparse
import glob
import os
import random
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
GREEN = (182, 255, 0)
WHITE = (248, 248, 248)
FONTS = (os.path.join(BASE, "assets", "fonts") + os.sep) if os.path.isdir(os.path.join(BASE, "assets", "fonts")) else "C:/Windows/Fonts/"
W, H = 1280, 720

# --- varianti (restano on-brand, cambiano vibe) ---
HEADS = [("DARK", "PSYTRANCE"), ("NIGHT", "PSYTRANCE"), ("FOREST", "PSY"),
         ("DEEP", "DARK PSY"), ("HYPNOTIC", "PSY"), ("PSY", "TRANCE"),
         ("DARK", "PSY WALK")]
SUBS = ["1 HOUR MIX", "1 HOUR WALK", "FOCUS MIX", "NIGHT DRIVE",
        "DEEP FOCUS", "STUDY & CODE", "GYM & RUN"]
TAGS = ["walk together under the bass", "endless steps and rolling bass",
        "lose yourself in the bass", "one beat, one movement, forever",
        "no faces, just steps and bass"]
FLOORS = ["neongrid", "lava", "circuit", "ice", "marble", "metal", "asphalt", "concrete"]


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit", r"C:\Program Files (x86)\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    return None


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def cover(img, tw, th):
    iw, ih = img.size
    s = max(tw / iw, th / ih)
    img = img.resize((int(iw * s), int(ih * s)), Image.LANCZOS)
    x = (img.width - tw) // 2
    y = (img.height - th) // 2
    return img.crop((x, y, x + tw, y + th))


def fit(draw, text, fname, maxw, start):
    s = start
    f = font(fname, s)
    while draw.textlength(text, font=f) > maxw and s > 24:
        s -= 2
        f = font(fname, s)
    return f


def pick_bg(seed):
    """Estrae un frame da un pavimento a caso (sfondo)."""
    ff = ffmpeg()
    tmp = os.path.join(BASE, "_cover_bg.png")
    random.shuffle(FLOORS)
    for name in FLOORS:
        src = os.path.join(BASE, "video_output", f"walk_floor_{name}.mp4")
        if os.path.exists(src) and ff:
            t = 0.5 + (seed % 3)
            r = subprocess.run([ff, "-y", "-ss", str(t), "-i", src, "-frames:v", "1",
                                tmp, "-loglevel", "error"])
            if r.returncode == 0 and os.path.exists(tmp):
                return tmp
    return None


def main():
    ap = argparse.ArgumentParser(description="Copertina YouTube TeknoSteps (variabile)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(BASE, "teknosteps-thumbnail.png"))
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(100000)
    random.seed(seed)

    head = random.choice(HEADS)
    sub = random.choice(SUBS)
    tag = random.choice(TAGS)

    base = Image.new("RGB", (W, H), (4, 4, 6)).convert("RGBA")

    bg = pick_bg(seed)
    IMGW = 560
    if bg:
        neon = Image.open(bg).convert("RGBA")
        base.alpha_composite(cover(neon, IMGW, H), (W - IMGW, 0))

    # sfumatura nera verso sinistra (leggibilita testo)
    grad = Image.new("L", (W, 1), 0)
    for x in range(W):
        if x < W - IMGW - 120:
            grad.putpixel((x, 0), 255)
        elif x < W - IMGW + 160:
            grad.putpixel((x, 0), int(255 * (1 - (x - (W - IMGW - 120)) / 280)))
        else:
            grad.putpixel((x, 0), 0)
    base = Image.composite(Image.new("RGBA", (W, H), (4, 4, 6, 255)), base, grad.resize((W, H)))
    d = ImageDraw.Draw(base)

    # impronte brand in alto a sinistra
    logo_path = os.path.join(BASE, "assets", "brand", "teknosteps-logo-official.png")
    if os.path.exists(logo_path):
        foot = Image.open(logo_path).convert("RGBA").crop((315, 0, 1221, 565))
        fw = 150
        base.alpha_composite(foot.resize((fw, int(foot.height * fw / foot.width)), Image.LANCZOS), (60, 48))

    LX = 60
    maxw = W - IMGW - LX - 30

    f1 = fit(d, head[0], "ariblk.ttf", maxw, 150)
    d.text((LX, 175), head[0], font=f1, fill=WHITE)
    f2 = fit(d, head[1], "ariblk.ttf", maxw, 130)
    d.text((LX, 175 + f1.size + 6), head[1], font=f2, fill=WHITE)

    y = 175 + f1.size + f2.size + 24
    f3 = fit(d, sub, "ariblk.ttf", maxw, 86)
    tw3 = d.textlength(sub, font=f3)
    d.rectangle([LX - 8, y, LX + tw3 + 18, y + f3.size + 18], fill=GREEN)
    d.text((LX + 4, y + 2), sub, font=f3, fill=(6, 6, 8))

    y += f3.size + 36
    f4 = fit(d, tag, "arialbd.ttf", maxw, 42)
    d.text((LX, y), tag, font=f4, fill=GREEN)

    fb = font("arialbd.ttf", 30)
    d.text((LX, H - 58), "NO COPYRIGHT   -   teknosteps.com", font=fb, fill=(200, 200, 205))

    base.convert("RGB").save(args.out, quality=95)
    if os.path.exists(os.path.join(BASE, "_cover_bg.png")):
        try:
            os.remove(os.path.join(BASE, "_cover_bg.png"))
        except OSError:
            pass
    print(f"[OK] Copertina: {args.out}  (seed {seed}: {head[0]} {head[1]} / {sub} / bg pavimento)")


if __name__ == "__main__":
    main()
