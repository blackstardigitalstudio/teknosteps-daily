# -*- coding: utf-8 -*-
"""
Strange Light (canale 2) - Copertina 1280x720 dal visual ipnotico (Made in Italy).
Estrae un frame dall'attrattore e ci mette sopra un titolo forte. Titoli variabili.

Uso: python genera_copertina_ipno.py [--video teknosteps_ipno_1h.mp4] [--seed N]
"""
import argparse, os, random, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
FONTS = (os.path.join(BASE, "assets", "fonts") + os.sep) if os.path.isdir(os.path.join(BASE, "assets", "fonts")) else "C:/Windows/Fonts/"
GREEN = (150, 255, 0)
WHITE = (250, 250, 250)
W, H = 1280, 720
HEADS = [("HYPNOTIC", "DARK PSY"), ("STRANGE", "LIGHT"), ("PSY", "TRANCE"),
         ("DEEP", "DARK PSY"), ("TRIPPY", "VISUALS"), ("NIGHT", "PSY TRIP")]
SUBS = ["1 HOUR MIX", "FOCUS & TRIP", "DEEP FOCUS", "NIGHT SESSION", "STUDY & CODE"]


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    return None


def font(n, s):
    return ImageFont.truetype(FONTS + n, s)


def fit(d, text, fn, maxw, start):
    s = start
    f = font(fn, s)
    while d.textlength(text, font=f) > maxw and s > 22:
        s -= 2
        f = font(fn, s)
    return f


def neon(base, xy, text, f, fill, glow, stroke=2):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=f, fill=glow + (255,))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(base).text(xy, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(BASE, "teknosteps_ipno_1h.mp4"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(BASE, "ipno-thumbnail.png"))
    args = ap.parse_args()
    seed = args.seed if args.seed is not None else random.randrange(100000)
    random.seed(seed)

    bgp = os.path.join(BASE, "_ipno_bg.png")
    ff = ffmpeg()
    base = None
    if ff and os.path.exists(args.video):
        t = 20 + (seed % 200)
        if subprocess.run([ff, "-y", "-ss", str(t), "-i", args.video, "-frames:v", "1",
                           bgp, "-loglevel", "error"]).returncode == 0 and os.path.exists(bgp):
            img = Image.open(bgp).convert("RGBA")
            s = max(W / img.width, H / img.height)
            img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
            base = img.crop((0, 0, W, H))
    if base is None:
        base = Image.new("RGBA", (W, H), (4, 6, 8, 255))

    # sfumatura scura a sinistra per leggibilita'
    grad = Image.new("L", (W, 1), 0)
    for x in range(W):
        grad.putpixel((x, 0), max(0, min(220, int(220 * (1 - x / (W * 0.62))))))
    base = Image.composite(Image.new("RGBA", (W, H), (3, 5, 7, 255)), base, grad.resize((W, H)))

    head = random.choice(HEADS)
    sub = random.choice(SUBS)
    d = ImageDraw.Draw(base)
    LX = 58
    maxw = int(W * 0.62)
    f1 = fit(d, head[0], "impact.ttf", maxw, 150)
    neon(base, (LX, 96), head[0], f1, WHITE, GREEN)
    d = ImageDraw.Draw(base)
    f2 = fit(d, head[1], "impact.ttf", maxw, 150)
    neon(base, (LX, 96 + f1.size + 2), head[1], f2, GREEN, (40, 90, 0))
    d = ImageDraw.Draw(base)
    y = 96 + f1.size + f2.size + 28
    f3 = fit(d, sub, "ariblk.ttf", maxw, 70)
    tw = d.textlength(sub, font=f3)
    d.rectangle([LX - 6, y, LX + tw + 22, y + f3.size + 16], fill=GREEN)
    d.text((LX + 6, y), sub, font=f3, fill=(5, 7, 9))
    d.text((LX, H - 56), "NO COPYRIGHT  -  teknosteps.com", font=font("arialbd.ttf", 30), fill=(210, 210, 215))

    base.convert("RGB").save(args.out, quality=95)
    if os.path.exists(bgp):
        try:
            os.remove(bgp)
        except OSError:
            pass
    print(f"[OK] Copertina ipnotica: {args.out} (seed {seed}: {head[0]} {head[1]} / {sub})")


if __name__ == "__main__":
    main()
