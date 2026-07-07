# -*- coding: utf-8 -*-
"""Carica un file locale su teknosteps.com/assets/live/<remote> (FTPS). Uso: python _up.py <local> <remote>"""
import ftplib, json, os, ssl, sys
BASE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(BASE, "_deploy_secret.json"), encoding="utf-8"))
local, remote = sys.argv[1], sys.argv[2]
lp = os.path.join(BASE, local)
if not os.path.exists(lp):
    sys.exit("[X] manca " + local)
REMOTE = "/" + cfg.get("remote_dir", "public_html").strip("/") + "/assets/live"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ftp = ftplib.FTP_TLS(context=ctx, timeout=180)
ftp.connect(cfg["host"], int(cfg.get("port", 21)))
ftp.login(cfg["user"], cfg["password"])
ftp.prot_p()
for part in REMOTE.strip("/").split("/"):
    try:
        ftp.cwd(part)
    except ftplib.error_perm:
        ftp.mkd(part); ftp.cwd(part)
ftp.cwd("/")
with open(lp, "rb") as fh:
    ftp.storbinary("STOR " + REMOTE + "/" + remote, fh, blocksize=1024 * 256)
ftp.quit()
print("[OK] " + local + " -> https://teknosteps.com/assets/live/" + remote)
