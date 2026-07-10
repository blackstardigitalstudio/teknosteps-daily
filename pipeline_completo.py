# -*- coding: utf-8 -*-
"""
TeknoSteps - PIPELINE COMPLETA AUTOMATICA (Made in Italy)
==========================================================
Un comando -> nuovo episodio dark psytrance dall'inizio alla fine:
  1) genera l'audio (genera_audio_techno.py)
  2) monta il video 1h (crea_video_youtube.py)
  3) taglia gli Short (crea_short.py)
  4) carica TUTTO su YouTube con SEO + copertina (youtube_upload.py)

Pensato per essere SCHEDULATO (Utilità di pianificazione di Windows) -> il canale
va avanti da solo. Richiede la configurazione una-tantum: SETUP_YOUTUBE_API.md

Uso:
  python pipeline_completo.py                 # tutto: genera, monta, taglia, carica
  python pipeline_completo.py --no-upload     # crea i file ma non carica
  python pipeline_completo.py --shorts 3 --bpm 145 --cicli 6
"""
import argparse
import os
import random
import subprocess
import sys

import seo_youtube

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(args_list, desc):
    print(f"\n=== {desc} ===")
    r = subprocess.run([PY] + args_list, cwd=BASE)
    if r.returncode != 0:
        print(f"[X] Fallito: {desc}")
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description="Pipeline completa TeknoSteps")
    ap.add_argument("--cicli", type=int, default=12, help="piu' cicli = piu' mood diversi nella traccia (BPM viene dai mood)")
    ap.add_argument("--durata", type=float, default=60, help="durata video in minuti")
    ap.add_argument("--shorts", type=int, default=3)
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--privacy", default="public")
    ap.add_argument("--title-index", type=int, default=-1, help="-1 = casuale")
    args = ap.parse_args()

    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    video = os.path.join(BASE, "teknosteps_psy_1h.mp4")
    desc_file = os.path.join(BASE, "_desc_tmp.txt")

    # 1) audio (BPM 145 COSTANTE -> BPM esatto nel titolo)
    print("\n=== 1/4 Genero audio (synth del sito: frenchtek/tribe, mood dal manifest) ===")
    subprocess.run([PY, "genera_audio_techno.py", "--cicli", str(args.cicli), "--bpm", "145"],
                   cwd=BASE, env=env, check=True)
    # 2) video
    run(["crea_video_youtube.py", "--durata", str(args.durata), "--crf", "30",
         "--fps", "24", "--threads", "6", "--out", video], "2/4 Monto il video 1h")
    # 3) shorts
    run(["crea_short.py", "--preset", "feet", "--input", video, "--auto", str(args.shorts)], "3/4 Taglio gli Short")

    # 3.5) copertina SEMPRE DIVERSA (sfondo/titolo/tagline casuali, on-brand)
    run(["genera_copertina.py"], "Genero copertina variabile")

    if args.no_upload:
        print("\n[OK] File creati. Upload saltato (--no-upload).")
        return

    # 4) upload — SEO: titolo con BPM + descrizione keyword-rich (legge _audio_meta.json)
    # SEO Shorts: pool di titoli con HOOK (il top performer del canale era una
    # domanda-gancio, "Can you walk to this bass?"). Keyword "Dark Psytrance"
    # front-loaded + branding #shorts | TeknoSteps. Rotazione senza ripetizioni.
    SHORT_HOOKS = [
        "Can you walk to this bass? Dark Psytrance",
        "How long can you walk to this dark psytrance?",
        "Bet you can't walk to this dark psytrance",
        "POV: dark psytrance takes over your focus",
        "Wait for the drop in this dark psytrance",
        "Dark Psytrance that hits different at night",
    ]
    short_titles = random.sample(SHORT_HOOKS, min(args.shorts, len(SHORT_HOOKS)))
    while len(short_titles) < args.shorts:
        short_titles.append(random.choice(SHORT_HOOKS))

    title, desc, tags = seo_youtube.build("psy")
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(desc)
    print("\n=== 4/4 Carico su YouTube ===\n[SEO] " + title)
    subprocess.run([PY, "youtube_upload.py", "--video", video, "--title", title,
                    "--description-file", desc_file, "--tags", tags,
                    "--thumbnail", "teknosteps-thumbnail.png", "--privacy", args.privacy],
                   cwd=BASE, check=True)
    for i in range(1, args.shorts + 1):
        sp = os.path.join(BASE, f"short_feet_{i:02d}.mp4")
        if os.path.exists(sp):
            short_title = f"{short_titles[i-1]} #shorts | TeknoSteps"
            subprocess.run([PY, "youtube_upload.py", "--video", sp, "--short",
                            "--title", short_title,
                            "--tags", tags, "--privacy", args.privacy], cwd=BASE, check=True)

    print("\n[OK] EPISODIO COMPLETO PUBBLICATO. Made in Italy.")


if __name__ == "__main__":
    main()
