# -*- coding: utf-8 -*-
"""
TeknoSteps - VISUAL "STRANGE LIGHT" (Made in Italy)
Attrattori caotici (de Jong / Clifford / Svensson) a filamenti di luce neon, 16:9.
IPNOTICO: colori che CICLANO nello spettro + ROTAZIONE continua + forma che si
trasforma. Tutto PERIODICO sul loop -> clip ripetibile all'infinito senza stacco.
Ogni render sceglie un attrattore e una palette diversi -> mai uguale.
100% generato (no campioni, no copyright).

Uso: python genera_visual_attrattore.py --loop 40 --w 1920 --h 1080 --out base_ipno.mp4
"""
import argparse, math, os, shutil, subprocess, sys, tempfile
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    sys.exit("ffmpeg non trovato")


# ---- attrattori caotici: ognuno ha una "forma" diversa ----
def dejong(x, y, a, b, c, d):
    return np.sin(a * y) - np.cos(b * x), np.sin(c * x) - np.cos(d * y)


def clifford(x, y, a, b, c, d):
    return np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y)


def svensson(x, y, a, b, c, d):
    return d * np.sin(a * x) - np.sin(b * y), c * np.cos(a * x) + np.cos(b * y)


ATTRACTORS = {"dejong": (dejong, 2.4), "clifford": (clifford, 2.8), "svensson": (svensson, 3.0)}


def hsv_to_rgb(h, s, v):
    """HSV->RGB vettoriale (array)."""
    h = (h % 1.0) * 6.0
    i = np.floor(h).astype(int); f = h - i
    p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s); i = i % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return r, g, b


def neon_palette(hue_shift):
    """256 colori neon: la tinta RUOTA (hue_shift) e SPAZIA lungo l'intensita'
    -> filamenti multicolore che cambiano nel tempo. Scuro->brillante."""
    i = np.linspace(0, 1, 256)
    h = (hue_shift + i * 0.85)                 # attraversa gran parte dello spettro
    s = np.clip(1.0 - i * 0.35, 0, 1)          # centri piu' bianchi (glow)
    v = np.clip(i ** 0.7, 0, 1)                # dark -> bright
    r, g, b = hsv_to_rgb(h, s, v)
    pal = np.stack([r, g, b], axis=1) * 255.0
    return pal.astype(np.uint8)                 # (256,3)


def frame_rgb(fn, a, b, c, d, W, H, pal, theta, P=130000, T=26, span=2.6):
    x = np.random.uniform(-2, 2, P); y = np.random.uniform(-2, 2, P)
    flat = np.zeros(H * W, np.float32)
    ct, st = math.cos(theta), math.sin(theta)   # rotazione continua (ipnotica)
    for it in range(T):
        x, y = fn(x, y, a, b, c, d)
        if it > 5:
            xr = x * ct - y * st; yr = x * st + y * ct        # ruota il campo
            ix = ((xr + span) / (2 * span) * (W - 1)).astype(np.int32)
            iy = ((yr + span) / (2 * span) * (H - 1)).astype(np.int32)
            m = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
            flat += np.bincount(iy[m] * W + ix[m], minlength=H * W).astype(np.float32)
    acc = np.log1p(flat.reshape(H, W))
    mx = acc.max()
    if mx > 0:
        acc /= mx
    idx = np.clip(acc ** 0.7 * 255, 0, 255).astype(np.uint8)   # intensita' -> palette
    return pal[idx]                                            # (H,W,3) colorato


def main():
    ap = argparse.ArgumentParser(description="Visual Strange Light (loop ipnotico)")
    ap.add_argument("--loop", type=float, default=40)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--points", type=int, default=130000)
    ap.add_argument("--out", default=os.path.join(BASE, "base_ipno.mp4"))
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    from PIL import Image
    import random
    seed = args.seed if args.seed is not None else random.randrange(100000)
    np.random.seed(seed); rng = random.Random(seed)

    # attrattore casuale (forma diversa ogni volta) + tinta base casuale
    name = rng.choice(list(ATTRACTORS))
    fn, span = ATTRACTORS[name]
    hue0 = rng.random()
    turns = rng.choice([1, 1, 2])              # quanti giri di rotazione sul loop

    n = int(args.loop * args.fps)
    # frame temporanei FUORI da OneDrive (sennò la sync in tempo reale blocca l'I/O)
    tmp = os.path.join(tempfile.gettempdir(), "teknosteps_str_frames")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    ff = ffmpeg()

    a0 = 1.40 + rng.uniform(-0.2, 0.2); b0 = -2.30 + rng.uniform(-0.2, 0.2)
    c0 = 2.40 + rng.uniform(-0.2, 0.2); d0 = -2.10 + rng.uniform(-0.2, 0.2)
    Aa, Ab, Ac, Ad = 0.30, 0.26, 0.30, 0.26    # deriva piu' ampia = piu' morphing
    for i in range(n):
        ph = 2 * math.pi * i / n               # 0..2pi sul loop -> tutto seamless
        a = a0 + Aa * math.sin(ph); b = b0 + Ab * math.sin(ph + 1.7)
        c = c0 + Ac * math.sin(ph + 3.1); d = d0 + Ad * math.sin(ph + 4.6)
        pal = neon_palette(hue0 + i / n)        # tinta ruota di 1 giro sul loop
        theta = turns * ph                      # rotazione continua
        img = frame_rgb(fn, a, b, c, d, args.w, args.h, pal, theta, P=args.points, span=span)
        Image.fromarray(img, "RGB").save(os.path.join(tmp, f"f{i:05d}.png"))

    subprocess.run([ff, "-y", "-framerate", str(args.fps), "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", args.out, "-loglevel", "error"], check=True)
    shutil.rmtree(tmp)
    print(f"[OK] {args.out} ({os.path.getsize(args.out)/1048576:.0f} MB, {args.loop:.0f}s, "
          f"attrattore {name}, seed {seed}) - Made in Italy")


if __name__ == "__main__":
    main()
