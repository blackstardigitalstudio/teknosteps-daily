# -*- coding: utf-8 -*-
"""
ANALISI PROFONDA PSYTRANCE — accurata, multi-segmento. TeknoSteps · Made in Italy.
Campiona PIU' segmenti lungo TUTTA la traccia (15..85%), tiene solo le parti "groove"
(kick attivo, non breakdown) e AGGREGA. Per ogni traccia misura:
  - BPM (mediana sui segmenti groove)
  - Tonalita' (nota fondamentale dal basso/kick -> root del genere)
  - Kick colpi/beat (~1 = four-on-floor) + coda
  - Basso: note/beat + PROFILO sui 16esimi (rolling psy vs offbeat)
  - Bilancio spettrale per bande (quanto il low-end sta "in prima fila")
  - Indice psichedelia (energia/flux medio-alti)
Leggero: analizza solo i segmenti estratti, non l'ora intera.
Uso:  python analisi_profonda_psy.py [file...]
"""
import os, sys, glob, subprocess, tempfile, wave
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
SR = 22050
SEG = 35.0
POS = [0.15, 0.28, 0.41, 0.54, 0.67, 0.80]   # dove campionare (frazione del brano)
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def ffmpeg():
    for c in (r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe", "ffmpeg"):
        try: subprocess.run([c, "-version"], capture_output=True); return c
        except Exception: pass
    return None

def dur(ff, path):
    fp = ff.replace("ffmpeg", "ffprobe")
    try:
        r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception: return 0.0

def load_seg(ff, path, ss):
    tmp = os.path.join(tempfile.gettempdir(), "psyseg.wav")
    subprocess.run([ff, "-y", "-v", "error", "-ss", str(ss), "-t", str(SEG),
                    "-i", path, "-ac", "1", "-ar", str(SR), tmp], capture_output=True)
    try:
        w = wave.open(tmp, "rb"); n = w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        w.close(); return a
    except Exception: return np.zeros(0, np.float32)

def onset_env(x, lo, hi):
    N = 1024; hop = 512
    freqs = np.fft.rfftfreq(N, 1.0 / SR); sel = (freqs >= lo) & (freqs < hi)
    win = np.hanning(N); prev = None; env = []
    for i in range(0, len(x) - N, hop):
        mag = np.abs(np.fft.rfft(x[i:i+N] * win))[sel]
        if prev is not None: env.append(np.maximum(mag - prev, 0).sum())
        prev = mag
    return np.array(env), SR / hop

def bpm_from(env, fps):
    e = env - env.mean(); ac = np.correlate(e, e, "full")[len(e)-1:]
    lo = int(fps * 60 / 200); hi = min(len(ac)-1, int(fps * 60 / 120))
    lag = lo + int(np.argmax(ac[lo:hi])) if hi > lo else 0
    return (60.0 * fps / lag) if lag else 0.0

def peaks_per_beat(env, fps, bpm, thr_mult=1.5):
    if bpm <= 0: return 0.0, []
    thr = env.mean() + thr_mult * env.std(); beat = fps * 60 / bpm
    mind = max(1, int(beat * 0.18)); peaks = []; last = -mind
    for i in range(1, len(env)-1):
        if env[i] > thr and env[i] >= env[i-1] and env[i] > env[i+1] and i - last >= mind:
            peaks.append(i); last = i
    beats = len(env) / beat
    return (len(peaks)/beats if beats else 0.0), peaks

def sixteenth_profile(env, fps, bpm, kick_peaks):
    """Folda l'inviluppo del BASSO sui 4 sedicesimi del beat, usando i kick come fase."""
    if bpm <= 0 or len(kick_peaks) < 4: return [0,0,0,0]
    beat = fps * 60 / bpm; step = beat / 4
    bins = np.zeros(4); cnt = np.zeros(4)
    phase0 = kick_peaks[0]
    for i in range(len(env)):
        pos = ((i - phase0) / step) % 4
        b = int(round(pos)) % 4
        bins[b] += env[i]; cnt[b] += 1
    prof = bins / np.maximum(cnt, 1)
    m = prof.max() or 1.0
    return list(np.round(prof / m, 2))

def bands(x):
    N = 4096; hop = 2048; freqs = np.fft.rfftfreq(N, 1.0/SR)
    B = {"sub 20-60":(20,60), "kick 60-120":(60,120), "basso 120-250":(120,250),
         "low-mid 250-800":(250,800), "mid 800-3k":(800,3000), "alti 3k-11k":(3000,11000)}
    acc = {k:0.0 for k in B}; win = np.hanning(N)
    for i in range(0, len(x)-N, hop):
        mag = np.abs(np.fft.rfft(x[i:i+N]*win))**2
        for k,(lo,hi) in B.items(): acc[k] += mag[(freqs>=lo)&(freqs<hi)].sum()
    tot = sum(acc.values()) or 1.0
    return {k:100.0*v/tot for k,v in acc.items()}

def tonic(x):
    """Nota fondamentale dominante nel basso (30-200Hz) -> root del brano."""
    N = 8192; hop = 4096; freqs = np.fft.rfftfreq(N, 1.0/SR)
    sel = (freqs>=30)&(freqs<=200); fsel = freqs[sel]; acc = np.zeros(sel.sum()); win = np.hanning(N)
    for i in range(0, len(x)-N, hop):
        acc += np.abs(np.fft.rfft(x[i:i+N]*win))[sel]
    if acc.sum()==0: return "?", 0
    f0 = fsel[int(np.argmax(acc))]
    midi = int(round(69 + 12*np.log2(f0/440.0)))
    return NOTES[midi%12], round(f0,1)

def analyze(ff, path):
    d = dur(ff, path); segs = []
    for fr in POS:
        x = load_seg(ff, path, d*fr)
        if len(x) < SR: continue
        ke, fps = onset_env(x, 40, 120)
        bpm = bpm_from(ke, fps)
        kpb, kpk = peaks_per_beat(ke, fps, bpm)
        if kpb < 0.7: continue                       # scarta breakdown (poco kick)
        bo, _ = onset_env(x, 60, 260)
        bpb, _ = peaks_per_beat(bo, fps, bpm)
        prof = sixteenth_profile(bo, fps, bpm, kpk)
        ho, _ = onset_env(x, 3000, 10000)
        segs.append(dict(bpm=bpm, kpb=kpb, bpb=bpb, prof=prof,
                         psy=ho.mean()/(ke.mean()+1e-9), bands=bands(x), tonic=tonic(x)))
    if not segs: return dict(dur=d, groove=0)
    agg = lambda k: float(np.mean([s[k] for s in segs]))
    med_bpm = float(np.median([s["bpm"] for s in segs]))
    bd = {k: float(np.mean([s["bands"][k] for s in segs])) for k in segs[0]["bands"]}
    prof = list(np.round(np.mean([s["prof"] for s in segs], axis=0), 2))
    # tonica piu' frequente
    from collections import Counter
    tn = Counter([s["tonic"][0] for s in segs]).most_common(1)[0][0]
    return dict(dur=d, groove=len(segs), bpm=med_bpm, kpb=agg("kpb"), bpb=agg("bpb"),
                prof=prof, psy=agg("psy"), bands=bd, tonic=tn)

def main():
    ff = ffmpeg()
    if not ff: print("[X] ffmpeg mancante"); sys.exit(1)
    files = sys.argv[1:] or [p for p in sorted(glob.glob(os.path.join(BASE,"_tracce_riferimento","*")))
                             if p.lower().endswith((".mp3",".wav",".flac",".m4a",".ogg"))]
    for p in files:
        print("\n" + "="*70); print(os.path.basename(p))
        r = analyze(ff, p)
        if r.get("groove",0)==0: print("  nessun segmento groove valido"); continue
        print(f"  Durata ~{r['dur']/60:.0f} min | segmenti groove analizzati: {r['groove']}/{len(POS)}")
        print(f"  BPM ~{r['bpm']:.1f}   |   TONALITA' (root basso): {r['tonic']}")
        low = r['bands']['sub 20-60']+r['bands']['kick 60-120']+r['bands']['basso 120-250']
        print(f"  KICK: {r['kpb']:.1f} colpi/beat (~1 = cassa dritta) | BASSO: {r['bpb']:.1f} note/beat")
        print(f"  PROFILO BASSO sui 16esimi [1° 2° 3° 4°]: {r['prof']}  (alto su 2/3/4 = ROLLING psy)")
        print(f"  LOW-END in prima fila: {low:.0f}% dell'energia | PSICHEDELIA: {r['psy']:.2f}")
        print("  Spettro:")
        for k,v in r['bands'].items(): print(f"    {k:16} {v:5.1f}%  {'#'*int(v/2)}")

if __name__ == "__main__":
    main()
