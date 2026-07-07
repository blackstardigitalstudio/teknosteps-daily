# -*- coding: utf-8 -*-
"""
CREA SHORT PROMO - clip verticale 9:16 per TikTok/Reels/YouTube Shorts. Made in Italy.
Camminata + traccia + logo + CTA. Uso: python crea_short_promo.py [video] [traccia] [durata]
"""
import os, sys, subprocess, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
FF = shutil.which("ffmpeg") or r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe"
OUT_DIR = os.path.join(BASE, "promo"); os.makedirs(OUT_DIR, exist_ok=True)

VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "video_output", "teknosteps_neon_jungle_final.mp4")
TRACK = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "assets", "tracks_out", "TeknoSteps - Psy Walk.mp3")
DUR = int(sys.argv[3]) if len(sys.argv) > 3 else 30
LOGO = os.path.join(BASE, "assets", "brand", "teknosteps-logo-official.png")
_stem = os.path.splitext(os.path.basename(VIDEO))[0].replace("teknosteps_", "").replace("_final", "").replace("walk_floor_", "")
OUT = os.path.join(OUT_DIR, "short_" + _stem + ".mp4")
FONT = "C\\:/Windows/Fonts/arialbd.ttf"   # font di sistema, escaped per ffmpeg


def _dur(path):
    try:
        r = subprocess.run([FF.replace("ffmpeg", "ffprobe"), "-v", "error",
            "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception:
        return 999.0


def _make_seamless(src):
    """Loop corti (<4s) come i walk_floor: crossfado la coda sull'inizio per
    togliere lo SCATTO/pop del pavimento al punto di loop. Ritorna un mp4 nuovo."""
    d = _dur(src)
    if d >= 4.0 or d <= 0.6:
        return src   # gia' lungo: lascio com'e'
    xf = 0.25
    tmp = os.path.join(OUT_DIR, "_seamless_" + _stem + ".mp4")
    fc = ("[0]trim=0:%f,setpts=PTS-STARTPTS[bd];"
          "[0]trim=%f:%f,setpts=PTS-STARTPTS,format=yuva420p,"
          "fade=t=out:st=0:d=%f:alpha=1[tl];"
          "[bd][tl]overlay=0:0,fps=24,format=yuv420p[o]" % (d - xf, d - xf, d, xf))
    r = subprocess.run([FF, "-y", "-loglevel", "error", "-i", src,
        "-filter_complex", fc, "-map", "[o]", "-an",
        "-c:v", "libx264", "-crf", "18", tmp], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(tmp):
        print("[!] seamless fallito, uso la clip originale:", r.stderr[-300:])
        return src
    print("[i] loop seamless creato (no pop al punto di loop)")
    return tmp


VIDEO = _make_seamless(VIDEO)

# video (loop) -> largh 1080, centrato su tela 1080x1920 nera; logo in alto; CTA in basso
vf = (
    "[0:v]scale=1080:-2,setsar=1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black[bg];"
    "[1:v]scale=760:-1[lg];"
    "[bg][lg]overlay=(W-w)/2:150[v1];"
    "[v1]drawtext=fontfile='%s':text='24/7 TECHNO RADIO':fontcolor=0x00FF9C:fontsize=52:"
    "x=(w-tw)/2:y=1520:box=1:boxcolor=black@0.5:boxborderw=18[v2];"
    "[v2]drawtext=fontfile='%s':text='NO FACES. JUST STEPS AND BASS.':fontcolor=white:fontsize=40:"
    "x=(w-tw)/2:y=1600:box=1:boxcolor=black@0.45:boxborderw=14[v3];"
    "[v3]drawtext=fontfile='%s':text='teknosteps.com   @teknosteps':fontcolor=0x00FF9C:fontsize=44:"
    "x=(w-tw)/2:y=1720:box=1:boxcolor=black@0.55:boxborderw=16[vout]" % (FONT, FONT, FONT)
)

cmd = [FF, "-y", "-loglevel", "error",
       "-stream_loop", "-1", "-i", VIDEO,   # 0: video (loop)
       "-i", LOGO,                          # 1: logo
       "-i", TRACK,                         # 2: audio
       "-filter_complex", vf,
       "-map", "[vout]", "-map", "2:a",
       "-af", "afade=t=in:st=0:d=0.5,afade=t=out:st=%d:d=1.5" % (DUR - 2),
       "-t", str(DUR), "-r", "30",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT]

print("[i] Rendering short verticale (%ds)..." % DUR)
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("ERRORE ffmpeg:\n", r.stderr[-800:]); sys.exit(1)
print("[OK] Short creato:", OUT, "(%.1f MB)" % (os.path.getsize(OUT) / 1048576))
