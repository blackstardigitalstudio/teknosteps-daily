# -*- coding: utf-8 -*-
"""
TeknoSteps - Video SCIMMIETTA che BALLA A TEMPO (canale 3) - Made in Italy
Non un rimbalzo da figurina: una COREOGRAFIA sincronizzata al BPM. La scimmietta
corre, salta, fa piroette; arrivano oggetti (campana, piatto) che colpisce a tempo
con flash + "PING/CRASH", onde d'urto e scossa dello schermo. Sfondo nero + palco
neon che pulsa su ogni beat. Tutto sintetico, no copyright.

Uso:
  python crea_video_scimmia.py                     # audio + coreografia + 1h
  python crea_video_scimmia.py --bpm 150 --bars 8
"""
import argparse, json, math, os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FONTS = "C:/Windows/Fonts/"
W, H = 1920, 1080
FLOOR_Y = int(H * 0.90)
GREEN = (150, 255, 0)
GOLD = (255, 205, 60)
DARK = (170, 120, 20)

# Coreografia: una "mossa" per battuta (4 beat ciascuna). Neutra ai confini di
# battuta -> l'intero giro e' un loop perfetto e senza stacchi.
SCHEDULE = [
    ("RUN", 1), ("JUMP", 4), ("SPIN", 2), ("HIT", "R"),
    ("RUN", -1), ("JUMP", 2), ("SPIN", 3), ("HIT", "combo"),
]
# Impatti oggetti: B = beat globale nel giro (battuta*4 + beat)
EVENTS = [
    dict(Bimp=14, side="R", kind="bell",   sound="PING!"),
    dict(Bimp=28, side="L", kind="cymbal", sound="CRASH!"),
    dict(Bimp=30, side="R", kind="bell",   sound="POM!"),
]


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    sys.exit("ffmpeg non trovato")


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


def manifest_bpm():
    try:
        g = json.load(open(os.path.join(BASE, "manifest.json"), encoding="utf-8")).get("audioGenerator", {})
        bs = [m["bpm"] for m in g.get("moods", []) if m.get("bpm")]
        if bs:
            return sum(bs) / len(bs)          # media dei mood -> minor deriva
    except Exception:
        pass
    return 155.0


def monkey_rgba(path, target_h):
    m = Image.open(path).convert("RGBA")
    arr = np.array(m)
    lum = arr[..., :3].max(axis=2)
    arr[..., 3] = (lum >= 26).astype(np.uint8) * 255
    m = Image.fromarray(arr, "RGBA")
    m.putalpha(m.split()[3].filter(ImageFilter.GaussianBlur(1.3)))
    bb = m.getbbox()
    if bb:
        m = m.crop(bb)
    w = int(m.width * target_h / m.height)
    return m.resize((w, target_h), Image.LANCZOS)


def make_bell(s):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = max(2, s // 36)
    d.ellipse([0.15 * s, 0.10 * s, 0.85 * s, 0.80 * s], fill=GOLD, outline=DARK, width=o)
    d.rectangle([0.15 * s, 0.55 * s, 0.85 * s, 0.80 * s], fill=GOLD, outline=DARK, width=o)
    d.ellipse([0.12 * s, 0.72 * s, 0.88 * s, 0.86 * s], fill=GOLD, outline=DARK, width=o)   # bordo
    d.ellipse([0.43 * s, 0.02 * s, 0.57 * s, 0.14 * s], fill=GOLD, outline=DARK, width=o)   # pomello
    d.ellipse([0.45 * s, 0.84 * s, 0.55 * s, 0.94 * s], fill=DARK)                          # battaglio
    d.ellipse([0.28 * s, 0.20 * s, 0.40 * s, 0.48 * s], fill=(255, 240, 190))               # luce
    return im


def make_cymbal(s):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = max(2, s // 40)
    d.ellipse([0.02 * s, 0.36 * s, 0.98 * s, 0.60 * s], fill=(232, 190, 80), outline=DARK, width=o)
    d.ellipse([0.30 * s, 0.42 * s, 0.70 * s, 0.54 * s], fill=(255, 225, 130), outline=DARK, width=max(1, o // 2))
    d.ellipse([0.44 * s, 0.44 * s, 0.56 * s, 0.52 * s], fill=(200, 150, 40))
    return im


def ease_out(x):
    return 1 - (1 - x) ** 3


def move_transform(kind, param, bp):
    """(ox, oy, sx, sy, rot, flip, trail) per la mossa; neutra a bp=0 e bp=4."""
    ox = oy = rot = 0.0
    sx = sy = 1.0
    flip = trail = False
    if kind == "RUN":
        dr = param
        ox = math.sin(bp / 4 * math.pi) * W * 0.30 * dr        # va e torna
        oy = -abs(math.sin(bp * math.pi * 2)) * 48             # passi/salti
        rot = 7 * dr * math.sin(bp * math.pi * 4)
        sx, sy, flip, trail = 1.06, 0.95, dr < 0, True
    elif kind == "JUMP":
        j = param
        seg = 4.0 / j
        local = (bp % seg) / seg                               # 0..1 per salto
        oy = -math.sin(local * math.pi) * (200 if j > 2 else 300)
        land = max(0.0, 1 - min(local, 1 - local) * 4)         # 1 a terra
        sx, sy = 1 + 0.13 * land, 1 - 0.13 * land
        rot = 9 * math.sin(local * math.pi * 2)
        trail = True
    elif kind == "SPIN":
        rot = (bp / 4) * 360 * param                           # piroetta/e
        oy = -abs(math.sin(bp * math.pi)) * 130
        trail = True
    elif kind == "HIT":
        oy = -abs(math.sin(bp * math.pi * 2)) * 26             # idle a tempo
        sx, sy = 1.03, 0.99
    return ox, oy, sx, sy, rot, flip, trail


def place(canvas, mk, ox, oy, sx, sy, rot, flip, alpha=1.0):
    m = mk.transpose(Image.FLIP_LEFT_RIGHT) if flip else mk
    w = max(1, int(m.width * sx)); h = max(1, int(m.height * sy))
    m = m.resize((w, h), Image.LANCZOS)
    if abs(rot) > 0.5:
        m = m.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        m = m.copy()
        m.putalpha(m.split()[3].point(lambda p: int(p * alpha)))
    px = int(W / 2 + ox - m.width / 2)
    py = int(FLOOR_Y + oy - m.height)
    canvas.alpha_composite(m, (px, py))


def make_choreo(monkey_path, out, bpm, bars, fps):
    mk = monkey_rgba(monkey_path, 600)
    bell = make_bell(230); cymbal = make_cymbal(300)
    spb = 60.0 / bpm
    loop_beats = bars * 4
    base_len = loop_beats * spb
    n = int(round(base_len * fps))
    tmp = os.path.join(BASE, "_monkey_frames")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    imp_font = font("impact.ttf", 150)

    for i in range(n):
        B = (i / fps) / spb % loop_beats               # beat nel giro
        bar = int(B // 4)
        bp = B - bar * 4                                # 0..4 nella battuta
        beat_i = int(B)
        fb = B - beat_i                                 # 0..1 nel beat
        pulse = (1 - fb) ** 1.6                         # lampo su ogni beat
        kind, param = SCHEDULE[bar % len(SCHEDULE)]

        # --- mossa base (serve anche per far seguire lo spotlight) ---
        ox, oy, sx, sy, rot, flip, trail = move_transform(kind, param, bp)

        cv = Image.new("RGBA", (W, H), (6, 7, 10, 255))
        # --- palco neon che pulsa a tempo e SEGUE la scimmia ---
        gx = int(W // 2 + ox * 0.92)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gw = int(360 + 150 * pulse); gh = int(70 + 34 * pulse)
        gd.ellipse([gx - gw, FLOOR_Y - gh, gx + gw, FLOOR_Y + gh],
                   fill=(GREEN[0], GREEN[1], GREEN[2], int(90 + 110 * pulse)))
        cv = Image.alpha_composite(cv, glow.filter(ImageFilter.GaussianBlur(45)))
        if beat_i % 4 == 0:                            # flash sul downbeat
            fl = Image.new("RGBA", (W, H), (GREEN[0], GREEN[1], GREEN[2], int(26 * pulse)))
            cv = Image.alpha_composite(cv, fl)

        shx = shy = 0.0
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for ev in EVENTS:
            d = B - ev["Bimp"]
            if not (-1.05 <= d < 0.85):
                continue
            sgn = 1 if ev["side"] == "R" else -1
            hx = W / 2 + 210 * sgn; hy = FLOOR_Y - 430
            spr = bell if ev["kind"] == "bell" else cymbal
            if d < 0:                                   # oggetto in arrivo
                k = ease_out(d + 1)
                sx0 = (1.2 * W) if sgn > 0 else (-0.2 * W)
                x = sx0 + (hx - sx0) * k
                sc = 0.6 + 0.4 * k
                s = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.LANCZOS)
                cv.alpha_composite(s, (int(x - s.width / 2), int(hy - s.height / 2)))
            else:                                       # impatto: onda + testo + scossa
                x = hx + d * 150 * sgn; y = hy - d * 80
                al = max(0.0, 1 - d / 0.85)
                s = spr.resize((max(1, int(spr.width * (1 + d))), max(1, int(spr.height * (1 + d)))), Image.LANCZOS)
                s = s.copy(); s.putalpha(s.split()[3].point(lambda p: int(p * al)))
                cv.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))
                for rr in (1.0, 0.7):                    # onde d'urto
                    r = int((d + (1 - rr) * 0.2) * 300); a = int(220 * max(0, 1 - d / 0.6) * rr)
                    if r > 2 and a > 0:
                        od.ellipse([hx - r, hy - r, hx + r, hy + r], outline=(255, 255, 200, a), width=max(2, int(10 * rr)))
                ts = 0.5 + min(d / 0.2, 1) * 0.8         # testo pop
                tf = font("impact.ttf", max(20, int(150 * ts)))
                ta = int(255 * max(0, 1 - d / 0.7))
                tw = od.textlength(ev["sound"], font=tf)
                od.text((hx - tw / 2, hy - 250 - 40 * d), ev["sound"], font=tf,
                        fill=(255, 240, 90, ta), stroke_width=4, stroke_fill=(0, 0, 0, ta))
                sh = max(0.0, 1 - d / 0.35) * 22         # scossa schermo
                shx += math.sin(d * 90) * sh; shy += math.cos(d * 70) * sh
                if abs(d) < 0.28 and kind == "HIT":      # la scimmia scatta verso l'oggetto
                    ox += 70 * sgn; sx += 0.06; sy += 0.06

        # --- scia (afterimage) per corsa/salto/piroetta ---
        if trail:
            for j, a in ((0.10, 0.22), (0.20, 0.12)):
                o2 = move_transform(kind, param, max(0.0, bp - j))
                place(cv, mk, o2[0], o2[1], o2[2], o2[3], o2[4], o2[5], alpha=a)
        # scatto extra della scimmia sul beat
        sx *= 1 + 0.04 * pulse; sy *= 1 - 0.02 * pulse
        place(cv, mk, ox, oy, sx, sy, rot, flip)

        cv = Image.alpha_composite(cv, overlay)
        if shx or shy:
            cv = ImageChops.offset(cv, int(shx), int(shy))
        cv.convert("RGB").save(os.path.join(tmp, f"f{i:05d}.png"))

    ff = ffmpeg()
    subprocess.run([ff, "-y", "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", out, "-loglevel", "error"], check=True)
    shutil.rmtree(tmp)
    return base_len


def main():
    ap = argparse.ArgumentParser(description="Video scimmietta che balla a tempo (1h)")
    ap.add_argument("--durata", type=float, default=60)
    ap.add_argument("--bpm", type=float, default=None, help="BPM coreografia (default: media mood del manifest)")
    ap.add_argument("--bars", type=int, default=8, help="battute del giro coreografico")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--cicli", type=int, default=8)
    ap.add_argument("--monkey", default=os.path.join(BASE, "scimmia.png"))
    ap.add_argument("--crf", type=int, default=22)
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(BASE, "teknosteps_scimmia_1h.mp4"))
    ap.add_argument("--no-audio-gen", action="store_true")
    ap.add_argument("--no-anim-gen", action="store_true", help="riusa base_scimmia.mp4")
    args = ap.parse_args()

    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    audio = os.path.join(BASE, "teknosteps_audio.wav")
    base = os.path.join(BASE, "base_scimmia.mp4")
    bpm = args.bpm or manifest_bpm()

    if not args.no_audio_gen or not os.path.exists(audio):
        print("=== 1/4 Audio (con giungla + scimmia) ===")
        subprocess.run([PY, "genera_audio_techno.py", "--cicli", str(args.cicli), "--jungle"],
                       cwd=BASE, env=env, check=True)

    if args.no_anim_gen and os.path.exists(base):
        base_len = args.bars * 4 * (60.0 / bpm)
        print("=== 2/4 Coreografia: riuso base_scimmia.mp4 ===")
    else:
        print("=== 2/4 Coreografia a tempo (BPM %.0f, %d battute) ===" % (bpm, args.bars))
        base_len = make_choreo(args.monkey, base, bpm, args.bars, args.fps)

    ff = ffmpeg(); dur = max(5.0, args.durata * 60.0)
    capped = os.path.join(BASE, "base_scimmia_capped.mp4")

    # allungo il giro a ~120s (loop intero di giri) e ricodifico a bitrate controllato,
    # poi loop-in-copia fino a 1h (i clip cortissimi corrompono il NAL: qui e' lungo).
    segs = max(1, int(round(120.0 / max(1.0, base_len))))
    print("=== 3/4 Ricodifico ~%ds a bitrate controllato (1080p24) ===" % int(segs * base_len))
    enc = [ff, "-y", "-stream_loop", str(segs - 1), "-i", base, "-t", str(segs * base_len),
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=24",
           "-threads", str(args.threads),
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
           "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p",
           "-an", "-movflags", "+faststart", capped, "-loglevel", "error", "-stats"]
    if subprocess.run(enc).returncode != 0:
        sys.exit("ffmpeg errore ricodifica loop")

    print("=== 4/4 Loop in copia fino a %d min + audio ===" % args.durata)
    cmd = [ff, "-y", "-stream_loop", "-1", "-i", capped, "-stream_loop", "-1", "-i", audio,
           "-t", str(dur), "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
           "-movflags", "+faststart", args.out, "-loglevel", "error", "-stats"]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("ffmpeg errore")
    print(f"\n[OK] {args.out}  ({os.path.getsize(args.out)/1048576:.0f} MB) - Made in Italy")


if __name__ == "__main__":
    main()
