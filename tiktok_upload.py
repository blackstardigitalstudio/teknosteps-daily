# -*- coding: utf-8 -*-
"""
TeknoSteps - Upload su TikTok via Content Posting API (Made in Italy)
=====================================================================
Carica uno short nel TUO TikTok. Finche' l'app non e' approvata da TikTok, il
video va nella INBOX/bozze (apri l'app e pubblichi con un tap). Dopo l'approvazione
basta usare --direct per pubblicare in automatico (direct post, zero tap).

Config (tiktok_config.json nella cartella):
  { "client_key": "...", "client_secret": "...",
    "redirect_uri": "https://teknosteps.com/tiktok-callback" }

Flusso OAuth (una volta):
  1) python tiktok_upload.py --auth-url        -> apri l'URL, autorizza, copia il ?code=...
  2) python tiktok_upload.py --code <CODE>     -> salva tiktok_token.json
Poi ogni giorno:
  python tiktok_upload.py --video short.mp4 --title "..."      (inbox/bozza)
  python tiktok_upload.py --video short.mp4 --title "..." --direct   (dopo approvazione)
"""
import argparse, json, os, sys

try:
    import pip_system_certs.wrapt_requests  # certificati Windows (AV/VPN)
except Exception:
    pass
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "tiktok_config.json")
TOKEN = os.path.join(BASE, "tiktok_token.json")
# Solo bozze (inbox) -> serve SOLO video.upload. video.publish (post pubblico
# diretto) richiede l'audit TikTok e fa fallire l'OAuth se non approvato: lo
# aggiungiamo solo dopo l'approvazione, quando si usera' --direct.
SCOPES = "user.info.basic,video.upload"
AUTH = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
API = "https://open.tiktokapis.com/v2"


def cfg():
    if not os.path.exists(CONFIG):
        sys.exit(f"[X] Manca {CONFIG} (client_key, client_secret, redirect_uri)")
    return json.load(open(CONFIG, encoding="utf-8"))


def save_token(d):
    json.dump(d, open(TOKEN, "w", encoding="utf-8"))


def load_token():
    if not os.path.exists(TOKEN):
        sys.exit("[X] Nessun token. Fai prima l'OAuth: --auth-url poi --code <CODE>")
    return json.load(open(TOKEN, encoding="utf-8"))


def auth_url():
    c = cfg()
    from urllib.parse import urlencode
    q = urlencode({"client_key": c["client_key"], "scope": SCOPES, "response_type": "code",
                   "redirect_uri": c["redirect_uri"], "state": "teknosteps"})
    return f"{AUTH}?{q}"


def exchange(code):
    c = cfg()
    r = requests.post(TOKEN_URL, data={
        "client_key": c["client_key"], "client_secret": c["client_secret"],
        "code": code, "grant_type": "authorization_code", "redirect_uri": c["redirect_uri"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        sys.exit(f"[X] OAuth fallito: {d}")
    save_token(d); print("[OK] Token TikTok salvato:", TOKEN)


def access_token():
    c = cfg(); t = load_token()
    r = requests.post(TOKEN_URL, data={
        "client_key": c["client_key"], "client_secret": c["client_secret"],
        "grant_type": "refresh_token", "refresh_token": t["refresh_token"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    d = r.json()
    if "access_token" in d:
        save_token(d); return d["access_token"]
    return t["access_token"]


def upload(video, title, direct=False):
    at = access_token()
    H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8"}
    size = os.path.getsize(video)
    src = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}
    if direct:
        body = {"post_info": {"title": title, "privacy_level": "PUBLIC_TO_EVERYONE",
                              "disable_comment": False, "disable_duet": False, "disable_stitch": False},
                "source_info": src}
        init = requests.post(f"{API}/post/publish/video/init/", headers=H, json=body, timeout=30).json()
    else:
        init = requests.post(f"{API}/post/publish/inbox/video/init/", headers=H,
                             json={"source_info": src}, timeout=30).json()
    err = init.get("error", {})
    if err.get("code") not in (None, "ok"):
        sys.exit(f"[X] init: {err}")
    up = init["data"]["upload_url"]
    with open(video, "rb") as f:
        data = f.read()
    put = requests.put(up, headers={"Content-Type": "video/mp4",
                       "Content-Range": f"bytes 0-{size-1}/{size}", "Content-Length": str(size)},
                       data=data, timeout=300)
    if put.status_code not in (200, 201, 206):
        sys.exit(f"[X] upload bytes: {put.status_code} {put.text[:200]}")
    print("[OK] Inviato a TikTok:", "PUBBLICO (direct)" if direct else "INBOX/bozza (pubblica con un tap)")
    print("     publish_id:", init["data"].get("publish_id"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth-url", action="store_true")
    ap.add_argument("--code", default=None)
    ap.add_argument("--video", default=None)
    ap.add_argument("--title", default="Tekno Monkey on the beat #tekno #psytrance #nocopyright")
    ap.add_argument("--direct", action="store_true", help="post pubblico diretto (solo dopo approvazione TikTok)")
    args = ap.parse_args()
    if args.auth_url:
        print(auth_url()); return
    if args.code:
        exchange(args.code); return
    if args.video:
        if not os.path.exists(args.video):
            sys.exit(f"[X] Video non trovato: {args.video}")
        upload(args.video, args.title, args.direct); return
    ap.print_help()


if __name__ == "__main__":
    main()
