# -*- coding: utf-8 -*-
"""
TeknoSteps - Upload automatico su YouTube (Made in Italy)
==========================================================
Carica un video (anche grande, anche Short) su YouTube via YouTube Data API v3,
con titolo/descrizione/tag/categoria/copertina e visibilità. Niente browser,
niente limiti di dimensione.

Prerequisiti (una volta sola): vedi SETUP_YOUTUBE_API.md
  - client_secret.json nella cartella (dalle credenziali OAuth di Google Cloud)
  - pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Al primo avvio si apre il browser per il consenso Google -> salva token.json.
Dopo, funziona da solo (rinnova il token automaticamente).

Esempi:
  python youtube_upload.py --video teknosteps_psy_1h.mp4 ^
      --title "Dark Psytrance Mix - 1 Hour ..." --description-file desc.txt ^
      --tags "dark psytrance,psytrance mix" --thumbnail teknosteps-thumbnail.png ^
      --privacy public
  python youtube_upload.py --video teknosteps_short_01.mp4 --short --privacy public
"""
import argparse
import os
import sys

# Usa i certificati di Windows (evita errori SSL con antivirus/VPN che ispezionano HTTPS)
try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except Exception:
    pass

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
BASE = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET = os.path.join(BASE, "client_secret.json")
TOKEN = os.path.join(BASE, "token.json")


def _client_secret_for(token_path):
    """Client_secret del progetto giusto per questo canale.
    Ogni canale puo' avere il SUO progetto Google (quota separata): dal nome del
    token deriva il client_secret. Es. token_ch2.json -> client_secret_ch2.json;
    se non esiste, usa il client_secret.json di default (progetto condiviso)."""
    base = os.path.basename(token_path or TOKEN)
    if base.startswith("token_"):
        cand = os.path.join(BASE, "client_secret_" + base[len("token_"):])
        if os.path.exists(cand):
            return cand
    return CLIENT_SECRET


def get_service(token_path=None, client_secret_path=None):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[X] Mancano le librerie. Esegui:")
        print("    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        sys.exit(1)

    token_path = token_path or TOKEN
    client_secret_path = client_secret_path or _client_secret_for(token_path)
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secret_path):
                print(f"[X] Manca {client_secret_path}. Vedi SETUP_YOUTUBE_API.md")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            # prompt select_account: permette di scegliere il canale/brand giusto (es. Strange Light)
            creds = flow.run_local_server(port=0, prompt="select_account")
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def main():
    ap = argparse.ArgumentParser(description="Upload YouTube TeknoSteps")
    ap.add_argument("--video", default=None)
    ap.add_argument("--auth-only", action="store_true", help="fai solo il consenso OAuth e salva il token")
    ap.add_argument("--title", default=None)
    ap.add_argument("--description", default="")
    ap.add_argument("--description-file", default=None, help="file di testo con la descrizione")
    ap.add_argument("--tags", default="", help="tag separati da virgola")
    ap.add_argument("--thumbnail", default=None)
    ap.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    ap.add_argument("--short", action="store_true", help="aggiunge #Shorts e usa titolo breve")
    ap.add_argument("--category", default="10", help="10 = Música")
    ap.add_argument("--token", default=None, help="file token (es. token_ch2.json per il 2 canale)")
    ap.add_argument("--client-secret", default=None, help="client_secret del progetto (default: auto dal nome token, poi client_secret.json)")
    args = ap.parse_args()

    if args.auth_only:
        get_service(args.token, args.client_secret)
        print(f"[OK] Consenso fatto, token salvato: {args.token or 'token.json'}")
        return

    if not args.video or not os.path.exists(args.video):
        print(f"[X] Video non trovato: {args.video}")
        sys.exit(1)

    from googleapiclient.http import MediaFileUpload

    desc = args.description
    if args.description_file and os.path.exists(args.description_file):
        with open(args.description_file, encoding="utf-8") as f:
            desc = f.read()

    title = args.title or os.path.splitext(os.path.basename(args.video))[0]
    if args.short and "#shorts" not in (title + desc).lower():
        title = (title[:90] + " #Shorts").strip()
        desc = (desc + "\n\n#Shorts #psytrance #darkpsy").strip()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    yt = get_service(args.token, args.client_secret)
    body = {
        "snippet": {
            "title": title[:100],
            "description": desc[:4900],
            "tags": tags,
            "categoryId": args.category,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"[i] Carico: {args.video}  ({os.path.getsize(args.video)/1048576:.0f} MB)")
    media = MediaFileUpload(args.video, chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"    upload {int(status.progress()*100)}%")
    vid = resp["id"]
    print(f"[OK] Pubblicato: https://youtu.be/{vid}")

    if args.thumbnail and os.path.exists(args.thumbnail):
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(args.thumbnail)).execute()
        print("[OK] Copertina impostata")

    return vid


if __name__ == "__main__":
    main()
