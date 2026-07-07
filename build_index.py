# -*- coding: utf-8 -*-
"""
BUILD INDEX — indicizza i suoni VERI (CC0) della libreria per genere e SLOT.
TeknoSteps · Made in Italy.
==================================================================================
Scansiona assets/sounds/<genere>/*.wav e li raggruppa per SLOT (kick, sub, bass,
stab, hat, openhat, clap, perc, fx), distinguendo suoni di LIBRERIA reali
(<slot>_lib<ID>.wav / _sim<ID>.wav, CC0 professionali) dai fallback sintetici
(<slot>.wav). Scrive assets/sounds/index.json in formato:
  { "<genere>": { "<slot>": [ {"f": "file.wav", "real": true/false}, ... ] } }

L'auditioner usa questo per farti ASCOLTARE e SCEGLIERE il suono migliore per
ogni slot (una passata sola), poi il kit scelto va nella radio.

USO:  python build_index.py
"""
import os, json, re

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "assets", "sounds")
GENRES = ["techno", "techhouse", "minimal", "psytrance", "trance", "hardtek"]
SLOTS = ["kick", "sub", "bass", "stab", "hat", "openhat", "clap", "perc", "fx"]


def slot_of(fname):
    """Slot dal nome file: 'openhat_lib12.wav'->openhat, 'kick.wav'->kick."""
    stem = fname[:-4] if fname.lower().endswith(".wav") else fname
    # togli suffissi libreria _lib<ID> / _sim<ID>
    stem = re.split(r"_(?:lib|sim)\d+$", stem)[0]
    stem = stem.lower()
    # match slot piu' lungo (openhat prima di hat)
    for s in sorted(SLOTS, key=len, reverse=True):
        if stem == s:
            return s
    return None


def is_real(fname):
    return bool(re.search(r"_(?:lib|sim)\d+\.wav$", fname, re.I))


def main():
    index = {}
    print("Indicizzo i suoni per genere e slot (real = libreria CC0):")
    for g in GENRES:
        d = os.path.join(OUT, g)
        if not os.path.isdir(d):
            continue
        buckets = {s: [] for s in SLOTS}
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".wav"):
                continue
            s = slot_of(f)
            if s:
                buckets[s].append({"f": f, "real": is_real(f)})
        # ordina: reali prima, sintetico in fondo
        for s in SLOTS:
            buckets[s].sort(key=lambda x: (not x["real"], x["f"]))
        index[g] = {s: buckets[s] for s in SLOTS if buckets[s]}
        counts = " ".join(f"{s}:{len(buckets[s])}" for s in SLOTS if buckets[s])
        nreal = sum(1 for s in SLOTS for x in buckets[s] if x["real"])
        print(f"  {g:10} {nreal:3d} reali | {counts}")
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False)
    print("Scritto:", os.path.join(OUT, "index.json"))


if __name__ == "__main__":
    main()
