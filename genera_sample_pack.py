# -*- coding: utf-8 -*-
"""
GENERA SAMPLE PACK v2 — suoni originali per la radio TeknoSteps.  Made in Italy.
============================================================================
Rende OFFLINE (numpy) un "kit" di one-shot .wav per ogni genere, con timbri
DIVERSI genere per genere, CALIBRATI sulle impronte reali misurate dalle tracce
di riferimento (analizza_tracce.py) + teoria di produzione (GENERI_WORKFLOW.md).
Sono suoni 100% nostri (nessun copyright): le tracce di altri si usano solo per
STUDIARE, i suoni li ricreiamo qui.

6 GENERI: techno · techhouse · minimal · psytrance · trance · hardtek
Firme (chiave anti-copione):
  techno    -> acid 303 scuro + reese offbeat
  techhouse -> ORGANO drawbar + hat cristallini (il piu' brillante) + poco sub
  minimal   -> DUB CHORD lavato + SUB pieno + groove rado
  psytrance -> ROLLING bass sine+saw tight + stab FM brillante + kick click
  trance    -> SUPERSAW + riser
  hardtek   -> KICK 909 distorto + HOOVER + SIRENA rave + acid spinto

Cartelle:  assets/sounds/<genere>/<suono>.wav   (+ index.json rigenerato)
Kit (nomi fissi):  kick sub bass stab hat openhat clap perc fx
Riferimenti intonazione:  basso 55 Hz (La1), stab 220 Hz (La3) -> il motore li
ri-intona (playbackRate) per suonare le note del pattern.

USO:  python genera_sample_pack.py
"""
import os, math, json, wave
import numpy as np

SR = 44100
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "assets", "sounds")
BASS_REF = 55.0      # La1
STAB_REF = 220.0     # La3
KIT_ORDER = ["kick", "sub", "bass", "stab", "hat", "openhat", "clap", "perc", "fx"]


# --------------------------------------------------------------- helpers ----
def t_arr(dur): return np.arange(int(dur * SR)) / SR

def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak

def fade(x, ms=4):
    n = int(SR * ms / 1000)
    if len(x) > 2 * n:
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    return x

def saw(freq, t):    return 2.0 * (t * freq - np.floor(0.5 + t * freq))
def sq(freq, t):     return np.sign(np.sin(2 * np.pi * freq * t))
def sine(freq, t):   return np.sin(2 * np.pi * freq * t)
def noise(n):        return np.random.rand(n) * 2 - 1

def lp_tv(x, cutoff):
    """Lowpass a un polo con cutoff variabile nel tempo (array). Liscio, no risonanza."""
    a = np.exp(-2 * np.pi * np.clip(cutoff, 20, SR / 2) / SR)
    y = np.empty_like(x); yp = 0.0
    for i in range(len(x)):
        yp = (1 - a[i]) * x[i] + a[i] * yp
        y[i] = yp
    return y

def svf_lp(x, cutoff, res=0.7):
    """Lowpass RISONANTE (state-variable, Chamberlin) con cutoff variabile.
    res ~0.5 morbido .. ~0.97 squelch acido. Serve per 303/hoover/organo."""
    q = 2.0 - 1.9 * float(np.clip(res, 0.0, 0.97))       # damping: res alto -> q piccolo
    c = np.clip(np.asarray(cutoff, dtype=float), 20, SR * 0.18)
    low = band = 0.0
    y = np.empty_like(x)
    for i in range(len(x)):
        f = 2.0 * math.sin(math.pi * c[i] / SR)
        low += f * band
        high = x[i] - low - q * band
        band += f * high
        y[i] = low
    return y

def hp(x, cut):
    """Highpass semplice = segnale - lowpass fisso."""
    a = math.exp(-2 * math.pi * cut / SR)
    y = np.empty_like(x); yp = 0.0
    for i in range(len(x)):
        yp = (1 - a) * x[i] + a * yp
        y[i] = x[i] - yp
    return y

def echo(x, delay_s, taps=3, fb=0.5):
    """Eco/dub cotto nel one-shot: aggiunge code ritardate decrescenti."""
    d = int(delay_s * SR)
    out = np.zeros(len(x) + taps * d)
    out[:len(x)] += x
    for k in range(1, taps + 1):
        out[k * d:k * d + len(x)] += x * (fb ** k)
    return out


# --------------------------------------------------------------- KICK -------
def kick(f0, f1, dur, drive, click, tail=3.0):
    """Kick pulito/punch: pitch env f0->f1, corpo saturato morbido, click d'attacco."""
    t = t_arr(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * (tail / dur))
    body = np.tanh(body * drive) / math.tanh(drive)          # saturazione morbida
    cl = noise(len(t)) * np.exp(-t * 500) * click            # click
    return norm(fade(body + cl), 0.97)

def kick_hard(f0, f1, dur, drive, click):
    """Kick 909/808 DISTORTO (hardtek/acidcore): hard-clip + coda distorta."""
    t = t_arr(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * (2.3 / dur))
    body = np.clip(np.tanh(body * drive) * 1.5, -1, 1)       # clipping duro = 909 distorto
    cl = noise(len(t)) * np.exp(-t * 350) * click
    return norm(fade(body + cl), 0.98)


# --------------------------------------------------------------- BASSI ------
def sub(freq, dur, tail=2.2):
    t = t_arr(dur)
    return norm(fade(np.sin(2 * np.pi * freq * t) * np.exp(-t * (tail / dur))), 0.95)

def bass_reese(freq, dur, cut0, cut1, drive):
    """Reese/offbeat: saw detunati + sub, lowpass con env, saturato."""
    t = t_arr(dur)
    s = (saw(freq, t) + saw(freq * 1.004, t) + sq(freq * 0.5, t) * 0.6) / 2.6
    cut = cut1 + (cut0 - cut1) * np.exp(-t * 6)
    s = lp_tv(s, cut)
    s = np.tanh(s * drive)
    s *= np.exp(-t * (2.4 / dur))
    return norm(fade(s), 0.95)

def bass_fm(freq, dur, ratio, index, drive):
    """Rolling plucky (psy/trance): FM con index in decay, tight."""
    t = t_arr(dur)
    I = index * np.exp(-t * 8)
    s = np.sin(2 * np.pi * freq * t + I * np.sin(2 * np.pi * freq * ratio * t))
    s = np.tanh(s * drive)
    s *= np.exp(-t * (2.6 / dur))
    return norm(fade(s), 0.95)

def bass_acid(freq, dur, cut0, cut1, res, drive):
    """Basso acid 303 distorto (hardtek): saw -> lowpass risonante con env -> drive."""
    t = t_arr(dur)
    env = np.exp(-t * (3.0 / dur))
    cut = cut1 + (cut0 - cut1) * np.exp(-t * (5.0 / dur))
    s = svf_lp(saw(freq, t), cut, res)
    s = np.tanh(s * drive)
    s *= env
    return norm(fade(s), 0.95)

def bass_house(freq, dur):
    """Basso house RUBBERY (tech house): sine + poco saw, lowpass basso, plucky, pulito."""
    t = t_arr(dur)
    s = np.sin(2 * np.pi * freq * t) + 0.3 * saw(freq, t)
    s = lp_tv(s, 500 + 700 * np.exp(-t * (6.0 / dur)))
    s = np.tanh(s * 1.2)
    s *= np.exp(-t * (2.6 / dur))
    return norm(fade(s), 0.95)


# --------------------------------------------------------------- STAB/LEAD --
def acid303(freq, dur, cut0, cut1, res, drive):
    """Lead acid 303 (techno/hardtek): squelch risonante."""
    t = t_arr(dur)
    cut = cut1 + (cut0 - cut1) * np.exp(-t * (4.0 / dur))
    s = svf_lp(saw(freq, t), cut, res)
    s = np.tanh(s * drive)
    s *= np.exp(-t * (2.2 / dur))
    return norm(fade(s), 0.9)

def stab_fm(freq, dur, ratio, index, decay):
    """Stab FM brillante (psytrance)."""
    t = t_arr(dur)
    I = index * np.exp(-t * decay)
    s = np.sin(2 * np.pi * freq * t + I * np.sin(2 * np.pi * freq * ratio * t))
    s *= np.exp(-t * decay)
    return norm(fade(s), 0.9)

def stab_supersaw(freq, dur, cut):
    """Supersaw (trance): 7 saw detunati, lowpass con env, attacco morbido."""
    t = t_arr(dur)
    s = np.zeros(len(t))
    for d in (-14, -7, -3, 0, 3, 7, 14):
        s += saw(freq * (2 ** (d / 1200.0)), t)
    s /= 7
    s = svf_lp(s, cut + (4000 - cut) * np.exp(-t * 4), 0.6)
    s *= np.minimum(1.0, t * 40) * np.exp(-t * (1.6 / dur))
    return norm(fade(s), 0.9)

def organ(freq, dur):
    """Organo drawbar CALDO (tech house): additivo, meno armoniche alte, poca grinta."""
    t = t_arr(dur)
    parts = [(1, 1.0), (2, 0.6), (3, 0.4), (4, 0.25), (6, 0.12)]     # niente 8a armonica (meno tagliente)
    s = sum(l * np.sin(2 * np.pi * freq * h * t) for h, l in parts)
    s = lp_tv(s, 2200 + 800 * np.exp(-t * 4))                        # smussa gli acuti
    s *= np.minimum(1.0, t * 300) * np.exp(-t * (2.5 / dur))
    s = np.tanh(s * 1.05)                                            # calda, non distorta
    return norm(fade(s), 0.9)

def stab_chord(freq, dur, cut):
    """Stab accordo minore CALDO (techno): saw detunati, filtro gentile, niente acid urlante."""
    t = t_arr(dur)
    ratios = [1.0, 2 ** (3 / 12.0), 2 ** (7 / 12.0)]                 # triade minore
    s = np.zeros(len(t))
    for r in ratios:
        s += saw(freq * r, t) + saw(freq * r * 1.005, t)
    s /= len(ratios) * 2
    s = svf_lp(s, cut + cut * 1.4 * np.exp(-t * (4.0 / dur)), 0.4)   # risonanza BASSA
    s = np.tanh(s * 1.15)
    s *= np.minimum(1.0, t * 60) * np.exp(-t * (2.2 / dur))
    return norm(fade(s), 0.9)

def dubchord(freq, dur):
    """Dub chord minore7 lavato + eco (minimal): accordo che si chiude, plate/dub."""
    t = t_arr(dur)
    ratios = [1.0, 2 ** (3 / 12.0), 2 ** (7 / 12.0), 2 ** (10 / 12.0), 2.0]  # min7 + ottava
    s = np.zeros(len(t))
    for r in ratios:
        s += 0.5 * saw(freq * r, t) + 0.5 * np.sin(2 * np.pi * freq * r * t)
    s /= len(ratios)
    s = lp_tv(s, 900 + 500 * np.exp(-t * 3))                  # si chiude
    s *= np.minimum(1.0, t * 18) * np.exp(-t * (1.7 / dur))   # attacco morbido
    return norm(fade(echo(s, 0.13, taps=3, fb=0.5)), 0.85)

def hoover(freq, dur):
    """Hoover rave (hardtek): saw detunati + pitch drop, lowpass risonante, distorto."""
    t = t_arr(dur)
    slide = 1.0 + 0.05 * np.exp(-t * 18)                     # leggero calo di pitch iniziale
    s = np.zeros(len(t))
    for d in (-12, -5, 0, 5, 12):
        f = freq * slide * (2 ** (d / 1200.0))
        s += saw(1, np.cumsum(f) / SR)
    s += sq(freq * 0.5, t) * 0.5
    s /= 5.5
    s = svf_lp(s, 1400 + 900 * np.exp(-t * 4), 0.6)          # risonanza piu' bassa (meno "panico")
    s = np.tanh(s * 1.6)                                      # meno drive
    s *= np.minimum(1.0, t * 60) * np.exp(-t * (1.8 / dur))
    return norm(fade(s), 0.85)


# --------------------------------------------------------------- PERC/FX ----
def hat(dur, cut):
    t = t_arr(dur)
    s = hp(noise(len(t)), cut) * np.exp(-t * (5.0 / dur))
    return norm(fade(s, 1), 0.8)

def clap():
    t = t_arr(0.18)
    s = np.zeros(len(t))
    for k in range(3):
        e = np.exp(-np.maximum(0, (t - 0.012 * k)) * 120)
        s += hp(noise(len(t)), 1200) * e
    s += hp(noise(len(t)), 1200) * np.exp(-t * 18) * 0.6
    return norm(fade(s), 0.85)

def tom(freq, dur):
    t = t_arr(dur)
    f = freq * (1 + 1.4 * np.exp(-t * 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(fade(np.sin(ph) * np.exp(-t * (3.5 / dur))), 0.9)

def rim():
    t = t_arr(0.05)
    f = 400 + 1400 * np.exp(-t * 300)
    return norm(fade(np.sin(2 * np.pi * f * t) * np.exp(-t * 120)), 0.8)

def shaker():
    t = t_arr(0.09)
    s = hp(noise(len(t)), 6000) * np.minimum(1, t * 200) * np.exp(-t * 40)
    return norm(fade(s, 1), 0.6)

def zap():
    t = t_arr(0.22)
    f = 80 + 1700 * np.exp(-t * 25)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(fade(saw(1, ph / (2 * np.pi)) * np.exp(-t * 14)), 0.85)

def riser(dur):
    t = t_arr(dur)
    cut = 300 * (2 ** (t / dur * 6))
    s = lp_tv(noise(len(t)), cut) * (t / dur) ** 2
    return norm(fade(s, 20), 0.7)

def siren(dur=0.9):
    """Sirena rave (hardtek): wail su/giu' distorto. [NB: troppo 'allarme' -> uso impact()]"""
    t = t_arr(dur)
    f = 700 + 450 * np.sin(2 * np.pi * 3.0 * t)
    s = np.tanh(saw(1, np.cumsum(f) / SR) * 2.2)
    s *= np.minimum(1.0, t * 20) * np.exp(-t * (1.1 / dur))
    return norm(fade(s), 0.72)

def impact(dur=0.5):
    """Impatto/boom di transizione (hardtek): sub che scende + coda noise. NON allarmante."""
    t = t_arr(dur)
    f = 40 + 120 * np.exp(-t * 8)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * (3.0 / dur))
    s += lp_tv(noise(len(t)), np.full(len(t), 800.0)) * np.exp(-t * (5.0 / dur)) * 0.4
    return norm(fade(s), 0.9)


# ------------------------------------------------------- kit per genere -----
def build(genre, kit):
    d = os.path.join(OUT, genre); os.makedirs(d, exist_ok=True)
    for name in KIT_ORDER:
        sig = kit[name]
        p = os.path.join(d, name + ".wav")
        x = np.clip(sig, -1, 1)
        with wave.open(p, "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x * 32767).astype("<i2").tobytes())
    print(f"  {genre:10} -> {len(kit)} suoni")


def scrivi_index(generi):
    """Rigenera assets/sounds/index.json in sync col pack (nomi fissi KIT_ORDER)."""
    idx = {g: [n + ".wav" for n in KIT_ORDER] for g in generi}
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=1, ensure_ascii=False)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("Genero il sample pack v2 (suoni nostri, no-copyright):")

    # --- TECHNO: stab accordo caldo + reese morbido (niente acid gracchiante) ---
    build("techno", {
        "kick": kick(150, 48, 0.32, 2.4, 0.35),
        "sub": sub(BASS_REF, 0.5),
        "bass": bass_reese(BASS_REF, 0.34, 1600, 420, 1.6),   # meno cutoff/drive = meno buzz
        "stab": stab_chord(STAB_REF, 0.42, 900),              # accordo min caldo, non acid
        "hat": hat(0.05, 6200),
        "openhat": hat(0.28, 4800),
        "clap": clap(),
        "perc": rim(),
        "fx": zap(),
    })

    # --- TECH HOUSE: kick tight pulito + basso rubbery + organo caldo ---
    build("techhouse", {
        "kick": kick(155, 52, 0.22, 1.8, 0.45),               # tight, pulito, click
        "sub": sub(BASS_REF, 0.36, tail=2.6),
        "bass": bass_house(BASS_REF, 0.26),                   # rubbery sine+saw, non reese
        "stab": organ(STAB_REF, 0.28),                        # organo caldo
        "hat": hat(0.045, 7200),                              # crisp ma non tagliente
        "openhat": hat(0.24, 6000),
        "clap": clap(),
        "perc": shaker(),
        "fx": rim(),
    })

    # --- MINIMAL/DEEP: dub chord + BASSO in primo piano (armoniche+corpo) + sub pieno ---
    build("minimal", {
        "kick": kick(140, 45, 0.30, 1.8, 0.28),
        "sub": sub(BASS_REF, 0.55, tail=1.8),                 # sub pieno e lungo
        "bass": bass_reese(BASS_REF, 0.34, 1700, 380, 1.9),   # piu' cutoff+drive = si SENTE davanti
        "stab": dubchord(STAB_REF, 0.5),
        "hat": hat(0.04, 7000),
        "openhat": hat(0.20, 5500),
        "clap": clap(),
        "perc": rim(),
        "fx": shaker(),
    })

    # --- PSYTRANCE: rolling bass sine+saw tight + stab FM brillante + kick click ---
    build("psytrance", {
        "kick": kick(165, 46, 0.20, 3.2, 0.6),                # tight, click brillante
        "sub": sub(BASS_REF, 0.28),
        "bass": bass_fm(BASS_REF, 0.16, 2.0, 4.0, 2.4),       # rolling plucky
        "stab": stab_fm(STAB_REF, 0.30, 2.0, 5.0, 9),
        "hat": hat(0.045, 7200),
        "openhat": hat(0.24, 5800),
        "clap": clap(),
        "perc": tom(110, 0.24),
        "fx": zap(),
    })

    # --- TRANCE: supersaw + riser, euforico ---
    build("trance", {
        "kick": kick(150, 48, 0.28, 2.0, 0.4),
        "sub": sub(BASS_REF, 0.5),
        "bass": bass_reese(BASS_REF, 0.28, 2200, 450, 1.8),
        "stab": stab_supersaw(STAB_REF, 0.6, 700),
        "hat": hat(0.05, 6800),
        "openhat": hat(0.30, 4800),
        "clap": clap(),
        "perc": shaker(),
        "fx": riser(2.0),
    })

    # --- HARDTEK: kick 909 distorto + hoover CALMO + impact (niente sirena "panico") ---
    build("hardtek", {
        "kick": kick_hard(160, 44, 0.28, 4.0, 0.5),           # distorto ma meno brutale
        "sub": sub(BASS_REF, 0.32),
        "bass": bass_acid(BASS_REF, 0.18, 1800, 400, 0.65, 2.2),  # driving, non urlante
        "stab": hoover(STAB_REF, 0.42),                       # hoover ammorbidito (vedi funzione)
        "hat": hat(0.05, 5800),
        "openhat": hat(0.26, 4800),
        "clap": clap(),
        "perc": tom(120, 0.22),
        "fx": impact(0.5),                                    # boom di transizione, non sirena
    })

    generi = ["techno", "techhouse", "minimal", "psytrance", "trance", "hardtek"]
    scrivi_index(generi)
    print("Fatto. Cartella:", OUT, "| index.json aggiornato (6 generi).")


if __name__ == "__main__":
    main()
