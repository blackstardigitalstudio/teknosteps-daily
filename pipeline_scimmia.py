# -*- coding: utf-8 -*-
"""TeknoSteps - Pipeline giornaliera CANALE 3 (scimmietta che balla). Made in Italy.
Genera audio -> video scimmietta 1h -> copertina -> carica su canale 3 (token_ch3.json).
Uso: python pipeline_scimmia.py [--no-upload]"""
import argparse, datetime, json, os, random, subprocess, sys
import seo_youtube
BASE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable


def run(a, d):
    print("\n=== " + d + " ===")
    if subprocess.run([PY] + a, cwd=BASE, env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")).returncode != 0:
        sys.exit("[X] " + d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--privacy", default="public")
    args = ap.parse_args()
    video = os.path.join(BASE, "teknosteps_scimmia_kling_1h.mp4")
    short = os.path.join(BASE, "short_monkey_kling.mp4")
    df = os.path.join(BASE, "_desc_scimmia.txt")
    # SCIMMIA VERA (clip Kling 3D: danza + camminata) invece della PNG che rimbalza.
    # Scimmia 3D "tosta/incazzata" (clip Kling). Se c'e' anche la camminata la aggiunge.
    kling_clips = ["scimmia_kling_clip.mp4"]
    if os.path.exists(os.path.join(BASE, "scimmia_kling_walk.mp4")):
        kling_clips.append("scimmia_kling_walk.mp4")
    run(["crea_video_kling.py", "--clips", *kling_clips,
         "--durata", "60", "--long-out", video, "--short-out", short, "--only", "both"],
        "1/3 Video scimmia 3D (Kling)")   # <- genera audio + _audio_meta.json
    # 5 Short verticali a tempi distribuiti del video 1h (hook "THIS MONKEY / IS ON BEAT")
    run(["crea_short.py", "--preset", "monkey", "--input", video, "--auto", "5"], "1b/3 Short verticali scimmia (x5)")
    run(["genera_brand_scimmia.py", "--thumb-only"], "2/3 Copertina scimmietta")
    # A/B test copertine: ruota control/A/B per giorno; risultati in SEO_LOG.md
    variant = ["control", "A", "B"][datetime.date.today().toordinal() % 3]
    if variant != "control":
        run(["genera_thumb_ab.py", "--variant", variant, "--out", "scimmia-thumbnail.png"],
            "2b/3 Copertina variante " + variant)
    # SEO: titolo con BPM + descrizione keyword-rich (legge _audio_meta.json)
    title, desc, tags = seo_youtube.build("monkey")
    ab = os.path.join(BASE, "_ab_thumbs.json")
    hist = json.load(open(ab, encoding="utf-8")) if os.path.exists(ab) else []
    hist.append({"date": str(datetime.date.today()), "variant": variant, "title": title})
    json.dump(hist, open(ab, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(df, "w", encoding="utf-8").write(desc)
    print("[SEO] " + title)
    if args.no_upload:
        print("[OK] Creato, upload saltato."); return
    run(["youtube_upload.py", "--video", video, "--title", title, "--description-file", df,
         "--tags", tags, "--thumbnail", "scimmia-thumbnail.png", "--token", "token_ch3.json",
         "--privacy", args.privacy], "4/4 Upload canale 3 (scimmietta)")
    # SEO Shorts: pool di titoli-gancio (keyword "dark psytrance" + curiosita' + branding).
    # 5 short, un hook diverso per ciascuno (no ripetizioni: il titolo identico ripetuto
    # restava a 0 view).
    MONKEY_HOOKS = [
        "This monkey is ON BEAT",
        "Wait for the drop... this monkey dances dark psytrance",
        "POV: a monkey drops the hardest dark psytrance beat",
        "Can this monkey stay on beat? Dark Psytrance",
        "Dark psytrance but a monkey is losing it",
        "This monkey feels the dark psytrance bass",
    ]
    hooks = random.sample(MONKEY_HOOKS, 5)
    for i in range(1, 6):
        sp = os.path.join(BASE, f"short_monkey_{i:02d}.mp4")
        if not os.path.exists(sp):
            continue
        short_title = hooks[(i - 1) % len(hooks)] + " #shorts | Tekno Monkey"
        run(["youtube_upload.py", "--video", sp, "--short", "--token", "token_ch3.json",
             "--title", short_title, "--tags", tags, "--privacy", args.privacy], f"Short {i}/5 -> canale 3")
    print("\n[OK] Episodio scimmietta + 5 short pubblicati. Made in Italy.")


if __name__ == "__main__":
    main()
