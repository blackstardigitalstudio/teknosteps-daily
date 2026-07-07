"""
GENERA MONDI — ComfyUI FRAME INTERO (no taglio, no divisione)  ·  TeknoSteps
============================================================================
Made in Italy.

Restyle a FRAME INTERO (niente maschera): un'unica immagine coerente, i TUOI piedi
stilizzati DENTRO la scena. Niente divisione a metà, niente seconda persona.
denoise 0.50 = cambia atmosfera/mondo ma mantiene piedi e camminata reali.

USO:
  1. Stability Matrix → ComfyUI → Launch (attendi http://127.0.0.1:8188)
  2. python genera_mondi_comfyui.py
  3. video_output/walk_ai_*.mp4 + frammento manifest. (Rilanciabile: salta i fatti.)

ROBUSTO per GPU 6GB: un mondo alla volta, blocchi piccoli, attese lunghe.
"""
import json, time, urllib.request, urllib.error, shutil, sys
from pathlib import Path

COMFY = "http://127.0.0.1:8188"
PROJ = Path(__file__).parent
COMFY_ROOT = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI")
COMFY_INPUT = COMFY_ROOT / "input"
COMFY_OUTPUT = COMFY_ROOT / "output"
OUTDIR = PROJ / "video_output"

SOURCE_NAME = "VID_20260527_162202.mp4"
W = H = 576            # risoluzione AFFIDABILE sui 6GB (768/1024 in video bloccano la GPU).
FPS = 12               # La morbidezza del 576 viene compensata dall'UPSCALE+SHARPEN ffmpeg (sotto).
FRAMES = 36            # ~3s a 12fps
BATCH = 2              # proven reliable (whole-frame, mai bloccato)
STEPS = 22
DENOISE = 0.50         # frame intero: coerente, piedi reali, niente divisione
UPSCALE_TO = 1080      # dopo la generazione: upscale lanczos + unsharp -> nitido a schermo
FFMPEG = None          # risolto a runtime

# Mondi neon/psichedelici (atmosfere techno) — funzionano benissimo a frame intero.
# (id, prompt, seed)
WORLDS = [
    ("tokyo",  "POV first person looking down at my own two feet walking forward on a wet neon-lit Tokyo street at night, black asphalt, green and pink neon reflections, rain puddles, cinematic, single person, my sneakers", 777),
    ("club",   "POV first person looking down at my own two feet walking forward on a glossy black nightclub floor, green laser beams, fog, strobe lights, reflections, cinematic, single person, my sneakers", 202),
    ("acid",   "POV first person looking down at my own two feet walking forward on a dark floor with psychedelic rainbow oil-slick reflections, trippy swirling colors, neon, cinematic, single person, my sneakers", 333),
    ("lava",   "POV first person looking down at my own two feet walking forward on a dark cracked floor with glowing orange and red lava in the cracks, embers, heat haze, cinematic, single person, my sneakers", 414),
    ("matrix", "POV first person looking down at my own two feet walking forward on a dark wet floor with falling green digital code reflections, cyber, neon green, rain, cinematic, single person, my sneakers", 525),
    ("ice",    "POV first person looking down at my own two feet walking forward on a frozen blue ice floor with frost and cold cyan neon light, glowing cracks, cinematic, single person, my sneakers", 636),
]
NEG = ("another person, two people, second pair of legs, extra legs, extra feet, extra shoes, "
       "duplicated shoes, pink shoes, person ahead, people walking, crowd, face, body, "
       "horizontal seam, split screen, divided in half, two halves, hard edge, "
       "deformed feet, bad anatomy, cartoon, anime, painting, text, logo, watermark")


def api(path, data=None, timeout=180, retries=2):
    last = None
    for _ in range(retries + 1):
        try:
            url = f"{COMFY}{path}"
            req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Content-Type": "application/json"} if data is not None else {})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e; time.sleep(3)
    raise last


def comfy_alive():
    try: api("/system_stats", timeout=15, retries=4); return True
    except Exception: return False


def find_ffmpeg():
    import shutil
    f = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if f: return f
    for c in [r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe",
              r"C:\Program Files\Tenorshare\Tenorshare 4DDiG\ffmpeg.exe"]:
        if Path(c).exists(): return c
    return None


def upscale_sharpen(src_mp4, dst_mp4):
    """Upscala 576 -> UPSCALE_TO con lanczos + unsharp -> nitido a tutto schermo.
       Se ffmpeg manca, copia e basta."""
    global FFMPEG
    if FFMPEG is None: FFMPEG = find_ffmpeg() or ""
    if not FFMPEG:
        shutil.copy(src_mp4, dst_mp4); return
    import subprocess
    vf = f"scale={UPSCALE_TO}:{UPSCALE_TO}:flags=lanczos,unsharp=5:5:1.0:5:5:0.0"
    cmd = [FFMPEG, "-y", "-i", str(src_mp4), "-vf", vf, "-r", str(FPS),
           "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", str(dst_mp4)]
    kw = {}
    if sys.platform == "win32": kw["creationflags"] = 0x08000000
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        shutil.copy(src_mp4, dst_mp4)


def queue_idle():
    try:
        q = api("/queue", timeout=20, retries=1)
        return not q.get("queue_running") and not q.get("queue_pending")
    except Exception:
        return False


def build_graph(prompt, seed):
    # FRAME INTERO: VAEEncode -> KSampler (niente mask).
    return {
        "1": {"class_type": "VHS_LoadVideoFFmpeg", "inputs": {
            "video": SOURCE_NAME, "force_rate": FPS, "custom_width": W, "custom_height": H,
            "frame_load_cap": FRAMES, "start_time": 0, "meta_batch": ["9", 0]}},
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "juggernautXL_ragnarokBy.safetensors"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 2]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": STEPS, "cfg": 6.5, "sampler_name": "dpmpp_2m",
            "scheduler": "karras", "denoise": DENOISE}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["2", 2]}},
        "8": {"class_type": "VHS_VideoCombine", "inputs": {
            "images": ["7", 0], "frame_rate": FPS, "loop_count": 0,
            "filename_prefix": f"teknosteps_wf_{seed}",
            "format": "video/h264-mp4", "pingpong": False, "save_output": True,
            "meta_batch": ["9", 0]}},
        "9": {"class_type": "VHS_BatchManager", "inputs": {"frames_per_batch": BATCH}},
    }


def wait_for_file(seed, since, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        cands = [p for p in COMFY_OUTPUT.glob(f"teknosteps_wf_{seed}*.mp4")
                 if p.stat().st_mtime >= since - 2]
        if cands and queue_idle():
            return max(cands, key=lambda p: p.stat().st_mtime)
        time.sleep(4)
    return None


def manifest_entry(wid, dst):
    dur = round(FRAMES / FPS, 2)
    return {"scenario": f"ai_{wid}", "name": wid.capitalize(), "file": f"video_output/{dst.name}",
            "loopDuration": dur, "fps": FPS, "stepsPerLoop": max(2, int(round(1.57 * dur))),
            "beatPhaseOffset": 0.0, "tags": ["ai", wid]}


def main():
    print("=" * 64)
    print("  GENERA MONDI — FRAME INTERO (no taglio, no divisione)")
    print("=" * 64)
    if not comfy_alive():
        print("\n  X ComfyUI non risponde. Avvialo da Stability Matrix (Launch).")
        return
    if not (COMFY_INPUT / SOURCE_NAME).exists() and (PROJ / SOURCE_NAME).exists():
        shutil.copy(PROJ / SOURCE_NAME, COMFY_INPUT / SOURCE_NAME)
    OUTDIR.mkdir(exist_ok=True)
    print(f"  ComfyUI OK · {len(WORLDS)} mondi @ {W}x{H} {FRAMES}f denoise {DENOISE} — uno alla volta\n")

    videos = []
    for wid, prompt, seed in WORLDS:
        dst = OUTDIR / f"walk_ai_{wid}.mp4"
        if dst.exists():
            print(f"  [{wid}] già presente, salto."); videos.append(manifest_entry(wid, dst)); continue
        for _ in range(30):
            if queue_idle(): break
            time.sleep(4)
        print(f"  [{wid}] invio... ", end="", flush=True)
        since = time.time()
        try:
            res = api("/prompt", {"prompt": build_graph(prompt, seed)}, timeout=60, retries=2)
        except Exception as e:
            print(f"X errore invio: {e}"); continue
        print(f"in coda ({res.get('prompt_id','')[:8]}), genero...", flush=True)
        out = wait_for_file(seed, since, timeout=900)
        if out:
            upscale_sharpen(out, dst)   # 576 -> 1080 nitido
            print(f"        OK -> {dst.name}  ({dst.stat().st_size/1024/1024:.1f} MB, upscalato+nitidezza)")
            videos.append(manifest_entry(wid, dst))
        else:
            print(f"        X timeout/nessun file per {wid}")
        # libera la VRAM tra un mondo e l'altro (evita accumulo -> hang sui 6GB)
        try: api("/free", {"unload_models": True, "free_memory": True}, timeout=20, retries=0)
        except Exception: pass
        time.sleep(8)

    if videos:
        frag = OUTDIR / "videos_AI_manifest_fragment.json"
        frag.write_text(json.dumps({"videos": videos}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  FATTO: {len(videos)} mondi. Frammento: {frag.name}")
    print("=" * 64)


if __name__ == "__main__":
    main()
