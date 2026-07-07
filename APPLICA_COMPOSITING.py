"""
[!] DEPRECATO — questo script TAGLIA il frame a metà (gambe vere sotto + AI sopra),
    ed è la causa del "video diviso in due". NON usarlo.
    Usa invece: genera_camminata_reale.py  (vedi docs/GENERATORE_VIDEO.md)

APPLICA COMPOSITING GAMBE
=========================
Prende i 10 video già generati da ComfyUI e li composta con le gambe
originali dal video sorgente.

Risultato:
  - Ambiente (parte alta):  100% AI (trasformato per scenario)
  - Gambe/scarpe (parte bassa): 100% video sorgente (pixel identici, invariati)

Regola SPLIT_Y_TOP e SPLIT_Y_BOT se il taglio non è perfetto.
"""

import subprocess
import shutil
import sys
from pathlib import Path

# ─── CONFIGURAZIONE ────────────────────────────────────────────────
COMFY_OUTPUT = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI\output")
SOURCE_VIDEO  = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI\input\VID_20260527_162202.mp4")
OUTPUT_DIR    = Path(__file__).parent / "video_output"

WIDTH  = 576
HEIGHT = 576

# Zona di compositing (in frazione dell'altezza):
#   Sopra SPLIT_Y_TOP  → 100% ambiente AI
#   Da SPLIT_Y_TOP a SPLIT_Y_BOT → blend sfumato
#   Sotto SPLIT_Y_BOT → 100% gambe originali (INVARIATE)
SPLIT_Y_TOP = 0.44   # ~253 px su 576
SPLIT_Y_BOT = 0.60   # ~346 px su 576

# Scenari da processare
SCENARIOS = [
    "forest", "dirt_path", "gravel", "tiles", "cobblestone",
    "neon_grid", "neon_jungle", "neon_lava", "neon_circuit", "neon_crystals"
]

# ─── FUNZIONI ──────────────────────────────────────────────────────
def find_ffmpeg():
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg:
        return ffmpeg
    sm_base = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data")
    candidates = [
        sm_base / "Assets" / "ffmpeg.exe",
        sm_base / "Packages" / "ComfyUI" / "ffmpeg.exe",
    ]
    pkg = sm_base / "Packages" / "ComfyUI"
    if pkg.exists():
        for f in pkg.rglob("ffmpeg*.exe"):
            candidates.append(f)
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return None


def composite(generated_path, source_path, output_path):
    """
    Compositing corretto:
    1. Il video sorgente viene scalato a WIDTH×HEIGHT (stesso del generato)
    2. La parte BASSA viene presa dal sorgente scalato (gambe originali)
    3. La parte ALTA viene presa dal generato (ambiente AI)
    4. Taglio netto — nessun blur, nessuna sfumatura che degrada la qualità
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg non trovato"

    # Altezza della zona gambe (pixels dal basso da preservare)
    legs_start_y = int(HEIGHT * SPLIT_Y_BOT)   # da qui in giù: gambe originali
    legs_height  = HEIGHT - legs_start_y         # pixel di gambe

    # Filtro in 3 passi (senza label [out] per compatibilità Windows):
    # 1. Scala sorgente a WIDTH×HEIGHT (stessa dimensione del generato)
    # 2. Ritaglia solo la zona gambe (parte bassa del frame)
    # 3. Overlay: gambe originali sul video AI in basso
    filter_complex = (
        f"[1:v]scale={WIDTH}:{HEIGHT}[sc];"
        f"[sc]crop={WIDTH}:{legs_height}:0:{legs_start_y}[lg];"
        f"[0:v][lg]overlay=0:{legs_start_y}"
    )
    cmd = [
        ffmpeg, "-y",
        "-i", str(generated_path),   # video AI (ambiente trasformato)
        "-i", str(source_path),       # sorgente originale (gambe reali)
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-crf", "15", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path)
    ]
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kwargs)
        if r.returncode == 0:
            return True, "OK"
        return False, (r.stderr or "")[-300:]
    except Exception as e:
        return False, str(e)


# ─── MAIN ──────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  COMPOSITING GAMBE — Applica maschera a video esistenti")
    print("=" * 60)
    print()

    if not SOURCE_VIDEO.exists():
        print(f"  ✗ Video sorgente non trovato: {SOURCE_VIDEO}")
        input("\nPremi Enter per uscire...")
        return

    if not find_ffmpeg():
        print("  ✗ ffmpeg non trovato nel sistema.")
        print("    Installalo o mettilo in PATH.")
        input("\nPremi Enter per uscire...")
        return

    print(f"  Sorgente gambe : {SOURCE_VIDEO.name}")
    print(f"  Zona blend     : y={int(HEIGHT*SPLIT_Y_TOP)}px → y={int(HEIGHT*SPLIT_Y_BOT)}px  (su {HEIGHT}px totali)")
    print(f"  Output         : {OUTPUT_DIR}")
    print()
    print("  ─── Regola SPLIT_Y_TOP/BOT nel codice se il taglio non è giusto ───")
    print()

    ok_count = 0
    for s_id in SCENARIOS:
        filename  = f"teknosteps_{s_id}_00001.mp4"
        final_out = OUTPUT_DIR / f"teknosteps_{s_id}_final.mp4"

        # Cerca il video generato (prima in ComfyUI output, poi in video_output)
        src_gen = COMFY_OUTPUT / filename
        if not src_gen.exists():
            src_gen = OUTPUT_DIR / filename

        if not src_gen.exists():
            print(f"  [{s_id}]  ✗ video AI non trovato ({filename})")
            continue

        print(f"  [{s_id}]  ", end="", flush=True)
        ok, msg = composite(src_gen, SOURCE_VIDEO, final_out)
        if ok:
            size_mb = final_out.stat().st_size / 1024 / 1024
            print(f"✓ → teknosteps_{s_id}_final.mp4  ({size_mb:.1f} MB)")
            ok_count += 1
        else:
            print(f"✗ {msg[:80]}")

    print()
    print("=" * 60)
    print(f"  FATTO: {ok_count}/{len(SCENARIOS)} video composited")
    print()
    print(f"  I video _final.mp4 in: {OUTPUT_DIR}")
    print()
    print("  Se il taglio gambe/suolo non è perfetto:")
    print("  → Modifica SPLIT_Y_TOP e SPLIT_Y_BOT (ora: "
          f"{SPLIT_Y_TOP:.2f} / {SPLIT_Y_BOT:.2f})")
    print("  → Valori più bassi = più ambiente AI, meno gambe")
    print("  → Valori più alti  = meno ambiente AI, più gambe originali")
    print("=" * 60)
    input("\nPremi Enter per chiudere...")


if __name__ == "__main__":
    main()
