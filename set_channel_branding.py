# -*- coding: utf-8 -*-
"""
Imposta NOME + DESCRIZIONE + KEYWORDS (SEO) e opzionalmente il BANNER di un canale
via YouTube Data API (Made in Italy). L'avatar NON e' impostabile via API.

Uso:
  python set_channel_branding.py --token token_ch3.json ^
     --title "Tekno Monkey" --desc-file _brand_desc.txt ^
     --keywords "dancing monkey,techno monkey,dark psytrance,..." ^
     --banner scimmia-banner.png
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
    ap.add_argument("--token", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--description", default=None)
    ap.add_argument("--desc-file", default=None)
    ap.add_argument("--keywords", default=None, help="virgola-separati; le frasi con spazi vengono quotate")
    ap.add_argument("--banner", default=None)
    args = ap.parse_args()

    creds = Credentials.from_authorized_user_file(args.token, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds)

    me = yt.channels().list(part="snippet,brandingSettings", mine=True).execute()
    item = me["items"][0]
    cid = item["id"]
    bs = item.get("brandingSettings", {})
    bs.setdefault("channel", {})
    print(f"[i] Canale: {item['snippet']['title']}  (id {cid})")

    if args.banner:
        path = args.banner if os.path.isabs(args.banner) else os.path.join(BASE, args.banner)
        print("[i] Carico banner...")
        up = yt.channelBanners().insert(media_body=MediaFileUpload(path, resumable=True)).execute()
        bs.setdefault("image", {})["bannerExternalUrl"] = up["url"]

    if args.title:
        bs["channel"]["title"] = args.title
    desc = args.description
    if args.desc_file:
        p = args.desc_file if os.path.isabs(args.desc_file) else os.path.join(BASE, args.desc_file)
        with open(p, encoding="utf-8") as f:
            desc = f.read().strip()
    if desc is not None:
        bs["channel"]["description"] = desc[:1000]
    if args.keywords is not None:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        bs["channel"]["keywords"] = " ".join(f'"{k}"' if " " in k else k for k in kws)

    yt.channels().update(part="brandingSettings", body={"id": cid, "brandingSettings": bs}).execute()
    print("[OK] Branding aggiornato:")
    if args.title:
        print("     nome    :", args.title)
    print("     keywords:", bs["channel"].get("keywords", "")[:120])
    print("     banner  :", "si" if args.banner else "invariato")
    print("Made in Italy.")


if __name__ == "__main__":
    main()
