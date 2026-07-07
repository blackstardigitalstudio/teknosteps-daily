# -*- coding: utf-8 -*-
"""
TeknoSteps - Immagini PROMO da allegare ai post (Made in Italy)
Genera un post quadrato (1080x1080) e un banner largo (1920x1080) con la
scimmia mascotte, il brand, la tagline e i link. Salvati in OneDrive/TeknoSteps_Promo
-> pronti da copiare/allegare su Reddit, forum, IG, ecc.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.expanduser("~"), "OneDrive", "TeknoSteps_Promo")
MONKEY = os.path.join(BASE, "assets", "tiktok_app_icon.png")
NEON = (150, 255, 0)
INK = (244, 244, 240)
MUTED = (150, 150, 140)


def font(bold, size):
    p = "C:/Windows/Fonts/" + ("impact.ttf" if bold == "title" else
                               ("arialbd.ttf" if bold else "arial.ttf"))
    return ImageFont.truetype(p, size)


def bg(W, H):
    """Sfondo nero con glow verde radiale in alto."""
    img = Image.new("RGB", (W, H), (5, 5, 5))
    glow = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(glow)
    cx, cy, r = W // 2, int(H * 0.10), int(W * 0.6)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(W // 8))
    green = Image.new("RGB", (W, H), (20, 60, 10))
    img = Image.composite(green, img, glow)
    return img


def ctext(d, cx, y, txt, f, fill, shadow=True):
    w = d.textlength(txt, font=f)
    x = cx - w / 2
    if shadow:
        d.text((x + 3, y + 3), txt, font=f, fill=(0, 0, 0))
    d.text((x, y), txt, font=f, fill=fill)
    bb = d.textbbox((x, y), txt, font=f)
    return bb[3] - bb[1]


def monkey_scaled(h):
    m = Image.open(MONKEY).convert("RGB")
    w = int(m.width * h / m.height)
    return m.resize((w, h), Image.LANCZOS)


def blend_monkey(img, m, x, y):
    """Compone la scimmia in 'lighten': lo sfondo scuro dell'immagine sparisce nella
    tela nera (resta solo scimmia + glow), quindi niente bordo rettangolare."""
    layer = Image.new("RGB", img.size, (0, 0, 0))
    layer.paste(m, (x, y))
    return ImageChops.lighter(img, layer)


def make_square():
    W = H = 1080
    img = bg(W, H)
    d = ImageDraw.Draw(img)
    ctext(d, W // 2, 60, "TEKNOSTEPS", font("title", 130), INK)
    ctext(d, W // 2, 210, "24/7 NO-COPYRIGHT PSYTRANCE", font(True, 40), NEON)
    m = monkey_scaled(600)
    img = blend_monkey(img, m, (W - m.width) // 2, 250)
    d = ImageDraw.Draw(img)
    ctext(d, W // 2, 900, "ONE WORLD  ·  ONE BEAT", font(True, 44), INK)
    ctext(d, W // 2, 970, "teknosteps.com  ·  YouTube: @teknosteps  ·  Discord", font(False, 30), MUTED)
    p = os.path.join(OUT, "promo_square.jpg")
    img.save(p, quality=92)
    return p


def make_banner():
    W, H = 1920, 1080
    img = bg(W, H)
    m = monkey_scaled(940)
    img = blend_monkey(img, m, W - m.width - 40, (H - m.height) // 2)
    d = ImageDraw.Draw(img)
    lx = 90
    d.text((lx, 150), "TEKNOSTEPS", font=font("title", 160), fill=INK)
    d.text((lx, 360), "24/7 NO-COPYRIGHT", font=font(True, 66), fill=NEON)
    d.text((lx, 440), "PSYTRANCE RADIO", font=font(True, 66), fill=NEON)
    d.text((lx, 560), "No faces. Just steps and bass.", font=font(False, 46), fill=INK)
    d.text((lx, 620), "One global walk, one beat.", font=font(False, 46), fill=INK)
    d.text((lx, 780), "teknosteps.com", font=font(True, 50), fill=INK)
    d.text((lx, 850), "YouTube: @teknosteps  ·  @teknomonkeytv  ·  @strangelightpsy",
           font=font(False, 34), fill=MUTED)
    d.text((lx, 900), "Discord: discord.gg/QeBkCe3qE", font=font(False, 34), fill=MUTED)
    p = os.path.join(OUT, "promo_banner.jpg")
    img.save(p, quality=92)
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    for fn in (make_square, make_banner):
        p = fn()
        print(f"[OK] {p}  ({os.path.getsize(p)/1024:.0f} KB)")
    print(f"\nPromo pronte in: {OUT}\nMade in Italy")


if __name__ == "__main__":
    main()
