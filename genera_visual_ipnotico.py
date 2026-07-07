# -*- coding: utf-8 -*-
"""
TeknoSteps - VISUAL IPNOTICO "BASS BLOOM" (Made in Italy)
=========================================================
Organismo vivo generativo (reazione-diffusione Gray-Scott) audio-reattivo:
ogni picco dell'audio (kick) fa "sbocciare" nuove forme; il livello modula
la crescita. Nero + verde neon del brand. Non e' mai uguale.

Uso (prototipo):  python genera_visual_ipnotico.py --secondi 6 --res 540 --grid 220 --out prova.mp4
Uso (pieno):      python genera_visual_ipnotico.py --secondi 180 --res 1080 --grid 360 --out base_ipno.mp4
(poi il montaggio finale lo fa loopare a 1 ora, come per i pavimenti)
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))


def ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    for d in [r"C:\Program Files\Wondershare\Recoverit", r"C:\Program Files (x86)\Wondershare\Recoverit"]:
        p = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(p):
            return p
    print("[X] ffmpeg non trovato"); sys.exit(1)


def load_envelope(wav_path, fps, n_frames):
    """Inviluppo di ampiezza per frame (per l'audio-reattivita')."""
    if not os.path.exists(wav_path):
        return np.zeros(n_frames)
    w = wave.open(wav_path, "rb")
    sr = w.getframerate(); nch = w.getnchannels()
    d = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    if nch > 1:
        d = d.reshape(-1, nch).mean(axis=1)
    env = np.zeros(n_frames)
    hop = sr / fps
    for i in range(n_frames):
        a = int(i * hop); b = int(a + hop)
        seg = d[a:b]
        env[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0
    if env.max() > 0:
        env = env / env.max()
    return env


def lap(X):
    # kernel Gray-Scott standard (somma pesi = 0 -> stabile)
    return (0.2 * (np.roll(X, 1, 0) + np.roll(X, -1, 0) + np.roll(X, 1, 1) + np.roll(X, -1, 1))
            + 0.05 * (np.roll(np.roll(X, 1, 0), 1, 1) + np.roll(np.roll(X, 1, 0), -1, 1)
                      + np.roll(np.roll(X, -1, 0), 1, 1) + np.roll(np.roll(X, -1, 0), -1, 1))
            - X)


def seed(B, n, g, rng):
    for _ in range(n):
        cy, cx = rng.integers(8, g - 8), rng.integers(8, g - 8)
        B[cy - 3:cy + 3, cx - 3:cx + 3] = 0.9


def colorize(B):
    """B (0..~0.5) -> RGB neon verde su nero."""
    v = np.clip(B * 2.2, 0, 1)
    r = (v ** 2.2 * 170).astype(np.uint8)
    g = (v ** 0.8 * 255).astype(np.uint8)
    b = (v ** 3.0 * 130).astype(np.uint8)
    return np.dstack([r, g, b])


def main():
    ap = argparse.ArgumentParser(description="Visual ipnotico Bass Bloom")
    ap.add_argument("--secondi", type=float, default=6)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--res", type=int, default=540, help="risoluzione output (quadrato)")
    ap.add_argument("--grid", type=int, default=220, help="griglia simulazione (piu' alta = piu' dettaglio, piu' lento)")
    ap.add_argument("--audio", default=os.path.join(BASE, "teknosteps_audio.wav"))
    ap.add_argument("--out", default=os.path.join(BASE, "visual_ipno.mp4"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from PIL import Image
    rng = np.random.default_rng(args.seed)
    g = args.grid
    n_frames = int(args.secondi * args.fps)
    env = load_envelope(args.audio, args.fps, n_frames)

    Da, Db, f, k, dt = 0.16, 0.08, 0.0367, 0.0649, 1.0
    A = np.ones((g, g), np.float32)
    B = np.zeros((g, g), np.float32)
    seed(B, 6, g, rng)
    # PRE-EVOLUZIONE: lascia crescere l'organismo prima di registrare (pattern organici)
    for _ in range(1600):
        La = lap(A); Lb = lap(B); AB2 = A * B * B
        A += (Da * La - AB2 + f * (1 - A)) * dt
        B += (Db * Lb + AB2 - (k + f) * B) * dt
    np.clip(A, 0, 1, A); np.clip(B, 0, 1, B)

    tmp = os.path.join(BASE, "_ipno_frames")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)

    ff = ffmpeg()
    prev = 0.0
    for i in range(n_frames):
        amp = env[i]
        # audio-reattivo: picco (kick) -> sboccia; livello -> feed
        if amp - prev > 0.20:
            seed(B, 1, g, rng)                 # un kick = un "germoglio"
        prev = amp
        fr = f + amp * 0.004                   # il basso "nutre" la crescita
        iters = 26
        for _ in range(iters):
            La = lap(A); Lb = lap(B)
            AB2 = A * B * B
            A += (Da * La - AB2 + fr * (1 - A)) * dt
            B += (Db * Lb + AB2 - (k + fr) * B) * dt
        np.clip(A, 0, 1, A); np.clip(B, 0, 1, B)
        img = Image.fromarray(colorize(B), "RGB").resize((args.res, args.res), Image.LANCZOS)
        img.save(os.path.join(tmp, f"f{i:05d}.png"))

    cmd = [ff, "-y", "-framerate", str(args.fps), "-i", os.path.join(tmp, "f%05d.png"),
           "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           args.out, "-loglevel", "error"]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    print(f"[OK] {args.out}  ({os.path.getsize(args.out)/1048576:.1f} MB, {args.secondi:.0f}s) - Made in Italy")


if __name__ == "__main__":
    main()
