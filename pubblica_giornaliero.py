# -*- coding: utf-8 -*-
"""
TeknoSteps - PUBBLICAZIONE GIORNALIERA A PROVA DI ERRORE (Made in Italy)
=======================================================================
Pubblica ogni giorno i 3 canali (video + short) e le bozze TikTok, con
AUTO-RETRY: se un canale fallisce (es. RAM esaurita), aspetta e RIPROVA finche'
non riesce. Prima di ogni canale aspetta che ci sia RAM libera a sufficienza,
cosi' non parte quando la memoria e' satura (era la causa del crash del 2/7).

Non si perde un giorno: ogni canale ha fino a MAX_TRIES tentativi.

Uso:  python pubblica_giornaliero.py
      python pubblica_giornaliero.py --no-upload   (crea i file senza pubblicare)
"""
import argparse
import ctypes
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ENV = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
LOG = os.path.join(BASE, "log_pipeline.txt")

MAX_TRIES = 6            # tentativi per canale
WAIT_RETRY = 45          # secondi tra un tentativo e l'altro
NEED_FREE_GB = 3.0       # RAM libera minima per partire
WAIT_RAM_MAX = 900       # attesa max per la RAM (15 min)
CH_TIMEOUT = 5400        # timeout per canale (90 min): CH2 con audio lungo + upload puo' durare

# Short per canale: da env TS_SHORTS (default 5). In cloud lo mettiamo a 1 per
# stare nella quota API di un solo progetto Google (~6 upload/giorno totali).
_S = (os.environ.get("TS_SHORTS", "") or "5").strip()
CHANNELS = [
    ("CH1 TeknoSteps",   ["pipeline_completo.py", "--shorts", _S]),
    ("CH2 Strange Light", ["pipeline_ipnotico.py", "--shorts", _S]),
    ("CH3 Tekno Monkey",  ["pipeline_scimmia.py", "--shorts", _S]),
]


class _MEM(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_gb():
    try:
        m = _MEM(); m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / (1024 ** 3)
    except Exception:
        return 999.0   # non-Windows: non bloccare


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def wait_for_ram():
    waited = 0
    while free_gb() < NEED_FREE_GB and waited < WAIT_RAM_MAX:
        log(f"   RAM libera {free_gb():.1f} GB < {NEED_FREE_GB} GB: aspetto...")
        time.sleep(30); waited += 30


def run_channel(name, args, no_upload):
    cmd = [PY] + args + (["--no-upload"] if no_upload else [])
    for attempt in range(1, MAX_TRIES + 1):
        wait_for_ram()
        log(f"[{name}] tentativo {attempt}/{MAX_TRIES} (RAM {free_gb():.1f} GB)")
        try:
            # TIMEOUT per canale: se si pianta (non esce), lo uccidiamo e riproviamo
            # invece di restare bloccati all'infinito (bug del 2/7 su CH2).
            r = subprocess.run(cmd, cwd=BASE, env=ENV, timeout=CH_TIMEOUT)
        except subprocess.TimeoutExpired:
            log(f"[{name}] PIANTATO (>{CH_TIMEOUT//60} min): interrotto. Riprovo tra {WAIT_RETRY}s...")
            time.sleep(WAIT_RETRY); continue
        if r.returncode == 0:
            log(f"[{name}] OK al tentativo {attempt}")
            return True
        log(f"[{name}] fallito (exit {r.returncode}). Riprovo tra {WAIT_RETRY}s...")
        time.sleep(WAIT_RETRY)
    log(f"[{name}] X NON riuscito dopo {MAX_TRIES} tentativi")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--only", default=None, help="solo canali il cui nome contiene queste parole (virgola)")
    args = ap.parse_args()

    channels = CHANNELS
    if args.only:
        keys = [k.strip().lower() for k in args.only.split(",")]
        channels = [(n, a) for n, a in CHANNELS if any(k in n.lower() for k in keys)]

    log("==================== START pubblicazione giornaliera ====================")
    # AUTO-UPDATE SYNTH: pubblica il sito (techno-audio.js + manifest) cosi' la
    # radio live riflette le rifiniture del synth; i video leggono gia' i mood dal
    # manifest, quindi si aggiornano da soli. Non blocca se il deploy fallisce.
    if not args.no_upload:
        log("[SYNTH auto-update] deploy sito (synth + manifest)")
        try:
            subprocess.run([PY, "deploy_hostinger.py"], cwd=BASE, env=ENV, timeout=600)
        except Exception as e:
            log(f"   deploy saltato: {e}")
    ok = 0
    for name, chan_args in channels:
        if run_channel(name, chan_args, args.no_upload):
            ok += 1
    # TikTok bozze (non critico: non ripetere se manca il token)
    if not args.no_upload:
        log("[TIKTOK bozze] invio short come bozze")
        subprocess.run([PY, "tiktok_drafts.py"], cwd=BASE, env=ENV)
    # Story verticali story-safe pronte in Download (per condividerle a mano su IG/TikTok/FB)
    log("[STORY] genero le story 9:16 pronte in Download")
    try:
        subprocess.run([PY, "crea_story.py"], cwd=BASE, env=ENV, timeout=900)
    except Exception as e:
        log(f"   story saltate: {e}")
    log(f"==================== FINE ({ok}/{len(channels)} canali pubblicati) ====================")
    sys.exit(0 if ok == len(channels) else 1)


if __name__ == "__main__":
    main()
