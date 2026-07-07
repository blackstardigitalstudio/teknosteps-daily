"""
GENERA PAVIMENTI — TeknoSteps  ·  Made in Italy.
================================================
IL FORMAT: piedi veri che camminano all'infinito su TANTISSIMI pavimenti diversi.

Restyle a FRAME INTERO (niente maschera -> niente divisione, niente seconda persona):
cambia SOLO il pavimento sotto i piedi, i piedi restano reali. denoise 0.65.
Genera a 576 (risoluzione affidabile sui 6GB) e poi UPSCALE+SHARPEN a 1080 con ffmpeg
-> nitido a tutto schermo. Un pavimento alla volta, libera la VRAM tra uno e l'altro.

USO:
  1. Avvia ComfyUI (Stability Matrix -> Launch). Attendi http://127.0.0.1:8188.
  2. python genera_pavimenti.py
  3. video_output/walk_floor_*.mp4 + frammento manifest. (Rilanciabile: salta i fatti.)
"""
import json, time, http.client, glob, os, subprocess, sys, shutil
from pathlib import Path

HOST, PORT = "127.0.0.1", 8188
PROJ = Path(__file__).parent
COMFY_ROOT = Path(r"C:\Users\stell\Downloads\StabilityMatrix-win-x64 (1)\Data\Packages\ComfyUI")
COMFY_INPUT = COMFY_ROOT / "input"
COMFY_OUTPUT = COMFY_ROOT / "output"
OUTDIR = PROJ / "video_output"
SOURCE_NAME = "VID_20260527_162202.mp4"

W = H = 576
FPS = 24            # FLUIDO (prima era 12 = scattoso). 24fps -> gambe fluide + meno flicker.
FRAMES = 48        # ~2s a 24fps. NON in un colpo: generati in CHUNK piccoli (vedi CHUNK) -> ogni
                   # job sta comodo nei 6GB. Il modello resta in VRAM tra i chunk = veloce.
CHUNK  = 6         # frame per mini-job (verificato: 6 stanno nei 6GB senza crash). Il totale FRAMES
                   # e' fatto in ceil(FRAMES/CHUNK) job, poi assemblo i PNG in un unico mp4.
XF = 0.35          # crossfade coda->testa (s) per un LOOP SEAMLESS (niente scatto/passo doppio)
BATCH = 2
STEPS = 20
DENOISE = 0.50     # PIEDI consistenti (0.65 li "morphava" = piedi storti). 0.50 li tiene fedeli.
UPSCALE_TO = 1080

# TANTISSIMI pavimenti diversi (texture del suolo). id, descrizione-pavimento, seed.
FLOORS = [
    ("wood",        "a rustic wooden boardwalk with weathered planks", 111),
    ("cobblestone", "an old wet cobblestone street", 122),
    ("marble",      "a polished white marble floor with grey veins", 133),
    ("neongrid",    "a dark glossy floor with a glowing neon grid, cyberpunk", 144),
    ("sand",        "desert sand with wind ripples", 155),
    ("grass",       "lush green grass field", 166),
    ("metal",       "industrial metal checker plate flooring, rivets", 177),
    ("tiles",       "colorful geometric mosaic ceramic tiles", 188),
    ("lava",        "black volcanic rock with glowing orange lava cracks", 199),
    ("ice",         "frozen blue ice with white cracks and frost", 210),
    ("leaves",      "autumn forest floor covered in orange fallen leaves", 221),
    ("concrete",    "cracked grey concrete with faded paint markings", 232),
    ("carpet",      "an ornate red persian carpet pattern", 243),
    ("circuit",     "a glowing green circuit board floor, techno", 254),
    ("brick",       "red brick pavement, herringbone pattern", 265),
    ("asphalt",     "wet black asphalt road with white lane markings at night, neon reflections", 276),
    ("water",       "shallow clear water over smooth pebbles, gentle ripples and reflections", 287),
    ("snow",        "fresh white snow with a crisp sparkling surface", 298),
    ("gold",        "a polished reflective gold metal floor, luxury sheen", 309),
    ("disco",       "a mirrored disco dancefloor reflecting colorful lights", 320),
    ("clouds",      "soft white fluffy clouds under a bright blue sky, dreamy", 331),
    ("moss",        "green mossy wet stone path in a forest", 342),
    ("crackedearth","cracked dry desert earth, drought pattern", 353),
    ("galaxy",      "a deep space starfield with a purple nebula, cosmic floor", 364),
    ("blossom",     "pink cherry blossom petals scattered on dark ground", 375),
    ("hexagon",     "a sci-fi glowing blue hexagonal tech floor, futuristic", 386),
]
NEG = ("blurry, soft, flicker, morphing shoes, changing shoes, distorted feet, twisted feet, "
       "another person, two people, second pair of legs, extra legs, extra feet, extra shoes, "
       "duplicated shoes, pink shoes, person ahead, people walking, crowd, face, body, "
       "horizontal seam, split screen, divided in half, hard edge, deformed feet, bad anatomy, "
       "cartoon, anime, painting, text, logo, watermark")

# ffmpeg VERO con libx264: preferisci quello di sistema, poi il binario imageio_ffmpeg del
# venv ComfyUI (verificato: encoda libx264), infine lo stub Wondershare come ultima spiaggia.
_imgio = glob.glob(str(COMFY_ROOT / "venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win*.exe"))
FFMPEG = shutil.which("ffmpeg") or (_imgio[0] if _imgio else r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe")


def call(method, path, body=None, timeout=60):
    c = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    try:
        if body is None:
            c.request(method, path)
        else:
            c.request(method, path, json.dumps(body), {"Content-Type": "application/json"})
        r = c.getresponse(); data = r.read()
        return json.loads(data) if data else {}
    finally:
        c.close()


def alive():
    try: call("GET", "/system_stats", timeout=10); return True
    except Exception: return False


COMFY_PY = COMFY_ROOT / "venv" / "Scripts" / "python.exe"


def restart_comfy():
    """Riavvia ComfyUI in una console vera (stdio reale -> niente crash OpenSSL).
    NIENTE --lowvram: con tanta RAM, ComfyUI tiene il modello in RAM pinned (cache
    veloce) e fa offload intelligente -> generazione molto più rapida e stabile."""
    # --lowvram è NECESSARIO sui 6GB. Lancio python con CREATE_NEW_CONSOLE: alloca una
    # console VERA (stdio reale -> niente crash OpenSSL), anche se il padre è staccato.
    if alive():
        # GUARDIA: NON riavviare mai sopra un'istanza gia' viva -> due ComfyUI sulla stessa
        # GPU corrompono il contesto CUDA (cudaErrorUnknown). Se risponde, si aspetta e basta.
        print("    (ComfyUI gia' vivo: niente riavvio, aspetto)", flush=True); return
    print("    ! ComfyUI giu' -> riavvio (lowvram, console nuova)...", flush=True)
    try:
        subprocess.Popen([str(COMFY_PY), "main.py", "--listen", "127.0.0.1",
                          "--port", "8188", "--lowvram"],
                         cwd=str(COMFY_ROOT),
                         creationflags=0x00000010 if sys.platform == "win32" else 0)  # CREATE_NEW_CONSOLE
    except Exception as e:
        print("    ! restart err:", e, flush=True)


def ensure_comfy(boot_wait=180, tries=3):
    if alive(): return True
    for _ in range(tries):
        restart_comfy()
        t0 = time.time()
        while time.time() - t0 < boot_wait:
            time.sleep(5)
            if alive(): time.sleep(3); return True
        print("    ! boot non riuscito, ritento...", flush=True)
    return alive()


def idle():
    try:
        q = call("GET", "/queue", timeout=15)
        return not q.get("queue_running") and not q.get("queue_pending")
    except Exception:
        return False


def prompt_text(floor):
    return (f"POV first person looking straight down at my own two feet walking forward on {floor}, "
            "sharp focus, highly detailed texture, cinematic, single person, consistent dark sneakers")


def graph(floor, seed, skip, cap):
    # CHUNK: carico solo 'cap' frame a partire da 'skip' -> pochi frame per job = sta nei 6GB
    # SENZA meta_batch (che richiedeva VHS_VideoCombine, il cui ffmpeg si rompe). SaveImage -> PNG.
    return {
        "1": {"class_type": "VHS_LoadVideoFFmpeg", "inputs": {
            "video": SOURCE_NAME, "force_rate": FPS, "custom_width": W, "custom_height": H,
            "frame_load_cap": cap, "skip_first_frames": skip, "start_time": 0}},
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "juggernautXL_ragnarokBy.safetensors"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text(floor), "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 1]}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 2]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
            "seed": seed, "steps": STEPS, "cfg": 6.5, "sampler_name": "dpmpp_2m",
            "scheduler": "karras", "denoise": DENOISE}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["2", 2]}},
        # SaveImage: nome col numero di chunk padded -> ordinamento corretto in assemblaggio.
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"ts_pav_{seed}_c{skip:03d}"}},
    }


def sharpen(src, dst):
    vf = f"scale={UPSCALE_TO}:{UPSCALE_TO}:flags=lanczos,unsharp=5:5:1.0:5:5:0.0"
    kw = {"capture_output": True}
    if sys.platform == "win32": kw["creationflags"] = 0x08000000
    r = subprocess.run([FFMPEG, "-y", "-i", str(src), "-vf", vf, "-r", str(FPS),
                        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", str(dst)], **kw)
    if r.returncode != 0: shutil.copy(src, dst)


def make_seamless(path):
    """LOOP SEAMLESS: crossfada gli ultimi XF sec sull'inizio -> il punto di giunzione
    del loop diventa invisibile (niente scatto/passo doppio). Metodo overlay+fade,
    compatibile col ffmpeg Wondershare (che non ha 'xfade'). La clip risultante dura
    (FRAMES/FPS - XF); loopDuration in entry() lo tiene in conto."""
    d = FRAMES / FPS
    tmp = str(path) + ".seam.mp4"
    fc = ("[0]trim=0:%f,setpts=PTS-STARTPTS[bd];"
          "[0]trim=%f:%f,setpts=PTS-STARTPTS,format=yuva420p,fade=t=out:st=0:d=%f:alpha=1[tl];"
          "[bd][tl]overlay=0:0,fps=%d,format=yuv420p[o]" % (d - XF, d - XF, d, XF, FPS))
    kw = {"capture_output": True}
    if sys.platform == "win32": kw["creationflags"] = 0x08000000
    r = subprocess.run([FFMPEG, "-y", "-i", str(path), "-filter_complex", fc, "-map", "[o]",
                        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                        "-movflags", "+faststart", tmp], **kw)
    if r.returncode == 0 and os.path.exists(tmp):
        shutil.move(tmp, str(path))


def wait_chunk(seed, skip, cap, since, timeout=180):
    """Aspetta che il mini-job (chunk) finisca: ComfyUI idle + i 'cap' PNG del chunk presenti.
    Ritorna True se ok, False se scade/crasha."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not alive():
            return False
        n = len([p for p in COMFY_OUTPUT.glob(f"ts_pav_{seed}_c{skip:03d}_*.png") if p.stat().st_mtime >= since - 2])
        if n >= cap and idle():
            return True
        time.sleep(3)
    return False


def assemble(frames, raw):
    """Compone i PNG (in ordine) in un mp4 grezzo con ffmpeg (concat demuxer)."""
    lst = raw + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        for p in frames:
            f.write("file '%s'\n" % str(p).replace("\\", "/"))
            f.write("duration %f\n" % (1.0 / FPS))
        f.write("file '%s'\n" % str(frames[-1]).replace("\\", "/"))   # concat vuole l'ultimo ripetuto
    kw = {"capture_output": True}
    if sys.platform == "win32": kw["creationflags"] = 0x08000000
    r = subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-r", str(FPS),
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", raw], **kw)
    try: os.remove(lst)
    except Exception: pass
    return raw if (r.returncode == 0 and os.path.exists(raw)) else None


def _unused_wait_file(seed, since, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        cands = [p for p in COMFY_OUTPUT.glob(f"ts_pav_{seed}*.mp4") if p.stat().st_mtime >= since - 2]
        if cands and idle():
            return max(cands, key=lambda p: p.stat().st_mtime)
        time.sleep(8)
    return None


def entry(fid, dst):
    # LOOP NATURALE (niente crossfade): la clip e' 48 frame dalla STESSA sorgente di wood,
    # quindi stessa andatura -> stessi parametri di wood (2.0s, 2.67 passi/loop) = cammina bene.
    dur = round(FRAMES / FPS, 2)           # durata piena, non tagliata
    return {"scenario": f"floor_{fid}", "name": fid.capitalize(), "file": f"video_output/{dst.name}",
            "loopDuration": dur, "fps": FPS, "stepsPerLoop": round(FRAMES / 18.0, 2),
            "beatPhaseOffset": 0.0, "tags": ["pavimento", fid]}


def main():
    print("=" * 64); print("  GENERA PAVIMENTI — tanti pavimenti diversi, frame intero, nitidi")
    print("=" * 64)
    if not ensure_comfy():
        print("\n  X ComfyUI non avviabile. Riprovo più tardi."); return
    if not (COMFY_INPUT / SOURCE_NAME).exists() and (PROJ / SOURCE_NAME).exists():
        shutil.copy(PROJ / SOURCE_NAME, COMFY_INPUT / SOURCE_NAME)
    OUTDIR.mkdir(exist_ok=True)
    print(f"  {len(FLOORS)} pavimenti @ {W} -> {UPSCALE_TO} nitido · denoise {DENOISE} · uno alla volta\n")
    videos = []
    for fid, floor, seed in FLOORS:
        dst = OUTDIR / f"walk_floor_{fid}.mp4"
        if dst.exists():
            print(f"  [{fid}] già presente, salto."); videos.append(entry(fid, dst)); continue

        ok = False
        if not ensure_comfy():
            print(f"  [{fid}] ComfyUI non recuperabile, salto."); continue
        # pulisci PNG vecchi di questo seed (run/retry precedenti)
        for old in COMFY_OUTPUT.glob(f"ts_pav_{seed}_c*.png"):
            try: old.unlink()
            except Exception: pass
        n_chunks = (FRAMES + CHUNK - 1) // CHUNK
        print(f"  [{fid}] {FRAMES}f in {n_chunks} chunk da {CHUNK}: ", end="", flush=True)
        allok = True
        for ci, skip in enumerate(range(0, FRAMES, CHUNK)):
            cap = min(CHUNK, FRAMES - skip)
            for _ in range(30):                    # aspetta idle prima del chunk
                if idle(): break
                time.sleep(2)
            since = time.time()
            try:
                call("POST", "/prompt", {"prompt": graph(floor, seed, skip, cap)})
            except Exception as e:
                print(f"[X invio {str(e)[:40]}]", end=" ", flush=True); allok = False; break
            # 1o chunk in assoluto = carica il modello a freddo (SDXL su 6GB, puo' volerci ~2min):
            # timeout largo per non far fallire il cold-start; i chunk dopo sono veloci.
            if wait_chunk(seed, skip, cap, since, timeout=300):
                print(f"{skip+cap}", end=" ", flush=True)
            else:
                print(f"[X chunk@{skip}]", end=" ", flush=True); allok = False; break
        # assembla i PNG di tutti i chunk (ordinati per nome = ordine temporale)
        frames = sorted(COMFY_OUTPUT.glob(f"ts_pav_{seed}_c*_*.png"))
        if allok and len(frames) >= int(FRAMES * 0.9):
            raw = str(OUTDIR / f"_raw_{fid}.mp4")
            if assemble(frames, raw):
                sharpen(raw, dst)                  # 576 -> 1080 nitido (loop naturale 48f, NO crossfade)
                try: os.remove(raw)
                except Exception: pass
                for p in frames:
                    try: p.unlink()
                    except Exception: pass
                print(f"-> OK {dst.name} ({dst.stat().st_size/1024/1024:.1f} MB, {len(frames)}f)")
                videos.append(entry(fid, dst)); ok = True
            else:
                print("-> X assemblaggio ffmpeg fallito")
        else:
            print(f"-> X incompleto ({len(frames)}/{FRAMES} frame)")
        time.sleep(2)
    if videos:
        frag = OUTDIR / "videos_PAVIMENTI_fragment.json"
        frag.write_text(json.dumps({"videos": videos}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  FATTO: {len(videos)}/{len(FLOORS)} pavimenti. Frammento: {frag.name}")
    print("=" * 64)


if __name__ == "__main__":
    main()
