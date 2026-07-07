# -*- coding: utf-8 -*-
"""
TeknoSteps - STORY 9:16 pronte da condividere (Made in Italy)
=============================================================
Le short normali hanno le scritte in alto/in basso, DOVE Instagram/TikTok/Facebook
mettono la loro interfaccia (nome profilo sopra, barra risposta sotto) -> il testo
viene coperto. Questo script rifà lo stesso video verticale ma con le scritte nella
ZONA SICURA centrale, durata 15s (ideale per le story) e salva tutto in una cartella
Download pronta da caricare a mano.

  python crea_story.py                       # tutti e 3 i canali dai 1h esistenti
  python crea_story.py --preset monkey --input teknosteps_scimmia_kling_1h.mp4
"""
import argparse, os, shutil, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
# cartella OneDrive -> si sincronizza da sola sul telefono (app OneDrive)
OUTDIR = os.path.join(os.path.expanduser("~"), "OneDrive", "TeknoSteps_Story")

# sorgente 1h per canale + testo hook + nome file story
CHANNELS = {
    "feet":   dict(src="teknosteps_psy_1h.mp4",            l1="CAN YOU WALK", l2="TO THIS BASS",
                   bottom="TEKNOSTEPS", out="story_teknosteps.mp4"),
    "hypno":  dict(src="teknosteps_ipno_1h.mp4",           l1="DON'T SCROLL", l2="JUST WATCH",
                   bottom="STRANGE LIGHT", out="story_strangelight.mp4"),
    "monkey": dict(src="teknosteps_scimmia_kling_1h.mp4",  l1="THIS MONKEY",  l2="IS ON BEAT",
                   bottom="TEKNO MONKEY", out="story_teknomonkey.mp4"),
}

# Zona sicura story 1080x1920: NON scrivere nei primi ~360px (profilo/nome) ne'
# negli ultimi ~420px (barra risposta / CTA). Tutto il testo sta nel mezzo.
SAFE_TOP = 470          # prima riga hook
SAFE_TOP2 = 590         # seconda riga hook
SAFE_BOTTOM = 470       # etichetta canale = h - SAFE_BOTTOM (ben sopra la barra UI)


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
    dst = os.path.join(BASE, "impact.ttf")
    if not os.path.exists(dst):
        src = "C:/Windows/Fonts/impact.ttf"
        if os.path.exists(src):
            shutil.copyfile(src, dst)
    return "impact.ttf" if os.path.exists(dst) else "arial.ttf"


def esc(t):
    return t.replace(":", "\\:").replace("'", "’")


def cut(ff, src, start, dur, out, l1, l2, bottom, font):
    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=26:2,eq=brightness=-0.34:saturation=1.25[bgb];"
        "[fg]scale=1080:-2[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2[base];"
        f"[base]drawtext=fontfile={font}:text='{esc(l1)}':fontcolor=white:fontsize=92:"
        f"borderw=8:bordercolor=black:x=(w-text_w)/2:y={SAFE_TOP}:box=1:boxcolor=black@0.30:boxborderw=24,"
        f"drawtext=fontfile={font}:text='{esc(l2)}':fontcolor=0x96FF00:fontsize=92:"
        f"borderw=8:bordercolor=black:x=(w-text_w)/2:y={SAFE_TOP2}:box=1:boxcolor=black@0.30:boxborderw=24,"
        f"drawtext=fontfile={font}:text='{esc(bottom)}':fontcolor=white:fontsize=54:"
        f"borderw=6:bordercolor=black:x=(w-text_w)/2:y=h-{SAFE_BOTTOM}:box=1:boxcolor=black@0.30:boxborderw=20[outv]"
    )
    cmd = [ff, "-y", "-ss", str(start), "-t", str(dur), "-i", src,
           "-filter_complex", fc, "-map", "[outv]", "-map", "0:a:0",
           "-c:v", "libx264", "-crf", "24", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-maxrate", "4M", "-bufsize", "8M", "-profile:v", "high", "-level", "4.0",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
           "-t", str(dur), "-movflags", "+faststart", out, "-loglevel", "error"]
    if subprocess.run(cmd, cwd=BASE).returncode != 0:
        sys.exit("[X] ffmpeg errore story")
    print(f"[OK] {out}  ({os.path.getsize(out)/1048576:.1f} MB)")


def main():
    ap = argparse.ArgumentParser(description="Story verticali story-safe TeknoSteps")
    ap.add_argument("--preset", default=None, choices=list(CHANNELS), help="solo un canale")
    ap.add_argument("--input", default=None, help="sovrascrivi il sorgente 1h")
    ap.add_argument("--start", default="00:07:30", help="da dove tagliare")
    ap.add_argument("--dur", type=int, default=15, help="durata story (<=60)")
    args = ap.parse_args()

    ff = ffmpeg(); font = ensure_font()
    os.makedirs(OUTDIR, exist_ok=True)
    keys = [args.preset] if args.preset else list(CHANNELS)
    fatti = []
    for k in keys:
        ch = CHANNELS[k]
        src = args.input or os.path.join(BASE, ch["src"])
        if not os.path.exists(src):
            print(f"[skip] {k}: sorgente mancante {src}")
            continue
        out = os.path.join(OUTDIR, ch["out"])
        cut(ff, src, args.start, args.dur, out, ch["l1"], ch["l2"], ch["bottom"], font)
        fatti.append(out)
    if fatti:
        print(f"\n[OK] {len(fatti)} story pronte in: {OUTDIR}")
        print("     Aprile dal telefono (o copiale) e caricale come Story su IG/TikTok/FB.")
    else:
        sys.exit("[X] nessuna story creata (sorgenti mancanti)")
    print("Made in Italy")


if __name__ == "__main__":
    main()
