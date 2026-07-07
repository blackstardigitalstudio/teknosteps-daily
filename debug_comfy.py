"""
Debug script: invia un workflow minimo a ComfyUI e mostra l'errore preciso.
"""
import json, urllib.request, urllib.error

COMFY_URL = "http://127.0.0.1:8188"

def api_get(endpoint):
    try:
        with urllib.request.urlopen(f"{COMFY_URL}{endpoint}", timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"GET {endpoint} -> ERRORE: {e}")
        return None

def api_post_debug(endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  COMFYUI DEBUG")
print("=" * 60)

# 1. Nodi VHS disponibili
print("\n[1] Nodi VHS installati:")
obj_info = api_get("/object_info")
if obj_info:
    vhs = [k for k in obj_info.keys() if "VHS" in k or "Video" in k.upper()]
    for v in sorted(vhs):
        print(f"   {v}")
else:
    print("   ERRORE: impossibile ottenere object_info")

# 2. Parametri VHS_LoadVideoFFmpeg
print("\n[2] Parametri VHS_LoadVideoFFmpeg:")
ffmpeg_info = api_get("/object_info/VHS_LoadVideoFFmpeg")
if ffmpeg_info:
    node = ffmpeg_info.get("VHS_LoadVideoFFmpeg", {})
    inputs = node.get("input", {})
    print(f"   required: {list(inputs.get('required', {}).keys())}")
    print(f"   optional: {list(inputs.get('optional', {}).keys())}")
    # force_size valori
    req = inputs.get("required", {})
    if "force_size" in req:
        print(f"   force_size options: {req['force_size']}")
else:
    print("   NON DISPONIBILE")

# 3. Parametri VHS_VideoCombine
print("\n[3] Parametri VHS_VideoCombine:")
combine_info = api_get("/object_info/VHS_VideoCombine")
if combine_info:
    node = combine_info.get("VHS_VideoCombine", {})
    inputs = node.get("input", {})
    req = inputs.get("required", {})
    print(f"   required: {list(req.keys())}")
    if "format" in req:
        print(f"   format options: {req['format']}")
else:
    print("   NON DISPONIBILE")

# 4. Parametri VHS_BatchManager
print("\n[4] VHS_BatchManager disponibile:", "SI" if api_get("/object_info/VHS_BatchManager") else "NO")

# 5. Video in input
print("\n[5] Video sorgente:")
files_info = api_get("/object_info/VHS_LoadVideoFFmpeg")
import os
comfy_input = r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI\input"
video = os.path.join(comfy_input, "VID_20260527_162202.mp4")
print(f"   Path: {video}")
print(f"   Esiste: {os.path.exists(video)}")

# 6. Test workflow minimo (solo KSampler image, no video)
print("\n[6] Test invio workflow minimo (img2img statico):")
test_workflow = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "juggernautXL_ragnarokBy.safetensors"}
    }
}
result, err = api_post_debug("/prompt", {"prompt": test_workflow, "client_id": "debug"})
if err:
    print(f"   ERRORE: {err[:500]}")
else:
    print(f"   OK: {result}")

print("\n[FINE DEBUG]")
