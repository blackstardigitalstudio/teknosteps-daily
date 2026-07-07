# -*- coding: utf-8 -*-
"""
TeknoSteps - Imposta il BANNER del canale via YouTube Data API (Made in Italy).
L'immagine profilo (avatar) NON e' impostabile via API: va caricata a mano dal sito.
Uso: python set_channel_banner.py
"""
import os
import sys

try:
    import pip_system_certs.wrapt_requests  # certificati di Windows (AV/VPN)
except Exception:
    pass

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
CHANNEL_ID = "UCfC-k_qJZrP_eqCaZm5A2oA"
BANNER = os.path.join(BASE, "assets", "brand", "teknosteps-yt-banner.png")


def main():
    creds = Credentials.from_authorized_user_file(os.path.join(BASE, "token.json"), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds)

    print("[i] Carico il banner...")
    up = yt.channelBanners().insert(
        media_body=MediaFileUpload(BANNER, resumable=True)
    ).execute()
    url = up["url"]
    print("[i] Banner caricato, leggo le impostazioni esistenti...")

    # GET le brandingSettings attuali, poi aggiorno solo il banner (l'API valida tutto l'oggetto)
    ch = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()
    bs = ch["items"][0].get("brandingSettings", {})
    bs.setdefault("image", {})["bannerExternalUrl"] = url

    yt.channels().update(
        part="brandingSettings",
        body={"id": CHANNEL_ID, "brandingSettings": bs},
    ).execute()
    print("[OK] Banner del canale impostato. Made in Italy.")


if __name__ == "__main__":
    main()
