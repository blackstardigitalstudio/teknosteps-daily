"""
[!] DEPRECATO per il sito — la maschera inpainting rigenera solo il pavimento in alto
    e protegge le gambe in basso: produce il "video diviso a metà" (taglio a split_y).
    Per il sito usa: genera_camminata_reale.py (no taglio) oppure il workflow AI a
    frame intero workflow_teknosteps_v2v_FIXED.json. Vedi docs/GENERATORE_VIDEO.md.

TEKNOSTEPS — Generatore Video Automatico v3
============================================
Genera video video-to-video per tutti gli scenari TeknoSteps.
NOVITÀ v3: maschera inpainting — l'AI trasforma SOLO il pavimento,
le gambe/scarpe restano pixel identici al sorgente.

UTILIZZO:
  1. Apri Stability Matrix e avvia ComfyUI
  2. Doppio click su AVVIA_VIDEO_GENERATOR.bat
  3. I video vengono salvati in: ./video_output/

REQUISITI:
  - ComfyUI in esecuzione su http://127.0.0.1:8188
  - Modello: juggernautXL_ragnarokBy.safetensors
  - Estensioni: VideoHelperSuite
  - Video sorgente: VID_20260527_162202.mp4 in ComfyUI/input/
"""

import json
import urllib.request
import urllib.error
import time
import sys
import os
import shutil
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────
#  CONFIGURAZIONE
# ─────────────────────────────────────────────────────
COMFY_URL   = "http://127.0.0.1:8188"
VIDEO_NAME  = "VID_20260527_162202.mp4"
MODEL       = "juggernautXL_ragnarokBy.safetensors"
OUTPUT_DIR  = Path(__file__).parent / "video_output"
OUTPUT_DIR.mkdir(exist_ok=True)

COMFY_INPUT_DIR = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI\input")

# ─────────────────────────────────────────────────────
#  COMPOSITING — Safety net post-generazione
#
#  v3: la maschera inpainting in ComfyUI già protegge le gambe.
#  Il compositing ffmpeg è un ulteriore livello di sicurezza
#  per garantire pixel identici al sorgente nella zona gambe.
#
#  Zona di protezione (in frazione dell'altezza frame):
#    - Sopra SPLIT_Y_BOT  → AI ha trasformato solo questo (pavimento)
#    - Sotto SPLIT_Y_BOT  → gambe originali al 100% (pixel identici)
# ─────────────────────────────────────────────────────
COMFY_OUTPUT_DIR  = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI\output")
SOURCE_VIDEO_FULL = COMFY_INPUT_DIR / VIDEO_NAME

SPLIT_Y_BOT = 0.60   # 60% altezza → sotto: gambe originali (pixel identici al sorgente)


def find_ffmpeg():
    """Cerca ffmpeg in PATH, Stability Matrix o ComfyUI."""
    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg:
        return ffmpeg
    sm_base = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data")
    candidates = [
        sm_base / "Assets" / "ffmpeg.exe",
        sm_base / "Packages" / "ComfyUI" / "ffmpeg.exe",
    ]
    # Cerca ffmpeg nei sottopackage (es. imageio_ffmpeg)
    pkg_dir = sm_base / "Packages" / "ComfyUI"
    if pkg_dir.exists():
        for f in pkg_dir.rglob("ffmpeg*.exe"):
            candidates.append(f)
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return None


def make_floor_mask_png(width, height, split_y_bot=0.60):
    """
    Crea maschera inpainting PNG per ComfyUI (nessuna dipendenza esterna).

    Bianco (255) = pavimento / ambiente → AI trasforma liberamente
    Nero   (0)   = gambe / scarpe       → AI preserva i pixel originali

    Restituisce il nome file salvato in ComfyUI/input/.
    Il nome è fisso così viene riusato senza ricreare ogni volta.
    """
    import struct, zlib

    mask_name = "teknosteps_floor_mask.png"
    mask_path = COMFY_INPUT_DIR / mask_name

    split_y = int(height * split_y_bot)

    def png_chunk(ctype, data):
        chunk = ctype + data
        return (struct.pack('>I', len(data)) + chunk +
                struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF))

    hdr  = b'\x89PNG\r\n\x1a\n'
    ihdr = png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))

    rows = []
    for y in range(height):
        px = 255 if y < split_y else 0      # bianco=pavimento, nero=gambe
        rows.append(b'\x00' + bytes([px] * width))

    idat = png_chunk(b'IDAT', zlib.compress(b''.join(rows), 6))
    iend = png_chunk(b'IEND', b'')

    try:
        mask_path.write_bytes(hdr + ihdr + idat + iend)
        return mask_name
    except Exception as e:
        print(f"  ⚠  maschera non salvata: {e}")
        return None


def composite_legs(generated_path, source_path, output_path, width, height):
    """
    Safety net: incolla la zona gambe originali sul video AI.

    Usa taglio netto (nessun geq/alpha, compatibile con ogni ffmpeg):
      [1:v] sorgente → scale → crop zona gambe → overlay sul video AI

    Returns: (True, "OK") oppure (False, "messaggio errore")
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return False, "ffmpeg non trovato nel sistema"
    if not Path(generated_path).exists():
        return False, f"video AI non trovato: {Path(generated_path).name}"
    if not Path(source_path).exists():
        return False, f"video sorgente non trovato: {Path(source_path).name}"

    legs_y = int(height * SPLIT_Y_BOT)     # pixel dove iniziano le gambe
    legs_h = height - legs_y               # altezza zona gambe

    # Taglio netto: scalare sorgente a WxH, crop zona gambe, overlay sul generato
    filter_complex = (
        f"[1:v]scale={width}:{height}[sc];"
        f"[sc]crop={width}:{legs_h}:0:{legs_y}[lg];"
        f"[0:v][lg]overlay=0:{legs_y}"
    )
    cmd = [
        ffmpeg, "-y",
        "-i", str(generated_path),
        "-i", str(source_path),
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
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kwargs)
        if result.returncode == 0:
            return True, "OK"
        err = (result.stderr or "")[-300:]
        return False, err
    except Exception as e:
        return False, str(e)

# Impostazioni qualità
# Con maschera inpainting il denoise si applica SOLO al pavimento (zona AI libera).
# Gambe/scarpe sono protette dalla maschera → denoise alto = pavimento più trasformato.
CONFIG = {
    "test": {
        "force_rate": 8,
        "custom_width": 576,
        "custom_height": 576,
        "frame_load_cap": 48,   # 48 frame / 8fps = 6 secondi
        "loop_count": 0,
        "steps": 20,
        "cfg": 6.0,
        "denoise": 0.65,        # alto OK perché maschera protegge le gambe
        "description": "Test (576x576, 48 frame = 6 sec, denoise 0.65 con maschera)"
    },
    "medium": {
        "force_rate": 10,
        "custom_width": 640,
        "custom_height": 640,
        "frame_load_cap": 60,
        "loop_count": 0,
        "steps": 24,
        "cfg": 6.5,
        "denoise": 0.70,
        "description": "Medio (640x640, 60 frame = 6 sec, denoise 0.70 con maschera)"
    },
    "high": {
        "force_rate": 12,
        "custom_width": 768,
        "custom_height": 768,
        "frame_load_cap": 96,
        "loop_count": 0,
        "steps": 28,
        "cfg": 7.0,
        "denoise": 0.75,
        "description": "Alta qualità (768x768, 96 frame = 8 sec, denoise 0.75 con maschera)"
    }
}

# ─────────────────────────────────────────────────────
#  PROMPT BASE — serie realistica
#  Obiettivo v3: trasformare SOLO il pavimento, preservare tutto il resto.
#  La maschera inpainting garantisce che le gambe non vengano toccate.
# ─────────────────────────────────────────────────────
PROMPT_BASE = (
    "walking video, first person perspective camera looking down at feet, "
    "ground surface texture transformed, realistic floor material, "
    "photorealistic floor, natural shadows on ground, "
    "open outdoor path, no walls, no ceiling, natural lighting, "
    "consistent ground texture, clear detailed floor surface"
)

# ─────────────────────────────────────────────────────
#  PROMPT BASE — serie neon/fluo psytrance
#  Obiettivo: pavimento neon vivido su sfondo nero, nessun tunnel.
# ─────────────────────────────────────────────────────
NEON_PROMPT_BASE = (
    "walking video, first person camera looking down at ground, "
    "floor surface glowing with intense neon fluorescent colors, "
    "pitch black dark void background and surroundings, "
    "bioluminescent glowing ground patterns, UV fluorescent floor, "
    "psytrance psy-techno aesthetic, acid neon colors on black ground, "
    "open dark space with only glowing floor visible, no walls, no ceiling"
)

NEGATIVE_PROMPT = (
    "tunnel, corridor, hallway, enclosed room, walls, ceiling, "
    "fog, haze, mist, smoke, blur, bokeh, depth of field, "
    "completely different scene, new background, teleportation, "
    "extra person, crowd, face, torso, upper body, "
    "cartoon, anime, painting, illustration, CGI render, "
    "text, logo, watermark, ui, hud, "
    "low quality, artifacts, noise, grain, overexposed, underexposed"
)

NEON_NEGATIVE_PROMPT = (
    "tunnel, neon corridor, neon hallway, neon room, enclosed neon space, "
    "fog, haze, mist, smoke, blur, "
    "natural daylight, realistic outdoor colors, normal floor, "
    "completely different scene, new environment, "
    "extra person, crowd, face, torso, "
    "cartoon, anime, illustration, "
    "text, logo, watermark, "
    "low quality, artifacts, noise, grain"
)

# ─────────────────────────────────────────────────────
#  SCENARI — Serie 1: REALISTICI (suoli naturali)
#  Gambe reali, suolo trasformato in ambienti naturali
# ─────────────────────────────────────────────────────
SCENARIOS = [

    # ── SERIE REALISTICA ──────────────────────────────
    {
        "id": "forest",
        "name": "Foresta",
        "prompt_override": PROMPT_BASE,
        "negative_override": NEGATIVE_PROMPT,
        "environment": (
            "dense forest floor, dark moist soil, tree roots crossing the path, "
            "fallen leaves, green moss patches, ferns, dappled light through canopy, "
            "wild flowers at the sides, realistic forest floor texture"
        ),
        "denoise_boost": 0.0
    },
    {
        "id": "dirt_path",
        "name": "Sterrato",
        "prompt_override": PROMPT_BASE,
        "negative_override": NEGATIVE_PROMPT,
        "environment": (
            "dry dirt track, dusty earth, small stones and pebbles, "
            "dry grass edges, natural soil texture, sunbaked cracked ground"
        ),
        "denoise_boost": 0.0
    },
    {
        "id": "gravel",
        "name": "Ghiaia",
        "prompt_override": PROMPT_BASE,
        "negative_override": NEGATIVE_PROMPT,
        "environment": (
            "fine grey gravel, loose small pebbles, crushed stone surface, "
            "uniform small stones, realistic gravel texture"
        ),
        "denoise_boost": 0.0
    },
    {
        "id": "tiles",
        "name": "Piastrelle",
        "prompt_override": PROMPT_BASE,
        "negative_override": NEGATIVE_PROMPT,
        "environment": (
            "large format ceramic floor tiles, clean geometric grid pattern, "
            "light grey polished tiles, grout lines clearly visible, smooth floor"
        ),
        "denoise_boost": 0.0
    },
    {
        "id": "cobblestone",
        "name": "Ciottoli",
        "prompt_override": PROMPT_BASE,
        "negative_override": NEGATIVE_PROMPT,
        "environment": (
            "ancient cobblestone pavement, irregular rounded dark stones, "
            "wet cobbles with reflections, moss between stones, historic street"
        ),
        "denoise_boost": 0.0
    },

    # ── SERIE NEON / PSY-TECHNO ───────────────────────
    {
        "id": "neon_grid",
        "name": "Neon Grid",
        "prompt_override": NEON_PROMPT_BASE,
        "negative_override": NEON_NEGATIVE_PROMPT,
        "environment": (
            "black ground with glowing electric cyan and acid green grid lines, "
            "tron-like neon grid, pulsating neon light, deep black void, matrix energy"
        ),
        "denoise_boost": 0.08
    },
    {
        "id": "neon_jungle",
        "name": "Neon Jungle",
        "prompt_override": NEON_PROMPT_BASE,
        "negative_override": NEON_NEGATIVE_PROMPT,
        "environment": (
            "pitch black ground with fluorescent tropical roots and plants, "
            "bioluminescent ferns, UV magenta pink and lime green vegetation"
        ),
        "denoise_boost": 0.08
    },
    {
        "id": "neon_lava",
        "name": "Neon Lava",
        "prompt_override": NEON_PROMPT_BASE,
        "negative_override": NEON_NEGATIVE_PROMPT,
        "environment": (
            "black cracked volcanic ground with glowing acid green and orange lava cracks, "
            "neon molten light through dark fissures, glowing magma cracks"
        ),
        "denoise_boost": 0.10
    },
    {
        "id": "neon_circuit",
        "name": "Neon Circuit",
        "prompt_override": NEON_PROMPT_BASE,
        "negative_override": NEON_NEGATIVE_PROMPT,
        "environment": (
            "black surface with glowing neon circuit board patterns, "
            "gold and cyan electronic traces, pulsing nodes, cyberpunk psytrance"
        ),
        "denoise_boost": 0.08
    },
    {
        "id": "neon_crystals",
        "name": "Neon Crystalli",
        "prompt_override": NEON_PROMPT_BASE,
        "negative_override": NEON_NEGATIVE_PROMPT,
        "environment": (
            "black floor with fluorescent crystal formations growing from ground, "
            "electric purple violet and hot pink glowing crystals, UV bioluminescent"
        ),
        "denoise_boost": 0.10
    },
]

# ─────────────────────────────────────────────────────
#  API COMFYUI
# ─────────────────────────────────────────────────────
def api_get(endpoint):
    try:
        req = urllib.request.Request(f"{COMFY_URL}{endpoint}")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return None


def api_post(endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} da ComfyUI: {body}")


def queue_prompt(workflow):
    payload = {"prompt": workflow, "client_id": "teknosteps_video"}
    try:
        result = api_post("/prompt", payload)
        return result.get("prompt_id") if result else None
    except RuntimeError as e:
        print(f"\n  ✗ Errore invio workflow: {e}")
        return None


def wait_for_completion(prompt_id, timeout=900):
    """Aspetta il completamento (max 15 min per video)."""
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        result = api_get(f"/history/{prompt_id}")
        if result and prompt_id in result:
            entry = result[prompt_id]
            status = entry.get("status", {})
            if status.get("completed", False):
                return entry
            # Controlla errori
            messages = status.get("messages", [])
            for msg_type, msg_data in messages:
                if msg_type == "execution_error":
                    print(f"\n  ✗ Errore ComfyUI: {msg_data.get('exception_message', 'unknown')}")
                    return None
        time.sleep(3)
        dots += 1
        if dots % 5 == 0:
            elapsed = int(time.time() - start)
            print(f"    ... {elapsed}s", end="\r", flush=True)
    return None


def get_video_path(history_entry):
    """Estrae il path del video dall'history entry."""
    outputs = history_entry.get("outputs", {})
    for node_id, node_out in outputs.items():
        if "gifs" in node_out:
            for item in node_out["gifs"]:
                return item.get("filename"), item.get("subfolder", ""), item.get("type", "output")
        if "videos" in node_out:
            for item in node_out["videos"]:
                return item.get("filename"), item.get("subfolder", ""), item.get("type", "output")
    return None, None, None


# ─────────────────────────────────────────────────────
#  BUILD WORKFLOW
# ─────────────────────────────────────────────────────
def build_workflow(scenario, cfg_preset, mask_filename=None):
    """
    Costruisce il workflow ComfyUI per la generazione video.

    Se mask_filename è fornito (nome file PNG in ComfyUI/input/), il workflow
    usa la maschera inpainting: AI trasforma solo il pavimento (bianco nella maschera),
    le gambe (nero) restano identiche al sorgente.

    Se mask_filename è None, usa img2img classico sull'intero frame.
    """
    cfg = CONFIG[cfg_preset]
    denoise = round(min(cfg["denoise"] + scenario["denoise_boost"], 0.95), 3)

    prompt_base = scenario.get("prompt_override", PROMPT_BASE)
    negative    = scenario.get("negative_override", NEGATIVE_PROMPT)
    positive    = f"{prompt_base}, {scenario['environment']}"
    prefix      = f"teknosteps_{scenario['id']}"

    workflow = {
        # ── Video sorgente ────────────────────────────
        "1": {
            "class_type": "VHS_LoadVideoFFmpeg",
            "inputs": {
                "video": VIDEO_NAME,
                "force_rate": cfg["force_rate"],
                "custom_width": cfg["custom_width"],
                "custom_height": cfg["custom_height"],
                "frame_load_cap": cfg["frame_load_cap"],
                "start_time": 0,
                "meta_batch": ["11", 0]
            }
        },
        # ── Modello ───────────────────────────────────
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": MODEL}},
        # ── Condizionamento ───────────────────────────
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative,  "clip": ["2", 1]}},
        # ── Encoding in spazio latente ────────────────
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 2]}},
        # ── KSampler: usa latente con o senza maschera ─
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model":         ["2", 0],
                "positive":      ["3", 0],
                "negative":      ["4", 0],
                "latent_image":  ["13", 0] if mask_filename else ["5", 0],
                "seed":          hash(scenario["id"]) % (2**31),
                "control_after_generate": "fixed",
                "steps":         cfg["steps"],
                "cfg":           cfg["cfg"],
                "sampler_name":  "dpmpp_2m",
                "scheduler":     "karras",
                "denoise":       denoise
            }
        },
        # ── Decodifica ────────────────────────────────
        "7": {"class_type": "VAEDecode",     "inputs": {"samples": ["6", 0], "vae": ["2", 2]}},
        # ── Salva video ───────────────────────────────
        "8": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images":          ["7", 0],
                "frame_rate":      cfg["force_rate"],
                "loop_count":      cfg["loop_count"],
                "filename_prefix": prefix,
                "format":          "video/h264-mp4",
                "pingpong":        False,
                "save_output":     True,
                "meta_batch":      ["11", 0]
            }
        },
        # ── Batch manager ─────────────────────────────
        "11": {
            "class_type": "VHS_BatchManager",
            "inputs": {"frames_per_batch": cfg["frame_load_cap"]}
        }
    }

    # ── Maschera inpainting (v3) ──────────────────────
    # Solo se mask_filename è disponibile.
    # Nodo 12: carica la maschera PNG (bianco=pavimento, nero=gambe)
    # Nodo 13: applica la maschera al latent → KSampler trasforma solo il bianco
    if mask_filename:
        workflow["12"] = {
            "class_type": "LoadImageMask",
            "inputs": {
                "image":   mask_filename,   # "teknosteps_floor_mask.png" in ComfyUI/input/
                "channel": "red"            # canale da usare come maschera
            }
        }
        workflow["13"] = {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": ["5", 0],        # latent codificato da VAEEncode
                "mask":    ["12", 0]        # maschera: 1.0=trasforma, 0.0=preserva
            }
        }

    return workflow


# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────
def main():
    global MODEL
    print("=" * 62)
    print("  TEKNOSTEPS — Video Generator v2v")
    print("  NO FACES. JUST STEPS AND BASS.")
    print("=" * 62)
    print()

    # Argomento preset da riga di comando
    preset = "test"
    if len(sys.argv) > 1 and sys.argv[1] in CONFIG:
        preset = sys.argv[1]
    print(f"  Preset: {preset} — {CONFIG[preset]['description']}")
    print()

    # 1. Verifica ComfyUI
    print("▶ Connessione a ComfyUI...")
    stats = api_get("/system_stats")
    if not stats:
        print("✗ ERRORE: ComfyUI non risponde su http://127.0.0.1:8188")
        print("  → Avvia ComfyUI da Stability Matrix e riprova.")
        sys.exit(1)
    gpu = stats.get("system", {}).get("gpu_type", "N/A")
    vram_total = stats.get("system", {}).get("vram_total", 0)
    vram_free  = stats.get("system", {}).get("vram_free", 0)
    print(f"✓ Connesso! GPU: {gpu} | VRAM: {vram_free//1024//1024}MB liberi / {vram_total//1024//1024}MB totali")
    print()

    # 2. Verifica modello
    print("▶ Verifica modello...")
    models_info = api_get("/object_info/CheckpointLoaderSimple")
    if models_info:
        available = models_info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        if MODEL in available:
            print(f"✓ Modello trovato: {MODEL}")
        else:
            print(f"✗ ATTENZIONE: {MODEL} non trovato! Modelli disponibili:")
            for m in available[:5]:
                print(f"   - {m}")
            print()
            # Usa il primo modello disponibile come fallback
            if available:
                fallback = available[0]
                print(f"  → Uso fallback: {fallback}")
                MODEL = fallback
    print()

    # 3. Crea maschera inpainting pavimento
    print("▶ Creazione maschera inpainting...")
    cfg_w = CONFIG[preset]["custom_width"]
    cfg_h = CONFIG[preset]["custom_height"]
    mask_file = make_floor_mask_png(cfg_w, cfg_h, SPLIT_Y_BOT)
    if mask_file:
        split_px = int(cfg_h * SPLIT_Y_BOT)
        print(f"  ✓ Maschera creata: bianco y=0→{split_px}px (pavimento AI), "
              f"nero y={split_px}→{cfg_h}px (gambe preservate)")
    else:
        print(f"  ⚠  Maschera non creata — uso img2img senza maschera (gambe potrebbero variare)")
    print()

    # 4. Avvia generazione scenari
    print(f"▶ Generazione {len(SCENARIOS)} scenari...")
    print(f"  Output → {OUTPUT_DIR}")
    print()

    results = []
    total = len(SCENARIOS)

    # Verifica ffmpeg una sola volta prima di partire
    ffmpeg_ok = find_ffmpeg() is not None
    if ffmpeg_ok:
        print(f"  ✓ ffmpeg trovato — compositing gambe attivo (safety net)")
    else:
        print(f"  ⚠  ffmpeg non trovato — compositing disattivato")
    print()

    for idx, scenario in enumerate(SCENARIOS):
        print(f"  [{idx+1:02d}/{total}] {scenario['name']}...", end=" ", flush=True)

        try:
            workflow = build_workflow(scenario, preset, mask_filename=mask_file)
            prompt_id = queue_prompt(workflow)

            if not prompt_id:
                print("✗ errore invio")
                continue

            # Attendi completamento
            entry = wait_for_completion(prompt_id)
            if not entry:
                print("✗ timeout o errore")
                continue

            # Recupera path video dall'history
            fname, subfolder, ftype = get_video_path(entry)
            if not fname:
                fname = f"teknosteps_{scenario['id']}_00001.mp4"
                subfolder = ""
                ftype = "output"

            # Copia video AI grezzo nella cartella progetto
            comfy_video = COMFY_OUTPUT_DIR / fname
            raw_out = OUTPUT_DIR / fname
            if comfy_video.exists():
                shutil.copy2(comfy_video, raw_out)

            # ── COMPOSITING GAMBE ─────────────────────────────
            # Incolla gambe/scarpe/vestiti ORIGINALI (bottom del frame)
            # sul video AI (che ha trasformato solo l'ambiente in top)
            comp_name = f"teknosteps_{scenario['id']}_final.mp4"
            comp_out  = OUTPUT_DIR / comp_name
            composited = False

            if ffmpeg_ok and comfy_video.exists() and SOURCE_VIDEO_FULL.exists():
                ok, msg = composite_legs(
                    generated_path=comfy_video,
                    source_path=SOURCE_VIDEO_FULL,
                    output_path=comp_out,
                    width=cfg_w,
                    height=cfg_h
                )
                if ok:
                    composited = True
                    print(f"✓  → {comp_name}  [gambe originali ✓]")
                else:
                    print(f"✓  → {fname}  [compositing: {msg[:60]}]")
            elif not comfy_video.exists():
                print(f"✓ (salvato in ComfyUI/output/{fname})")
            else:
                print(f"✓  → {fname}  [compositing non disponibile]")

            results.append({
                "scenario": scenario["id"],
                "name": scenario["name"],
                "filename_raw": fname,
                "filename_final": comp_name if composited else fname,
                "composited": composited,
                "subfolder": subfolder,
                "type": ftype,
                "preset": preset
            })

        except Exception as e:
            print(f"✗ {e}")

    # 4. Riepilogo
    composited_count = sum(1 for r in results if r.get("composited"))
    print()
    print("=" * 62)
    print(f"  COMPLETATO: {len(results)}/{total} video generati")
    print(f"  Compositing gambe: {composited_count}/{len(results)} video")
    print()
    print(f"  ℹ  Video finali in:")
    print(f"     {OUTPUT_DIR}")
    print()
    for r in results:
        tag = "✓ gambe originali" if r.get("composited") else "  grezzo"
        print(f"     [{tag}] {r['filename_final']}")
    print()
    print("  Prossimi step:")
    print("  • Apri i video _final.mp4 per vedere ambiente AI + gambe originali")
    print("  • Regola SPLIT_Y_TOP/BOT nel codice se il taglio non è perfetto")
    print("  • Passa a preset 'medium' o 'high' per qualità maggiore")
    print("=" * 62)

    # Salva log
    log_file = OUTPUT_DIR / f"generation_log_{preset}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"preset": preset, "config": CONFIG[preset], "videos": results}, f, indent=2, ensure_ascii=False)
    print(f"\n  Log: {log_file}")


if __name__ == "__main__":
    import traceback
    log_path = OUTPUT_DIR / "run_log.txt"

    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files: f.flush()

    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            sys.stdout = Tee(sys.__stdout__, logf)
            main()
            sys.stdout = sys.__stdout__
    except Exception:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\n\nERRORE:\n{traceback.format_exc()}\n")
        sys.stdout = sys.__stdout__
        raise
