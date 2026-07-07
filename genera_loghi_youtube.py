# -*- coding: utf-8 -*-
"""Genera immagine profilo (avatar) e banner YouTube per TeknoSteps. Made in Italy."""
import os
from PIL import Image, ImageDraw, ImageFont

BRAND = "assets/brand"
GREEN = (182, 255, 0)
WHITE = (245, 245, 245)
BG = (6, 6, 8)
FONTS = "C:/Windows/Fonts/"


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


logo = Image.open(os.path.join(BRAND, "teknosteps-logo-official.png")).convert("RGBA")

# bbox impronte (dalla nostra analisi): x 351-1205, y 24-531 -> con padding
foot = logo.crop((315, 0, 1221, 565))


def vgrad(w, h, top, bot):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px_row = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = px_row
    return img


def waveform(draw, cx, cy, width, height, color, alpha, seed=1):
    import random
    random.seed(seed)
    bars = 90
    bw = width / bars
    for i in range(bars):
        h = int(height * (0.15 + 0.85 * abs(__import__("math").sin(i * 0.5) * random.random())))
        x = int(cx - width / 2 + i * bw)
        draw.rectangle([x, cy - h // 2, x + int(bw * 0.5), cy + h // 2], fill=color + (alpha,))


# =================== AVATAR 800x800 ===================
A = 800
av = Image.new("RGBA", (A, A), (0, 0, 0, 255))  # nero pieno: il ritaglio si fonde
d = ImageDraw.Draw(av)
# anello neon sottile
d.ellipse([18, 18, A - 18, A - 18], outline=GREEN + (90,), width=6)

# impronte centrate in alto
fw = 470
fh = int(foot.height * fw / foot.width)
fp = foot.resize((fw, fh), Image.LANCZOS)
fy = 120
av.alpha_composite(fp, ((A - fw) // 2, fy))

# TEKNOSTEPS sotto (Arial Black), auto-fit
txt = "TEKNOSTEPS"
size = 96
f = font("ariblk.ttf", size)
while d.textlength(txt, font=f) > 660 and size > 20:
    size -= 2
    f = font("ariblk.ttf", size)
tw = d.textlength(txt, font=f)
ty = fy + fh + 18
# leggera ombra/glow
d.text(((A - tw) / 2, ty), txt, font=f, fill=WHITE)
av.convert("RGB").save(os.path.join(BRAND, "teknosteps-yt-avatar.png"), quality=95)
print("avatar salvato:", os.path.join(BRAND, "teknosteps-yt-avatar.png"))

# =================== BANNER 2048x1152 ===================
W, H = 2048, 1152
ban = Image.new("RGBA", (W, H), (0, 0, 0, 255))  # nero pieno: il logo si fonde
d = ImageDraw.Draw(ban)
cx, cy = W // 2, H // 2
# waveform decorativa di sfondo
waveform(d, cx, cy + 250, 1700, 120, GREEN, 40, seed=3)

# logo ufficiale centrato (entro la safe area 1235x338)
target_h = 300
lw = int(logo.width * target_h / logo.height)
lg = logo.resize((lw, target_h), Image.LANCZOS)
ly = cy - target_h // 2 - 30
ban.alpha_composite(lg, ((W - lw) // 2, ly))

# sottotitolo psytrance (entro safe area)
sub = "DARK PSYTRANCE  -  1 HOUR NO-COPYRIGHT MIXES"
fs = font("arialbd.ttf", 46)
sw = d.textlength(sub, font=fs)
d.text(((W - sw) / 2, ly + target_h + 4), sub, font=fs, fill=GREEN)

ban.convert("RGB").save(os.path.join(BRAND, "teknosteps-yt-banner.png"), quality=95)
print("banner salvato:", os.path.join(BRAND, "teknosteps-yt-banner.png"))
