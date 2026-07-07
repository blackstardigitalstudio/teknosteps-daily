"""
Script diagnostico - controlla la history di ComfyUI
e cerca le immagini generate.
"""
import json
import urllib.request
import os
import glob
from pathlib import Path

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT = Path(__file__).parent / "output_walking_images" / "diagnosi_output.txt"

def api_get(endpoint):
    try:
        req = urllib.request.Request(f"{COMFY_URL}{endpoint}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

lines = []
def log(s=""):
    print(s)
    lines.append(s)

log("=== DIAGNOSI COMFYUI ===")
log()

# 1. System stats
stats = api_get("/system_stats")
log(f"System stats GPU: {stats.get('system', {}).get('gpu_type', 'N/A')}")
log()

# 2. History completa (ultimi 10 elementi)
log("=== HISTORY (ultimi job) ===")
history = api_get("/history?max_items=5")
if "error" in history:
    log(f"Errore: {history['error']}")
else:
    for pid, entry in list(history.items())[:5]:
        log(f"\nPrompt ID: {pid}")
        outputs = entry.get("outputs", {})
        status = entry.get("status", {})
        log(f"  Status: {status.get('status_str', 'unknown')}")
        log(f"  Outputs keys: {list(outputs.keys())}")
        for node_id, node_out in outputs.items():
            log(f"    Node {node_id}: {list(node_out.keys())}")
            if "images" in node_out:
                for img in node_out["images"]:
                    log(f"      Image: {img}")

log()

# 3. Queue status
log("=== QUEUE STATUS ===")
queue = api_get("/queue")
pending = queue.get("queue_pending", [])
running = queue.get("queue_running", [])
log(f"In coda: {len(pending)}, In esecuzione: {len(running)}")
log()

# 4. Cerca file PNG recenti nel sistema
log("=== RICERCA PNG RECENTI (teknosteps) ===")
search_paths = [
    r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data",
    r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI",
]
found = []
for base in search_paths:
    for root, dirs, files in os.walk(base):
        for f in files:
            if "teknosteps" in f.lower() and f.endswith(".png"):
                full = os.path.join(root, f)
                found.append(full)
                log(f"  TROVATA: {full}")

if not found:
    log("  Nessuna immagine teknosteps trovata!")
    log()
    # Cerca qualsiasi PNG recente
    log("=== PNG GENERICI RECENTI ===")
    for base in search_paths:
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".png"):
                    full = os.path.join(root, f)
                    # Controlla se modificato di recente (oggi)
                    try:
                        import time
                        mtime = os.path.getmtime(full)
                        today = time.time() - 86400
                        if mtime > today:
                            log(f"  PNG recente: {full}")
                    except:
                        pass

log()
log("=== FINE DIAGNOSI ===")

OUTPUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nSalvato in: {OUTPUT}")
input("\nPremi INVIO per chiudere...")
