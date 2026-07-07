# -*- coding: utf-8 -*-
"""
FETCH SUONI mirato — scarica candidati CC0 VERI per slot specifici carenti.
TeknoSteps · Made in Italy.  Salva come <slot>_lib<ID>.wav (l'indice li vede reali).
USO:  python fetch_suoni.py
Riusa token/ffmpeg/search/grab da scarica_suoni_freesound.py. Best-effort: se
Freesound rate-limita (403/429), tiene cio' che ha scaricato e si ferma pulito.
"""
import os, sys, time, urllib.error
import scarica_suoni_freesound as fs

OUT = fs.OUT
FILT = 'license:"Creative Commons 0" duration:[0.05 TO 2.5]'

# (genere, slot, [query in ordine di preferenza], quanti_max)
TARGETS = [
    ("techhouse", "stab", ["organ stab", "synth chord stab", "electric piano stab",
                           "rhodes chord hit", "pluck chord stab", "house organ chord",
                           "hammond organ hit", "minor chord stab synth"], 10),
]


def existing_ids(genre, slot):
    d = os.path.join(OUT, genre)
    ids = set()
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.startswith(slot + "_"):
                import re
                m = re.search(r"_(?:lib|sim)(\d+)\.wav$", f)
                if m:
                    ids.add(m.group(1))
    return ids


def main():
    tok = fs.token()
    fm = fs.ffmpeg()
    if not fm:
        print("X ffmpeg non trovato."); sys.exit(1)
    total = 0
    for genre, slot, queries, cap in TARGETS:
        d = os.path.join(OUT, genre); os.makedirs(d, exist_ok=True)
        have = existing_ids(genre, slot)
        got = 0
        seen = set()
        for q in queries:
            if got >= cap:
                break
            try:
                res = fs.search(tok, q, cap, FILT)
            except urllib.error.HTTPError as e:
                if e.code in (403, 429):
                    print(f"! rate-limit Freesound ({e.code}) su '{q}' -> stop, tengo {total} suoni")
                    print("DONE", total); return
                res = []
            except Exception as ex:
                print(f"! errore ricerca '{q}': {ex}"); res = []
            for r in res:
                if got >= cap:
                    break
                sid = str(r.get("id"))
                if sid in have or sid in seen:
                    continue
                seen.add(sid)
                prev = (r.get("previews") or {}).get("preview-hq-mp3")
                if not prev:
                    continue
                dst = os.path.join(d, f"{slot}_lib{sid}.wav")
                try:
                    fs.grab(fm, tok, prev, dst)
                    got += 1; total += 1
                    print(f"  + {genre}/{slot}_lib{sid}.wav")
                except urllib.error.HTTPError as e:
                    if e.code in (403, 429):
                        print(f"! rate-limit sul download -> stop, tengo {total}")
                        print("DONE", total); return
                except Exception as ex:
                    print(f"  ! skip {sid}: {ex}")
                time.sleep(0.6)
            time.sleep(0.8)
        print(f"{genre}/{slot}: +{got} nuovi (avevo {len(have)})")
    print("DONE", total)


if __name__ == "__main__":
    main()
