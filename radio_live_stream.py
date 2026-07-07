# -*- coding: utf-8 -*-
"""
TeknoSteps - DIRETTA YouTube 24/7 sui 3 canali (Made in Italy)
==============================================================
Manda in loop INFINITO un video (con l'audio del synth, 100% no-copyright) verso
l'RTMP di YouTube Live, per uno o piu' canali contemporaneamente. Se ffmpeg cade
(rete, timeout YouTube), il supervisore lo RIAVVIA da solo -> diretta perpetua.

Perche' e' senza copyright: l'audio e' generato da genera_audio_techno.py e i
video sono nostri -> nessun contenuto di terzi, nessuno strike.

CONFIG (live_config.json nella cartella):
{
  "channels": [
    {"name": "TeknoSteps",   "video": "video_output/teknosteps_youtube_synthnew.mp4", "key": "xxxx-xxxx-xxxx-xxxx", "enabled": true},
    {"name": "Strange Light", "video": "video_output/strange_1h.mp4",                 "key": "yyyy-yyyy-yyyy-yyyy", "enabled": true},
    {"name": "Tekno Monkey",  "video": "video_output/monkey_1h.mp4",                  "key": "zzzz-zzzz-zzzz-zzzz", "enabled": true}
  ],
  "res": "1280x720", "fps": 30, "vbitrate": "3500k", "abitrate": "128k"
}
La "key" e' la CHIAVE DI TRASMISSIONE che trovi in YouTube Studio -> Trasmetti ->
Impostazioni streaming (una per canale). NON va condivisa/pubblicata.

USO:
  python radio_live_stream.py                 # avvia la diretta di tutti i canali enabled
  python radio_live_stream.py --only "Tekno Monkey"
  python radio_live_stream.py --check         # controlla ffmpeg, file e config, senza trasmettere
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "live_config.json")
RTMP = "rtmp://a.rtmp.youtube.com/live2/"


def find_ffmpeg():
    for c in (shutil.which("ffmpeg"),
              r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe",
              r"C:\Program Files (x86)\Wondershare\Recoverit\ffmpeg.exe"):
        if c and os.path.exists(c):
            return c
    return shutil.which("ffmpeg")


def load_config():
    if not os.path.exists(CONFIG):
        # crea un modello da compilare
        model = {
            "channels": [
                {"name": "TeknoSteps", "video": "video_output/teknosteps_youtube_synthnew.mp4",
                 "key": "INCOLLA-CHIAVE-STREAM", "enabled": True},
                {"name": "Strange Light", "video": "video_output/strange_1h.mp4",
                 "key": "INCOLLA-CHIAVE-STREAM", "enabled": False},
                {"name": "Tekno Monkey", "video": "video_output/monkey_1h.mp4",
                 "key": "INCOLLA-CHIAVE-STREAM", "enabled": False},
            ],
            "res": "1280x720", "fps": 30, "vbitrate": "3500k", "abitrate": "128k",
        }
        json.dump(model, open(CONFIG, "w", encoding="utf-8"), indent=2)
        print(f"[i] Creato modello {CONFIG}. Incolla le chiavi di stream e riavvia.")
        sys.exit(0)
    return json.load(open(CONFIG, encoding="utf-8"))


def prepared_path(video):
    """Percorso del file 'live-ready' (720p, keyframe ogni 2s) accanto al sorgente."""
    root, _ = os.path.splitext(video)
    return root + "_live720.mp4"


def prepare_live_file(ffmpeg, ch, cfg):
    """Transcodifica UNA VOLTA il video a 720p leggero con keyframe ogni 2s e
    faststart, poi in diretta si fa STREAM-COPY (zero CPU di encoding) -> stabile
    anche con piu' canali insieme. Se il file pronto esiste ed e' piu' recente del
    sorgente, non rifa' nulla."""
    src = os.path.join(BASE, ch["video"])
    dst = prepared_path(src)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return dst
    w, h = cfg.get("res", "1280x720").split("x")
    fps = int(cfg.get("fps", 30))
    vb = cfg.get("vbitrate", "2500k")
    ab = cfg.get("abitrate", "128k")
    g = str(fps * 2)
    print(f"[PREP] {ch['name']}: preparo il file 720p per la diretta (una volta sola)...")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", src,
           "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                  f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-b:v", vb, "-maxrate", vb, "-bufsize", vb,
           "-g", g, "-keyint_min", g, "-sc_threshold", "0",
           "-c:a", "aac", "-b:a", ab, "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", dst]
    if subprocess.run(cmd).returncode != 0:
        print(f"[X] {ch['name']}: preparazione fallita, uso il sorgente cosi' com'e'.")
        return src
    print(f"[PREP] {ch['name']}: pronto -> {os.path.basename(dst)}")
    return dst


def ff_cmd(ffmpeg, prepared, ch):
    """Diretta in STREAM-COPY: il file e' gia' 720p pronto -> nessuna ricodifica,
    ffmpeg inoltra e basta (CPU quasi zero)."""
    return [
        ffmpeg, "-hide_banner", "-loglevel", "warning",
        "-fflags", "+genpts", "-stream_loop", "-1", "-re", "-i", prepared,
        "-c", "copy",
        "-f", "flv", RTMP + ch["key"],
    ]


def stream_channel(ffmpeg, ch, cfg, stop):
    """Trasmette un canale in loop; riavvia ffmpeg se cade. Ferma su stop.set()."""
    name = ch["name"]
    video = os.path.join(BASE, ch["video"])
    if not os.path.exists(video):
        print(f"[X] {name}: video mancante -> {ch['video']} (salto)")
        return
    if not ch.get("key") or "INCOLLA" in ch["key"]:
        print(f"[X] {name}: chiave di stream mancante (salto)")
        return
    prepared = prepare_live_file(ffmpeg, ch, cfg)   # 720p pronto (una volta) -> stream-copy
    delay = 3
    while not stop.is_set():
        print(f"[LIVE] {name}: avvio diretta (stream-copy 720p) ...")
        try:
            p = subprocess.Popen(ff_cmd(ffmpeg, prepared, ch))
        except Exception as e:
            print(f"[X] {name}: ffmpeg non parte: {e}")
            return
        while p.poll() is None and not stop.is_set():
            time.sleep(2)
        if stop.is_set():
            p.terminate()
            print(f"[STOP] {name}: diretta fermata.")
            return
        code = p.returncode
        print(f"[!] {name}: ffmpeg uscito (code {code}). Riavvio tra {delay}s...")
        for _ in range(delay):
            if stop.is_set():
                return
            time.sleep(1)
        delay = min(30, delay + 3)   # backoff se continua a cadere


def main():
    ap = argparse.ArgumentParser(description="Diretta YouTube 24/7 TeknoSteps")
    ap.add_argument("--only", default=None, help="trasmetti solo il canale col nome dato")
    ap.add_argument("--check", action="store_true", help="verifica config/ffmpeg/file senza trasmettere")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    cfg = load_config()
    chans = [c for c in cfg["channels"] if c.get("enabled", False)]
    if args.only:
        chans = [c for c in cfg["channels"] if c["name"].lower() == args.only.lower()]

    if args.check or not ffmpeg:
        print("=== CHECK diretta ===")
        print("ffmpeg:", ffmpeg or "NON TROVATO")
        for c in cfg["channels"]:
            v = os.path.join(BASE, c["video"])
            print(f"- {c['name']}: enabled={c.get('enabled')} | video={'OK' if os.path.exists(v) else 'MANCA'} "
                  f"| key={'OK' if c.get('key') and 'INCOLLA' not in c['key'] else 'MANCA'}")
        if not ffmpeg:
            print("[X] Installa ffmpeg o mettilo nel PATH.")
        return

    if not chans:
        print("[i] Nessun canale attivo. Metti \"enabled\": true e la chiave in live_config.json.")
        return

    stop = threading.Event()
    threads = [threading.Thread(target=stream_channel, args=(ffmpeg, c, cfg, stop), daemon=True) for c in chans]
    for t in threads:
        t.start()
    print(f"[i] Diretta 24/7 avviata su {len(chans)} canale/i. Ctrl+C per fermare. Made in Italy.")
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[i] Fermo le dirette...")
        stop.set()
        for t in threads:
            t.join(timeout=10)
        print("[i] Dirette fermate.")


if __name__ == "__main__":
    main()
