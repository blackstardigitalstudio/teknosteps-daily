# -*- coding: utf-8 -*-
"""
CREA TRACCIA — masterizza un render della radio in una traccia pronta.  Made in Italy.
=====================================================================================
Prende un WAV renderizzato (da render-audio.html / TeknoAudio.renderOffline, scaricato
nei Download) e lo trasforma in traccia pronta per la distribuzione (Spotify ecc.):
dissolvenze + normalizzazione loudness a -14 LUFS (standard streaming) -> WAV + MP3
in assets/tracks_out/. 100% suono nostro = no-copyright.

USO:  python crea_traccia.py "<percorso_wav>" "Titolo Traccia"
      python crea_traccia.py                      (usa l'ultimo TeknoSteps_*.wav nei Download)
"""
import os, sys, glob, shutil, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "assets", "tracks_out")
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
FF = shutil.which("ffmpeg") or r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe"


def dur_of(path):
    fp = FF.replace("ffmpeg", "ffprobe")
    r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    title = sys.argv[2] if len(sys.argv) > 2 else "Global Walk II"
    if not src:
        cands = sorted(glob.glob(os.path.join(DOWNLOADS, "TeknoSteps_*.wav")),
                       key=os.path.getmtime)
        if not cands:
            print("X Nessun WAV in Download (TeknoSteps_*.wav). Passa il percorso."); return
        src = cands[-1]
    if not os.path.exists(src):
        print("X File non trovato:", src); return
    os.makedirs(OUT, exist_ok=True)
    d = dur_of(src)
    fade_out_start = max(0.0, d - 4.0)
    base = os.path.join(OUT, "TeknoSteps - %s" % title)
    wav = base + ".wav"; mp3 = base + ".mp3"
    # dissolvenze + loudness streaming (-14 LUFS, true peak -1 dBTP)
    af = ("afade=t=in:st=0:d=0.6,afade=t=out:st=%.2f:d=4," % fade_out_start +
          "loudnorm=I=-14:TP=-1.0:LRA=11")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", src, "-af", af,
                    "-ar", "44100", "-ac", "2", wav], check=True)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", wav, "-b:a", "320k", mp3], check=True)
    print("[OK] Traccia creata (%.1fs):" % d)
    print("   ", wav)
    print("   ", mp3)
    print("Copertina: assets/covers/cover_teknosteps_v1.jpg (3000x3000). Distribuzione: RouteNote.")


if __name__ == "__main__":
    main()
