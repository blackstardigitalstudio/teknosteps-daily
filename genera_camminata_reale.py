"""
GENERA CAMMINATA REALE — TeknoSteps  (no-split)
================================================
Made in Italy.

Dal video sorgente REALE (piedi che camminano in avanti, POV dall'alto) genera
clip a FRAME INTERO — niente taglio a metà, niente compositing AI. Solo color
grading "mondi" diversi, coerenti col brand (neon/psichedelico), per dare
l'effetto di camminare in giro per il mondo.

  Sorgente -> crop quadrato centrato -> 720x720 30fps -> grade per "mondo"

Output in video_output/walk_<mondo>.mp4 + scrive il blocco "videos" del manifest.

Richiede solo ffmpeg (lo trova da solo, incluso il build di Wondershare).
NON serve ComfyUI/GPU per questo generatore.
"""
import subprocess, shutil, sys, json
from pathlib import Path

PROJ = Path(__file__).parent
SOURCE = PROJ / "VID_20260527_162202.mp4"
OUTDIR = PROJ / "video_output"
# Filma altre clip POV (telefono in basso sui piedi) e mettile QUI: ognuna
# diventa un "mondo" reale diverso (vero giro del mondo, qualità top, zero AI).
SORGENTI_DIR = PROJ / "sorgenti_camminata"
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")

# --- inquadratura ---
CROP = "crop=1080:1080:420:0"                  # crop tarato sul sorgente originale
CROP_AUTO = "crop='min(iw\\,ih)':'min(iw\\,ih)'"  # quadrato centrato per nuove clip
SIZE = "scale=720:720:flags=lanczos"
TRIM = 7.0                       # secondi (evita la coda nera del sorgente)
FPS = 30

# Base comune: contrasto + NITIDEZZA (unsharp) + texture + vignettatura cinematografica
BASE = "eq=contrast=1.10:saturation=1.05,unsharp=5:5:0.9:5:5:0.0,vignette=PI/4.2"
GRAIN = "noise=alls=5:allf=t"    # grana leggera "gritty"

# --- I "mondi" (grading cinematografico split-tone, frame intero, piedi reali, NITIDI) ---
# Uso 'curves' per colorare le ombre lasciando puliti i mezzitoni -> look da film,
# non tinta piatta. Niente virgole dentro un singolo filtro.
WORLDS = [
    ("midnight", "Midnight Teal",  "neon",          "curves=b='0/0.08 0.5/0.55 1/1':g='0/0.03 0.5/0.5 1/0.98':r='0/0 0.5/0.45 1/0.95',eq=brightness=-0.02:saturation=1.12"),
    ("acid",     "Acid Green",     "neon",          "curves=g='0/0.07 0.5/0.6 1/1':r='0/0 0.5/0.42 1/0.9':b='0/0.02 0.5/0.45 1/0.92',eq=saturation=1.25:contrast=1.12"),
    ("ember",    "Ember Amber",    "caldo",         "curves=r='0/0.06 0.5/0.6 1/1':g='0/0.02 0.5/0.48 1/0.95':b='0/0 0.5/0.38 1/0.82',eq=saturation=1.18"),
    ("magenta",  "Magenta Rave",   "psichedelico",  "curves=r='0/0.06 0.5/0.56 1/1':b='0/0.06 0.5/0.56 1/1':g='0/0 0.5/0.38 1/0.84',eq=saturation=1.22"),
    ("violet",   "Violet Haze",    "psichedelico",  "curves=b='0/0.10 0.5/0.6 1/1':r='0/0.03 0.5/0.48 1/0.95':g='0/0 0.5/0.36 1/0.8',eq=saturation=1.16"),
    ("ice",      "Ice Cyan",       "freddo",        "curves=b='0/0.10 0.5/0.6 1/1':g='0/0.05 0.5/0.56 1/1':r='0/0 0.5/0.44 1/0.92',eq=brightness=0.02:saturation=0.98"),
]


def find_ffmpeg():
    f = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if f:
        return f
    for c in [
        r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe",
        r"C:\Program Files\Tenorshare\Tenorshare 4DDiG\ffmpeg.exe",
    ]:
        if Path(c).exists():
            return c
    return None


def build(ffmpeg, source, out_name, crop, grade):
    out = OUTDIR / out_name
    vf = f"{crop},{SIZE},{BASE},{grade},{GRAIN},format=yuv420p"
    cmd = [
        ffmpeg, "-y", "-t", str(TRIM), "-i", str(source),
        "-vf", vf, "-r", str(FPS),
        "-an",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-movflags", "+faststart",
        str(out),
    ]
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
    r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return out, (r.returncode == 0), (r.stderr or "")[-300:]


def discover_sources():
    """Clip POV reali nella cartella sorgenti_camminata/ (un mondo ciascuna)."""
    if not SORGENTI_DIR.exists():
        return []
    return sorted(p for p in SORGENTI_DIR.iterdir() if p.suffix.lower() in VIDEO_EXT)


def main():
    print("=" * 60)
    print("  GENERA CAMMINATA REALE — frame intero, niente taglio")
    print("=" * 60)
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("  X ffmpeg non trovato.")
        return
    OUTDIR.mkdir(exist_ok=True)

    # job = (source, out_name, crop, grade, scenario, name, tag)
    jobs = []
    extra = discover_sources()
    if extra:
        # MODALITÀ MULTI-SORGENTE: ogni clip filmata = un mondo reale diverso
        print(f"  {len(extra)} clip in sorgenti_camminata/  ->  un mondo reale ciascuna\n")
        for p in extra:
            wid = "".join(c if c.isalnum() else "_" for c in p.stem).lower()
            jobs.append((p, f"walk_{wid}.mp4", CROP_AUTO, "eq=gamma=1.02",
                         wid, p.stem, "reale"))
    else:
        # MODALITÀ COLORI: un solo sorgente, 6 atmosfere diverse
        if not SOURCE.exists():
            print(f"  X sorgente non trovato: {SOURCE}")
            return
        print(f"  Sorgente: {SOURCE.name}  ->  {len(WORLDS)} mondi colore @ 720x720 {FPS}fps {TRIM}s")
        print(f"  (Suggerimento: metti altre clip POV in sorgenti_camminata/ per mondi REALI diversi)\n")
        for wid, name, tag, grade in WORLDS:
            jobs.append((SOURCE, f"walk_{wid}.mp4", CROP, grade, wid, name, tag))

    videos = []
    ok = 0
    for source, out_name, crop, grade, wid, name, tag in jobs:
        print(f"  [{wid}] ", end="", flush=True)
        out, success, err = build(ffmpeg, source, out_name, crop, grade)
        if success:
            mb = out.stat().st_size / 1024 / 1024
            print(f"OK -> {out.name}  ({mb:.1f} MB)")
            ok += 1
            videos.append({
                "scenario": wid, "name": name,
                "file": f"video_output/{out.name}",
                "loopDuration": TRIM, "fps": FPS,
                "stepsPerLoop": 11, "beatPhaseOffset": 0.0,
                "tags": [tag, "reale"],
            })
        else:
            print(f"X  {err[:120]}")

    # scrive un frammento manifest pronto da incollare
    frag = PROJ / "video_output" / "videos_manifest_fragment.json"
    frag.write_text(json.dumps({"videos": videos}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  FATTO: {ok}/{len(jobs)} clip generate.")
    print(f"  Frammento manifest: {frag}")
    print("=" * 60)


if __name__ == "__main__":
    main()
