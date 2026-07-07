# -*- coding: utf-8 -*-
"""Snapshot statistiche YouTube 3 canali per routine SEO. Made in Italy."""
import os, json
import youtube_upload

BASE = os.path.dirname(os.path.abspath(__file__))
CHANNELS = [("CH1 TeknoSteps", "token.json"),
            ("CH2 Strange Light", "token_ch2.json"),
            ("CH3 Tekno Monkey", "token_ch3.json")]


def recent(yt, n=15):
    ch = yt.channels().list(part="contentDetails,statistics,snippet", mine=True).execute()
    item = ch["items"][0]
    cst = item["statistics"]
    pl = item["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="contentDetails,snippet", playlistId=pl, maxResults=n).execute()
    vids = [{"id": it["contentDetails"]["videoId"], "title": it["snippet"]["title"],
             "published": it["snippet"]["publishedAt"]} for it in items.get("items", [])]
    if vids:
        stats = yt.videos().list(part="statistics", id=",".join(v["id"] for v in vids)).execute()
        by = {s["id"]: s.get("statistics", {}) for s in stats.get("items", [])}
        for v in vids:
            st = by.get(v["id"], {})
            v["views"] = int(st.get("viewCount", 0))
            v["likes"] = int(st.get("likeCount", 0))
    return item["snippet"]["title"], cst, vids


for name, tok in CHANNELS:
    try:
        yt = youtube_upload.get_service(os.path.join(BASE, tok))
        title, cst, vids = recent(yt)
        print("\n===== %s (%s) =====" % (name, title))
        print("subs=%s | views_tot=%s | videos=%s" % (
            cst.get("subscriberCount", "?"), cst.get("viewCount", "?"), cst.get("videoCount", "?")))
        for v in sorted(vids, key=lambda x: -x["views"])[:12]:
            print("  %6d v  %3d lk  | %s | %s" % (v["views"], v["likes"], v["published"][:10], v["title"][:62]))
    except Exception as e:
        print("\n===== %s ERRORE: %s" % (name, e))
