# -*- coding: utf-8 -*-
"""
analizza_tracce.py  —  Analizzatore tracce frenchtek/tribe per TeknoSteps.
Made in Italy.

COSA FA
  Decodifica una o piu' tracce audio (mp3/wav/...) con ffmpeg e ne misura, in
  puro numpy (niente librosa/scipy), le caratteristiche che servono al synth
  Web Audio (techno-audio.js):

    • BPM            (tempo, via spectral-flux + autocorrelazione)
    • Tonalita'      (root, via chromagram -> rootSemis relativo ad A)
    • Kick decay     (coda del kick in secondi, dall'inviluppo banda bassa)
    • Brillantezza   (centroide spettrale -> parametro `bright`)
    • Sub / Basso    (bilancio energia 30-60 Hz vs 60-160 Hz -> subLevel/bassLevel)
    • Grit / Drive   (contenuto armonico medio sul basso -> bassDriveAmt)

  Stampa un report leggibile per ogni traccia e genera i preset MOOD nello
  schema ESATTO di manifest.json -> audioGenerator.moods, pronti da incollare
  (o con --scrivi-manifest li aggiorna direttamente, facendo backup).

USO
  python analizza_tracce.py                          # analizza _tracce_riferimento/*.mp3
  python analizza_tracce.py traccia1.mp3 traccia2.mp3
  python analizza_tracce.py --json                   # stampa solo il JSON dei moods
  python analizza_tracce.py --scrivi-manifest        # aggiorna manifest.json (con backup)

Richiede ffmpeg (cercato nel PATH e nei fallback noti, come crea_video_youtube.py).
"""

import os
import sys
import glob
import json
import shutil
import argparse
import subprocess

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
SR = 22050              # sample rate di analisi (basta per basso/kick + brillantezza)
N_FFT = 2048
HOP = 512
FPS = SR / HOP         # frame al secondo dell'inviluppo (~43 Hz)

# Nomi note per pitch-class (C=0 ... A=9 ... B=11)
NOTE_NAMES = ["Do", "Do#", "Re", "Re#", "Mi", "Fa",
              "Fa#", "Sol", "Sol#", "La", "La#", "Si"]


# ---------------------------------------------------------------- ffmpeg ----
def trova_ffmpeg():
    """ffmpeg dal PATH o dai fallback noti (stessa logica di crea_video_youtube.py)."""
    fm = shutil.which("ffmpeg")
    if fm:
        return fm
    for d in (r"C:\Program Files\Wondershare\Recoverit",
              r"C:\Program Files (x86)\Wondershare\Recoverit"):
        cand = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(cand):
            return cand
    return None


def decodifica(ffmpeg, path, max_s=150):
    """Segnale mono float32 a SR Hz, normalizzato. Per file lunghi (DJ set da 1h+)
    decodifica solo una FINESTRA CENTRALE di ~max_s secondi: rappresentativa del
    suono e leggera in memoria (evita di allocare centinaia di MB per un set intero)."""
    seek = []
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    try:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nk=1:nw=1", path],
                           capture_output=True, text=True)
        dur = float((r.stdout or "").strip())
        if dur > max_s:
            seek = ["-ss", str(max(0.0, (dur - max_s) / 2.0)), "-t", str(max_s)]
    except Exception:
        seek = ["-t", str(max_s)]           # se non riesco a leggere la durata, cappo comunque
    cmd = [ffmpeg, "-v", "error", *seek, "-i", path,
           "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(out, dtype=np.float32).astype(np.float64)
    if x.size == 0:
        raise RuntimeError(f"ffmpeg non ha prodotto audio per: {path}")
    # togli eventuale DC e normalizza per stabilita' delle misure
    x = x - x.mean()
    peak = np.max(np.abs(x)) or 1.0
    return x / peak


# ----------------------------------------------------------------- STFT -----
def stft_mag(x):
    """Spettrogramma di ampiezza |STFT| con finestra di Hann. Shape [bins, frames]."""
    win = np.hanning(N_FFT)
    n_frames = 1 + (len(x) - N_FFT) // HOP
    if n_frames < 4:
        raise RuntimeError("traccia troppo corta per l'analisi")
    # matrice di frame (vista a finestra scorrevole)
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    frames = x[idx] * win                      # [frames, N_FFT]
    spec = np.fft.rfft(frames, axis=1)
    return np.abs(spec).T                       # [bins, frames]


def freqs_bin():
    return np.fft.rfftfreq(N_FFT, 1.0 / SR)     # Hz per ogni bin


def banda(S, fbins, lo, hi):
    """Energia media nel tempo sulla banda [lo, hi] Hz."""
    m = (fbins >= lo) & (fbins < hi)
    if not m.any():
        return 0.0
    return float(S[m, :].sum(axis=0).mean())


# ------------------------------------------------------------- BPM ----------
def stima_bpm(S):
    """BPM via spectral flux + autocorrelazione, ripiegato nel range tek (140-180)."""
    # spectral flux: somma delle differenze positive tra frame consecutivi
    diff = np.diff(S, axis=1)
    flux = np.maximum(diff, 0).sum(axis=0)
    flux = flux - flux.mean()
    flux = flux / (np.std(flux) or 1.0)

    # autocorrelazione dell'inviluppo di onset
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    # lag (in frame) corrispondente a 60..200 BPM
    lag_min = int(FPS * 60.0 / 200.0)
    lag_max = int(FPS * 60.0 / 60.0)
    lag_max = min(lag_max, len(ac) - 1)
    seg = ac[lag_min:lag_max].copy()
    if seg.size == 0:
        return 0.0
    best = lag_min + int(np.argmax(seg))
    bpm = 60.0 * FPS / best

    # ripiega negli ottava giusta per il genere (frenchtek/tribe ~ 140-180)
    while bpm < 140:
        bpm *= 2.0
    while bpm > 185:
        bpm /= 2.0
    return round(bpm, 1)


# ------------------------------------------------------------- Tonalita' ----
def stima_root(S, fbins):
    """Chromagram pesato sul registro basso -> (pitch_class, rootSemis, nome)."""
    chroma = np.zeros(12)
    # enfatizza 40-520 Hz: in questo genere la tonica vive nel kick/basso
    m = (fbins >= 40) & (fbins < 520)
    energia = S[m, :].sum(axis=1)               # energia totale per bin
    for f, e in zip(fbins[m], energia):
        if f <= 0:
            continue
        midi = 69 + 12 * np.log2(f / 440.0)     # nota MIDI (A4=69)
        pc = int(round(midi)) % 12
        chroma[pc] += e
    pc = int(np.argmax(chroma))
    # rootSemis relativo ad A (pc 9). G#(8) -> -1, in [-6, +5]
    rootSemis = ((pc - 9 + 6) % 12) - 6
    return pc, rootSemis, NOTE_NAMES[pc]


# ------------------------------------------------------------- Kick ---------
def stima_kick_decay(S, fbins):
    """Coda media del kick (s): picchi nell'inviluppo 30-130 Hz e tempo a -20 dB."""
    m = (fbins >= 30) & (fbins < 130)
    env = S[m, :].sum(axis=0)
    if env.max() <= 0:
        return 0.40
    env = env / env.max()

    # soglia + minima distanza tra kick (a 180 BPM il beat dista ~0.33s)
    thr = max(0.35, np.percentile(env, 75))
    min_gap = int(0.20 * FPS)
    picchi = []
    i = 1
    while i < len(env) - 1:
        if env[i] >= thr and env[i] >= env[i - 1] and env[i] > env[i + 1]:
            picchi.append(i)
            i += min_gap
        else:
            i += 1

    decadimenti = []
    for p in picchi:
        peak = env[p]
        target = peak * 0.10                    # -20 dB
        j = p + 1
        # ferma alla prossima possibile battuta per non sommare due kick
        limit = min(len(env), p + int(0.55 * FPS))
        while j < limit and env[j] > target:
            j += 1
        decadimenti.append((j - p) / FPS)

    if not decadimenti:
        return 0.40
    val = float(np.median(decadimenti))
    return round(min(0.55, max(0.28, val)), 3)


# ---------------------------------------------------- Brillantezza / centroide
def centroide(S, fbins):
    """Centroide spettrale medio (Hz): indice di brillantezza del mix."""
    pesi = S.sum(axis=1)
    tot = pesi.sum() or 1.0
    return float((fbins * pesi).sum() / tot)


def densita_basso(S, fbins, bpm):
    """Colpi di basso per movimento (beat): distingue il groove del genere.
    ~1 = offbeat (techno), ~3-4 = rolling a 16esimi (psytrance), <1 = rado (minimal)."""
    m = (fbins >= 30) & (fbins < 160)
    env = S[m, :].sum(axis=0)
    if env.max() <= 0:
        return 0.0
    env = env / env.max()
    thr = max(0.30, np.percentile(env, 70))
    min_gap = max(1, int(0.06 * FPS))              # ~60ms tra colpi (fino a ~16esimi veloci)
    picchi = 0
    i = 1
    while i < len(env) - 1:
        if env[i] >= thr and env[i] >= env[i - 1] and env[i] > env[i + 1]:
            picchi += 1
            i += min_gap
        else:
            i += 1
    durata = len(env) / FPS
    onsets_al_sec = picchi / durata if durata > 0 else 0
    beats_al_sec = (bpm or 140) / 60.0
    return round(onsets_al_sec / beats_al_sec, 2) if beats_al_sec else 0.0


# Config di stile per genere (coerente coi mood base del manifest): il mood custom
# eredita groove/scala/cassa/lead del genere riconosciuto, non parametri generici.
STILE_GENERE = {
    "techno":    {"bassStyle": "offbeat", "scale": "minor",    "kickStyle": "punch", "leadStyle": "acid"},
    "techhouse": {"bassStyle": "offbeat", "scale": "minor",    "kickStyle": "punch", "leadStyle": "pluck"},
    "minimal":   {"bassStyle": "sparse",  "scale": "pent",     "kickStyle": "punch", "leadStyle": "pluck"},
    "psytrance": {"bassStyle": "rolling", "scale": "phrygian", "kickStyle": "808",   "leadStyle": "pluck"},
    "trance":    {"bassStyle": "rolling", "scale": "dorian",   "kickStyle": "punch", "leadStyle": "supersaw"},
    "hardtek":   {"bassStyle": "offbeat", "scale": "minor",    "kickStyle": "808",   "leadStyle": "acid"},
}
# Densita' lead e acid per genere (psy/trance "cantano", techno/minimal no).
LEAD_DENS = {"psytrance": [0.10, 0.24], "trance": [0.14, 0.30], "hardtek": [0.0, 0.0],
             "techno": [0.0, 0.06], "techhouse": [0.06, 0.16], "minimal": [0.0, 0.0]}
ACID_LVL = {"psytrance": 0.5, "trance": 0.2, "techno": 0.12, "techhouse": 0.1,
            "minimal": 0.05, "hardtek": 0.0}
GENERI = ["techno", "techhouse", "minimal", "psytrance", "trance", "hardtek"]

# La cartella che contiene la traccia e' la VERITA' sul genere (l'utente le ordina a
# mano): _tracce_riferimento/<genere>/... -> mappa il nome cartella al genere canonico.
FOLDER_GENRE = {
    "techno": "techno", "techhouse": "techhouse", "tech house": "techhouse",
    "tech-house": "techhouse", "minimal": "minimal", "psytrance": "psytrance",
    "psy": "psytrance", "trance": "trance", "tekno": "hardtek", "hardtek": "hardtek",
    "freetekno": "hardtek", "tribe": "hardtek", "acidcore": "hardtek",
}

# Coda del kick TIPICA per genere (s). Usata quando la misura sul MIX e' inaffidabile
# (su un mix denso la banda bassa non torna a zero prima della cassa dopo -> il valore
# satura al tetto ~0.55s e non e' la vera coda del kick). Valori da produzione:
# psy tight/corto, hardtek 909 con coda distorta piu' lunga.
KICK_DECAY_GENRE = {"techno": 0.16, "techhouse": 0.13, "minimal": 0.14,
                    "psytrance": 0.10, "trance": 0.16, "hardtek": 0.20}


def genere_da_cartella(path):
    """Genere dal nome della cartella genitore (verita' sull'ordinamento manuale).
    Ritorna None se la traccia sta nella root (_tracce_riferimento) -> si auto-classifica."""
    parent = os.path.basename(os.path.dirname(os.path.abspath(path))).strip().lower()
    return FOLDER_GENRE.get(parent)


def applica_genere(mood, genere):
    """Applica a un mood lo STILE del genere (groove/scala/cassa/lead + lead/acid).
    Usato sia da a_preset sia dalla correzione manuale nel pannello."""
    st = STILE_GENERE.get(genere, STILE_GENERE["techno"])
    mood["genre"] = genere
    mood["bassStyle"] = st["bassStyle"]
    mood["scale"] = st["scale"]
    mood["kickStyle"] = st["kickStyle"]
    mood["leadStyle"] = st["leadStyle"]
    mood["leadDensity"] = list(LEAD_DENS.get(genere, [0.0, 0.0]))
    mood["acidLevel"] = ACID_LVL.get(genere, 0.1)
    mood["choir"] = 0.5 if genere == "trance" else 0.0
    return mood


def classifica_genere(bpm, centroid, sub_ratio, grit, bass_density):
    """Classifica il genere da BPM (segnale piu' forte per l'EDM) + densita' basso
    (rolling vs offbeat vs rado) + brillantezza. Ritorna (genere, motivazione)."""
    if bpm >= 155:
        return "hardtek", f"BPM molto alto ({bpm:.0f}) = frenchtek/hardtek"
    if bpm >= 138 and bass_density >= 2.4:
        return "psytrance", f"veloce ({bpm:.0f}) + basso rolling ({bass_density})"
    if bpm >= 143:
        return "psytrance", f"BPM da psytrance ({bpm:.0f})"
    if bpm <= 128 and bass_density < 1.6:
        return "minimal", f"lento ({bpm:.0f}) + groove rado ({bass_density})"
    if 133 <= bpm <= 143 and centroid > 1500 and grit < 0.55:
        return "trance", f"BPM trance ({bpm:.0f}) + brillante/melodico"
    return "techno", f"BPM techno ({bpm:.0f}) + groove offbeat"


# --------------------------------------------------------- Analisi completa -
def analizza(ffmpeg, path):
    x = decodifica(ffmpeg, path)
    dur = len(x) / SR
    # se molto lunga, analizza una finestra centrale di 90s (stabile e veloce)
    if dur > 100:
        c = len(x) // 2
        h = int(45 * SR)
        x = x[c - h:c + h]

    S = stft_mag(x)
    fbins = freqs_bin()

    bpm = stima_bpm(S)
    pc, rootSemis, nota = stima_root(S, fbins)
    kick_decay_mis = stima_kick_decay(S, fbins)
    cen = centroide(S, fbins)

    sub = banda(S, fbins, 30, 60)
    bass = banda(S, fbins, 60, 160)
    lowmid = banda(S, fbins, 160, 500)
    mid = banda(S, fbins, 500, 3000)
    low_tot = sub + bass + 1e-9

    sub_ratio = sub / low_tot                     # quanta parte del basso e' sub
    grit = mid / (bass + lowmid + 1e-9)           # armoniche medie = distorsione bassi
    bass_density = densita_basso(S, fbins, bpm)   # colpi di basso per beat (groove)

    # GENERE: la cartella vince (ordinamento manuale). In root -> auto-classifica.
    genere_auto, motivo_auto = classifica_genere(bpm, cen, sub_ratio, grit, bass_density)
    genere_cart = genere_da_cartella(path)
    if genere_cart:
        genere = genere_cart
        motivo = f"cartella '{genere_cart}'"
        if genere_auto != genere_cart:
            motivo += f" (auto avrebbe detto {genere_auto})"
    else:
        genere, motivo = genere_auto, motivo_auto

    # KICK DECAY: la misura sui mix satura (~0.55s) e non e' la vera coda -> se e'
    # vicina al tetto usa il default di produzione per il genere.
    if kick_decay_mis >= 0.50:
        kick_decay = KICK_DECAY_GENRE.get(genere, 0.16)
        kick_note = f"default {genere} (misura {int(kick_decay_mis*1000)}ms inaffidabile sul mix)"
    else:
        kick_decay = kick_decay_mis
        kick_note = "misurato"

    return {
        "file": os.path.basename(path),
        "durata_s": round(dur, 1),
        "bpm": bpm,
        "nota": nota,
        "rootSemis": rootSemis,
        "kick_decay_s": kick_decay,
        "kick_note": kick_note,
        "centroide_hz": round(cen, 0),
        "sub_ratio": round(sub_ratio, 3),
        "grit": round(grit, 3),
        "bass_density": bass_density,
        "genere": genere,
        "genere_motivo": motivo,
        "_bande": {"sub": sub, "bass": bass, "lowmid": lowmid, "mid": mid},
    }


# ---------------------------------------- Mappa misure -> parametri synth ----
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def a_preset(a, nome):
    """Converte le misure grezze nei parametri MOOD del synth (range calibrati)."""
    # bright: centroide ~1200 Hz (scuro) -> 0.70 ; ~3200 Hz (brillante) -> 1.05
    bright = round(clamp(0.70 + (a["centroide_hz"] - 1200.0) / 4000.0, 0.65, 1.10), 2)
    # subLevel: piu' il basso e' "sub", piu' alziamo il sub (0.30..0.50)
    subLevel = round(clamp(0.30 + 0.45 * a["sub_ratio"], 0.30, 0.50), 2)
    # bassLevel: livello basso "pieno" del genere (1.15..1.35)
    bassLevel = round(clamp(1.15 + 0.6 * a["sub_ratio"], 1.15, 1.35), 2)
    # bassDriveAmt: grit medio -> distorsione. Calibrato sul range osservato
    # (grit ~0.4 frenchtek .. ~0.65 tribe) per NON saturare e mantenere lo stacco.
    bassDriveAmt = round(clamp(2.0 + 3.3 * a["grit"], 2.8, 4.3), 1)
    gen = a.get("genere", "techno")
    preset = {
        "name": nome,
        "_ref": f"{a['file']} (~{a['bpm']:.0f} BPM, {a['nota']} min, "
                f"kick {int(a['kick_decay_s']*1000)}ms, {gen})",
        "bpm": int(round(a["bpm"])),
        "rootSemis": a["rootSemis"],
        "bassDriveAmt": bassDriveAmt,
        "bassLevel": bassLevel,
        "subLevel": subLevel,
        "kickDecay": a["kick_decay_s"],
        "bright": bright,
    }
    return applica_genere(preset, gen)   # genre + groove/scala/cassa/lead/acid


def stampa_report(a):
    print(f"\n=== {a['file']}  ({a['durata_s']}s) ===")
    print(f"  BPM ............. {a['bpm']}")
    print(f"  Tonalita' (root)  {a['nota']}  (rootSemis {a['rootSemis']:+d} rispetto ad A)")
    print(f"  Kick decay ...... {int(a['kick_decay_s']*1000)} ms  ({a.get('kick_note','')})")
    print(f"  Centroide ....... {int(a['centroide_hz'])} Hz  (brillantezza)")
    print(f"  Sub ratio ....... {a['sub_ratio']:.2f}  (1=tutto sub, 0=tutto basso medio)")
    print(f"  Grit/drive ...... {a['grit']:.2f}  (armoniche medie sul basso = distorsione)")
    print(f"  Densita' basso .. {a['bass_density']}  (colpi/beat: ~1 offbeat, 3-4 rolling, <1 rado)")
    print(f"  >>> GENERE ...... {a['genere'].upper()}   ({a['genere_motivo']})")


# ---------------------------------------------------------------- main ------
def main():
    # console Windows: evita crash su nomi con emoji/unicode (cp1252)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Analizza tracce e genera i mood del synth.")
    ap.add_argument("tracce", nargs="*", help="file audio (default: _tracce_riferimento/*)")
    ap.add_argument("--json", action="store_true", help="stampa solo il JSON dei moods")
    ap.add_argument("--scrivi-manifest", action="store_true",
                    help="aggiorna manifest.json -> audioGenerator.moods (con backup)")
    args = ap.parse_args()

    ffmpeg = trova_ffmpeg()
    if not ffmpeg:
        print("[X] ffmpeg non trovato. Mettilo nel PATH.")
        sys.exit(1)

    tracce = args.tracce
    if not tracce:
        pat = os.path.join(BASE, "_tracce_riferimento", "**", "*")
        tracce = [p for p in sorted(glob.glob(pat, recursive=True))
                  if p.lower().endswith((".mp3", ".wav", ".flac", ".m4a", ".ogg"))]
    if not tracce:
        print("[X] Nessuna traccia trovata. Passa dei file o riempi _tracce_riferimento/.")
        sys.exit(1)

    analisi = []
    for t in tracce:
        try:
            a = analizza(ffmpeg, t)
            analisi.append(a)
            if not args.json:
                stampa_report(a)
        except Exception as e:
            print(f"[!] {os.path.basename(t)}: {e}")

    if not analisi:
        sys.exit(1)

    # genera i preset (nome derivato dal file, maiuscolo)
    moods = []
    for a in analisi:
        nome = os.path.splitext(a["file"])[0].split(" - ")[0].upper()[:18] or "MOOD"
        moods.append(a_preset(a, nome))

    blob = json.dumps(moods, indent=2, ensure_ascii=False)
    if args.json:
        print(blob)
    else:
        print("\n--- PRESET MOOD (schema manifest.json) ---")
        print(blob)

    if args.scrivi_manifest:
        mpath = os.path.join(BASE, "manifest.json")
        with open(mpath, encoding="utf-8") as f:
            man = json.load(f)
        shutil.copyfile(mpath, mpath + ".bak")
        man.setdefault("audioGenerator", {})["moods"] = moods
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(man, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] manifest.json aggiornato ({len(moods)} mood). Backup: manifest.json.bak")


if __name__ == "__main__":
    main()
