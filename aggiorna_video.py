# -*- coding: utf-8 -*-
"""
Aggiorna i METADATI (titolo/descrizione/tag/categoria) e la COPERTINA di un
video gia' online, via YouTube Data API (Made in Italy). Utile per sistemare
video caricati a mano con titoli-spazzatura.

Uso:
  python aggiorna_video.py <VIDEO_ID> --token token_ch3.json ^
     --title "..." --desc-file file.txt --tags "a,b,c" [--thumbnail img.png] [--privacy public]
"""
import argparse
import os
import sys

try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except Exception:
    pass

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--token", default="token.json")
    ap.add_argument("--title", default=None)
    ap.add_argument("--desc-file", default=None)
    ap.add_argument("--description", default=None)
    ap.add_argument("--tags", default=None)
    ap.add_argument("--category", default="10")
    ap.add_argument("--thumbnail", default=None)
    ap.add_argument("--privacy", default=None, choices=[None, "public", "unlisted", "private"])
    args = ap.parse_args()

    creds = Credentials.from_authorized_user_file(os.path.join(BASE, args.token), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds)

    cur = yt.videos().list(part="snippet,status", id=args.video_id).execute()["items"][0]
    sn = cur["snippet"]; stt = cur["status"]
    if args.title:
        sn["title"] = args.title[:100]
    desc = args.description
    if args.desc_file:
        p = args.desc_file if os.path.isabs(args.desc_file) else os.path.join(BASE, args.desc_file)
        with open(p, encoding="utf-8") as f:
            desc = f.read()
    if desc is not None:
        sn["description"] = desc[:4900]
    if args.tags is not None:
        sn["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    sn["categoryId"] = args.category

    body = {"id": args.video_id, "snippet": sn}
    parts = "snippet"
    if args.privacy:
        stt["privacyStatus"] = args.privacy
        body["status"] = stt
        parts = "snippet,status"
    yt.videos().update(part=parts, body=body).execute()
    print("[OK] Metadati aggiornati:", sn["title"])

    if args.thumbnail:
        tp = args.thumbnail if os.path.isabs(args.thumbnail) else os.path.join(BASE, args.thumbnail)
        if os.path.exists(tp):
            yt.thumbnails().set(videoId=args.video_id, media_body=MediaFileUpload(tp)).execute()
            print("[OK] Copertina impostata")
    print("Made in Italy.")


if __name__ == "__main__":
    main()
