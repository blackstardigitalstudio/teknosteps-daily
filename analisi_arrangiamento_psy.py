# -*- coding: utf-8 -*-
"""
ANALISI ARRANGIAMENTO PSY — mappa build/drop/breakdown lungo TUTTA la traccia.
TeknoSteps · Made in Italy.
Estrae l'energia del KICK/SUB (lowpass 150Hz, downsample 1000Hz = leggerissimo anche
per un'ora) -> RMS al secondo -> classifica ogni tratto: DROP (kick pieno), GROOVE,
BREAKDOWN (kick assente/ipnotico) -> stampa le sezioni e le DURATE tipiche (in bar).
Uso:  python analisi_arrangiamento_psy.py [file...] --bpm 144
"""
import os, sys, glob, subprocess, tempfile, wave
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
LSR = 1000  # sample rate ridotto per l'inviluppo

def ffmpeg():
    for c in (r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe", "ffmpeg"):
        try: subprocess.run([c, "-version"], capture_output=True); return c
        except Exception: pass
    return None

def kick_env(ff, path):
    tmp = os.path.join(tempfile.gettempdir(), "arr.wav")
    subprocess.run([ff, "-y", "-v", "error", "-i", path,
                    "-af", "lowpass=f=150", "-ac", "1", "-ar", str(LSR), tmp],
                   capture_output=True)
    w = wave.open(tmp, "rb"); n = w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    w.close()
    # RMS al secondo
    win = LSR
    m = len(a) // win
    rms = np.sqrt(np.array([np.mean(a[i*win:(i+1)*win]**2) for i in range(m)]) + 1e-12)
    return rms

def sections(rms, bpm):
    mx = np.percentile(rms, 95) or 1.0
    r = rms / mx
    # classi per secondo
    cls = np.where(r > 0.60, "DROP", np.where(r > 0.28, "GROOVE", "BREAK"))
    # merge in blocchi
    secs = []
    cur = cls[0]; start = 0
    for i in range(1, len(cls)):
        if cls[i] != cur:
            secs.append((cur, start, i)); cur = cls[i]; start = i
    secs.append((cur, start, len(cls)))
    # filtra blocchi troppo corti (<4s = rumore di classificazione) fondendoli
    out = []
    for c, s, e in secs:
        if out and (e - s) < 4:
            out[-1] = (out[-1][0], out[-1][1], e)   # estende il precedente
        else:
            out.append((c, s, e))
    bar = 4 * 60.0 / bpm
    return out, bar

def main():
    ff = ffmpeg()
    if not ff: print("[X] ffmpeg mancante"); sys.exit(1)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    bpm = 144
    if "--bpm" in sys.argv: bpm = float(sys.argv[sys.argv.index("--bpm")+1])
    files = args or [p for p in sorted(glob.glob(os.path.join(BASE,"_tracce_riferimento","*")))
                     if p.lower().endswith((".mp3",".wav",".flac",".m4a",".ogg"))]
    for p in files:
        print("\n"+"="*70); print(os.path.basename(p)); print(f"(bar = {4*60/bpm:.2f}s @ {bpm:.0f} BPM)")
        rms = kick_env(ff, p)
        secs, bar = sections(rms, bpm)
        durs = {"DROP": [], "GROOVE": [], "BREAK": []}
        seq = []
        for c, s, e in secs:
            secn = e - s; barn = secn / bar
            durs[c].append(barn)
            seq.append(f"{c}({barn:.0f}b)")
        print("  Sequenza:", " -> ".join(seq[:40]) + (" ..." if len(seq) > 40 else ""))
        print("  Durate tipiche (bar, mediana):")
        for c in ("BREAK", "GROOVE", "DROP"):
            if durs[c]:
                arr = np.array(durs[c])
                print(f"    {c:7} n={len(arr):2}  mediana {np.median(arr):.0f} bar  (min {arr.min():.0f} / max {arr.max():.0f})")
        tot = len(rms)
        share = {c: 100.0*sum(e-s for cc,s,e in secs if cc==c)/tot for c in ("DROP","GROOVE","BREAK")}
        print(f"  Quota tempo: DROP {share['DROP']:.0f}% · GROOVE {share['GROOVE']:.0f}% · BREAK {share['BREAK']:.0f}%")

if __name__ == "__main__":
    main()
