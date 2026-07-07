# -*- coding: utf-8 -*-
"""
TeknoSteps - Short VERTICALI virali 9:16 (Made in Italy)
=========================================================
Formato "reel": il video al centro, sfondo sfumato dal video stesso (blur), HOOK
grande in alto e hashtag in basso -> molto piu' cliccabile del semplice crop.
Riusa i video 1h gia' fatti (ffmpeg, niente re-render pesante).

Preset per canale:
  python crea_short.py --preset monkey --input teknosteps_scimmia_1h_v3.mp4 --auto 3
  python crea_short.py --preset feet   --input teknosteps_psy_1h.mp4 --auto 3
  python crea_short.py --preset hypno  --input teknosteps_ipno_1h.mp4 --auto 3
"""
import argparse, os, shutil, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))

PRESETS = {
    # hook: due righe corte (Impact non ha emoji, testo secco che buca)
    "monkey": dict(l1="THIS MONKEY", l2="IS ON BEAT", bottom="TEKNO MONKEY   -   #Shorts"),
    "feet":   dict(l1="CAN YOU WALK", l2="TO THIS BASS", bottom="DARK PSYTRANCE   -   #Shorts"),
    "hypno":  dict(l1="DON'T SCROLL", l2="JUST WATCH", bottom="HYPNOTIC PSY   -   #Shorts"),
}


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit", r"C:\Program Files (x86)\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    sys.exit("[X] ffmpeg non trovato")


def ensure_font():
    """Copia Impact nella cartella -> fontfile relativo, niente escaping di 'C:'."""
    dst = os.path.join(BASE, "impact.ttf")
    if not os.path.exists(dst):
        src = "C:/Windows/Fonts/impact.ttf"
        if os.path.exists(src):
            shutil.copyfile(src, dst)
    return "impact.ttf" if os.path.exists(dst) else "arial.ttf"


def esc(t):
    return t.replace(":", "\\:").replace("'", "’")


def cut(ff, src, start, dur, out, pre, font):
    l1, l2, bottom = pre["l1"], pre["l2"], pre["bottom"]
    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=26:2,eq=brightness=-0.34:saturation=1.25[bgb];"
        "[fg]scale=1080:-2[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2[base];"
        f"[base]drawtext=fontfile={font}:text='{esc(l1)}':fontcolor=white:fontsize=96:"
        "borderw=8:bordercolor=black:x=(w-text_w)/2:y=150:box=1:boxcolor=black@0.28:boxborderw=24,"
        f"drawtext=fontfile={font}:text='{esc(l2)}':fontcolor=0x96FF00:fontsize=96:"
        "borderw=8:bordercolor=black:x=(w-text_w)/2:y=260:box=1:boxcolor=black@0.28:boxborderw=24,"
        f"drawtext=fontfile={font}:text='{esc(bottom)}':fontcolor=white:fontsize=46:"
        "borderw=6:bordercolor=black:x=(w-text_w)/2:y=h-210[outv]"
    )
    cmd = [ff, "-y", "-ss", str(start), "-t", str(dur), "-i", src,
           "-filter_complex", fc, "-map", "[outv]", "-map", "0:a:0",
           "-c:v", "libx264", "-crf", "22", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2",
           "-t", str(dur), "-movflags", "+faststart", out, "-loglevel", "error"]
    if subprocess.run(cmd, cwd=BASE).returncode != 0:
        sys.exit("[X] ffmpeg errore short")
    print(f"[OK] {out}  ({os.path.getsize(out)/1048576:.0f} MB)")


def main():
    ap = argparse.ArgumentParser(description="Short verticali virali TeknoSteps")
    ap.add_argument("--input", required=True)
    ap.add_argument("--preset", default="monkey", choices=list(PRESETS))
    ap.add_argument("--start", default="00:05:00")
    ap.add_argument("--dur", type=int, default=24, help="durata short (<=60)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--auto", type=int, default=0, help="N short a tempi distribuiti")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"[X] Input non trovato: {args.input}")
    ff = ffmpeg(); font = ensure_font(); pre = PRESETS[args.preset]

    if args.auto > 0:
        spots = [6 + int(i * 48 / max(1, args.auto)) for i in range(args.auto)]
        for i, m in enumerate(spots, 1):
            out = os.path.join(BASE, f"short_{args.preset}_{i:02d}.mp4")
            cut(ff, args.input, f"00:{m:02d}:00", args.dur, out, pre, font)
    else:
        out = args.out or os.path.join(BASE, f"short_{args.preset}.mp4")
        cut(ff, args.input, args.start, args.dur, out, pre, font)


if __name__ == "__main__":
    main()
