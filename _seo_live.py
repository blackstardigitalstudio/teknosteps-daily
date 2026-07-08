# -*- coding: utf-8 -*-
"""SEO dirette YouTube 24/7 - 3 canali. Made in Italy.

Le dirette con chiave RTMP persistente ricevono da YouTube il titolo di default
"Emision en directo de <canale>" (spagnolo, zero keyword). Questo script rilegge
tutte le broadcast (attive/programmate/concluse) e i relativi VOD e applica
metadati SEO ottimizzati (titolo keyword-rich EN, descrizione, tag, categoria
Musica, lingua EN). Idempotente e auto-guarente: le broadcast gia' sistemate
(titolo che inizia con la bandierina) vengono saltate.

Uso:
  python _seo_live.py            # SOLO report (read-only)
  python _seo_live.py --fix      # applica i metadati SEO
"""
import argparse, os, sys, datetime
import youtube_upload

BASE = os.path.dirname(os.path.abspath(__file__))

# Anno corrente = ancora di ricerca "24/7 psytrance radio 2026" (dinamico: si aggiorna da solo).
YEAR = datetime.datetime.now().year

SITE = "https://teknosteps.com"
CREDIT = "Website by Blackstar Digital - https://www.blackstardigitalstudio.com/"
DEFAULT_MARKERS = ("emision en directo", "emisión en directo", "live stream of", "en directo de")
DONE_MARK = "\U0001F534"  # bandierina rossa: marca le broadcast gia' sistemate

# Metadati SEO per canale (titolo <100 char, descrizione keyword-rich, tag)
LIVE = {
    "token.json": {
        "name": "TeknoSteps",
        "title": DONE_MARK + f" Dark Psytrance Radio {YEAR} • 24/7 Live Mix for Focus, Coding & Night Drive [No Copyright]",
        "desc": (
            "\U0001F534 LIVE 24/7 — Dark Psytrance Radio by TeknoSteps.\n\n"
            "Non-stop hypnotic, driving dark psytrance: endless rolling bass and steps, "
            "no faces, no ads breaking the flow. Perfect background music for deep focus, "
            "coding, studying, gym, gaming and late-night drives. 100% no copyright / "
            "copyright-free, safe to listen and stream.\n\n"
            "▶ Genres: dark psytrance, hi-tech psy, forest psy, hypnotic techno.\n"
            "▶ Made with an original generative synth engine — every minute is unique.\n\n"
            "\U0001F310 Website & free downloads: " + SITE + "\n"
            "\U0001F517 More channels: Strange Light (hypnotic visuals) • Tekno Monkey (dancing beats).\n\n"
            + CREDIT + "\n\n"
            "#darkpsytrance #psytrance #psytranceradio #247radio #nocopyrightmusic "
            "#focusmusic #codingmusic #psy #darkpsy #livestream"
        ),
        "tags": ["dark psytrance", "psytrance radio", "dark psytrance radio", "24/7 psytrance",
                 "psytrance live", "psytrance mix", "dark psy", "hypnotic psytrance",
                 "focus music", "coding music", "night drive music", "no copyright music",
                 "psytrance 24/7", "live radio", "teknosteps"],
    },
    "token_ch2.json": {
        "name": "Strange Light",
        "title": DONE_MARK + f" Strange Light Radio {YEAR} • 24/7 Hypnotic Dark Psytrance Visuals for Focus & Trip [No Copyright]",
        "desc": (
            "\U0001F534 LIVE 24/7 — Strange Light Radio: hypnotic dark psytrance with "
            "mesmerizing visuals.\n\n"
            "A non-stop visual trip — rolling dark psy, deep forest psytrance and hypnotic "
            "loops paired with strange, glowing visuals. Ideal for focus, meditation, studying, "
            "psychedelic ambience and long work sessions. 100% no copyright / copyright-free.\n\n"
            "▶ Genres: hypnotic psytrance, dark psy, forest psy, psychedelic ambient.\n"
            "▶ Original generative synth engine — the mix never repeats.\n\n"
            "\U0001F310 Website & free downloads: " + SITE + "\n"
            "\U0001F517 More channels: TeknoSteps (dark psytrance) • Tekno Monkey (dancing beats).\n\n"
            + CREDIT + "\n\n"
            "#psytrance #darkpsytrance #hypnotic #psytranceradio #247radio #nocopyrightmusic "
            "#focusmusic #visuals #psy #livestream"
        ),
        "tags": ["hypnotic psytrance", "dark psytrance", "psytrance radio", "strange light",
                 "24/7 psytrance", "psychedelic visuals", "psy trip", "forest psytrance",
                 "focus music", "meditation music", "no copyright music", "psytrance live",
                 "dark psy", "live radio", "visual music"],
    },
    "token_ch3.json": {
        "name": "Tekno Monkey",
        "title": DONE_MARK + f" Tekno Monkey Radio {YEAR} • 24/7 Dark Psytrance Beats to Dance, Focus & Code [No Copyright]",
        "desc": (
            "\U0001F534 LIVE 24/7 — Tekno Monkey Radio: dark psytrance beats with a dancing monkey.\n\n"
            "Non-stop on-beat dark psytrance and tribal tekno — fun, driving and hypnotic. "
            "Great for workouts, gaming, focus, coding and parties. The monkey never stops, "
            "and neither does the bass. 100% no copyright / copyright-free.\n\n"
            "▶ Genres: dark psytrance, tribe, hi-tech psy, tekno.\n"
            "▶ Original generative synth engine — every drop is unique.\n\n"
            "\U0001F310 Website & free downloads: " + SITE + "\n"
            "\U0001F517 More channels: TeknoSteps (dark psytrance) • Strange Light (hypnotic visuals).\n\n"
            + CREDIT + "\n\n"
            "#psytrance #darkpsytrance #teknomonkey #psytranceradio #247radio #nocopyrightmusic "
            "#workoutmusic #gamingmusic #psy #livestream"
        ),
        "tags": ["dark psytrance", "tekno monkey", "psytrance radio", "24/7 psytrance",
                 "dancing monkey", "psytrance beats", "workout music", "gaming music",
                 "tribe tekno", "hi-tech psy", "no copyright music", "psytrance live",
                 "dark psy", "live radio", "focus music"],
    },
}

CH_ORDER = [("CH1 TeknoSteps", "token.json"),
            ("CH2 Strange Light", "token_ch2.json"),
            ("CH3 Tekno Monkey", "token_ch3.json")]


def collect_broadcasts(yt):
    out = []
    for st in ("active", "upcoming", "completed"):
        try:
            r = yt.liveBroadcasts().list(part="snippet,status", broadcastStatus=st, maxResults=25).execute()
        except Exception as e:
            print("   [%s] ERRORE list: %s" % (st, e)); continue
        for b in r.get("items", []):
            out.append((st, b["id"], b["snippet"].get("title", ""), b["snippet"].get("description", "")))
    return out


def is_default_title(t):
    tl = t.lower()
    return any(m in tl for m in DEFAULT_MARKERS)


def apply_seo(yt, vid, meta):
    """Aggiorna titolo/descrizione/tag/categoria/lingua del video (broadcast o VOD)."""
    body = {"id": vid, "snippet": {
        "title": meta["title"][:100],
        "description": meta["desc"][:4900],
        "tags": meta["tags"],
        "categoryId": "10",           # Musica
        "defaultLanguage": "en",
        "defaultAudioLanguage": "en",
    }}
    yt.videos().update(part="snippet", body=body).execute()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="applica i metadati SEO (default: solo report)")
    args = ap.parse_args()

    for name, tok in CH_ORDER:
        meta = LIVE[tok]
        print("\n===== %s =====" % name)
        try:
            yt = youtube_upload.get_service(os.path.join(BASE, tok))
        except Exception as e:
            print("  auth ERRORE:", e); continue
        bcs = collect_broadcasts(yt)
        if not bcs:
            print("  nessuna broadcast trovata.")
            continue
        for st, vid, title, desc in bcs:
            done = title.startswith(DONE_MARK)
            flag = "OK-gia-SEO" if done else ("DEFAULT" if is_default_title(title) else "custom")
            print("  [%s] %s | %s | %s" % (st, vid, flag, title[:60]))
            if not args.fix:
                continue
            if done:
                print("        -> saltato (gia' sistemato)")
                continue
            try:
                apply_seo(yt, vid, meta)
                print("        -> SEO applicata: %s" % meta["title"][:60])
            except Exception as e:
                print("        -> ERRORE update: %s" % e)

    if not args.fix:
        print("\n(read-only) Rilancia con  --fix  per applicare i metadati SEO.")


if __name__ == "__main__":
    main()
