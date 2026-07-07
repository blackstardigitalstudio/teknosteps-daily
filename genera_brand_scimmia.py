# -*- coding: utf-8 -*-
"""
Tekno Monkey (canale 3) - Immagini brand FORTI e chiamative (Made in Italy).
Da scimmia.png genera:
  - scimmia-avatar.png      800x800   (foto profilo)
  - scimmia-banner.png      2048x1152 (banner canale, testo nell'area sicura)
  - scimmia-thumbnail.png   1280x720  (copertina video, click-bait pulito)
Sfondo nero + verde neon (palco), scimmia ritagliata dallo sfondo near-black.

Uso: python genera_brand_scimmia.py
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
FONTS = (os.path.join(BASE, "assets", "fonts") + os.sep) if os.path.isdir(os.path.join(BASE, "assets", "fonts")) else "C:/Windows/Fonts/"
GREEN = (150, 255, 0)
WHITE = (250, 250, 250)
DARK = (6, 7, 9)


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def monkey_rgba(path):
    """Apre scimmia e rende trasparente lo sfondo near-black."""
    m = Image.open(path).convert("RGBA")
    arr = np.array(m)
    lum = arr[..., :3].max(axis=2)
    arr[..., 3] = (lum >= 26).astype(np.uint8) * 255
    m = Image.fromarray(arr, "RGBA")
    a = m.split()[3].filter(ImageFilter.GaussianBlur(1.4))
    m.putalpha(a)
    # ritaglia al bounding box della scimmia
    bbox = m.getbbox()
    return m.crop(bbox) if bbox else m


def stage_bg(W, H, cx, cy, r=520, color=GREEN):
    """Fondo nero con bagliore neon (palco) centrato in (cx,cy)."""
    base = Image.new("RGBA", (W, H), DARK + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - r, cy - int(r * 0.5), cx + r, cy + int(r * 0.5)], fill=color + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    base = Image.alpha_composite(base, glow)
    # vignettatura
    vg = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vg)
    vd.ellipse([-W * 0.2, -H * 0.2, W * 1.2, H * 1.2], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    base = Image.composite(base, dark, vg)
    return base


def neon_text(base, xy, text, fnt, fill=WHITE, glow=GREEN, anchor="la", stroke=0, stroke_fill=(0, 0, 0)):
    """Testo con alone neon dietro."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text(xy, text, font=fnt, fill=glow + (255,), anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(14))
    base.alpha_composite(layer)
    d = ImageDraw.Draw(base)
    d.text(xy, text, font=fnt, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def fit_font(name, text, maxw, start):
    s = start
    f = font(name, s)
    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    while dummy.textlength(text, font=f) > maxw and s > 20:
        s -= 2
        f = font(name, s)
    return f


def scaled(mk, target_h):
    w = int(mk.width * target_h / mk.height)
    return mk.resize((w, target_h), Image.LANCZOS)


def make_avatar(mk, out):
    W = H = 800
    base = stage_bg(W, H, W // 2, int(H * 0.62), r=360)
    # anello neon
    d = ImageDraw.Draw(base)
    d.ellipse([18, 18, W - 18, H - 18], outline=GREEN + (255,), width=10)
    m = scaled(mk, 640)
    base.alpha_composite(m, (W // 2 - m.width // 2, H - m.height - 40))
    base.convert("RGB").save(out, quality=95)
    print("[OK]", out)


def make_banner(mk, out):
    W, H = 2048, 1152
    # scimmia ancorata a destra (fuori, ma visibile su desktop)
    m = scaled(mk, 700)
    mx = W - m.width - 70
    base = stage_bg(W, H, mx + m.width // 2, int(H * 0.62), r=520)
    base.alpha_composite(m, (mx, H // 2 - m.height // 2 + 50))
    # blocco testo nell'area sicura, a sinistra della scimmia
    tx = 240
    maxw = mx - tx - 60
    f1 = fit_font("impact.ttf", "TEKNO MONKEY", maxw, 140)
    neon_text(base, (tx, H // 2 - 70), "TEKNO MONKEY", f1, fill=WHITE, glow=GREEN, anchor="lm")
    d = ImageDraw.Draw(base)
    f2 = fit_font("arialbd.ttf", "DARK PSYTRANCE  -  DANCING MONKEY", maxw, 46)
    d.text((tx + 4, H // 2 + 26), "DARK PSYTRANCE  -  DANCING MONKEY", font=f2, fill=GREEN, anchor="lm")
    f3 = fit_font("arialbd.ttf", "1 HOUR MIXES - 100% NO COPYRIGHT - NEW EVERY DAY", maxw, 36)
    d.text((tx + 4, H // 2 + 86), "1 HOUR MIXES - 100% NO COPYRIGHT - NEW EVERY DAY", font=f3, fill=(210, 210, 215), anchor="lm")
    base.convert("RGB").save(out, quality=95)
    print("[OK]", out)


def make_thumbnail(mk, out, line1="DANCING", line2="MONKEY"):
    W, H = 1280, 720
    cx = int(W * 0.74)
    base = stage_bg(W, H, cx, int(H * 0.66), r=440)
    m = scaled(mk, 660)
    base.alpha_composite(m, (cx - m.width // 2, H - m.height - 10))
    LX = 56
    maxw = int(W * 0.52)
    f1 = fit_font("impact.ttf", line1, maxw, 170)
    neon_text(base, (LX, 70), line1, f1, fill=WHITE, glow=GREEN, anchor="la", stroke=3)
    f2 = fit_font("impact.ttf", line2, maxw, 170)
    neon_text(base, (LX, 70 + f1.size + 4), line2, f2, fill=GREEN, glow=(40, 90, 0), anchor="la", stroke=3)
    # barra verde "1 HOUR DARK PSY"
    y = 70 + f1.size + f2.size + 30
    bar = "1 HOUR DARK PSY"
    f3 = fit_font("ariblk.ttf", bar, maxw, 72)
    d = ImageDraw.Draw(base)
    tw = d.textlength(bar, font=f3)
    d.rectangle([LX - 6, y, LX + tw + 22, y + f3.size + 16], fill=GREEN)
    d.text((LX + 6, y), bar, font=f3, fill=DARK)
    f4 = font("arialbd.ttf", 30)
    d.text((LX, H - 56), "NO COPYRIGHT  -  teknosteps.com", font=f4, fill=(205, 205, 210))
    base.convert("RGB").save(out, quality=95)
    print("[OK]", out)


THUMB_LINES = [("DANCING", "MONKEY"), ("TEKNO", "MONKEY"), ("PSY", "MONKEY"),
               ("MONKEY", "RAVE"), ("DARK PSY", "MONKEY"), ("MONKEY", "DANCE")]


def main():
    import argparse
    import random
    ap = argparse.ArgumentParser()
    ap.add_argument("--thumb-only", action="store_true", help="rigenera solo la copertina (per la pipeline)")
    ap.add_argument("--line1", default=None)
    ap.add_argument("--line2", default=None)
    args = ap.parse_args()
    mk = monkey_rgba(os.path.join(BASE, "scimmia.png"))
    l1, l2 = (args.line1, args.line2)
    if not l1:
        l1, l2 = random.choice(THUMB_LINES)
    if args.thumb_only:
        make_thumbnail(mk, os.path.join(BASE, "scimmia-thumbnail.png"), l1, l2)
        return
    make_avatar(mk, os.path.join(BASE, "scimmia-avatar.png"))
    make_banner(mk, os.path.join(BASE, "scimmia-banner.png"))
    make_thumbnail(mk, os.path.join(BASE, "scimmia-thumbnail.png"), l1, l2)
    print("[OK] Brand Tekno Monkey generato. Made in Italy.")


if __name__ == "__main__":
    main()
