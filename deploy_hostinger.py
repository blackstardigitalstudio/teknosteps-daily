"""
DEPLOY HOSTINGER — TeknoSteps  ·  Made in Italy.
================================================
Sincronizza il sito su Hostinger via FTP con UN comando. Niente piu' ZIP / upload
manuale / extract. Carica SOLO i file nuovi o cambiati (confronto per dimensione),
quindi gli aggiornamenti sono veloci.

USO:
  1. Crea il file dei dati FTP:  _deploy_secret.json   (vedi modello sotto / .esempio)
     {
       "host": "ftp.tuodominio.it",   // o l'host FTP che vedi in hPanel
       "user": "u669530404.tuodominio",
       "password": "LA_TUA_PASSWORD_FTP",
       "remote_dir": "public_html",   // di solito public_html
       "tls": true                    // true = FTPS (consigliato), false = FTP semplice
     }
     I dati FTP stanno in hPanel Hostinger -> File -> Account FTP (o "FTP Accounts").
  2. python deploy_hostinger.py            (carica solo i cambiati)
     python deploy_hostinger.py --all      (ricarica tutto)
     python deploy_hostinger.py --watch     (resta in ascolto: deploya a ogni salvataggio)

NB: _deploy_secret.json NON va caricato online ne' messo nello ZIP (contiene la password).
"""
import os, sys, json, ftplib, time, ssl

PROJ = os.path.dirname(os.path.abspath(__file__))
SECRET = os.path.join(PROJ, "_deploy_secret.json")

# File del sito da pubblicare (gli stessi che vanno in public_html)
SITE_FILES = ["index.html", "styles.css", "app.js", "walk-engine.js",
              "techno-audio.js", "dev-panel.js", "manifest.json", ".htaccess",
              "app.webmanifest", "sw.js", "store.html", "order.php",
              "privacy.html", "tiktok-callback.html", "audition.html",
              "sitemap.xml", "robots.txt", "community.php", "links.html",
              "license.html", "terms.html"]
SITE_DIRS = ["video_output", "assets"]            # ricorsivi
DIR_FILTER = {"video_output": lambda f: f.startswith("walk_floor_") and f.endswith(".mp4")}


def load_secret():
    if not os.path.exists(SECRET):
        print("X Manca _deploy_secret.json. Crealo coi dati FTP (vedi istruzioni in cima).")
        sys.exit(1)
    return json.load(open(SECRET, encoding="utf-8"))


def local_files():
    """Lista (percorso_locale, percorso_remoto_relativo)."""
    out = []
    for f in SITE_FILES:
        p = os.path.join(PROJ, f)
        if os.path.exists(p):
            out.append((p, f))
    for d in SITE_DIRS:
        base = os.path.join(PROJ, d)
        if not os.path.isdir(base):
            continue
        filt = DIR_FILTER.get(d)
        for dp, _, fs in os.walk(base):
            for f in fs:
                if filt and not filt(f):
                    continue
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, PROJ).replace(os.sep, "/")
                out.append((full, rel))
    return out


def connect(cfg):
    if cfg.get("tls", True):
        ftp = ftplib.FTP_TLS(timeout=30)
        ftp.connect(cfg["host"], cfg.get("port", 21))
        ftp.login(cfg["user"], cfg["password"])
        ftp.prot_p()
    else:
        ftp = ftplib.FTP(timeout=30)
        ftp.connect(cfg["host"], cfg.get("port", 21))
        ftp.login(cfg["user"], cfg["password"])
    return ftp


def ensure_dir(ftp, remote_dir):
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            ftp.mkd(cur)
        except ftplib.error_perm:
            pass  # esiste gia'


def remote_size(ftp, path):
    try:
        return ftp.size(path)
    except Exception:
        return None


def deploy(upload_all=False):
    cfg = load_secret()
    remote_root = "/" + cfg.get("remote_dir", "public_html").strip("/")
    ftp = connect(cfg)
    ensure_dir(ftp, remote_root)
    files = local_files()
    made_dirs = set()
    up = skip = 0
    for local, rel in files:
        remote = remote_root + "/" + rel
        # crea sottocartelle remote
        rdir = os.path.dirname(remote)
        if rdir not in made_dirs:
            ensure_dir(ftp, rdir); made_dirs.add(rdir)
        lsize = os.path.getsize(local)
        # I file di codice (piccoli) si caricano SEMPRE: una modifica puo' non
        # cambiare la dimensione (es. 700->380) e il confronto-size la perderebbe.
        # Il confronto per dimensione resta solo per i media pesanti (video/immagini).
        always = rel in SITE_FILES
        if not upload_all and not always and remote_size(ftp, remote) == lsize:
            skip += 1; continue
        with open(local, "rb") as fh:
            ftp.storbinary("STOR " + remote, fh)
        up += 1
        print(f"  ^ {rel}  ({lsize/1024:.0f} KB)")
    ftp.quit()
    print(f"\n  DEPLOY OK -> {cfg['host']}{remote_root}  ({up} caricati, {skip} gia' aggiornati)")


def watch():
    print("  WATCH attivo: deploya a ogni modifica dei file del sito. Ctrl+C per uscire.")
    last = {}
    def snap():
        s = {}
        for local, rel in local_files():
            try: s[rel] = os.path.getmtime(local)
            except OSError: pass
        return s
    last = snap()
    deploy()
    while True:
        time.sleep(2)
        cur = snap()
        if cur != last:
            changed = [k for k in cur if last.get(k) != cur[k]]
            print(f"\n  modifiche: {', '.join(changed[:6])}{'...' if len(changed)>6 else ''}")
            try: deploy()
            except Exception as e: print("  ! errore deploy:", e)
            last = cur


if __name__ == "__main__":
    if "--watch" in sys.argv:
        try: watch()
        except KeyboardInterrupt: print("\n  watch fermato.")
    else:
        deploy(upload_all=("--all" in sys.argv))
