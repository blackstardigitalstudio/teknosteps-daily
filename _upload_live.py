# -*- coding: utf-8 -*-
"""Carica i 3 video compatti della diretta su teknosteps.com/assets/live/ (FTPS)."""
import ftplib, json, os, ssl, sys
BASE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(BASE, "_deploy_secret.json"), encoding="utf-8"))
FILES = ["teknosteps_live.mp4", "strange_live.mp4", "monkey_live.mp4"]
REMOTE = "/" + cfg.get("remote_dir", "public_html").strip("/") + "/assets/live"

for f in FILES:
    if not os.path.exists(os.path.join(BASE, f)):
        sys.exit("[X] manca " + f + " (compressione non finita?)")

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ftp = ftplib.FTP_TLS(context=ctx, timeout=60)
ftp.connect(cfg["host"], int(cfg.get("port", 21)))
ftp.login(cfg["user"], cfg["password"])
ftp.prot_p()
# assicura le cartelle assets/ e assets/live/
for part in REMOTE.strip("/").split("/"):
    try:
        ftp.cwd(part)
    except ftplib.error_perm:
        ftp.mkd(part); ftp.cwd(part)
ftp.cwd("/")

for f in FILES:
    lp = os.path.join(BASE, f)
    sz = os.path.getsize(lp) / 1048576
    print(f"[..] {f}  ({sz:.0f} MB) -> {REMOTE}/{f}", flush=True)
    with open(lp, "rb") as fh:
        ftp.storbinary("STOR " + REMOTE + "/" + f, fh, blocksize=1024 * 256)
    print(f"[OK] {f} caricato", flush=True)
ftp.quit()
print("=== 3 video live caricati su teknosteps.com/assets/live/ ===")
