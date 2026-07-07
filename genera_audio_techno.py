# -*- coding: utf-8 -*-
"""
TeknoSteps - Audio dei video = PORTING del synth del sito (techno-audio.js).
Made in Italy.

Replica in offline (numpy) il motore frenchtek/tribe del sito:
  - MOOD letti dal MANIFEST (audioGenerator.moods + rotation) -> resta
    sincronizzato col synth del sito: se l'utente ritocca i mood la', cambiano
    anche i video.
  - basso OFFBEAT saturato (drive) + SUB + SIDECHAIN sul kick (low-end ducked),
    kick punchy (200->40Hz), hi-hat fitti frenchtek, acid 303 (assente se acidLevel=0),
    pad discreto + CORO vocale a formanti (choir del mood), saturazione master.
  - STRUTTURA variabile per ciclo (classic / driving / deep / double-drop) + dropcut.
  - rotazione mood ogni ~6 cicli (con jitter) e BPM per-mood -> la traccia evolve
    e ogni video parte da un mood diverso => musica sempre un po' diversa.
Produce un WAV loopabile, no-copyright.

Uso: python genera_audio_techno.py [--cicli 10] [--seed N]
"""
import argparse
import json
import os
import random
import wave

import numpy as np

SR = 44100
CYCLE_BARS = 32
ROOT_MIDI = 33                      # A1
MINOR = [0, 2, 3, 5, 7, 8, 10]
# SCALE per genere: cambiano il "colore" melodico e la tonalita' percepita
# (come SCALES in techno-audio.js).
SCALES = dict(minor=[0, 2, 3, 5, 7, 8, 10],      # techno/tek
              phrygian=[0, 1, 3, 5, 7, 8, 10],   # psy/goa: 2a minore = tensione dark
              dorian=[0, 2, 3, 5, 7, 9, 10],     # trance: piu' aperto/melodico
              pent=[0, 3, 5, 7, 10])             # minimal: pentatonica ipnotica
BASE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_MOOD = dict(name="24/7 TEKNO", bpm=145, rootSemis=0, bassDriveAmt=2.6,
                    bassLevel=0.85, subLevel=0.70, kickDecay=0.40, bright=1.0,
                    acidLevel=1.0, leadDensity=[0.12, 0.28], choir=0.0,
                    scale="minor", bassStyle="offbeat", leadStyle="acid",
                    kickStyle="punch")


def load_moods():
    try:
        d = json.load(open(os.path.join(BASE, "manifest.json"), encoding="utf-8"))
        g = d.get("audioGenerator", {})
        ms = g.get("moods")
        rot = g.get("rotation", {}) or {}
        if ms:
            moods = [dict(DEFAULT_MOOD, **m) for m in ms]
            return moods, int(rot.get("everyCycles", 6)), bool(rot.get("random", True))
    except Exception as e:
        print("[!] manifest moods non letti:", e)
    return [DEFAULT_MOOD], 6, False


def mtof(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def scale_note(deg, octave, root_semis, scale="minor"):
    sc = SCALES.get(scale, MINOR)
    L = len(sc)
    octv = deg // L + octave
    idx = ((deg % L) + L) % L
    return ROOT_MIDI + root_semis + sc[idx] + octv * 12


# Sezioni dell'arrangiamento (come techno-audio.js)
SECS = dict(
    INTRO=dict(name="INTRO",  kick=True,  bass=False, clap=False, openhat=False, lead=False, pad=False, hat=1),
    RISE=dict(name="RISE",    kick=True,  bass=True,  clap=False, openhat=False, lead=False, pad=False, hat=1),
    GROOVE=dict(name="GROOVE",kick=True,  bass=True,  clap=True,  openhat=True,  lead=True,  pad=False, hat=2),
    BREAK=dict(name="BREAKDOWN", kick=False, bass=False, clap=False, openhat=False, lead=True, pad=True, hat=1),
    BUILD=dict(name="BUILD",  kick=True,  bass=True,  clap=False, openhat=False, lead=True,  pad=True,  hat=2),
    DROP=dict(name="DROP",    kick=True,  bass=True,  clap=True,  openhat=True,  lead=True,  pad=False, hat=3),
)


def build_sections():
    """STRUTTURA variabile per ciclo (4 forme) -> ogni 32 battute cambia forma."""
    a = [None] * CYCLE_BARS

    def put(fr, to, s):
        for p in range(fr, min(to, CYCLE_BARS)):
            a[p] = s
    v = random.randrange(4)
    S = SECS
    if v == 0:        # CLASSIC
        put(0, 2, S["INTRO"]); put(2, 4, S["RISE"]); put(4, 16, S["GROOVE"])
        put(16, 18, S["BREAK"]); put(18, 20, S["BUILD"]); put(20, 32, S["DROP"])
    elif v == 1:      # DRIVING (kick+basso sempre)
        put(0, 2, S["INTRO"]); put(2, 16, S["GROOVE"]); put(16, 32, S["DROP"])
    elif v == 2:      # DEEP
        put(0, 2, S["INTRO"]); put(2, 10, S["GROOVE"]); put(10, 13, S["BREAK"])
        put(13, 16, S["BUILD"]); put(16, 32, S["DROP"])
    else:             # DOUBLE DROP
        put(0, 2, S["INTRO"]); put(2, 8, S["GROOVE"]); put(8, 9, S["BUILD"]); put(9, 16, S["DROP"])
        put(16, 20, S["GROOVE"]); put(20, 21, S["BUILD"]); put(21, 32, S["DROP"])
    for p in range(CYCLE_BARS):
        if a[p] is None:
            a[p] = S["GROOVE"]
    return a


def build_pattern(mood):
    lead_oct = 1 if random.random() < 0.5 else 2
    ld = mood.get("leadDensity", [0.12, 0.28])
    density = ld[0] + random.random() * (ld[1] - ld[0])
    rs = mood.get("rootSemis", 0)
    scl = mood.get("scale", "minor")
    lead = []
    deg = 0
    for i in range(16):
        if i % 2 == 0 and random.random() < density:        # melodia solo sugli ottavi
            deg += random.randint(-1, 1)
            deg = max(0, min(13, deg))
            lead.append(dict(on=True, midi=scale_note(deg, lead_oct, rs, scl),
                             accent=random.random() < 0.3, slide=random.random() < 0.2))
        else:
            lead.append(dict(on=False))
    # GROOVE DEL BASSO per GENERE (bassStyle): differenza ritmica che fa "sentire"
    # i generi. offbeat (techno) alterna col kick, rolling (psy/trance) rulla sui
    # 16esimi, sparse (minimal) lascia spazio.
    style = mood.get("bassStyle", "offbeat")
    bass = []
    for i in range(16):
        pos = i % 4                                  # 0 = dove cade il kick
        if style == "rolling":
            on = (pos != 0)
        elif style == "sparse":
            on = (pos == 2) and ((i // 4) % 2 == 0)
        else:                                        # offbeat (default techno/tek)
            on = (pos == 2)
            if pos == 3 and random.random() < 0.35:
                on = True
        bdeg = (7 if random.random() < 0.5 else 4) if (pos == 3 and random.random() < 0.15) else 0
        bass.append(dict(on=on, midi=scale_note(bdeg, 0, rs, scl)))
    strings_cycle = random.random() < 0.4           # ~40% cicli: archi martellanti nei drop
    return dict(lead=lead, bass=bass, strings=strings_cycle)


# ============================ STRUMENTI (numpy) ============================

def _smooth(sig, k):
    k = max(1, int(k))
    return sig if k <= 1 else np.convolve(sig, np.ones(k) / k, mode="same").astype(np.float32)


def kick(mood):
    dec = mood.get("kickDecay", 0.4)
    dur = dec + 0.02
    n = int(dur * SR); t = np.arange(n) / SR
    f = 200.0 * (38.0 / 200.0) ** (np.minimum(t, 0.12) / 0.12)   # scende piu' giu' (38Hz) = piu' boom
    env = 1.85 * (1 - np.exp(-t / 0.0015)) * np.exp(-t / (dec * 0.55))  # cassa piu' forte e lunga
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env
    # SUB-BOOM extra: sine bassa pulita ~55->40Hz -> il "colpo nel petto"
    fsub = 55.0 * (40.0 / 55.0) ** (np.minimum(t, 0.10) / 0.10)
    sb = np.sin(2 * np.pi * np.cumsum(fsub) / SR)
    body += sb * (1 - np.exp(-t / 0.004)) * np.exp(-t / (dec * 0.5)) * 0.55
    cn = int(0.025 * SR); ct = np.arange(cn) / SR
    body[:cn] += np.sin(2 * np.pi * (1100 * (200 / 1100) ** (ct / 0.02)) * ct) * np.exp(-ct / 0.006) * 0.5
    nn = int(0.012 * SR)
    hp = np.diff(np.random.uniform(-1, 1, nn + 1)) * np.exp(-np.arange(nn) / SR / 0.004) * 0.25
    body[:nn] += hp
    return body.astype(np.float32)


def bass(freq, dur, mood):
    n = int(dur * SR); t = np.arange(n) / SR
    saw = 2 * ((np.arange(n) * freq / SR) % 1.0) - 1
    f2 = freq * 2 ** (-6 / 1200.0)
    sq = np.sign(np.sin(2 * np.pi * f2 * t))
    br = max(0.3, mood.get("bright", 1.0))        # bright basso (TRIBE) = piu' cupo
    body = _smooth(saw * 0.7 + sq * 0.5, SR / (freq * 6 * br))
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / (dur * 0.5))
    out = body * env * mood.get("bassLevel", 0.85)
    k = mood.get("bassDriveAmt", 2.6)            # DRIVE / saturazione (waveshaper tanh)
    out = np.tanh(k * out) / np.tanh(k)
    return out.astype(np.float32)


def subbass(freq, dur, mood):
    n = int(dur * 0.9 * SR); t = np.arange(n) / SR
    o = np.sin(2 * np.pi * freq * t)
    env = (1 - np.exp(-t / 0.008)) * np.exp(-t / (dur * 0.45))
    return (o * env * mood.get("subLevel", 0.7)).astype(np.float32)


def acid(freq, dur, accent, mood):
    n = int(dur * SR); t = np.arange(n) / SR
    saw = 2 * ((np.arange(n) * freq / SR) % 1.0) - 1
    sine = np.sin(2 * np.pi * freq * t)
    k = np.clip(t / dur, 0, 1)
    bright = (1.0 if accent else 0.7)
    tone = saw * (bright * (1 - k)) + sine * (k * 0.8)
    env = (1 - np.exp(-t / 0.003)) * np.exp(-t / (dur * 0.8))
    vol = (0.14 if accent else 0.08) * mood.get("acidLevel", 1.0)
    return (tone * env * vol).astype(np.float32)


def kick808(mood):
    """KICK 808 tonale: sine accordata alla tonica del mood, glide + coda lunga."""
    dec = max(0.42, mood.get("kickDecay", 0.4) * 1.7)
    rs = mood.get("rootSemis", 0)
    f0 = mtof(ROOT_MIDI + rs)                         # tonica (~A1 = 55Hz)
    n = int((dec + 0.03) * SR); t = np.arange(n) / SR
    gl = np.minimum(t, 0.07) / 0.07
    f = f0 * 3.2 * (1.0 / 3.2) ** gl                  # da f0*3.2 giu' alla tonica
    env = 1.7 * (1 - np.exp(-t / 0.0012)) * np.exp(-t / (dec * 0.5))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env
    cn = int(0.02 * SR); ct = np.arange(cn) / SR      # click d'attacco
    click = np.sin(2 * np.pi * (1700 * (320 / 1700) ** (ct / 0.015)) * ct) * np.exp(-ct / 0.005) * 0.55
    body[:cn] += click
    return body.astype(np.float32)


def supersaw_lead(freq, dur, accent, lvl=1.0):
    """SUPERSAW (trance): 5 saw detunati, ampio e melodico."""
    d = dur * 1.35; n = int(d * SR); t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float64)
    for c in (-12, -5, 0, 5, 12):
        fr = freq * 2 ** (c / 1200.0)
        out += 2 * ((np.arange(n) * fr / SR) % 1.0) - 1
    cut = (4200 if accent else 2600)
    out = _smooth(out / 5, SR / (cut * 0.9))
    env = (1 - np.exp(-t / 0.02)) * np.exp(-t / (d * 0.6))
    vol = (0.085 if accent else 0.055) * lvl
    return (out * env * vol).astype(np.float32)


def pluck_lead(freq, dur, accent, lvl=1.0):
    """PLUCK (psy): square+saw, env cortissima -> 'plick' ritmico."""
    d = dur * 0.85; n = int(d * SR); t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * freq * t))
    fr2 = freq * 2 ** (7 / 1200.0)
    saw = 2 * ((np.arange(n) * fr2 / SR) % 1.0) - 1
    cut = (5000 if accent else 3200)
    body = _smooth(sq * 0.6 + saw * 0.6, SR / (cut * 0.9))
    env = (1 - np.exp(-t / 0.004)) * np.exp(-t / (d * 0.4))
    vol = (0.08 if accent else 0.05) * lvl
    return (body * env * vol).astype(np.float32)


def lead_voice(freq, dur, accent, slide, mood):
    """Dispatcher LEAD: acid=303(techno), supersaw=trance, pluck=psy."""
    style = mood.get("leadStyle", "acid")
    if style == "supersaw":
        return supersaw_lead(freq, dur, accent)
    if style == "pluck":
        return pluck_lead(freq, dur, accent)
    return acid(freq, dur, accent, mood)


def strings(freqs, dur):
    """ARCHI 'INCAZZATI': stab STACCATO distorto, medi aggressivi, vibrato veloce."""
    n = int((dur + 0.05) * SR); t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float64)
    vib = 12.0 / freqs[0] * np.sin(2 * np.pi * 7 * t)       # vibrato stretto e veloce
    for i, fr in enumerate(freqs):
        for det in (-11, 0, 11):
            f = fr * 2 ** ((det + (i - 1) * 4) / 1200.0)
            out += 2 * (((np.arange(n) * f / SR) * (1 + vib)) % 1.0) - 1
    out /= (len(freqs) * 3)
    out = np.tanh(2.4 * out) / np.tanh(2.4)                 # grinta / distorsione
    # band-pass ~1700 + via i bassi: differenza (hp) su segnale smussato (lp)
    lp = _smooth(out, SR / 3400.0)
    out = out - _smooth(out, SR / 320.0)                    # highpass ~320
    out = _smooth(out, SR / 3200.0) * 0.6 + lp * 0.4
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / (dur * 0.5))
    return (out * env * 0.20).astype(np.float32)


def siren(vol=0.10, variant=None):
    """SIRENA rave: PIU' LUNGA e con VARIANTI (wail/airraid/police/uplift), band-pass."""
    if variant is None:
        variant = random.choice(["wail", "airraid", "police", "uplift"])
    if variant == "wail":                                   # su-giu' ripetuto (classico)
        dur = 3.6; pts = [(0.0, 520)]; x = 0.0; hi = True
        while x < dur:
            x += 0.5; pts.append((min(dur, x), 1450 if hi else 520)); hi = not hi
    elif variant == "airraid":                              # salita/discesa lenta (allarme)
        dur = 3.8; pts = [(0.0, 420), (dur * 0.62, 1500), (dur, 430)]
    elif variant == "police":                               # due-toni alternati veloci
        dur = 3.0; pts = [(0.0, 780)]; x = 0.0; hi = True
        while x < dur:
            x += 0.28; pts.append((min(dur, x), 1180 if hi else 780)); hi = not hi
    else:                                                   # uplift: salita continua nel drop
        dur = 2.6; pts = [(0.0, 500), (dur, 1800)]
    n = int((dur + 0.05) * SR); t = np.arange(n) / SR
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    f = np.interp(t, xs, ys)
    o = 2 * ((np.cumsum(f) / SR) % 1.0) - 1                 # saw
    o = o - _smooth(o, SR / 600.0)                          # verso band-pass ~1200
    o = _smooth(o, SR / 2400.0)
    env = np.minimum(1.0, (1 - np.exp(-t / 0.05))) * np.minimum(1.0, np.linspace(1.3, 0.0, n))
    return (o * env * vol).astype(np.float32)


def pad(freqs, dur):
    n = int(dur * SR); out = np.zeros(n, dtype=np.float64)
    for fr in freqs:
        for det in (0.997, 1.004):
            out += 2 * ((np.arange(n) * fr * det / SR) % 1.0) - 1
    out = _smooth(out / (len(freqs) * 2), SR / (freqs[0] * 3))
    atk = max(1, int(0.8 * SR)); rel = max(1, int(0.8 * SR))
    env = np.ones(n); env[:atk] = np.linspace(0, 1, atk); env[-rel:] = np.linspace(1, 0, rel)
    return (out * env * 0.055).astype(np.float32)


def vocal_pad(freqs, dur, level):
    """Coro 'aah' sintetico a FORMANTI (F1/F2/F3) - come vocalPad() del sito."""
    if not level or not freqs:
        return np.zeros(1, dtype=np.float32)
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float64)
    FORM = [(700.0, 9.0, 1.0), (1150.0, 11.0, 0.55), (2600.0, 12.0, 0.28)]
    for k, fr in enumerate(freqs):
        f0 = fr * 2 ** (((k - 1) * 7) / 1200.0)            # coro leggermente largo (+-7 cent)
        h = 1
        while h * f0 < 9000:
            cf = h * f0
            amp = 0.0
            for c, q, g in FORM:
                amp += g * np.exp(-((cf - c) / (c / q)) ** 2)
            if amp > 0.01:
                out += np.sin(2 * np.pi * cf * t) * (amp / h)
            h += 1
    out /= max(1, len(freqs))
    atk = max(1, int(1.1 * SR)); rel = max(1, int(1.4 * SR))
    env = np.ones(n)
    env[:atk] = np.linspace(0, 1, atk)
    if rel < n:
        env[-rel:] = np.linspace(1, 0, rel)
    return (out * env * level * 0.8).astype(np.float32)


def hat(dur, vol, openh=False):
    n = int(dur * SR)
    hp = np.diff(np.random.uniform(-1, 1, n + 1))
    return (hp * np.exp(-(np.arange(n) / SR) / (dur * 0.4)) * vol).astype(np.float32)


def clap(vol=0.35):
    n = int(0.16 * SR); out = np.zeros(n, dtype=np.float32)
    for k in range(3):
        seg = hat(0.12, 1.0); off = int(k * 0.012 * SR)
        m = min(len(seg), n - off)
        if m > 0:
            out[off:off + m] += seg[:m]
    return out * vol


def snare(vol):
    dur = 0.12; n = int(dur * SR); t = np.arange(n) / SR
    hp = np.diff(np.random.uniform(-1, 1, n + 1)) * np.exp(-t / 0.04)
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.05) * 0.5
    return ((hp + tone) * vol).astype(np.float32)


def riser(dur, vol=0.16):
    n = int(dur * SR)
    hp = np.diff(np.random.uniform(-1, 1, n + 1))
    return (hp * (np.linspace(0, 1, n) ** 2) * vol).astype(np.float32)


# ===================== GIUNGLA + SCIMMIA (solo canale Tekno Monkey) =====================
# Tutto sintetizzato (no campioni) -> resta 100% no-copyright come il resto.

def monkey_call():
    """Scimmia INCAZZATA: screech/ruggito AGGRESSIVO e distorto (dark), non allegro.
    Acuto e rauco (scimmia, non elefante) ma cattivo -> distorsione + growl."""
    dur = 0.30 + random.random() * 0.26
    n = int(dur * SR); t = np.arange(n) / SR; k = t / dur
    # pitch alto che sale (hoot -> screech) + vibrato veloce e AMPIO = rabbia
    f = 560 + 1050 * k + 220 * np.sin(2 * np.pi * (13 + random.random() * 9) * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    o = np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.45 * np.sin(3 * ph)
    # RASPO/growl gutturale piu' marcato
    nz = np.random.uniform(-1, 1, n).astype(np.float32)
    o = o * 0.75 + _smooth(nz, 8) * (0.35 + 0.45 * k)
    o = np.tanh(2.6 * o)                                    # DISTORSIONE = ruggito cattivo
    env = (1 - np.exp(-t / 0.006)) * (np.sin(np.pi * k) ** 0.4)  # attacco secco, snarl
    return (o * env * 0.34).astype(np.float32)


def monkey_chatter():
    """Chiacchiericcio 'ki-ki-ki' rapido e ACUTO (scimmia), non 'ooh' grave."""
    parts = []; base = 720 + random.random() * 320
    for g in range(random.randint(4, 7)):
        dur = 0.04 + random.random() * 0.03; nn = int(dur * SR); t = np.arange(nn) / SR
        f = base * (1 + 0.14 * g) * (1 + 0.6 * np.exp(-t / 0.010))       # acuto, sale, chirp
        ph = 2 * np.pi * np.cumsum(f) / SR
        o = np.sin(ph) + 0.5 * np.sin(2 * ph)
        nz = np.random.uniform(-1, 1, nn).astype(np.float32)
        o = o * 0.7 + _smooth(nz, 3) * 0.35                              # un po' di raspo
        parts.append((o * np.exp(-t / (dur * 0.4))).astype(np.float32))
        parts.append(np.zeros(int((0.02 + random.random() * 0.03) * SR), dtype=np.float32))
    return (np.concatenate(parts) * 0.3).astype(np.float32)


def bird_chirp():
    """Cinguettio d'uccello: trillo veloce ad alta frequenza."""
    dur = 0.07 + random.random() * 0.13; n = int(dur * SR); t = np.arange(n) / SR
    f = 2600 + 2200 * np.sin(2 * np.pi * (7 + random.random() * 7) * t)
    o = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return (o * np.exp(-t / (dur * 0.4)) * 0.16).astype(np.float32)


def cricket_bed(dur):
    """Tappeto di grilli/insetti: rumore acuto pulsante (tremolo)."""
    n = int(dur * SR); t = np.arange(n) / SR
    nz = np.random.uniform(-1, 1, n).astype(np.float32)
    hp = nz - _smooth(nz, 10)                                          # highpass -> shimmer
    trem = _smooth((0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 24 * t))).astype(np.float32), 40)
    return (hp * trem * 0.05).astype(np.float32)                       # tappeto piu' udibile


# ===================== VOCI NATURALISTICHE EN (solo Strange Light) =====================

def voice_fx(v):
    """Normalizza + riverbero atmosferico (documentario)."""
    v = (v / (float(np.abs(v).max()) or 1.0)) * 0.55
    L = len(v) + int(0.6 * SR)
    out = np.zeros(L, dtype=np.float32); out[:len(v)] += v
    for dl, g in [(0.09, 0.40), (0.18, 0.27), (0.28, 0.17), (0.40, 0.11), (0.55, 0.07)]:
        d = int(dl * SR)
        out[d:d + len(v)] += v * g                     # code di riverbero
    return out.astype(np.float32)


def load_voices():
    """Carica le frasi TTS EN da assets/voices/ (mono, resample a SR, con riverbero)."""
    d = os.path.join(BASE, "assets", "voices")
    out = []
    if not os.path.isdir(d):
        return out
    for fn in sorted(f for f in os.listdir(d) if f.endswith(".wav")):
        try:
            w = wave.open(os.path.join(d, fn)); sr = w.getframerate(); nch = w.getnchannels()
            raw = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
            w.close()
            if nch == 2:
                raw = raw.reshape(-1, 2).mean(1)
            if sr != SR:
                idx = np.linspace(0, len(raw) - 1, int(len(raw) * SR / sr))
                raw = np.interp(idx, np.arange(len(raw)), raw).astype(np.float32)
            out.append(voice_fx(raw))
        except Exception as e:
            print("[!] voce non letta", fn, e)
    return out


def load_brand():
    """Jingle vocali 'TeknoSteps' (assets/audio/jingle*.wav) -> branding su TUTTI i canali."""
    d = os.path.join(BASE, "assets", "audio")
    out = []
    for fn in ("jingle1.wav", "jingle2.wav", "jingle3.wav"):
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            continue
        try:
            w = wave.open(p); sr = w.getframerate(); nch = w.getnchannels()
            raw = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
            w.close()
            if nch == 2:
                raw = raw.reshape(-1, 2).mean(1)
            if sr != SR:
                idx = np.linspace(0, len(raw) - 1, int(len(raw) * SR / sr))
                raw = np.interp(idx, np.arange(len(raw)), raw).astype(np.float32)
            raw = raw / (float(np.abs(raw).max()) or 1.0) * 0.6
            out.append(raw.astype(np.float32))
        except Exception as e:
            print("[!] jingle non letto", fn, e)
    return out


def add(buf, t, sig):
    i = int(round(t * SR))
    if i < 0:
        sig = sig[-i:]; i = 0
    j = i + len(sig)
    if j > len(buf):
        sig = sig[:len(buf) - i]; j = len(buf)
    if i < len(buf) and len(sig) > 0:
        buf[i:j] += sig


# ============================ ARRANGIAMENTO ============================

def render(cycles, jungle=False, voices=False, force_bpm=None, dark=False):
    moods, rot_every, rot_random = load_moods()
    voice_clips = load_voices() if voices else []
    vseq = list(range(len(voice_clips))); random.shuffle(vseq); vi = 0
    brand_clips = load_brand(); bi = 0        # jingle "TeknoSteps" su TUTTI i canali
    # schedule mood (rotazione sequenziale, jitter sui cicli) - start casuale
    idx = random.randrange(len(moods))
    rem = max(2, rot_every + (random.randint(-2, 2) if rot_random else 0))
    schedule = []
    for c in range(cycles):
        schedule.append(idx); rem -= 1
        if rem <= 0:
            idx = (idx + 1) % len(moods)
            rem = max(2, rot_every + (random.randint(-2, 2) if rot_random else 0))

    total = sum(CYCLE_BARS * 4 * (60.0 / (force_bpm or moods[i]["bpm"])) for i in schedule)
    L = int(total * SR) + SR
    main = np.zeros(L, dtype=np.float32)   # PUNCH: cassa/clap/hat -> NON duckati (bucano)
    music = np.zeros(L, dtype=np.float32)  # MELODIA: pad/lead/stab/archi/voci -> POMPANO col kick
    low = np.zeros(L, dtype=np.float32)
    voc = np.zeros(L, dtype=np.float32)    # VOCALI (brand/scimmia/voci/grilli): layer basso e DUCKATO, sta SOTTO
    sc = np.ones(L, dtype=np.float32)
    jgain = np.zeros(L, dtype=np.float32) if jungle else None  # livello grilli per sezione
    cuts = []

    t = 0.0
    for c in range(cycles):
        mood = moods[schedule[c]]
        if dark:
            # CATTIVO/AGGRESSIVO (dark psy): scala frigia tesa, lead acid urlante,
            # basso piu' distorto, meno brillante, cassa piu' secca -> techno cupo.
            mood = dict(mood, scale="phrygian", leadStyle="acid",
                        bassDriveAmt=mood.get("bassDriveAmt", 2.6) * 1.55,
                        bright=min(mood.get("bright", 1.0), 0.6),
                        acidLevel=mood.get("acidLevel", 1.0) * 1.3,
                        kickDecay=min(mood.get("kickDecay", 0.4), 0.34),
                        leadDensity=[max(0.18, mood.get("leadDensity", [0.12, 0.28])[0]),
                                     max(0.34, mood.get("leadDensity", [0.12, 0.28])[1])])
        spb = 60.0 / (force_bpm or mood["bpm"]); sub16 = spb / 4
        patt = build_pattern(mood)
        dropcut = random.random() < 0.5
        sections = build_sections()                # struttura variabile del ciclo
        for bic in range(CYCLE_BARS):
            sec = sections[bic]
            nxt = sections[bic + 1] if bic + 1 < CYCLE_BARS else None
            bar = c * CYCLE_BARS + bic
            for beat in range(4):
                bt = t
                if sec["kick"]:
                    add(main, bt, kick808(mood) if mood.get("kickStyle") == "808" else kick(mood))
                    k = int(bt * SR); rec = max(1, int(min(0.16, 0.55 * spb) * SR))
                    e = min(L, k + rec)
                    sc[k:e] = np.linspace(0.30, 1.0, e - k, dtype=np.float32)
                if sec["clap"] and beat in (1, 3):
                    add(main, bt, clap())
                for s in range(4):
                    tt = bt + s * sub16
                    step = beat * 4 + s
                    subp = step % 4
                    # HI-HAT come techno-audio.js: fitti in groove/drop, accenti, doppi nei drop
                    if sec["hat"] >= 2:
                        add(main, tt, hat(0.018, 0.20))                # ogni 16esimo
                    elif sec["hat"] >= 1 and subp == 2:
                        add(main, tt, hat(0.02, 0.18))                 # intro/rise: solo offbeat
                    if sec["hat"] >= 2 and subp == 2:
                        add(main, tt, hat(0.03, 0.30))                 # accento sull'offbeat
                    if sec["hat"] >= 3 and subp in (1, 3):
                        add(main, tt, hat(0.015, 0.16))                # doppi nei drop
                    if sec["openhat"] and step in (6, 14):
                        add(main, tt, hat(0.16, 0.34, openh=True))     # open hat (lift)
                    if sec["bass"]:
                        b = patt["bass"][step]
                        if b["on"]:
                            fr = mtof(b["midi"])
                            # rolling (psy/trance) = note corte staccate; altrimenti piene
                            gate = sub16 * (0.85 if mood.get("bassStyle") == "rolling" else 1.6)
                            add(low, tt, bass(fr, gate, mood))
                            add(low, tt, subbass(fr, gate, mood))
                    if sec["lead"] and mood.get("acidLevel", 1.0) > 0:
                        p = patt["lead"][step]
                        if p["on"]:
                            add(music, tt, lead_voice(mtof(p["midi"]), sub16 * (1.6 if p["slide"] else 0.9),
                                                     p["accent"], p["slide"], mood))
                rs = mood.get("rootSemis", 0); scl = mood.get("scale", "minor")
                cdeg = 0 if (bar // 2) % 2 == 0 else 5
                chord = [mtof(scale_note(cdeg, 1, rs, scl)), mtof(scale_note(cdeg + 2, 1, rs, scl)),
                         mtof(scale_note(cdeg + 4, 1, rs, scl))]
                if sec["pad"] and beat == 0 and bar % 2 == 0:
                    add(music, bt, pad(chord, spb * 8))
                    if mood.get("choir", 0.0) > 0:                      # coro un'ottava sopra
                        add(music, bt, vocal_pad([f * 2 for f in chord], spb * 8, mood["choir"]))
                # ARCHI martellanti: stab su OGNI beat nei DROP/BUILD, solo nei cicli "strings"
                if patt.get("strings") and sec["name"] in ("DROP", "BUILD"):
                    add(music, bt, strings(chord, spb * 0.72))
                # SIRENA rave all'ingresso del DROP (ogni tanto)
                if (beat == 0 and sec["name"] == "DROP" and bic > 0
                        and sections[bic - 1]["name"] != "DROP" and random.random() < 0.18):
                    add(music, bt, siren())
                # GIUNGLA + SCIMMIA (solo Tekno Monkey): whoop nell'intro/breakdown e
                # all'ingresso dei drop, con cinguettii sparsi. Vanno in 'main' (non duckati).
                if jungle:
                    # grilli PER SEZIONE: forti nei momenti calmi, comunque UDIBILI nei drop
                    if beat == 0:
                        lvl = {"INTRO": 1.0, "BREAKDOWN": 1.0, "RISE": 0.85, "BUILD": 0.75,
                               "GROOVE": 0.7, "DROP": 0.4}.get(sec["name"], 0.6)
                        js = int(bt * SR); je = min(L, int((bt + 4 * spb) * SR))
                        jgain[js:je] = lvl
                    # VOCE SCIMMIA: SOLO nei "caricamenti" (intro/rise/breakdown/build),
                    # mai in groove/drop -> non insistente, entra nelle salite del brano.
                    if beat == 0 and sec["name"] in ("INTRO", "RISE", "BREAKDOWN", "BUILD"):
                        if random.random() < 0.55:
                            add(voc, bt + random.random() * spb, monkey_call())
                        if random.random() < 0.3:
                            add(voc, bt + spb * 2, monkey_chatter())
                    # cinguettii sparsi (uccelli, ambiente giungla) — ovunque, discreti
                    if random.random() < 0.06:
                        add(voc, bt + random.random() * spb, bird_chirp())
                # VOCI EN naturalistiche (Strange Light): una frase nei breakdown/intro
                # -> spezza l'ora di musica. Non duckata (chiara), ciclo senza ripetizioni.
                if voice_clips and beat == 0 and sec["name"] in ("BREAKDOWN", "INTRO") and random.random() < 0.5:
                    add(voc, bt + spb * 0.5, voice_clips[vseq[vi % len(vseq)]]); vi += 1
                # BRAND "TeknoSteps": jingle vocale all'inizio del brano e ogni tanto negli
                # intro -> fissa il nome in testa. Su TUTTI i canali. Nel layer voc (basso+duckato).
                if brand_clips and beat == 0 and bic == 0 and (
                        (c == 0) or (sec["name"] == "INTRO" and random.random() < 0.25)):
                    add(voc, bt, brand_clips[bi % len(brand_clips)]); bi += 1
                if bic == 22 and beat == 0:
                    add(music, bt, riser(spb * 8))
                if bic in (19, 23):
                    for s in range(4):
                        stp = beat * 4 + s
                        add(main, bt + s * sub16, snare(0.12 + (stp / 15) * 0.34))
                # dropCut dinamico: silenzio sull'ultimo beat PRIMA di un DROP
                if dropcut and beat == 3 and nxt is not None and nxt["name"] == "DROP" and sec["name"] != "DROP":
                    cuts.append((int(bt * SR), int((bt + spb) * SR)))
                t += spb

    # GIUNGLA: tappeto di grilli/insetti modulato PER SEZIONE (forte in intro/breakdown,
    # quasi assente nei drop) -> ambiente giusto al momento giusto, non un ronzio fisso.
    if jungle:
        bed = cricket_bed(6.0)
        tiled = np.zeros(L, dtype=np.float32)
        for i in range(0, L, len(bed)):
            m = min(len(bed), L - i)
            tiled[i:i + m] = bed[:m]
        jgain = _smooth(jgain, int(0.4 * SR))   # transizioni morbide tra sezioni
        voc += tiled * jgain                     # grilli nel layer voc (basso, sotto al mix)

    # SIDECHAIN / PUMP: a ogni cassa la MELODIA (pad/lead/stab/archi/voci) e il
    # LOW (basso+sub) si abbassano e risalgono -> il "pum pum pum" buca ed elevata.
    # La cassa/clap/hat (in main) NON vengono duckati: restano in faccia.
    # SIDECHAIN PIU' MARCATO: quando entra la cassa la MELODIA si abbassa a ~22% (quasi
    # si zittisce) e il BASSO spinge di piu' -> la cassa BUCA, si sente il "boom".
    scm = 0.05 + (sc - 0.30) * (0.95 / 0.70)   # melodia -> QUASI ZERO sul boom: niente suoni sopra la cassa
    scb = 0.70 + (sc - 0.30) * (0.30 / 0.70)   # basso -> duck LEGGERO: resta pieno e SPINGE col boom
    scv = 0.45 + (sc - 0.30) * (0.55 / 0.70)   # VOCALI -> duckati: respirano sotto la cassa
    final = main + music * scm + low * scb * 1.55 + voc * scv * 0.55  # vocali bassi e puliti, non sporcano
    for a, b in cuts:                       # dropCut: silenzio sull'ultimo beat del build
        b = min(L, b)
        if b > a:
            final[a:b] *= np.linspace(1.0, 0.0, b - a, dtype=np.float32)
    final = final[:int(total * SR)]
    peak = float(np.max(np.abs(final))) or 1.0
    # SATURAZIONE master (soft-clip tanh) come masterDrive del sito -> grezzo/brillante
    final = np.tanh(1.7 * final * (0.92 / peak)) / np.tanh(1.7)
    final *= 0.9

    names = []
    for i in schedule:
        nm = moods[i]["name"]
        if not names or names[-1] != nm:
            names.append(nm)
    return final, total, names


def stream_forever(args):
    """RADIO 24/7 generativa: rende blocchi all'infinito (seed sempre diverso =
    musica SEMPRE NUOVA) e li scrive come PCM s16 mono @44100 su stdout, SENZA BUCHI
    (un thread rende avanti mentre l'altro trasmette). Uso tipico:
      python genera_audio_techno.py --stream | ffmpeg -f s16le -ar 44100 -ac 1 -i - \\
        -c:a libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:PASS@127.0.0.1:8000/teknosteps.mp3
    Flag canale: --jungle (Tekno Monkey), --voices (Strange Light)."""
    import sys, threading, queue
    batch = max(2, args.batch)
    q = queue.Queue(maxsize=2)

    def producer():
        while True:
            sd = random.randrange(1000000)
            random.seed(sd); np.random.seed(sd % (2 ** 32))
            final, dur, _ = render(batch, jungle=args.jungle, voices=args.voices)
            pcm = (np.clip(final[:int(dur * SR)], -1, 1) * 32767).astype("<i2").tobytes()
            q.put(pcm)                       # si blocca se il buffer e' pieno (max 2 blocchi avanti)

    threading.Thread(target=producer, daemon=True).start()
    out = sys.stdout.buffer
    while True:
        buf = q.get()
        try:
            out.write(buf); out.flush()      # si blocca al ritmo di ffmpeg (realtime)
        except (BrokenPipeError, OSError):
            break


def write_audio_meta(path, bpm, blocks):
    """Sidecar _audio_meta.json accanto al wav: BPM e blocchi (start+nome) ->
    le pipeline lo leggono per mettere i BPM nel TITOLO e i CAPITOLI nella descrizione."""
    meta = {"bpm": int(bpm) if bpm else None,
            "blocks": [{"start": round(s, 2), "name": n} for s, n in blocks]}
    try:
        mp = os.path.join(os.path.dirname(path) or BASE, "_audio_meta.json")
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception as e:
        print("[!] meta non scritto:", e)


def render_to_file_minutes(path, minutes, jungle=False, voices=False, batch=8, force_bpm=None, dark=False):
    """Scrive un WAV lungo `minutes` minuti generandolo a BLOCCHI (RAM-safe).
    Ogni blocco ha un SEED nuovo -> mood/pattern/bassline/ritmo DIVERSI: la traccia
    cambia proprio 'linea del ritmo' ogni ~5 min. Se force_bpm e' impostato il TEMPO
    resta COSTANTE per tutta l'ora (transizioni beat-allineate + BPM esatto nel titolo).
    I frame vengono aggiunti man mano al file, senza tenere l'ora intera in RAM."""
    target = minutes * 60.0
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    done = 0.0
    names_all = []
    blocks = []
    blocco = 0
    while done < target:
        blocco += 1
        sd = random.randrange(1000000)
        random.seed(sd); np.random.seed(sd % (2 ** 32))
        blocks.append((done, None))                       # start del blocco (nome sotto)
        final, dur, names = render(batch, jungle=jungle, voices=voices, force_bpm=force_bpm, dark=dark)
        data = (np.clip(final[:int(dur * SR)], -1, 1) * 32767).astype("<i2")
        w.writeframes(data.tobytes())
        nm = names[0] if names else "?"
        blocks[-1] = (blocks[-1][0], nm)
        done += dur
        names_all.append(nm)
        print(f"    blocco {blocco}: +{dur/60:.1f} min ({nm}) "
              f"-> {done/60:.1f}/{minutes} min", flush=True)
        del final, data
    w.close()
    write_audio_meta(path, force_bpm, blocks)
    print(f"[OK] {path}  ({os.path.getsize(path)/1048576:.1f} MB, {done/60:.1f} min, "
          f"{blocco} blocchi{', ' + str(force_bpm) + ' BPM' if force_bpm else ''}) - "
          f"ritmi: {' -> '.join(names_all)} - Made in Italy")


def main():
    ap = argparse.ArgumentParser(description="Audio video TeknoSteps (porting synth sito)")
    ap.add_argument("--cicli", type=int, default=10)
    ap.add_argument("--minuti", type=float, default=0,
                    help="genera un WAV lungo N minuti che CAMBIA ritmo a blocchi (no loop)")
    ap.add_argument("--bpm", type=int, default=0,
                    help="forza un BPM COSTANTE per tutta la traccia (0 = usa i BPM dei mood)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(BASE, "teknosteps_audio.wav"))
    ap.add_argument("--jungle", action="store_true",
                    help="aggiunge vocali di scimmia + giungla (canale Tekno Monkey)")
    ap.add_argument("--voices", action="store_true",
                    help="aggiunge voci EN naturalistiche nei breakdown (canale Strange Light)")
    ap.add_argument("--stream", action="store_true",
                    help="RADIO 24/7: genera all'infinito e scrive PCM s16 mono 44100 su stdout (per ffmpeg -> Icecast)")
    ap.add_argument("--batch", type=int, default=6, help="cicli per blocco in --stream")
    ap.add_argument("--dark", action="store_true",
                    help="carattere CATTIVO/aggressivo (dark psy): frigia + acid urlante + piu' distorsione")
    args = ap.parse_args()

    if args.stream:
        stream_forever(args); return

    fbpm = args.bpm if args.bpm and args.bpm > 0 else None

    if args.minuti and args.minuti > 0:
        if args.seed is not None:
            random.seed(args.seed)
        print(f"[i] Render LUNGO {args.minuti} min a blocchi (ritmo che cambia"
              f"{', ' + str(fbpm) + ' BPM fisso' if fbpm else ''})"
              f"{' + GIUNGLA/SCIMMIA' if args.jungle else ''}{' + VOCI EN' if args.voices else ''}...")
        render_to_file_minutes(args.out, args.minuti, jungle=args.jungle,
                               voices=args.voices, batch=max(4, args.cicli), force_bpm=fbpm, dark=args.dark)
        return

    seed = args.seed if args.seed is not None else random.randrange(1000000)
    random.seed(seed); np.random.seed(seed % (2 ** 32))

    print(f"[i] Render {args.cicli} cicli (seed {seed}) - mood dal manifest"
          f"{' + GIUNGLA/SCIMMIA' if args.jungle else ''}{' + VOCI EN' if args.voices else ''}...")
    final, dur, names = render(args.cicli, jungle=args.jungle, voices=args.voices, force_bpm=fbpm, dark=args.dark)

    data = (np.clip(final, -1, 1) * 32767).astype("<i2")
    w = wave.open(args.out, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(data.tobytes()); w.close()
    # meta per titolo/SEO: qui l'audio e' un loop, quindi niente capitoli (blocks vuoto)
    write_audio_meta(args.out, fbpm, [])

    print(f"[OK] {args.out}  ({os.path.getsize(args.out)/1048576:.1f} MB, {dur/60:.1f} min)")
    print(f"     Mood: {' -> '.join(names)}  - Made in Italy")


if __name__ == "__main__":
    main()
