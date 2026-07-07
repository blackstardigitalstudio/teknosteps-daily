# -*- coding: utf-8 -*-
"""
Tekno Monkey - A/B test copertine (Made in Italy).
Genera varianti AGGRESSIVE della thumbnail partendo da scimmia.png:
  - variant A "rave":  occhi neon senza pupille, sopracciglia cattive, fumo + strobo verdi
  - variant B "dark":  faccia gigante (inquadratura dominante), occhi glow con bordo rosso,
                       luce di taglio rossa, scanline glitch
Uso:
  python genera_thumb_ab.py --variant A [--out scimmia-thumbnail.png]
  python genera_thumb_ab.py --variant B
Senza --out scrive scimmia-thumbnail-A.png / scimmia-thumbnail-B.png (anteprima).
"""
import argparse
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

import genera_brand_scimmia as gb

BASE = os.path.dirname(os.path.abspath(__file__))
GREEN = gb.GREEN
DARK = gb.DARK
RED = (255, 40, 40)


# ---------- occhi: coordinate misurate su scimmia.png dopo monkey_rgba (808x985) ----------
# (il rilevamento automatico prendeva il verde delle cuffie: coordinate fisse, verificate a mano)
EYES_SCIMMIA = [(442.0, 253.0, 40.0), (556.0, 236.0, 40.0)]


def find_eyes(m):
    if m.size != (808, 985):
        # scala le coordinate se la base cambia
        fx, fy = m.width / 808.0, m.height / 985.0
        return [(cx * fx, cy * fy, r * (fx + fy) / 2) for cx, cy, r in EYES_SCIMMIA]
    return list(EYES_SCIMMIA)


# ---------- scimmia cattiva: palpebre abbassate + sopracciglia + occhi glow ----------
def angry_monkey(mk, rim_red=False):
    m = mk.copy()
    eyes = find_eyes(m)
    d = ImageDraw.Draw(m)
    fur = (56, 33, 20, 255)
    glow_layer = Image.new("RGBA", m.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    for i, (cx, cy, rad) in enumerate(eyes):
        R = rad * 1.35
        # 1) copre l'occhio dolce con "sclera" scura
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(12, 12, 10, 255))
        # 2) iride neon senza pupilla (posseduta)
        rr = R * 0.62
        col = GREEN
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (255,))
        if rim_red:
            gd.ellipse([cx - R * 0.95, cy - R * 0.95, cx + R * 0.95, cy + R * 0.95],
                       outline=RED + (200,), width=max(3, int(R * 0.14)))
        # 3) palpebra superiore inclinata (occhi socchiusi, cattivi):
        #    l'interno scende, l'esterno resta su
        inner = 1 if i == 0 else -1   # occhio sx: interno a destra
        lid = [
            (cx - R * 1.25, cy - R * 1.05),
            (cx + R * 1.25, cy - R * 1.05),
            (cx + R * 1.25 * inner, cy - R * 0.05),
            (cx - R * 1.25 * inner, cy - R * 0.75),
        ]
        d.polygon(lid, fill=fur)
        # 4) sopracciglio spesso arrabbiato
        bw = int(R * 0.5)
        x0, y0 = cx - R * 1.15, cy - R * (0.55 if inner == 1 else 1.35)
        x1, y1 = cx + R * 1.15, cy - R * (1.35 if inner == 1 else 0.55)
        d.line([x0, y0, x1, y1], fill=(20, 10, 5, 255), width=bw)
    halo = glow_layer.filter(ImageFilter.GaussianBlur(6))
    m.alpha_composite(halo)
    m.alpha_composite(glow_layer)
    # ghigno: piega la bocca in giu' agli angoli con due tratti scuri (smorfia)
    return m


def smoke(base, cx, cy, color=(120, 150, 110), n=7, seed=3):
    rng = np.random.default_rng(seed)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(n):
        x = cx + rng.integers(-420, 420)
        y = cy + rng.integers(-40, 120)
        w = rng.integers(160, 380)
        hh = rng.integers(40, 90)
        ld.ellipse([x - w, y - hh, x + w, y + hh], fill=color + (70,))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(40)))


def strobes(base, cx, top_y, color=GREEN, n=5, alpha=60, spread=900):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    W, H = base.size
    for i in range(n):
        x_end = cx - spread // 2 + i * (spread // max(1, n - 1))
        ld.polygon([(cx, top_y), (x_end - 40, H), (x_end + 40, H)], fill=color + (alpha,))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(6)))


def scanlines(img, step=5, dark=36):
    arr = np.array(img.convert("RGB"), dtype=np.int16)
    arr[::step, :, :] -= dark
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def rim_light(base, m, pos, color=RED, off=14):
    sil = Image.new("RGBA", base.size, (0, 0, 0, 0))
    tint = Image.new("RGBA", m.size, color + (255,))
    tint.putalpha(m.split()[3])
    sil.alpha_composite(tint, (pos[0] - off, pos[1]))
    base.alpha_composite(sil.filter(ImageFilter.GaussianBlur(10)))


def variant_A(mk, out):
    """Rave cattiva: corpo intero, occhi neon, strobo + fumo."""
    W, H = 1280, 720
    cx = int(W * 0.74)
    m = angry_monkey(mk)
    base = gb.stage_bg(W, H, cx, int(H * 0.66), r=440)
    strobes(base, cx, -80, color=GREEN, n=5, alpha=48)
    ms = gb.scaled(m, 700)
    pos = (cx - ms.width // 2, H - ms.height + 10)
    base.alpha_composite(ms, pos)
    smoke(base, cx, H - 90)
    LX = 56
    maxw = int(W * 0.52)
    f1 = gb.fit_font("impact.ttf", "MONKEY", maxw, 175)
    gb.neon_text(base, (LX, 62), "MONKEY", f1, fill=gb.WHITE, glow=GREEN, anchor="la", stroke=3)
    f2 = gb.fit_font("impact.ttf", "RAVE", maxw, 175)
    gb.neon_text(base, (LX, 62 + f1.size + 2), "RAVE", f2, fill=GREEN, glow=(40, 90, 0), anchor="la", stroke=3)
    y = 62 + f1.size + f2.size + 30
    bar = "1 HOUR DARK PSY"
    f3 = gb.fit_font("ariblk.ttf", bar, maxw, 72)
    d = ImageDraw.Draw(base)
    tw = d.textlength(bar, font=f3)
    d.rectangle([LX - 6, y, LX + tw + 22, y + f3.size + 16], fill=GREEN)
    d.text((LX + 6, y), bar, font=f3, fill=DARK)
    f4 = gb.font("arialbd.ttf", 30)
    d.text((LX, H - 56), "NO COPYRIGHT  -  teknosteps.com", font=f4, fill=(205, 205, 210))
    img = base.convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img.save(out, quality=95)
    print("[OK] variante A ->", out)


def variant_B(mk, out):
    """Dark dominante: faccia gigante dal basso, bordo rosso, scanline."""
    W, H = 1280, 720
    cx = int(W * 0.72)
    m = angry_monkey(mk, rim_red=True)
    base = gb.stage_bg(W, H, cx, int(H * 0.7), r=470)
    strobes(base, cx, -60, color=RED, n=3, alpha=36, spread=700)
    # zoom: solo testa+petto, grande = dominanza (angolo dal basso percepito)
    ms = gb.scaled(m, 1150)
    pos = (cx - ms.width // 2, H - int(ms.height * 0.62))
    rim_light(base, ms, pos, color=RED, off=18)
    base.alpha_composite(ms, pos)
    smoke(base, cx, H - 60, color=(140, 60, 60), seed=7)
    LX = 56
    maxw = int(W * 0.5)
    f1 = gb.fit_font("impact.ttf", "DARK", maxw, 185)
    gb.neon_text(base, (LX, 58), "DARK", f1, fill=gb.WHITE, glow=RED, anchor="la", stroke=3)
    f2 = gb.fit_font("impact.ttf", "MONKEY", maxw, 185)
    gb.neon_text(base, (LX, 58 + f1.size + 2), "MONKEY", f2, fill=GREEN, glow=(40, 90, 0), anchor="la", stroke=3)
    y = 58 + f1.size + f2.size + 28
    bar = "1 HOUR DARK PSY"
    f3 = gb.fit_font("ariblk.ttf", bar, maxw, 70)
    d = ImageDraw.Draw(base)
    tw = d.textlength(bar, font=f3)
    d.rectangle([LX - 6, y, LX + tw + 22, y + f3.size + 16], fill=GREEN)
    d.text((LX + 6, y), bar, font=f3, fill=DARK)
    f4 = gb.font("arialbd.ttf", 30)
    d.text((LX, H - 56), "NO COPYRIGHT  -  teknosteps.com", font=f4, fill=(205, 205, 210))
    img = base.convert("RGB")
    img = scanlines(img, step=6, dark=26)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.08)
    img.save(out, quality=95)
    print("[OK] variante B ->", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["A", "B"], required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    mk = gb.monkey_rgba(os.path.join(BASE, "scimmia.png"))
    out = args.out or os.path.join(BASE, "scimmia-thumbnail-%s.png" % args.variant)
    (variant_A if args.variant == "A" else variant_B)(mk, out)


if __name__ == "__main__":
    main()
