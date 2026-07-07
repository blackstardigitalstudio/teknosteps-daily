# -*- coding: utf-8 -*-
"""
TeknoSteps - Crea video IPNOTICO da 1 ora (2 canale) - Made in Italy
Visual "Strange Light" (attrattore) in loop continuo + musica (synth del sito),
montati in un MP4 1080p da 1 ora. Stesso suono del canale principale, video diverso.

Uso:
  python crea_video_ipnotico.py                 # genera audio+visual e monta 1h
  python crea_video_ipnotico.py --durata 60 --loop 120
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


def main():
    ap = argparse.ArgumentParser(description="Video ipnotico 1h TeknoSteps")
    ap.add_argument("--durata", type=float, default=60, help="minuti")
    ap.add_argument("--loop", type=float, default=120, help="durata loop visual (s)")
    ap.add_argument("--cicli", type=int, default=8, help="cicli audio")
    ap.add_argument("--crf", type=int, default=27)
    ap.add_argument("--maxrate", default="5M", help="tetto bitrate video (file ~2GB/1h -> upload veloce)")
    ap.add_argument("--bufsize", default="10M")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(BASE, "teknosteps_ipno_1h.mp4"))
    ap.add_argument("--no-audio-gen", action="store_true", help="usa teknosteps_audio.wav esistente")
    ap.add_argument("--no-visual-gen", action="store_true", help="riusa base_ipno.mp4 esistente")
    args = ap.parse_args()

    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    audio = os.path.join(BASE, "teknosteps_audio.wav")
    base = os.path.join(BASE, "base_ipno.mp4")
    ff = ffmpeg()

    if not args.no_audio_gen or not os.path.exists(audio):
        print("=== 1/3 Audio LUNGO che cambia ritmo (synth + voci EN naturalistiche) ===")
        mins = max(5.0, args.durata + 1)   # 1 min di margine oltre il video
        # --cicli 5 => blocchi da ~4-5 min: il ritmo cambia ~13 volte nell'ora
        # --bpm 140 => tempo COSTANTE + numero TONDO molto cercato (progressive/hypnotic psy)
        subprocess.run([PY, "genera_audio_techno.py", "--minuti", str(mins), "--cicli", "5",
                        "--bpm", "140", "--voices"], cwd=BASE, env=env, check=True)

    if args.no_visual_gen and os.path.exists(base):
        print("=== 2/3 Visual: riuso base_ipno.mp4 esistente ===")
    else:
        print("=== 2/3 Visual Strange Light (loop) ===")
        subprocess.run([PY, "genera_visual_attrattore.py", "--loop", str(args.loop),
                        "--w", "1920", "--h", "1080", "--out", base], cwd=BASE, env=env, check=True)

    dur = max(5.0, args.durata * 60.0)
    capped = os.path.join(BASE, "base_ipno_capped.mp4")

    print("=== 3/4 Ricodifico il loop a bitrate controllato (1080p24) ===")
    enc = [ff, "-y", "-i", base,
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=24",
           "-threads", str(args.threads),
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
           "-maxrate", args.maxrate, "-bufsize", args.bufsize, "-pix_fmt", "yuv420p",
           "-an", "-movflags", "+faststart", capped, "-loglevel", "error", "-stats"]
    if subprocess.run(enc).returncode != 0:
        sys.exit("ffmpeg errore ricodifica loop")

    print("=== 4/4 Loop in copia fino a %d min + audio ===" % args.durata)
    cmd = [ff, "-y",
           "-stream_loop", "-1", "-i", capped,
           "-i", audio,
           "-t", str(dur),
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
           "-movflags", "+faststart", args.out, "-loglevel", "error", "-stats"]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("ffmpeg errore montaggio")
    print(f"\n[OK] {args.out}  ({os.path.getsize(args.out)/1048576:.0f} MB) - Made in Italy")


if __name__ == "__main__":
    main()
