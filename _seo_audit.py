# -*- coding: utf-8 -*-
"""Audit SEO completo 3 canali YouTube (read-only). Made in Italy.
Canale: snippet+branding+stats. Live: descrizioni piene (cerca errore '1 hour').
Video recenti: titoli/desc/tag."""
import os, io, sys
import youtube_upload

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.abspath(__file__))
CH = [("CH1 TeknoSteps", "token.json"),
      ("CH2 Strange Light", "token_ch2.json"),
      ("CH3 Tekno Monkey", "token_ch3.json")]


def show_channel(yt):
    r = yt.channels().list(part="snippet,brandingSettings,statistics,contentDetails,status",
                           mine=True).execute()
    c = r["items"][0]
    sn = c["snippet"]; bs = c.get("brandingSettings", {}); ch = bs.get("channel", {})
    img = bs.get("image", {})
    print("  TITLE      :", sn.get("title"))
    print("  HANDLE     :", sn.get("customUrl"))
    print("  COUNTRY    :", sn.get("country"), "| defaultLang:", ch.get("defaultLanguage"))
    print("  DESC       :", repr((sn.get("description") or "")[:400]))
    print("  KEYWORDS   :", repr(ch.get("keywords") or ""))
    print("  BANNER     :", "YES" if img.get("bannerExternalUrl") else "NO")
    print("  AVATAR     :", (sn.get("thumbnails", {}).get("high", {}) or {}).get("url"))
    st = c["statistics"]
    print("  STATS      : subs=%s views=%s videos=%s" % (
        st.get("subscriberCount"), st.get("viewCount"), st.get("videoCount")))
    return c


def show_lives(yt):
    for state in ("active", "upcoming", "completed"):
        r = yt.liveBroadcasts().list(part="snippet", broadcastStatus=state, maxResults=10).execute()
        for b in r.get("items", []):
            sn = b["snippet"]; d = sn.get("description", "")
            flag = " <<< CONTIENE '1 hour/ora'!" if ("1 hour" in d.lower() or "1 ora" in d.lower()
                                                     or "1-hour" in d.lower()) else ""
            print("   LIVE[%s] %s | %s%s" % (state, b["id"], sn.get("title", "")[:55], flag))


def show_videos(yt, n=8):
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="contentDetails", playlistId=pl, maxResults=n).execute()
    ids = ",".join(it["contentDetails"]["videoId"] for it in items.get("items", []))
    if not ids:
        return
    vs = yt.videos().list(part="snippet", id=ids).execute()
    for v in vs.get("items", []):
        sn = v["snippet"]
        print("   VID %s | tags=%d | %s" % (v["id"], len(sn.get("tags", []) or []), sn.get("title", "")[:60]))


for name, tok in CH:
    print("\n" + "=" * 60 + "\n" + name + "\n" + "=" * 60)
    try:
        yt = youtube_upload.get_service(os.path.join(BASE, tok))
        show_channel(yt)
        print("  --- LIVE ---")
        show_lives(yt)
        print("  --- ULTIMI VIDEO ---")
        show_videos(yt)
    except Exception as e:
        print("  ERRORE:", e)
