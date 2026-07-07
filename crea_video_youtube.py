# -*- coding: utf-8 -*-
"""
TeknoSteps - Crea video YouTube (Made in Italy)
================================================
Monta un video lungo (default 1 ora) per YouTube:
  - VIDEO: i pavimenti TeknoSteps (video_output/walk_floor_*.mp4) in sequenza,
           ripetuti in loop fino alla durata richiesta, scalati a 1080p.
  - AUDIO: il file techno generato da render-audio.html (teknosteps_audio.wav),
           ripetuto in loop (è loopabile senza stacco) fino alla durata.

Uso:
  python crea_video_youtube.py
  python crea_video_youtube.py --durata 60 --audio teknosteps_audio.wav
  python crea_video_youtube.py --durata 10 --out test.mp4     (prova veloce)

Richiede ffmpeg (lo cerca nel PATH e, se assente, in Wondershare/Recoverit).
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))


def trova_ffmpeg():
    """Restituisce (ffmpeg, ffprobe) cercando nel PATH e nei fallback noti."""
    candidates_dirs = [
        None,  # PATH
        r"C:\Program Files\Wondershare\Recoverit",
        r"C:\Program Files (x86)\Wondershare\Recoverit",
    ]
    ffmpeg = ffprobe = None
    # 1) PATH
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg:
        return ffmpeg, ffprobe
    # 2) fallback noti
    for d in candidates_dirs[1:]:
        fm = os.path.join(d, "ffmpeg.exe")
        fp = os.path.join(d, "ffprobe.exe")
        if os.path.exists(fm):
            return fm, (fp if os.path.exists(fp) else None)
    return None, None


def trova_pavimenti():
    """Lista dei video di camminata da usare (in ordine)."""
    vids = sorted(glob.glob(os.path.join(BASE, "video_output", "walk_floor_*.mp4")))
    if not vids:
        vids = sorted(glob.glob(os.path.join(BASE, "video_output", "*.mp4")))
    return vids


def main():
    ap = argparse.ArgumentParser(description="Crea video YouTube TeknoSteps")
    ap.add_argument("--audio", default=os.path.join(BASE, "teknosteps_audio.wav"),
                    help="file audio WAV (da render-audio.html)")
    ap.add_argument("--durata", type=float, default=60.0, help="durata in MINUTI (default 60)")
    ap.add_argument("--out", default=os.path.join(BASE, "teknosteps_youtube.mp4"),
                    help="file video di uscita")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--res", default="1920x1080", help="risoluzione, es. 1920x1080")
    ap.add_argument("--crf", type=int, default=20, help="qualità (più basso = migliore, 18-23)")
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--threads", type=int, default=0,
                    help="thread x264 (0=auto). Abbassa (es. 4) se la RAM è satura da altri processi")
    ap.add_argument("--hold", type=float, default=15.0,
                    help="secondi che ogni pavimento resta prima di cambiare (default 15). "
                         "Il cambio avviene al confine del passo (loop 1.5s) => fluido, niente scatti.")
    args = ap.parse_args()

    ffmpeg, _ = trova_ffmpeg()
    if not ffmpeg:
        print("[X] ffmpeg non trovato. Installa ffmpeg o mettilo nel PATH.")
        sys.exit(1)
    print(f"[i] ffmpeg: {ffmpeg}")

    if not os.path.exists(args.audio):
        print(f"[X] Audio non trovato: {args.audio}")
        print("    Genera prima il WAV aprendo 'render-audio.html' nel browser.")
        sys.exit(1)

    pavimenti = trova_pavimenti()
    if not pavimenti:
        print("[X] Nessun video in video_output/. Genera prima i pavimenti.")
        sys.exit(1)
    print(f"[i] {len(pavimenti)} video pavimento trovati.")

    try:
        w, h = (int(x) for x in args.res.lower().split("x"))
    except Exception:
        print("[X] --res non valida (usa es. 1920x1080)")
        sys.exit(1)

    durata_sec = max(5.0, args.durata * 60.0)

    # file concat temporaneo con i pavimenti (in ordine)
    # Ogni pavimento viene ripetuto consecutivamente per "tenerlo" ~hold secondi:
    # il cambio cade al confine del clip (1.5s = un loop di passo), quindi le gambe
    # restano in fase e si percepisce una camminata fluida (niente strobo di pavimenti).
    CLIP_SEC = 1.5
    repeats = max(1, round(args.hold / CLIP_SEC))
    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        for v in pavimenti:
            line = f"file '{v.replace(os.sep, '/')}'\n"
            for _ in range(repeats):
                tmp.write(line)
        tmp.close()

        vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={args.fps}")

        # VELOCE (2 passi): codifico UNA passata del loop pavimenti (scale/pad/fps)
        # e poi lo estendo in COPY fino alla durata piena, invece di ri-codificare
        # 60 minuti interi. Il video e' comunque un loop, quindi il risultato visivo
        # e' identico, ma il render e' ~15x piu' veloce e usa molta meno CPU
        # (fondamentale per farlo girare nel cloud/GitHub Actions).
        vloop = args.out + ".vloop.mp4"
        cmd1 = [
            ffmpeg, "-y",
            "-f", "concat", "-safe", "0", "-i", tmp.name,
            "-vf", vf,
            "-threads", str(args.threads),
            "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p",
            "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            "-an", "-movflags", "+faststart",
            vloop,
        ]
        print(f"[i] Creo video: {args.durata:.0f} min @ {args.res} {args.fps}fps -> {args.out}")
        print("[i] 1/2 codifico il loop visivo (una passata)...")
        if subprocess.run(cmd1).returncode != 0:
            print("[X] ffmpeg (loop visivo) ha restituito un errore.")
            sys.exit(1)
        cmd2 = [
            ffmpeg, "-y", "-fflags", "+genpts",
            "-stream_loop", "-1", "-i", vloop,       # video in loop (COPY, veloce)
            "-stream_loop", "-1", "-i", args.audio,  # audio in loop
            "-t", str(durata_sec),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            args.out,
        ]
        print("[i] 2/2 estendo a durata piena (copy)...")
        r = subprocess.run(cmd2)
        try:
            os.unlink(vloop)
        except OSError:
            pass
        if r.returncode != 0:
            print("[X] ffmpeg ha restituito un errore.")
            sys.exit(r.returncode)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    size_mb = os.path.getsize(args.out) / 1048576
    print(f"\n[OK] Video pronto: {args.out}  ({size_mb:.0f} MB)")
    print("     Caricalo su YouTube. Titolo suggerito:")
    print("     'Techno Walk 120 BPM - 1 Hour Hypnotic Tekno Mix (No Copyright)'")
    print("     Made in Italy.")


if __name__ == "__main__":
    main()
