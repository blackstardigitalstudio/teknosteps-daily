# -*- coding: utf-8 -*-
"""Imposta la copertina (thumbnail) su un video esistente via API. Made in Italy.
Uso: python set_thumbnail.py <VIDEO_ID> <immagine.png> [token.json]"""
import os
import sys

try:
    import pip_system_certs.wrapt_requests  # certificati di Windows
except Exception:
    pass

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

vid = sys.argv[1]
img = sys.argv[2]
token = sys.argv[3] if len(sys.argv) > 3 else "token.json"
creds = Credentials.from_authorized_user_file(os.path.join(BASE, token), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
yt = build("youtube", "v3", credentials=creds)
yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(img)).execute()
print("[OK] Copertina impostata sul video", vid)
