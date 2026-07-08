# -*- coding: utf-8 -*-
"""
TeknoSteps - SEO YouTube condivisa per i 3 canali (Made in Italy)
=================================================================
Costruisce TITOLO + DESCRIZIONE + TAG ottimizzati per la ricerca YouTube:
- keyword principale in testa al titolo + BPM (dal sidecar _audio_meta.json)
- descrizione: hook keyword nelle prime righe (prima di "Altro"), CAPITOLI
  (timestamp reali dai blocchi), paragrafo keyword-rich, link, 3-5 hashtag
- tag: branded + exact-match + long-tail

Le pipeline chiamano:  title, desc, tags = seo_youtube.build("strange")
"""
import json, os, random, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(BASE, "_audio_meta.json")

# Anno corrente come ancora di ricerca ("dark psytrance 2026", "psytrance mix 2026").
# Dinamico: mostra 2026 ora e passa a 2027 da solo a gennaio, non invecchia mai.
YEAR = datetime.datetime.now().year

LINKS = ("📻 24/7 Radio: https://teknosteps.com\n"
         "▶️ TeknoSteps: https://youtube.com/@teknosteps\n"
         "🐒 Tekno Monkey: https://youtube.com/@teknomonkeytv\n"
         "🌀 Strange Light: https://youtube.com/@strangelightpsy\n"
         "💬 Discord: https://discord.gg/QeBkCe3qE\n"
         "🎬 License / royalty-free: https://teknosteps.com/license.html")

# nomi mood del motore -> etichette pulite per i capitoli
MOOD_LABEL = {
    "PSYTRANCE": "Dark Psytrance", "MINIMAL": "Minimal Psy",
    "MINIMAL TECHNO M": "Minimal Techno", "TECHNO": "Driving Techno",
    "TRANCE": "Psy Trance", "WAKO TEKNO 2011": "Tribe Tekno",
    "SAJANKA": "Melodic Psy", "DEVOO": "Forest Psy",
    "STRANGE LIGHT": "Hypnotic Psy", "TEKNO MONKEY": "Tribal Tekno",
    "FRENCHTEK": "Frenchcore Tek", "TRIBE": "Tribe Groove", "24/7 TEKNO": "Tekno Groove",
}

USE_CASES = ["Focus & Coding", "Deep Work", "Study & Concentration",
             "Gaming", "Night Drive", "Trance State", "Workout"]

CH = {
    "psy": dict(
        genre="Dark Psytrance", brand="TeknoSteps",
        tags=("dark psytrance, psytrance mix, psytrance, dark psy, forest psytrance, "
              "hypnotic psytrance, 1 hour psytrance, no copyright music, psy trance, "
              "night psytrance, focus music, coding music, teknosteps"),
        hashtags="#psytrance #darkpsy #nocopyrightmusic",
        blurb=("Dark psytrance and hypnotic psy for deep focus, coding, studying and night "
               "sessions. Rolling basslines, driving kicks, forest and night psy vibes. "
               "100% no-copyright — free to use in your videos and streams.")),
    "strange": dict(
        genre="Dark Psytrance", brand="Strange Light",
        tags=("dark psytrance, hypnotic visuals, psytrance mix, psychedelic visuals, "
              "trippy visuals, hypnotic psytrance, 1 hour psytrance, no copyright music, "
              "psy trance, strange light, focus music, study music, teknosteps"),
        hashtags="#psytrance #darkpsy #hypnotic",
        blurb=("Hypnotic dark psytrance with generative light visuals — for focus, deep work, "
               "trips and night sessions. Psychedelic, trippy, endless. "
               "100% no-copyright — free to use in your videos and streams.")),
    "monkey": dict(
        genre="Dark Psytrance", brand="Tekno Monkey",
        tags=("dancing monkey, techno monkey, tekno monkey, dark psytrance, psytrance mix, "
              "funny animation, dancing animal, 1 hour psytrance, no copyright music, "
              "psy trance, tribal techno, teknosteps"),
        hashtags="#psytrance #teknomonkey #nocopyrightmusic",
        blurb=("Dark psytrance and tribal tekno with a dancing monkey on the beat — jungle "
               "vibes, rolling bass, driving kicks. Fun, hypnotic, endless. "
               "100% no-copyright — free to use in your videos and streams.")),
}


def load_meta():
    try:
        return json.load(open(META, encoding="utf-8"))
    except Exception:
        return {"bpm": None, "blocks": []}


def _ts(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def chapters(blocks, max_sec=3600):
    """Timestamp reali dai blocchi (solo modalita' --minuti). Primo a 0:00."""
    out, last = [], -1
    for b in blocks:
        st = b.get("start", 0)
        if st >= max_sec:
            break
        lab = MOOD_LABEL.get(b.get("name", ""), (b.get("name") or "Psy").title())
        line = f"{_ts(st)} {lab}"
        if int(st) != last:                    # niente timestamp doppi
            out.append(line); last = int(st)
    if len(out) < 3:
        return ""
    out[0] = "0:00 " + out[0].split(" ", 1)[1]  # il primo DEVE essere 0:00
    return "⏱ Chapters:\n" + "\n".join(out)


def build(channel):
    c = CH[channel]
    meta = load_meta()
    bpm = meta.get("bpm")
    bpm_s = f"{bpm} BPM" if bpm else ""
    use = random.choice(USE_CASES)

    # ---- TITLE: keyword+ANNO in testa + BPM + durata + use-case + [No Copyright] + brand
    # L'anno subito dopo la keyword = ancora di ricerca "dark psytrance 2026".
    if bpm_s:
        title = f"{c['genre']} {YEAR} · {bpm_s} · 1 Hour Mix for {use} [No Copyright] | {c['brand']}"
    else:
        title = f"{c['genre']} {YEAR} · 1 Hour Mix for {use} [No Copyright] | {c['brand']}"
    title = title[:100]

    # ---- DESCRIPTION: hook keyword+anno (prime righe) -> capitoli -> blurb -> link -> hashtag
    hook = f"{c['genre']} {YEAR}" + (f" • {bpm_s}" if bpm_s else "") + \
           f" • 1 hour of no-copyright psy for {use.lower()}."
    ch_txt = chapters(meta.get("blocks", []))
    parts = [hook, "", c["blurb"]]
    if ch_txt:
        parts += ["", ch_txt]
    parts += ["", LINKS,
              "", "🔔 Subscribe for a new 1-hour dark psytrance mix every day.",
              "", f"{c['hashtags']} #teknosteps"]
    desc = "\n".join(parts)

    tags = c["tags"]
    # l'anno come keyword di ricerca (vale sia per i mix sia per gli Short che ereditano questi tag)
    tags += f", {c['genre'].lower()} {YEAR}, psytrance {YEAR}, psytrance mix {YEAR}, best psytrance {YEAR}"
    if bpm:                                   # il BPM come keyword nei tag (numero tondo cercato)
        tags += f", {bpm} bpm, {bpm} bpm psytrance, {bpm} bpm mix"
    return title, desc, tags
