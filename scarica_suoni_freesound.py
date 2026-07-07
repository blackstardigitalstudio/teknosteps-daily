# -*- coding: utf-8 -*-
"""
SCARICA SUONI CC0 DA FREESOUND — libreria open-source.  TeknoSteps · Made in Italy.
==================================================================================
Cerca su Freesound.org SOLO suoni con licenza CC0 (dominio pubblico, nessuna
attribuzione richiesta — puliti come i nostri) e li scarica nella libreria per
genere: assets/sounds/<genere>/<tipo>_lib<ID>.wav  (convertiti con ffmpeg).

I BPM/tipi di suono per genere sono impostati da ricerca (vedi memoria):
  techno ~132  ·  minimal ~126  ·  psytrance ~146  ·  trance ~138

SERVE UN TOKEN (gratis):
  1. crea account su freesound.org
  2. vai su  https://freesound.org/apiv2/apply/  -> "New credential" (tipo: API key)
  3. copia la "Client secret/Api key" in  _freesound_secret.json:
       { "token": "LA_TUA_API_KEY" }

USO:  python scarica_suoni_freesound.py            (scarica 1 per tipo, tutti i generi)
      python scarica_suoni_freesound.py techno     (solo un genere)
      python scarica_suoni_freesound.py --n 3      (3 candidati per tipo)
"""
import os, sys, json, time, shutil, subprocess, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
SECRET = os.path.join(BASE, "_freesound_secret.json")
OUT = os.path.join(BASE, "assets", "sounds")

# Query per genere e tipo di suono (dai risultati di ricerca sui suoni-firma).
QUERIES = {
    "techno":    {"kick": "techno kick", "bass": "analog bass note",
                  "stab": "synth stab", "hat": "hi-hat closed", "clap": "clap drum",
                  "perc": "percussion hit", "fx": "sweep riser"},
    "minimal":   {"kick": "kick drum deep", "bass": "sub bass note",
                  "stab": "synth chord stab", "hat": "hi-hat closed", "clap": "rimshot",
                  "perc": "click percussion", "fx": "blip synth"},
    "psytrance": {"kick": "psytrance kick", "bass": "psy bass",
                  "stab": "synth lead stab", "hat": "hi-hat closed", "clap": "clap drum",
                  "perc": "tom drum", "fx": "zap laser"},
    "trance":    {"kick": "trance kick", "bass": "bass synth note",
                  "stab": "supersaw synth", "hat": "hi-hat open", "clap": "clap drum",
                  "perc": "shaker", "fx": "riser uplifter sweep"},
    "techhouse": {"kick": "house kick", "bass": "bass note",
                  "stab": "electric piano stab", "hat": "closed hihat", "clap": "clap",
                  "perc": "shaker", "fx": "vocal chop"},
    "hardtek":   {"kick": "distorted kick", "bass": "acid bass",
                  "stab": "hoover synth", "hat": "closed hihat", "clap": "clap",
                  "perc": "percussion loop", "fx": "riser"},
}


def ffmpeg():
    fm = shutil.which("ffmpeg")
    if fm:
        return fm
    for d in (r"C:\Program Files\Wondershare\Recoverit",):
        c = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(c):
            return c
    return None


def token():
    if not os.path.exists(SECRET):
        print("X Manca _freesound_secret.json. Metti { \"token\": \"API_KEY\" } "
              "(vedi istruzioni in cima).")
        sys.exit(1)
    return json.load(open(SECRET, encoding="utf-8"))["token"]


def search(tok, query, n, filt=None):
    params = urllib.parse.urlencode({
        "query": query,
        "filter": filt or 'license:"Creative Commons 0" duration:[0.05 TO 2.5]',
        "fields": "id,name,previews,duration,license",
        "sort": "score", "page_size": max(1, n), "token": tok,
    })
    url = "https://freesound.org/apiv2/search/text/?" + params
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r).get("results", [])


def write_index():
    """Rigenera assets/sounds/index.json (usato da audition.html)."""
    idx = {}
    for g in ("techno", "techhouse", "minimal", "psytrance", "trance", "hardtek"):
        d = os.path.join(OUT, g)
        if os.path.isdir(d):
            idx[g] = sorted(f for f in os.listdir(d) if f.lower().endswith(".wav"))
    json.dump(idx, open(os.path.join(OUT, "index.json"), "w"), indent=1)


# Termini di ricerca SPECIFICI per stile: cosi' scarica suoni COERENTI col genere
# (techno/hardtek/psy/tribe) e NON roba trap/generica.
STYLE_TERMS = {
    "techno":    {"kick": "techno kick punchy", "bass": "techno reese bass",
                  "stab": "techno stab hit", "hat": "techno closed hihat",
                  "perc": "techno percussion"},
    "minimal":   {"kick": "minimal techno kick", "bass": "deep dub techno bass",
                  "stab": "dub techno chord stab", "hat": "minimal hihat",
                  "perc": "minimal click percussion"},
    "techhouse": {"kick": "tech house kick", "bass": "rolling house bassline",
                  "stab": "house organ stab chord", "hat": "house swing hihat",
                  "perc": "house conga groove"},
    "psytrance": {"kick": "psytrance kick", "bass": "psytrance rolling bass",
                  "stab": "psytrance lead acid", "hat": "psytrance hihat",
                  "perc": "psytrance percussion"},
    "trance":    {"kick": "trance kick", "bass": "trance bass",
                  "stab": "trance supersaw stab", "hat": "trance open hihat",
                  "perc": "trance percussion"},
    "hardtek":   {"kick": "hardcore hardtek kick", "bass": "rave acid bass",
                  "stab": "hoover rave stab", "hat": "hardcore hihat",
                  "perc": "tribe rave percussion"},
}


# --------- Scarica campioni SIMILI a una canzone analizzata (coerenti col genere) ---
def scarica_simili(genere, centroid_hz, n=1):
    """Cerca su Freesound one-shot CC0 col timbro SIMILE (ac_brightness vicino al
    centroide della canzone) per i tipi principali e li scarica nella cartella del
    genere. Ritorna la lista dei file creati. Best-effort (salta in caso d'errore)."""
    try:
        tok = token(); fm = ffmpeg()
    except SystemExit:
        return []
    if not fm:
        return []
    # stile per i TERMINI (include hardtek), folder per il SALVATAGGIO (i 4 base)
    styleg = genere if genere in STYLE_TERMS else "techno"
    gkey = genere if genere in ("techno", "techhouse", "minimal", "psytrance", "trance") else "techno"
    terms = STYLE_TERMS[styleg]
    d = os.path.join(OUT, gkey); os.makedirs(d, exist_ok=True)
    out = []
    filt = 'license:"Creative Commons 0" duration:[0.05 TO 2.5]'
    for typ in ("kick", "bass", "stab", "hat", "perc"):
        res = []
        # query dallo stile -> fallback genere+tipo -> tipo (ma sempre col genere davanti)
        for query in (terms[typ], "%s %s" % (styleg, typ), "%s %s" % (gkey, typ)):
            try:
                res = search(tok, query, n, filt)
            except urllib.error.HTTPError as e:
                if e.code in (403, 429):      # rate-limit Freesound -> smetti, tieni cio' che hai
                    return out
                res = []
            except Exception:
                res = []
            if res:
                break
            time.sleep(0.5)                   # gentile con l'API
        time.sleep(0.8)
        for r in res[:n]:
            prev = (r.get("previews") or {}).get("preview-hq-mp3")
            if not prev:
                continue
            dst = os.path.join(d, "%s_sim%s.wav" % (typ, r["id"]))
            try:
                grab(fm, tok, prev, dst)
                out.append("%s/%s" % (gkey, os.path.basename(dst)))
            except Exception:
                pass
    if out:
        write_index()
    return out


def grab(fm, tok, url, dst):
    # scarica il preview mp3 (il token va in coda) e converte in wav mono 44.1k normalizzato
    tmp = dst + ".mp3"
    req = urllib.request.Request(url + ("&token=" + tok if "?" in url else "?token=" + tok),
                                 headers={"Authorization": "Token " + tok})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        f.write(r.read())
    subprocess.run([fm, "-y", "-loglevel", "error", "-i", tmp, "-ac", "1", "-ar", "44100",
                    "-af", "silenceremove=start_periods=1:start_threshold=-50dB,loudnorm",
                    dst], check=True)
    os.remove(tmp)


def main():
    tok = token()
    fm = ffmpeg()
    if not fm:
        print("X ffmpeg non trovato."); sys.exit(1)
    # parse: generi posizionali + flag --n N (escludo il valore di --n dai generi)
    raw = sys.argv[1:]
    args, n, skip = [], 1, False
    for i, a in enumerate(raw):
        if skip:
            skip = False; continue
        if a == "--n":
            skip = True
            try: n = int(raw[i + 1])
            except Exception: pass
            continue
        if a.startswith("--"):
            continue
        args.append(a)
    genres = args or list(QUERIES.keys())

    for g in genres:
        d = os.path.join(OUT, g); os.makedirs(d, exist_ok=True)
        print(f"\n== {g} ==")
        for typ, q in QUERIES[g].items():
            try:
                res = search(tok, q, n)
            except Exception as e:
                print(f"  [!] {typ}: ricerca fallita ({e})"); continue
            if not res:
                print(f"  [-] {typ}: nessun CC0 per '{q}'"); continue
            for i, r in enumerate(res[:n]):
                prev = (r.get("previews") or {}).get("preview-hq-mp3")
                if not prev:
                    continue
                dst = os.path.join(d, f"{typ}_lib{r['id']}.wav")
                try:
                    grab(fm, tok, prev, dst)
                    print(f"  [OK] {typ}: #{r['id']} {r['name'][:40]} ({r['duration']:.2f}s)")
                except Exception as e:
                    print(f"  [!] {typ}: download/convert fallito ({e})")
    print("\nFatto. I suoni sono in assets/sounds/<genere>/ (tipo_libID.wav). "
          "Ascoltali nello Studio/audition, tieni i migliori, poi Pubblica.")


if __name__ == "__main__":
    main()
