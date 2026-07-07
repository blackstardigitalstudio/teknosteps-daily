# -*- coding: utf-8 -*-
"""TeknoSteps - Genera la mascotte scimmietta via ComfyUI API. Made in Italy."""
import json, os, sys, time, urllib.request, urllib.parse, random

BASE = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:8188"
CKPT = sys.argv[1] if len(sys.argv) > 1 else "realismIllustriousBy_v55FP16.safetensors"
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else random.randint(1, 10**9)
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(BASE, "scimmia.png")

# stile ANIME/CARTOON (modello Illustrious)
POS = ("masterpiece, best quality, anime style, cute chibi monkey mascot character, "
       "full body, dancing pose, big sparkling eyes, happy, wearing headphones, "
       "glowing neon green accents, simple dark background, vibrant colors, clean lineart, centered")
NEG = ("worst quality, low quality, blurry, deformed, extra limbs, mutated, bad anatomy, "
       "text, watermark, signature, realistic, 3d, photo, ugly, scary")

wf = {
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
    "3": {"class_type": "KSampler", "inputs": {"seed": SEED, "steps": 26, "cfg": 5.5,
          "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0,
          "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "teknomonkey", "images": ["8", 0]}},
}


def post(path, data):
    req = urllib.request.Request(API + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def get(path):
    return json.load(urllib.request.urlopen(API + path, timeout=30))


print(f"[i] Modello: {CKPT} | seed {SEED}")
pid = post("/prompt", {"prompt": wf})["prompt_id"]
print("[i] In coda:", pid, "- genero (puo' volerci ~1-2 min su 6GB)...")
img = None
for _ in range(180):
    time.sleep(2)
    h = get(f"/history/{pid}")
    if pid in h:
        outs = h[pid]["outputs"]
        for nid, o in outs.items():
            if "images" in o:
                img = o["images"][0]
        break
if not img:
    sys.exit("[X] Nessuna immagine prodotta (timeout o errore ComfyUI)")

q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
data = urllib.request.urlopen(API + "/view?" + q, timeout=30).read()
with open(OUT, "wb") as f:
    f.write(data)
print(f"[OK] {OUT} ({len(data)/1024:.0f} KB) - Made in Italy")
