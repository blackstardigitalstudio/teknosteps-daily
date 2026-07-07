"""
GENERA_MASCHERA — Preview della maschera inpainting
====================================================
Crea un'immagine di anteprima che mostra dove cade il taglio
pavimento/gambe nel frame del video sorgente.

Risultato: maschera_preview.png nella cartella progetto.
  - Metà sinistra : frame dal video sorgente + linea di taglio
  - Metà destra   : maschera bianco/nero (bianco=AI, nero=gambe protette)

USO: doppio click su AVVIA_MASCHERA.bat  oppure  python GENERA_MASCHERA.py
"""

import struct
import zlib
import subprocess
import shutil
import sys
from pathlib import Path

# ─── CONFIGURAZIONE ────────────────────────────────────────────────────────────
SOURCE_VIDEO = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI\input\VID_20260527_162202.mp4")
OUTPUT_DIR   = Path(__file__).parent
WIDTH        = 576
HEIGHT       = 576

# Punto di taglio (0.0 = in alto, 1.0 = in basso)
# Sopra  SPLIT_Y → AI trasforma liberamente (pavimento/ambiente)
# Sotto  SPLIT_Y → pixel originali del sorgente (gambe, scarpe, vestiti)
SPLIT_Y = 0.60   # ← modifica qui se il taglio non è perfetto

# ─── UTILITY PNG ───────────────────────────────────────────────────────────────
def png_chunk(ctype, data):
    chunk = ctype + data
    return (struct.pack('>I', len(data)) + chunk +
            struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF))


def write_rgb_png(path, width, height, pixels_rgb):
    """Scrive un PNG RGB a colori. pixels_rgb: lista di (R,G,B) per ogni pixel."""
    hdr  = b'\x89PNG\r\n\x1a\n'
    ihdr = png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    rows = []
    for y in range(height):
        row = bytearray()
        row.append(0)  # filter type = None
        for x in range(width):
            r, g, b = pixels_rgb[y * width + x]
            row += bytes([r, g, b])
        rows.append(bytes(row))
    idat = png_chunk(b'IDAT', zlib.compress(b''.join(rows), 6))
    iend = png_chunk(b'IEND', b'')
    Path(path).write_bytes(hdr + ihdr + idat + iend)


def write_gray_png(path, width, height, pixels_gray):
    """Scrive un PNG in scala di grigi."""
    hdr  = b'\x89PNG\r\n\x1a\n'
    ihdr = png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
    rows = []
    for y in range(height):
        rows.append(b'\x00' + bytes(pixels_gray[y * width:(y + 1) * width]))
    idat = png_chunk(b'IDAT', zlib.compress(b''.join(rows), 6))
    iend = png_chunk(b'IEND', b'')
    Path(path).write_bytes(hdr + ihdr + idat + iend)


def read_png_rgb(path):
    """Legge un PNG RGB/RGBA (scritto da ffmpeg) in modo basilare.
    Usa ffmpeg per convertirlo in PPM raw, poi legge i pixel."""
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg:
        return None

    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(path), "-frames:v", "1",
             "-vf", f"scale={WIDTH}:{HEIGHT}", tmp_path],
            capture_output=True, timeout=30
        )
        if result.returncode != 0:
            return None

        raw = Path(tmp_path).read_bytes()
        # PPM header: "P6\n<width> <height>\n255\n"
        i = raw.index(b'\n', raw.index(b'\n', raw.index(b'\n') + 1) + 1) + 1
        pixel_data = raw[i:]
        pixels = []
        for j in range(0, len(pixel_data), 3):
            pixels.append((pixel_data[j], pixel_data[j+1], pixel_data[j+2]))
        return pixels
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  GENERA MASCHERA — Preview taglio pavimento/gambe")
    print("=" * 60)
    print()

    split_px = int(HEIGHT * SPLIT_Y)
    print(f"  Configurazione:")
    print(f"    Dimensioni frame  : {WIDTH}x{HEIGHT}px")
    print(f"    Punto di taglio   : y={split_px}px  ({SPLIT_Y*100:.0f}% altezza)")
    print(f"    Zona AI/pavimento : y=0 → y={split_px}px  ({split_px}px)")
    print(f"    Zona gambe orig.  : y={split_px} → y={HEIGHT}px  ({HEIGHT-split_px}px)")
    print()

    # ── Trova ffmpeg ─────────────────────────────────────────────────────────
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg:
        sm = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data")
        for c in [sm / "Assets" / "ffmpeg.exe",
                  sm / "Packages" / "ComfyUI" / "ffmpeg.exe"]:
            if c.exists():
                ffmpeg = str(c)
                break

    # ── Estrai frame dal video sorgente ─────────────────────────────────────
    frame_path = None
    if ffmpeg and SOURCE_VIDEO.exists():
        tmp_frame = OUTPUT_DIR / "_tmp_frame.png"
        try:
            r = subprocess.run(
                [ffmpeg, "-y", "-i", str(SOURCE_VIDEO),
                 "-vf", f"scale={WIDTH}:{HEIGHT}",
                 "-frames:v", "1", "-ss", "2",
                 str(tmp_frame)],
                capture_output=True, timeout=30
            )
            if r.returncode == 0 and tmp_frame.exists():
                frame_path = tmp_frame
                print(f"  ✓ Frame estratto dal sorgente")
        except Exception as e:
            print(f"  ⚠  Impossibile estrarre frame: {e}")
    elif not SOURCE_VIDEO.exists():
        print(f"  ⚠  Video sorgente non trovato: {SOURCE_VIDEO}")
        print(f"     La preview userà un frame grigio neutro.")

    # ── Crea maschera PNG ─────────────────────────────────────────────────────
    mask_pixels = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            mask_pixels.append(255 if y < split_px else 0)

    mask_path = OUTPUT_DIR / "teknosteps_floor_mask_preview.png"
    write_gray_png(mask_path, WIDTH, HEIGHT, mask_pixels)
    print(f"  ✓ Maschera salvata: {mask_path.name}")
    print(f"    Bianco = AI trasforma  |  Nero = gambe protette")

    # ── Crea preview comparativo ───────────────────────────────────────────────
    # Immagine finale: 2*WIDTH x HEIGHT
    #   Sinistra: frame sorgente con linea rossa di taglio
    #   Destra:   maschera bianco/nero con linea rossa
    preview_w = WIDTH * 2
    preview_pixels = []

    # Carica frame sorgente se disponibile
    source_px = None
    if frame_path and ffmpeg:
        source_px = read_png_rgb(frame_path)

    line_thickness = 3   # spessore linea rossa

    for y in range(HEIGHT):
        row = []
        is_line = abs(y - split_px) < line_thickness

        for x in range(WIDTH):
            # ── Sinistra: frame sorgente (o grigio) ──────────────────────────
            if is_line:
                row.append((255, 0, 0))  # linea rossa
            elif source_px and x + y * WIDTH < len(source_px):
                r, g, b = source_px[x + y * WIDTH]
                # Tinta verde sopra (pavimento AI), normale sotto (gambe)
                if y < split_px:
                    r2 = int(r * 0.7)
                    g2 = min(255, int(g * 0.7 + 40))
                    b2 = int(b * 0.7)
                    row.append((r2, g2, b2))
                else:
                    row.append((r, g, b))
            else:
                # Nessun frame: grigio tenue sopra, grigio scuro sotto
                gray = 160 if y < split_px else 80
                row.append((gray, gray, gray))

            # ── Destra: maschera ─────────────────────────────────────────────
            if is_line:
                row.append((255, 0, 0))  # linea rossa
            elif y < split_px:
                row.append((220, 220, 220))  # bianco (pavimento AI)
            else:
                row.append((30, 30, 30))     # nero (gambe protette)

        preview_pixels.extend(row)

    preview_path = OUTPUT_DIR / "maschera_preview.png"
    write_rgb_png(preview_path, preview_w, HEIGHT, preview_pixels)
    print(f"  ✓ Preview salvata  : {preview_path.name}")
    print()
    print("  Come leggere la preview:")
    print(f"    SINISTRA: frame del tuo video (verde tenue = zona AI, normale = zona gambe)")
    print(f"    DESTRA:   maschera (bianco = AI trasforma, nero = gambe preservate)")
    print(f"    LINEA ROSSA: punto di taglio y={split_px}px")
    print()
    print(f"  Se il taglio non è corretto:")
    print(f"    → Modifica SPLIT_Y in questo file (ora: {SPLIT_Y})")
    print(f"    → Valori più bassi = più AI in alto, più gambe preservate")
    print(f"    → Valori più alti  = meno AI, quasi tutto preservato")
    print()

    # Pulisci file temporaneo
    if frame_path and frame_path.exists() and "_tmp_frame" in str(frame_path):
        try:
            frame_path.unlink()
        except Exception:
            pass

    print("=" * 60)
    input("\nPremi Enter per chiudere...")


if __name__ == "__main__":
    main()
