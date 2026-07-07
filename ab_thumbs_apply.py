# -*- coding: utf-8 -*-
"""
A/B test copertine Tekno Monkey (canale 3) - Made in Italy.

--apply   : prende gli ultimi video lunghi del canale, applica
            variante B al piu' recente, variante A al secondo, lascia gli altri
            come controllo; salva la baseline in _ab_snapshot.json
--report  : rilegge le statistiche, calcola i delta views/ora per variante
            e stampa il confronto (aggiunge lo snapshot finale al file)

Uso: python ab_thumbs_apply.py --apply | --report
"""
import argparse
import datetime
import json
import os

import youtube_upload

BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.path.join(BASE, "token_ch3.json")
SNAP = os.path.join(BASE, "_ab_snapshot.json")
THUMBS = {"A": os.path.join(BASE, "scimmia-thumbnail-A.png"),
          "B": os.path.join(BASE, "scimmia-thumbnail-B.png")}


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def get_recent_videos(yt, n=8):
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="contentDetails,snippet", playlistId=pl, maxResults=n).execute()
    vids = []
    for it in items.get("items", []):
        vids.append({"id": it["contentDetails"]["videoId"],
                     "title": it["snippet"]["title"],
                     "published": it["snippet"]["publishedAt"]})
    ids = ",".join(v["id"] for v in vids)
    stats = yt.videos().list(part="statistics", id=ids).execute()
    by_id = {s["id"]: s.get("statistics", {}) for s in stats.get("items", [])}
    for v in vids:
        st = by_id.get(v["id"], {})
        v["views"] = int(st.get("viewCount", 0))
        v["likes"] = int(st.get("likeCount", 0))
    return vids


def is_short(v):
    return "#shorts" in v["title"].lower() or "on beat" in v["title"].lower()


def apply(yt):
    from googleapiclient.http import MediaFileUpload
    vids = [v for v in get_recent_videos(yt) if not is_short(v)]
    if len(vids) < 3:
        raise SystemExit("[X] servono almeno 3 video lunghi per il test")
    plan = {vids[0]["id"]: "B", vids[1]["id"]: "A"}   # il resto = controllo
    for v in vids:
        v["variant"] = plan.get(v["id"], "control")
    for vid, variant in plan.items():
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(THUMBS[variant])).execute()
        print("[OK] thumbnail %s -> video %s" % (variant, vid))
    snap = {"started": now_iso(), "baseline": vids, "checks": []}
    json.dump(snap, open(SNAP, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("[OK] baseline salvata in", SNAP)
    for v in vids:
        print("   %s | %s | views=%d | %s" % (v["variant"], v["id"], v["views"], v["title"][:60]))


def report(yt):
    if not os.path.exists(SNAP):
        raise SystemExit("[X] manca _ab_snapshot.json: esegui prima --apply")
    snap = json.load(open(SNAP, encoding="utf-8"))
    base = {v["id"]: v for v in snap["baseline"]}
    cur = {v["id"]: v for v in get_recent_videos(yt, n=15)}
    t0 = datetime.datetime.fromisoformat(snap["started"])
    hours = max(0.1, (datetime.datetime.now() - t0).total_seconds() / 3600)
    rows, agg = [], {}
    for vid, b in base.items():
        c = cur.get(vid)
        if not c:
            continue
        dv = c["views"] - b["views"]
        dl = c["likes"] - b["likes"]
        rate = dv / hours
        rows.append({"id": vid, "variant": b["variant"], "title": b["title"],
                     "views_start": b["views"], "views_now": c["views"],
                     "delta_views": dv, "delta_likes": dl, "views_per_hour": round(rate, 2)})
        agg.setdefault(b["variant"], []).append(rate)
    print("\n=== A/B THUMBNAIL REPORT (%.1f ore) ===" % hours)
    for r in sorted(rows, key=lambda x: x["variant"]):
        print(" %-7s %s  +%d views (%.2f/h)  +%d likes  | %s"
              % (r["variant"], r["id"], r["delta_views"], r["views_per_hour"], r["delta_likes"], r["title"][:50]))
    print("\n--- media views/ora per variante ---")
    for k, v in sorted(agg.items()):
        print(" %-7s %.2f views/h (n=%d)" % (k, sum(v) / len(v), len(v)))
    snap["checks"].append({"at": now_iso(), "hours": round(hours, 1), "rows": rows,
                           "avg_views_per_hour": {k: round(sum(v) / len(v), 2) for k, v in agg.items()}})
    json.dump(snap, open(SNAP, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n[OK] check aggiunto a", SNAP)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--report", action="store_true")
    args = ap.parse_args()
    yt = youtube_upload.get_service(TOKEN)
    (apply if args.apply else report)(yt)


if __name__ == "__main__":
    main()
