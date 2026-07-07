# -*- coding: utf-8 -*-
"""
TeknoSteps - Carica gli short del giorno su TikTok come BOZZE (Made in Italy)
============================================================================
Prende gli short creati dalla pipeline giornaliera dei 3 canali e li invia alla
INBOX/bozze di TikTok (endpoint inbox: NON pubblica, li pubblichi tu con un tap).
Pensato per girare in coda a AVVIA_TUTTI_I_CANALI.bat.

Serve il token OAuth (tiktok_token.json). Se manca, NON blocca la catena: stampa
le istruzioni e termina con codice 0.

Uso:
  python tiktok_drafts.py            # carica gli short esistenti come bozze
  python tiktok_drafts.py --list     # mostra solo quali short caricherebbe
"""
import argparse
import os
import sys

import tiktok_upload as tk

BASE = os.path.dirname(os.path.abspath(__file__))

# Short prodotti dalle 3 pipeline + titolo/hashtag adatto a ciascun canale.
SHORTS = [
    ("short_feet_01.mp4",   "Dark Psytrance walk 🌒 #psytrance #darkpsy #techno #rave #nocopyright"),
    ("short_feet_02.mp4",   "One beat, endless steps 👣 #psytrance #tekno #festival #nocopyright"),
    ("short_hypno_01.mp4",  "Hypnotic loop 🌀 #hypnotic #psytrance #visuals #trippy #nocopyright"),
    ("short_monkey_01.mp4", "Tekno Monkey on the beat 🐒🎧 #tekno #monkey #psytrance #funny #nocopyright"),
]


def main():
    ap = argparse.ArgumentParser(description="Short del giorno -> bozze TikTok")
    ap.add_argument("--list", action="store_true", help="mostra soltanto")
    args = ap.parse_args()

    present = [(f, t) for f, t in SHORTS if os.path.exists(os.path.join(BASE, f))]
    if not present:
        print("[i] Nessuno short trovato (short_feet_/short_hypno_/short_monkey_). Niente da caricare.")
        return
    print(f"[i] {len(present)} short da inviare a TikTok come BOZZE:")
    for f, t in present:
        print("   -", f)
    if args.list:
        return

    # Se manca il token, non rompere la catena: istruzioni e uscita pulita.
    if not os.path.exists(tk.TOKEN):
        print("\n[!] Manca tiktok_token.json: OAuth non ancora fatto. Le bozze NON sono state caricate.")
        print("    Autorizza una volta sola:")
        print("      1) python tiktok_upload.py --auth-url   (apri l'URL, autorizza)")
        print("      2) python tiktok_upload.py --code <CODE dal callback>")
        print("    Da domani in poi gli short andranno in bozze da soli.")
        return

    ok = 0
    for f, title in present:
        path = os.path.join(BASE, f)
        try:
            tk.upload(path, title, direct=False)   # inbox = BOZZA
            ok += 1
        except SystemExit as e:
            print(f"[X] {f}: {e}")
        except Exception as e:
            print(f"[X] {f}: {e}")
    print(f"\n[OK] {ok}/{len(present)} short inviati a TikTok come bozze. Aprili nell'app e pubblica. Made in Italy.")


if __name__ == "__main__":
    main()
