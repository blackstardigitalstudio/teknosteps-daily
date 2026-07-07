# -*- coding: utf-8 -*-
"""
TeknoSteps - Video scimmietta 3D (Blender) 1h - Made in Italy
Genera audio -> renderizza il personaggio 3D riggato che cammina (scimmia_blender.py
via Blender headless) -> monta 1h con la musica (loop a bitrate controllato).

Uso:
  python crea_video_scimmia3d.py                 # audio + 3D + 1h
  python crea_video_scimmia3d.py --frames 40 --no-audio-gen
"""
import argparse, glob, os, shutil, subprocess, sys

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


def blender():
    f = shutil.which("blender")
    if f:
        return f
    cands = glob.glob(r"C:\Program Files\Blender Foundation\*\blender.exe")
    if cands:
        return sorted(cands)[-1]
    sys.exit("[X] Blender non trovato. Installa: winget install --id BlenderFoundation.Blender --source winget")


def main():
    ap = argparse.ArgumentParser(description="Video scimmietta 3D 1h")
    ap.add_argument("--durata", type=float, default=60)
    ap.add_argument("--frames", type=int, default=40, help="frame del ciclo di camminata (loop)")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--bpm", type=float, default=150)
    ap.add_argument("--cicli", type=int, default=8)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--crf", type=int, default=22)
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(BASE, "teknosteps_scimmia3d_1h.mp4"))
    ap.add_argument("--no-audio-gen", action="store_true")
    ap.add_argument("--no-3d-gen", action="store_true", help="riusa i frame gia' renderizzati")
    args = ap.parse_args()

    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    ff = ffmpeg()
    audio = os.path.join(BASE, "teknosteps_audio.wav")
    frames_dir = os.path.join(BASE, "_blender_frames")
    base = os.path.join(BASE, "base_scimmia3d.mp4")

    if not args.no_audio_gen or not os.path.exists(audio):
        print("=== 1/4 Audio ===")
        subprocess.run([PY, "genera_audio_techno.py", "--cicli", str(args.cicli)], cwd=BASE, env=env, check=True)

    if not args.no_3d_gen:
        print("=== 2/4 Render 3D (Blender headless) ===")
        if os.path.isdir(frames_dir):
            shutil.rmtree(frames_dir)
        bl = blender()
        r = subprocess.run([bl, "--background", "--python", "scimmia_blender.py", "--",
                            "--frames", str(args.frames), "--fps", str(args.fps),
                            "--w", str(args.w), "--h", str(args.h),
                            "--bpm", str(args.bpm), "--out", "_blender_frames"], cwd=BASE)
        if r.returncode != 0:
            sys.exit("[X] Blender errore")

    pngs = sorted(glob.glob(os.path.join(frames_dir, "f*.png")))
    if not pngs:
        sys.exit("[X] Nessun frame 3D renderizzato")
    print("=== 3/4 Codifico il loop (%d frame) ===" % len(pngs))
    capped = os.path.join(BASE, "base_scimmia3d_capped.mp4")
    enc = [ff, "-y", "-framerate", str(args.fps), "-i", os.path.join(frames_dir, "f%04d.png"),
           "-vf", "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1,fps=%d" %
           (args.w, args.h, args.w, args.h, args.fps),
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
           "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p",
           "-an", "-movflags", "+faststart", base, "-loglevel", "error", "-stats"]
    if subprocess.run(enc).returncode != 0:
        sys.exit("[X] ffmpeg errore encode frame")

    # allunga a ~120s (loop del clip corto) per un loop-in-copia affidabile
    import subprocess as sp
    dur_probe = sp.run([ff, "-i", base], capture_output=True, text=True)
    loop_len = len(pngs) / args.fps
    segs = max(1, int(round(120.0 / max(1.0, loop_len))))
    enc2 = [ff, "-y", "-stream_loop", str(segs - 1), "-i", base, "-t", str(segs * loop_len),
            "-c:v", "copy", "-an", "-movflags", "+faststart", capped, "-loglevel", "error"]
    if subprocess.run(enc2).returncode != 0:
        # fallback: usa direttamente base
        capped = base

    print("=== 4/4 Loop in copia fino a %d min + audio ===" % args.durata)
    dur = max(5.0, args.durata * 60.0)
    cmd = [ff, "-y", "-stream_loop", "-1", "-i", capped, "-stream_loop", "-1", "-i", audio,
           "-t", str(dur), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "44100",
           "-movflags", "+faststart", args.out, "-loglevel", "error", "-stats"]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("[X] ffmpeg errore montaggio")
    print(f"\n[OK] {args.out}  ({os.path.getsize(args.out)/1048576:.0f} MB) - Made in Italy")


if __name__ == "__main__":
    main()
