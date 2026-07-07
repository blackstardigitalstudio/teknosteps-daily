# -*- coding: utf-8 -*-
"""
TeknoSteps - Monta le clip Kling (scimmietta 3D reale) - Made in Italy
Prende UNA o PIU' clip verticali 9:16 da Kling (5s, 720x1280), copre il watermark
col nostro brand, le concatena e fa un loop FLUIDO "boomerang" (avanti+indietro,
niente stacco), poi produce:
  - VIDEO 1h 16:9  (clip su palco neon sfumato) + audio techno
  - SHORT 9:16      (a tutto schermo + hook + brand) + audio techno

Uso:
  python crea_video_kling.py --clips scimmia_kling_clip.mp4 walk.mp4
  python crea_video_kling.py --clips a.mp4 --only short
"""
import argparse, os, shutil, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    sys.exit("ffmpeg non trovato")


def font_():
    dst = os.path.join(BASE, "impact.ttf")
    if not os.path.exists(dst) and os.path.exists("C:/Windows/Fonts/impact.ttf"):
        shutil.copyfile("C:/Windows/Fonts/impact.ttf", dst)
    return "impact.ttf" if os.path.exists(dst) else "arial.ttf"


def ensure_audio(env):
    audio = os.path.join(BASE, "teknosteps_audio.wav")
    # Audio EVOLUTIVO (--minuti: melodia/composizione/ritmo cambiano nell'ora) a BPM 150
    # fisso, carattere DARK/aggressivo (--dark) + scimmia incazzata (--jungle). Non piu' loop.
    subprocess.run([PY, "genera_audio_techno.py", "--minuti", "61", "--cicli", "5",
                    "--bpm", "150", "--dark", "--jungle"], cwd=BASE, env=env, check=True)
    return audio


COVER = ("drawbox=x=iw-340:y=ih-72:w=340:h=72:color=black@0.9:t=fill,"
         "drawtext=fontfile={f}:text='teknosteps.com':fontcolor=0x96FF00:fontsize=32:x=w-260:y=h-54")

VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"]


def norm_short(ff, clip, out, font, h1, h2):
    fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=24,"
          + COVER.format(f=font) + ","
          f"drawtext=fontfile={font}:text='{h1}':fontcolor=white:fontsize=92:borderw=8:bordercolor=black:x=(w-text_w)/2:y=140,"
          f"drawtext=fontfile={font}:text='{h2}':fontcolor=0x96FF00:fontsize=92:borderw=8:bordercolor=black:x=(w-text_w)/2:y=250[v]")
    subprocess.run([ff, "-y", "-i", clip, "-filter_complex", fc, "-map", "[v]"] + VENC + [out, "-loglevel", "error"], check=True)


def norm_long(ff, clip, out, font):
    fc = ("[0:v]" + COVER.format(f=font) + ",fps=24,split=2[a][b];"
          "[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:2,eq=brightness=-0.32:saturation=1.3[bg];"
          "[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]")
    subprocess.run([ff, "-y", "-i", clip, "-filter_complex", fc, "-map", "[v]"] + VENC + [out, "-loglevel", "error"], check=True)


def concat_copy(ff, files, out):
    lst = os.path.join(BASE, "_kl_list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in files:
            f.write("file '%s'\n" % p.replace("\\", "/"))
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out, "-loglevel", "error"], check=True)
    os.remove(lst)


def boomerang(ff, seq, out):
    # avanti + indietro -> loop perfettamente fluido (start == end)
    subprocess.run([ff, "-y", "-i", seq, "-filter_complex",
                    "[0:v]reverse[r];[0:v][r]concat=n=2:v=1[v]", "-map", "[v]"] + VENC + [out, "-loglevel", "error"], check=True)


def loop_with_audio(ff, base, audio, dur, out, stats=False):
    # audio EVOLUTIVO lungo tutta l'ora -> NON in loop (si ripete solo il video)
    cmd = [ff, "-y", "-stream_loop", "-1", "-i", base, "-i", audio,
           "-t", str(dur), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
           "-movflags", "+faststart", out, "-loglevel", "error"]
    if stats:
        cmd.append("-stats")
    subprocess.run(cmd, check=True)


def build(ff, clips, audio, out, font, mode, dur, h1, h2):
    norms = []
    for i, c in enumerate(clips):
        n = os.path.join(BASE, f"_kl_norm_{mode}_{i}.mp4")
        (norm_short if mode == "short" else norm_long)(ff, c, n, font, *( (h1, h2) if mode == "short" else () ))
        norms.append(n)
    seq = norms[0] if len(norms) == 1 else os.path.join(BASE, f"_kl_seq_{mode}.mp4")
    if len(norms) > 1:
        concat_copy(ff, norms, seq)
    boom = os.path.join(BASE, f"_kl_boom_{mode}.mp4")
    boomerang(ff, seq, boom)
    loop_with_audio(ff, boom, audio, dur, out, stats=(mode == "long"))
    for f in norms + [seq if len(norms) > 1 else None, boom]:
        if f and os.path.exists(f):
            os.remove(f)
    print(f"[OK] {mode.upper()} {out}  ({os.path.getsize(out)/1048576:.0f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", nargs="+", required=True)
    ap.add_argument("--short-out", default=os.path.join(BASE, "short_monkey_kling.mp4"))
    ap.add_argument("--long-out", default=os.path.join(BASE, "teknosteps_scimmia_kling_1h.mp4"))
    ap.add_argument("--durata", type=float, default=60)
    ap.add_argument("--hook1", default="TEKNO MONKEY")
    ap.add_argument("--hook2", default="ON THE BEAT")
    ap.add_argument("--only", choices=["short", "long", "both"], default="both")
    args = ap.parse_args()

    for c in args.clips:
        if not os.path.exists(c):
            sys.exit(f"[X] Clip non trovata: {c}")
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    ff = ffmpeg(); font = font_(); audio = ensure_audio(env)

    if args.only in ("short", "both"):
        build(ff, args.clips, audio, args.short_out, font, "short", 24, args.hook1, args.hook2)
    if args.only in ("long", "both"):
        build(ff, args.clips, audio, args.long_out, font, "long", max(5.0, args.durata * 60.0), args.hook1, args.hook2)
    print("Made in Italy.")


if __name__ == "__main__":
    main()
