# -*- coding: utf-8 -*-
"""TeknoSteps - Pipeline giornaliera CANALE 2 (Strange Light / visual ipnotico). Made in Italy.
Genera audio+visual -> video 1h -> copertina -> carica su canale 2 (token_ch2.json).
Uso: python pipeline_ipnotico.py [--no-upload]"""
import argparse, os, random, subprocess, sys
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
    ap.add_argument("--shorts", type=int, default=5)
    ap.add_argument("--reuse-visual", action="store_true",
                    help="riusa base_ipno.mp4 gia' pronto (rigenera solo audio+montaggio)")
    args = ap.parse_args()
    video = os.path.join(BASE, "teknosteps_ipno_1h.mp4")
    df = os.path.join(BASE, "_desc_ipno.txt")
    vcmd = ["crea_video_ipnotico.py", "--durata", "60", "--loop", "40", "--cicli", "8", "--out", video]
    if args.reuse_visual:
        vcmd.append("--no-visual-gen")
    run(vcmd, "1/4 Video ipnotico")   # <- qui viene generato l'audio + _audio_meta.json
    run(["genera_copertina_ipno.py", "--video", video], "2/4 Copertina ipnotica")
    run(["crea_short.py", "--preset", "hypno", "--input", video, "--auto", str(args.shorts)], f"3/4 Short verticali (x{args.shorts})")
    # SEO: titolo con BPM + descrizione con capitoli reali (legge _audio_meta.json)
    title, desc, tags = seo_youtube.build("strange")
    open(df, "w", encoding="utf-8").write(desc)
    print("[SEO] " + title)
    if args.no_upload:
        print("[OK] Creato, upload saltato."); return
    run(["youtube_upload.py", "--video", video, "--title", title, "--description-file", df,
         "--tags", tags, "--thumbnail", "ipno-thumbnail.png", "--token", "token_ch2.json",
         "--privacy", args.privacy], "4/4 Upload canale 2 (Strange Light)")
    # SEO Shorts: pool di titoli-gancio (keyword "Dark Psytrance" front-loaded + curiosita'
    # + branding | Strange Light). 5 hook = 5 short, uno diverso per ciascuno (no ripetizioni).
    STRANGE_HOOKS = [
        "Don't scroll... just watch this dark psytrance loop",
        "Dark Psytrance visuals you can't look away from",
        "This hypnotic dark psytrance loop is oddly satisfying",
        "POV: dark psytrance visuals take over your screen",
        "Dark Psytrance that hits different in the dark",
    ]
    hooks = random.sample(STRANGE_HOOKS, len(STRANGE_HOOKS))   # ordine casuale, senza ripetere
    for i in range(1, args.shorts + 1):
        sp = os.path.join(BASE, f"short_hypno_{i:02d}.mp4")
        if not os.path.exists(sp):
            continue
        short_title = f"{hooks[(i - 1) % len(hooks)]} #shorts | Strange Light"
        run(["youtube_upload.py", "--video", sp, "--short", "--token", "token_ch2.json",
             "--title", short_title, "--tags", tags,
             "--privacy", args.privacy], f"Short {i}/5 -> canale 2")
    print("\n[OK] Episodio Strange Light + 5 short pubblicati. Made in Italy.")


if __name__ == "__main__":
    main()
