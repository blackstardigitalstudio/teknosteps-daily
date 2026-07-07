"""
TEKNOSTEPS - Generatore Immagini Walking Loop
=============================================
Script per generare le 15-20 coppie start/end frame dei video walking loop.
Usa l'API di ComfyUI (deve essere in esecuzione su http://127.0.0.1:8188)

UTILIZZO:
  1. Assicurati che ComfyUI sia avviato via Stability Matrix
  2. Doppio click su questo file  (oppure: python genera_immagini_walking.py)
  3. Lo script mostra i modelli disponibili e genera le immagini automaticamente
  4. Le immagini vengono salvate in: ./output_walking_images/
"""

import json
import urllib.request
import urllib.error
import random
import time
import os
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────
#  CONFIGURAZIONE
# ─────────────────────────────────────────────────────────────
COMFY_URL  = "http://127.0.0.1:8188"
OUTPUT_DIR = Path(__file__).parent / "output_walking_images"
OUTPUT_DIR.mkdir(exist_ok=True)

# Dimensioni immagine – portrait verticale per mobile/web
IMG_WIDTH  = 768
IMG_HEIGHT = 1344

# Parametri generazione
# DreamShaper XL Lightning → CFG basso, pochi step!
STEPS      = 6
CFG        = 2.0
SAMPLER    = "dpm_2_ancestral"
SCHEDULER  = "karras"

# ─────────────────────────────────────────────────────────────
#  20 SCENARI GLOBALI  (superficie / location)
# ─────────────────────────────────────────────────────────────
SCENARIOS = [
    ("tokyo_rain",        "rain-soaked Tokyo street asphalt at night, neon reflections in puddles, wet pavement"),
    ("morocco_tiles",     "colorful Moroccan mosaic tiles, medina souk floor, terracotta and cobalt blue"),
    ("brazil_beach",      "wet tropical beach sand, shallow turquoise water, foam, Rio beach"),
    ("paris_cobble",      "old Parisian cobblestones, Seine riverside, classic European street"),
    ("nordic_snow",       "crisp white snow, ice crystals, frozen Scandinavian path"),
    ("india_temple",      "ancient Indian temple stone floor, ornate carvings, sacred geometry patterns"),
    ("nyc_subway",        "New York subway platform floor, yellow safety line, urban grit"),
    ("japan_bamboo",      "bamboo forest floor, fallen leaves, mossy earth, Japan"),
    ("dubai_sand",        "golden desert sand dunes, Dubai, fine sand grains, hot dry"),
    ("amsterdam_bridge",  "Amsterdam canal bridge stone, wet moss, bicycle lane markings"),
    ("mexico_flores",     "Dia de los Muertos flower petals, marigold orange, colorful offerings"),
    ("hongkong_neon",     "Hong Kong night market floor, neon signs reflected on wet tiles"),
    ("sahara_rock",       "Sahara rocky desert ground, ancient orange sand and stone"),
    ("iceland_lava",      "Icelandic black volcanic lava rock, moss, mist, dramatic landscape"),
    ("venice_water",      "Venice acqua alta flooded stone floor, shallow water, ancient pavement"),
    ("africa_earth",      "African savanna red earth, dry cracked soil, sparse grass"),
    ("korea_palace",      "Korean traditional palace wooden floor, Joseon dynasty, lacquered wood"),
    ("amazon_jungle",     "Amazon jungle floor, tropical leaves, roots, dark moist soil"),
    ("manhattan_marble",  "luxury Manhattan lobby polished marble floor, geometric pattern"),
    ("greece_white",      "Greek island white marble terrace, Santorini blue dome visible"),
]

# ─────────────────────────────────────────────────────────────
#  STILE PSICHEDELICO / NEON  (costante in tutti gli scenari)
# ─────────────────────────────────────────────────────────────
STYLE_POSITIVE = (
    "psychedelic neon color grading, fluorescent light leaks, vivid surreal atmosphere, "
    "artistic double exposure overlay, chromatic aberration, glitch art elements, "
    "ultra-detailed, sharp focus, cinematic lighting, professional photography"
)

STYLE_NEGATIVE = (
    "upper body, torso, face, head, hands, arms, background people, blurry, "
    "low quality, bad anatomy, deformed, watermark, text, logo, nsfw, ugly"
)

# Base della gamba – uguale per tutti gli scenari
LEG_BASE = (
    "top-down perspective looking down at human legs and feet walking, "
    "camera angle from waist height pointing down, only legs visible from knees down, "
    "realistic human legs, stylish sneakers and jeans"
)

# ─────────────────────────────────────────────────────────────
#  FUNZIONI API COMFYUI
# ─────────────────────────────────────────────────────────────
def api_get(endpoint):
    try:
        req = urllib.request.Request(f"{COMFY_URL}{endpoint}")
        with urllib.request.urlopen(req, timeout=10) as resp:
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_available_models():
    info = api_get("/object_info/CheckpointLoaderSimple")
    if not info:
        return []
    try:
        return info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except (KeyError, IndexError):
        return []


def get_history(prompt_id):
    result = api_get(f"/history/{prompt_id}")
    return result if result else {}


def build_workflow(model_name, positive_prompt, negative_prompt, seed, filename_prefix):
    """Costruisce il workflow ComfyUI classico text-to-image."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": model_name}
        },
        "2": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": IMG_WIDTH,
                "height": IMG_HEIGHT,
                "batch_size": 1
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": positive_prompt
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": negative_prompt
            }
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["2", 0],
                "seed": seed,
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": SAMPLER,
                "scheduler": SCHEDULER,
                "denoise": 1.0
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": filename_prefix,
                "images": ["6", 0]
            }
        }
    }


def queue_prompt(workflow):
    payload = {"prompt": workflow, "client_id": "teknosteps_script"}
    result = api_post("/prompt", payload)
    return result.get("prompt_id")


def wait_for_completion(prompt_id, timeout=300):
    """Attende il completamento con polling ogni 2 secondi."""
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(prompt_id)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    return None


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  TEKNOSTEPS — Generatore Immagini Walking Loop")
    print("=" * 60)
    print()

    # 1. Verifica connessione a ComfyUI
    print("▶ Verifica connessione a ComfyUI...")
    system_info = api_get("/system_stats")
    if system_info is None:
        print("✗ ERRORE: Impossibile connettersi a ComfyUI su http://127.0.0.1:8188")
        print("  → Assicurati che ComfyUI sia avviato tramite Stability Matrix")
        sys.exit(1)
    print(f"✓ Connesso! GPU: {system_info.get('system', {}).get('gpu_type', 'N/A')}")

    # 2. Trova modelli disponibili
    print()
    print("▶ Ricerca modelli disponibili...")
    models = get_available_models()

    if not models:
        print("✗ Nessun modello trovato nella cartella Checkpoints!")
        print()
        print("  SOLUZIONE: Scarica un modello tramite Stability Matrix:")
        print("  1. Apri Stability Matrix")
        print("  2. Clicca su 'Model Browser' nella barra sinistra")
        print("  3. Cerca 'SDXL' o 'dreamshaper' e scaricalo")
        print("  4. Oppure usa il ComfyUI Manager per scaricare direttamente")
        print()
        print("  Modelli consigliati per RTX 3060 6GB:")
        print("  • DreamShaper XL (ottimo per stili artistici)")
        print("  • SDXL Base 1.0 (qualità alta)")
        print("  • RealVisXL (fotorealistico)")
        sys.exit(1)

    print(f"✓ Trovati {len(models)} modelli:")
    for i, m in enumerate(models):
        print(f"   [{i+1}] {m}")

    # 3. Selezione modello (auto - primo disponibile, preferibilmente DreamShaper)
    print()
    dreamshaper = [m for m in models if "dreamshaper" in m.lower()]
    selected_model = dreamshaper[0] if dreamshaper else models[0]
    print(f"▶ Modello selezionato: {selected_model}")

    # 4. Generazione
    print()
    print(f"▶ Avvio generazione di {len(SCENARIOS) * 2} immagini ({len(SCENARIOS)} coppie start+end)...")
    print(f"  Output → {OUTPUT_DIR}")
    print()

    results = []
    total = len(SCENARIOS) * 2
    count = 0

    for scenario_id, (name, surface_desc) in enumerate(SCENARIOS):
        for frame_type in ["start", "end"]:
            count += 1

            # Seed diverso per start e end ma deterministico per riproducibilità
            seed = (scenario_id * 1000) + (0 if frame_type == "start" else 500)

            # Prompts
            # Per il frame END cambiamo leggermente la posizione del passo
            step_desc = (
                "mid-stride left foot forward right foot back"
                if frame_type == "start"
                else "mid-stride right foot forward left foot back"
            )

            positive = f"{LEG_BASE}, {step_desc}, walking on {surface_desc}, {STYLE_POSITIVE}"
            negative = STYLE_NEGATIVE
            filename_prefix = f"teknosteps_walk_{name}_{frame_type}"

            print(f"  [{count:02d}/{total}] {name}_{frame_type}...", end=" ", flush=True)

            try:
                wf = build_workflow(selected_model, positive, negative, seed, filename_prefix)
                prompt_id = queue_prompt(wf)

                if not prompt_id:
                    print("✗ errore invio")
                    continue

                result = wait_for_completion(prompt_id)
                if result:
                    # Recupera i file generati
                    outputs = result.get("outputs", {})
                    for node_id, node_out in outputs.items():
                        if "images" in node_out:
                            for img in node_out["images"]:
                                results.append({
                                    "scenario": name,
                                    "frame": frame_type,
                                    "filename": img["filename"],
                                    "subfolder": img.get("subfolder", ""),
                                })
                    print("✓")
                else:
                    print("✗ timeout")

            except Exception as e:
                print(f"✗ {e}")

    # 5. Riepilogo
    print()
    print("=" * 60)
    print(f"  COMPLETATO: {len(results)}/{total} immagini generate")
    print(f"  Salvate in: {OUTPUT_DIR.parent}/ComfyUI/output/")
    print()
    print("  NOTA: Le immagini sono nella cartella output di ComfyUI.")
    print("  Path tipico: C:\\Users\\stell\\Downloads\\StabilityMatrix-win-x64 (1)")
    print("               \\Data\\Packages\\ComfyUI\\output\\")
    print()
    print("  Prossimo step: usa queste immagini per generare i video loop")
    print("  con Kling AI, RunwayML o ComfyUI AnimateDiff.")
    print("=" * 60)

    # Salva log
    log_file = OUTPUT_DIR / "generazione_log.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"model": selected_model, "images": results}, f, indent=2, ensure_ascii=False)
    print(f"\n  Log salvato: {log_file}")

    input("\nPremi INVIO per chiudere...")


if __name__ == "__main__":
    import traceback
    log_path = OUTPUT_DIR / "run_log.txt"
    # Redirect stdout anche su file per debug
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()
    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            import sys as _sys
            orig_stdout = _sys.stdout
            _sys.stdout = Tee(orig_stdout, logf)
            main()
            _sys.stdout = orig_stdout
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\n\nERRORE FATALE:\n{traceback.format_exc()}\n")
        raise
