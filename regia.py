# -*- coding: utf-8 -*-
"""
REGIA TEKNOSTEPS — pannello di controllo locale della radio.  Made in Italy.
============================================================================
Un piccolo server web che gira SOLO sul tuo computer (127.0.0.1) e ti da'
un pannello privato per gestire la radio senza dover usare l'assistente:

  • PALINSESTO 24h  : scegli il genere/mood per ogni ora del giorno.
  • MOOD            : vedi i 4 generi base + quelli creati dalle tue tracce.
  • BRANI           : apri la cartella, metti i tuoi mp3, "Analizza & crea mood".
  • PUBBLICA        : manda tutto online (deploy) con un click.

SICUREZZA
  - Ascolta solo su 127.0.0.1 (nessuno dalla rete puo' raggiungerlo).
  - Login con PASSWORD (hash salato in _regia_secret.json, MAI online).
  - Sessione con cookie casuale in memoria.

AVVIO
  Doppio click su "Regia TeknoSteps.bat"  (oppure:  python regia.py)
  Si apre il browser su http://127.0.0.1:8787
"""
import os, sys, json, hmac, hashlib, secrets, threading, webbrowser, subprocess, time, base64, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(BASE, "manifest.json")
SECRET = os.path.join(BASE, "_regia_secret.json")
TRACKS_DIR = os.path.join(BASE, "radio_tracks")
PORT = 8787
BASE_MOODS = ["TECHNO", "MINIMAL", "PSYTRANCE", "TRANCE"]
AUDIO_EXT = (".mp3", ".wav", ".flac", ".m4a", ".ogg")

SESSIONS = set()          # token di sessione validi (in memoria)


# ----------------------------------------------------------------- auth ------
def load_secret():
    if os.path.exists(SECRET):
        return json.load(open(SECRET, encoding="utf-8"))
    return None


def set_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + pw).encode()).hexdigest()
    json.dump({"salt": salt, "hash": h}, open(SECRET, "w", encoding="utf-8"))


def check_password(pw):
    s = load_secret()
    if not s:
        return False
    h = hashlib.sha256((s["salt"] + pw).encode()).hexdigest()
    return hmac.compare_digest(h, s["hash"])


# ----------------------------------------------------------- manifest io -----
def read_manifest():
    return json.load(open(MANIFEST, encoding="utf-8"))


def write_manifest(m):
    tmp = MANIFEST + ".tmp"
    json.dump(m, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MANIFEST)


def mood_names(m):
    return [x.get("name", "?") for x in m.get("audioGenerator", {}).get("moods", [])]


def get_schedule(m):
    r = m.get("audioGenerator", {}).get("radio", {})
    sch = r.get("schedule")
    if not isinstance(sch, list) or len(sch) != 24:
        sch = ["TECHNO"] * 24
    return sch


def tracks_list():
    if not os.path.isdir(TRACKS_DIR):
        return []
    return sorted(f for f in os.listdir(TRACKS_DIR) if f.lower().endswith(AUDIO_EXT))


# ------------------------------------------- analisi -> UN mood per canzone -----
def _load_mod(fname, alias):
    import importlib.util
    spec = importlib.util.spec_from_file_location(alias, os.path.join(BASE, fname))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _nome_da_file(fname):
    import re as _re
    seg = os.path.splitext(fname)[0].split(" - ")[0].strip()   # prima parte = artista/titolo
    nome = _re.sub(r"[^A-Za-z0-9 ]", "", seg).upper().strip()[:16].strip() or "TRACK"
    if nome in BASE_MOODS:
        nome += " X"
    return nome


def analizza_e_crea_mood(prefix=None):
    """UN mood per OGNI canzone in radio_tracks/ (niente piu' media di gruppo!).
    Per le canzoni NUOVE scarica anche campioni CC0 dal TIMBRO SIMILE (Freesound)."""
    az = _load_mod("analizza_tracce.py", "az")
    ffmpeg = az.trova_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "err": "ffmpeg non trovato."}
    files = tracks_list()
    if not files:
        return {"ok": False, "err": "Nessun brano in radio_tracks/. Aggiungine e riprova."}

    m = read_manifest()
    moods = m.setdefault("audioGenerator", {}).setdefault("moods", [])
    existing = {x.get("name") for x in moods}
    fs = None
    if os.path.exists(os.path.join(BASE, "_freesound_secret.json")):
        try:
            fs = _load_mod("scarica_suoni_freesound.py", "fs")
        except Exception:
            fs = None

    created, downloaded, errors = [], [], []
    for f in files:
        try:
            a = az.analizza(ffmpeg, os.path.join(TRACKS_DIR, f))
        except Exception as e:
            errors.append(f"{f}: {e}"); continue
        gen = a.get("genere", "techno")
        nome = _nome_da_file(f)
        preset = az.a_preset(a, nome)
        is_new = nome not in existing
        moods = [x for x in moods if x.get("name") != nome]   # rimpiazza se rianalizzato
        moods.append(preset)
        created.append({"name": nome, "genere": gen, "bpm": preset["bpm"], "file": f})
        if is_new and fs is not None:                          # simili SOLO per i nuovi
            try:
                downloaded += fs.scarica_simili(gen, a["centroide_hz"], n=1)
            except Exception as e:
                errors.append(f"similar {f}: {e}")

    m["audioGenerator"]["moods"] = moods
    write_manifest(m)
    return {"ok": True, "created": created, "downloaded": downloaded,
            "n": len(created), "errors": errors}


# ------------------------------------------------------------- deploy --------
def run_deploy():
    try:
        p = subprocess.run([sys.executable, os.path.join(BASE, "deploy_hostinger.py")],
                           capture_output=True, text=True, cwd=BASE, timeout=300)
        out = (p.stdout or "") + (p.stderr or "")
        return {"ok": p.returncode == 0, "log": out[-1500:]}
    except Exception as e:
        return {"ok": False, "log": str(e)}


# =============================================================== HTTP =========
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silenzioso

    # -- helpers ------------------------------------------------------------
    def _tok(self):
        c = self.headers.get("Cookie", "")
        for part in c.split(";"):
            if part.strip().startswith("rgtok="):
                return part.strip()[6:]
        return None

    def _authed(self):
        t = self._tok()
        return t in SESSIONS

    def _send(self, code, body, ctype="application/json", cookie=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _state(self):
        m = read_manifest()
        hour = (time.gmtime().tm_hour + 2) % 24
        sch = get_schedule(m)
        return {
            "moods": [{"name": x.get("name"), "genre": x.get("genre", ""),
                       "bpm": x.get("bpm"), "custom": x.get("name") not in BASE_MOODS}
                      for x in m.get("audioGenerator", {}).get("moods", [])],
            "schedule": sch,
            "tracks": tracks_list(),
            "hour": hour,
            "currentMood": sch[hour],
            "baseMoods": BASE_MOODS,
        }

    # -- GET ----------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?")[0]
        first_run = load_secret() is None
        if path == "/":
            return self._send(200, PAGE, "text/html")
        if path == "/api/state":
            if not self._authed():
                return self._send(401, {"authed": False, "firstRun": first_run})
            st = self._state(); st["authed"] = True
            return self._send(200, st)
        if path == "/api/whoami":
            return self._send(200, {"authed": self._authed(), "firstRun": first_run})
        return self._send(404, {"err": "not found"})

    # -- POST ---------------------------------------------------------------
    def do_POST(self):
        path = self.path.split("?")[0]
        b = self._body()

        if path == "/api/setup":              # prima configurazione password
            if load_secret() is not None:
                return self._send(400, {"ok": False, "err": "gia' configurato"})
            pw = (b.get("password") or "").strip()
            if len(pw) < 6:
                return self._send(400, {"ok": False, "err": "password troppo corta (min 6)"})
            set_password(pw)
            tok = secrets.token_hex(24); SESSIONS.add(tok)
            return self._send(200, {"ok": True}, cookie=f"rgtok={tok}; HttpOnly; Path=/")

        if path == "/api/login":
            time.sleep(0.3)                   # piccolo freno anti brute-force
            if check_password((b.get("password") or "")):
                tok = secrets.token_hex(24); SESSIONS.add(tok)
                return self._send(200, {"ok": True}, cookie=f"rgtok={tok}; HttpOnly; Path=/")
            return self._send(401, {"ok": False, "err": "password errata"})

        # --- da qui in poi serve autenticazione ---
        if not self._authed():
            return self._send(401, {"ok": False, "err": "non autenticato"})

        if path == "/api/logout":
            t = self._tok(); SESSIONS.discard(t)
            return self._send(200, {"ok": True})

        if path == "/api/schedule":
            sch = b.get("schedule")
            if not isinstance(sch, list) or len(sch) != 24:
                return self._send(400, {"ok": False, "err": "schedule non valido"})
            m = read_manifest()
            m.setdefault("audioGenerator", {}).setdefault("radio", {})["schedule"] = sch
            write_manifest(m)
            return self._send(200, {"ok": True})

        if path == "/api/open-folder":
            os.makedirs(TRACKS_DIR, exist_ok=True)
            try:
                os.startfile(TRACKS_DIR)      # Windows
            except Exception as e:
                return self._send(200, {"ok": False, "err": str(e), "path": TRACKS_DIR})
            return self._send(200, {"ok": True, "path": TRACKS_DIR})

        if path == "/api/analyze":
            res = analizza_e_crea_mood(b.get("name"))
            code = 200 if res.get("ok") else 400
            return self._send(code, res)

        if path == "/api/delete-mood":
            name = b.get("name")
            if name in BASE_MOODS:
                return self._send(400, {"ok": False, "err": "non puoi togliere i generi base"})
            m = read_manifest()
            ag = m.setdefault("audioGenerator", {})
            ag["moods"] = [x for x in ag.get("moods", []) if x.get("name") != name]
            # togli il nome dallo schedule (sostituisci con TECHNO)
            r = ag.setdefault("radio", {})
            r["schedule"] = [s if s != name else "TECHNO" for s in get_schedule(m)]
            write_manifest(m)
            return self._send(200, {"ok": True})

        if path == "/api/set-genre":               # correggi il genere di un mood custom
            name = b.get("name")
            genre = str(b.get("genre", "")).lower()
            az = _load_mod("analizza_tracce.py", "az")
            if genre not in az.GENERI:
                return self._send(400, {"ok": False, "err": "genere non valido"})
            if name in BASE_MOODS:
                return self._send(400, {"ok": False, "err": "i generi base non si cambiano"})
            m = read_manifest()
            found = False
            for x in m.get("audioGenerator", {}).get("moods", []):
                if x.get("name") == name:
                    az.applica_genere(x, genre); found = True; break
            if not found:
                return self._send(404, {"ok": False, "err": "mood non trovato"})
            write_manifest(m)
            return self._send(200, {"ok": True, "genre": genre})

        if path == "/api/save-sound":
            genre = str(b.get("genre", "")).lower()
            name = re.sub(r"[^a-z0-9_]", "", str(b.get("name", "")).lower())[:24]
            wav_b64 = b.get("wav", "")
            if genre not in ("techno", "minimal", "psytrance", "trance"):
                return self._send(400, {"ok": False, "err": "genere non valido"})
            if not name:
                return self._send(400, {"ok": False, "err": "nome non valido"})
            try:
                data = base64.b64decode(wav_b64)
            except Exception:
                return self._send(400, {"ok": False, "err": "audio non valido"})
            if data[:4] != b"RIFF" or len(data) > 6_000_000:
                return self._send(400, {"ok": False, "err": "WAV non valido"})
            d = os.path.join(BASE, "assets", "sounds", genre)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, name + ".wav"), "wb").write(data)
            return self._send(200, {"ok": True, "path": f"assets/sounds/{genre}/{name}.wav"})

        if path == "/api/deploy":
            return self._send(200, run_deploy())

        return self._send(404, {"ok": False, "err": "not found"})


# =============================================================== UI ===========
PAGE = r"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Regia TeknoSteps</title>
<style>
 :root{--bg:#070707;--ink:#f2f2ee;--muted:#8f8f88;--neon:#b6ff00;--card:#101010;--line:#222;
   --techno:#b6ff00;--minimal:#38bdf8;--psytrance:#c084fc;--trance:#fb7185;--custom:#f59e0b;}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);
   font-family:'Segoe UI',system-ui,sans-serif}
 .wrap{max-width:1000px;margin:0 auto;padding:22px 18px 80px}
 h1{font-size:22px;letter-spacing:3px;margin:0} .sub{color:var(--muted);font-size:13px;margin:4px 0 20px}
 .hdr{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:14px}
 .neon{color:var(--neon)}
 .tabs{display:flex;gap:8px;margin:0 0 18px;padding:12px 0 10px;position:sticky;top:0;z-index:20;background:var(--bg);flex-wrap:wrap;border-bottom:1px solid var(--line)}
 .tab{padding:9px 16px;border:1px solid var(--line);border-radius:10px;background:var(--card);
   cursor:pointer;font-weight:600;font-size:14px} .tab.on{border-color:var(--neon);color:var(--neon)}
 .panel{display:none} .panel.on{display:block}
 .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
 button.act{background:var(--neon);color:#0a0a0a;border:none;border-radius:10px;padding:11px 18px;
   font-weight:800;cursor:pointer;letter-spacing:.5px} button.act:hover{filter:brightness(1.08)}
 button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);border-radius:10px;
   padding:10px 16px;cursor:pointer} button.ghost:hover{border-color:var(--neon)}
 input{background:#000;color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:11px 13px;font-size:15px;width:100%}
 label{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin:12px 0 6px}
 .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
 @media(max-width:640px){.grid{grid-template-columns:repeat(2,1fr)}}
 .slot{border:1px solid var(--line);border-radius:10px;padding:8px;background:#0c0c0c}
 .slot .h{font-size:12px;color:var(--muted);font-weight:700}
 .slot.now{outline:2px solid var(--neon)}
 select{width:100%;margin-top:5px;background:#000;color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px;font-weight:700}
 .chip{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:800}
 .moodrow{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line)}
 .dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:8px}
 .msg{margin-top:12px;font-size:14px;padding:10px 12px;border-radius:9px;display:none}
 .msg.ok{display:block;background:rgba(182,255,0,.08);border:1px solid var(--neon)}
 .msg.err{display:block;background:rgba(255,80,80,.1);border:1px solid #ff5050;color:#ffcaca}
 pre{white-space:pre-wrap;background:#000;border:1px solid var(--line);border-radius:9px;padding:12px;font-size:12px;color:#bdbdbd;max-height:240px;overflow:auto}
 .center{max-width:360px;margin:12vh auto;text-align:center}
</style></head><body>

<!-- LOGIN / SETUP -->
<div id="gate" class="center" style="display:none">
  <h1>REGIA <span class="neon">TEKNOSTEPS</span></h1>
  <p class="sub" id="gateSub">Accesso riservato</p>
  <div class="card">
    <label id="gateLbl">Password</label>
    <input id="pw" type="password" onkeydown="if(event.key==='Enter')gate()">
    <div style="height:12px"></div>
    <button class="act" style="width:100%" onclick="gate()" id="gateBtn">Entra</button>
    <div id="gateMsg" class="msg"></div>
  </div>
</div>

<!-- APP -->
<div id="app" class="wrap" style="display:none">
  <div class="hdr">
    <div><h1>REGIA <span class="neon">TEKNOSTEPS</span></h1>
      <div class="sub">Ora stazione: <b id="hourNow">--</b>:00 · sta suonando <b id="moodNow" class="neon">--</b></div></div>
    <button class="ghost" onclick="logout()">Esci</button>
  </div>
  <div class="tabs">
    <div class="tab on" data-t="pal" onclick="tab('pal')">Palinsesto</div>
    <div class="tab" data-t="moods" onclick="tab('moods')">Mood</div>
    <div class="tab" data-t="tracks" onclick="tab('tracks')">Brani</div>
    <div class="tab" data-t="studio" onclick="tab('studio')">Studio suoni</div>
    <div class="tab" data-t="pub" onclick="tab('pub')">Pubblica</div>
  </div>

  <!-- PALINSESTO -->
  <div id="pal" class="panel on">
    <div class="card">
      <b>Scaletta della giornata</b>
      <p class="sub">Scegli il genere per ogni ora. La radio evolve nel giorno e resta uguale per tutti gli ascoltatori. Le canzoni sono generate in tempo reale: qui decidi solo il MOOD.</p>
      <div id="slots" class="grid"></div>
      <div style="margin-top:16px;display:flex;gap:10px;align-items:center">
        <button class="act" onclick="saveSched()">Salva palinsesto</button>
        <button class="ghost" onclick="fillDay()">Riempi la giornata (varia)</button>
      </div>
      <div id="palMsg" class="msg"></div>
    </div>
  </div>

  <!-- MOOD -->
  <div id="moods" class="panel">
    <div class="card">
      <b>Generi / Mood attivi</b>
      <p class="sub">4 generi base + i mood creati dalle tue tracce. I custom entrano "a sorpresa" nella radio.</p>
      <div id="moodList"></div>
    </div>
  </div>

  <!-- BRANI -->
  <div id="tracks" class="panel">
    <div class="card">
      <b>I tuoi brani → un mood PER canzone</b>
      <p class="sub">Metti i brani nella cartella e premi Analizza: <b>ogni canzone</b> diventa un mood a sé (nome dal file, genere riconosciuto). Per le canzoni NUOVE scarico anche campioni CC0 dal <b>timbro simile</b> (Freesound). I file restano sul tuo PC.</p>
      <button class="ghost" onclick="openFolder()">📂 Apri cartella brani</button>
      <div id="trkList" style="margin:14px 0;color:var(--muted);font-size:14px"></div>
      <button class="act" onclick="analyze()">Analizza &amp; crea i mood</button>
      <div id="trkMsg" class="msg"></div>
    </div>
  </div>

  <!-- STUDIO SUONI -->
  <div id="studio" class="panel">
    <div class="card">
      <b>Studio suoni</b>
      <p class="sub">Scegli un suono, gira le manopole, premi Ascolta (anche "In ritmo" per sentirlo ripetuto). Quando ti piace, Salva: entra subito nella libreria del genere. Poi Pubblica per mandarlo online. Quello che senti e' esattamente cio' che viene salvato.</p>
      <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end">
        <div><label>Tipo di suono</label>
          <select id="stType" onchange="stBuild()">
            <option value="kick">Kick (cassa)</option>
            <option value="bass">Bass (basso)</option>
            <option value="stab">Stab / Lead</option>
            <option value="hat">Hi-hat</option>
          </select></div>
        <div><label>Genere (dove salvo)</label>
          <select id="stGenre">
            <option value="techno">Techno</option><option value="minimal">Minimal</option>
            <option value="psytrance">Psytrance</option><option value="trance">Trance</option>
          </select></div>
      </div>
      <div id="stKnobs" style="margin:16px 0"></div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <button class="act" onclick="stPlay()">&#9654; Ascolta</button>
        <button class="ghost" onclick="stLoop()"><span id="stLoopLbl">&#9654; In ritmo</span></button>
        <input id="stName" style="max-width:160px" placeholder="nome (es. kick)">
        <button class="act" onclick="stSave()">&#128190; Salva nel genere</button>
      </div>
      <div id="stMsg" class="msg"></div>
    </div>
  </div>

  <!-- PUBBLICA -->
  <div id="pub" class="panel">
    <div class="card">
      <b>Pubblica online</b>
      <p class="sub">Manda palinsesto e mood aggiornati su teknosteps.com. Serve la connessione.</p>
      <button class="act" onclick="deploy()">🚀 Pubblica ora</button>
      <div id="pubMsg" class="msg"></div>
      <pre id="pubLog" style="display:none"></pre>
    </div>
  </div>
</div>

<script>
const GENRE_COLORS={TECHNO:'var(--techno)',MINIMAL:'var(--minimal)',PSYTRANCE:'var(--psytrance)',TRANCE:'var(--trance)'};
let STATE=null;
const $=id=>document.getElementById(id);
function msg(el,t,ok){el.className='msg '+(ok?'ok':'err');el.textContent=t;}

async function boot(){
  const w=await (await fetch('/api/whoami')).json();
  if(w.authed){ return load(); }
  $('gate').style.display='block';
  if(w.firstRun){
    $('gateSub').textContent='Prima configurazione: crea la TUA password';
    $('gateLbl').textContent='Nuova password (min 6)';
    $('gateBtn').textContent='Crea e entra';
    $('gate').dataset.mode='setup';
  }
}
async function gate(){
  const mode=$('gate').dataset.mode==='setup'?'setup':'login';
  const r=await fetch('/api/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({password:$('pw').value})});
  const j=await r.json();
  if(j.ok){ $('gate').style.display='none'; load(); }
  else msg($('gateMsg'),j.err||'Errore',false);
}
async function logout(){ await fetch('/api/logout',{method:'POST'}); location.reload(); }

async function load(){
  const r=await fetch('/api/state'); if(r.status===401){location.reload();return;}
  STATE=await r.json();
  $('app').style.display='block';
  $('hourNow').textContent=String(STATE.hour).padStart(2,'0');
  $('moodNow').textContent=STATE.currentMood;
  renderSlots(); renderMoods(); renderTracks();
}
function tab(t){document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x.dataset.t===t));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('on',p.id===t));}

function moodOptions(sel){
  return STATE.moods.map(m=>`<option ${m.name===sel?'selected':''}>${m.name}</option>`).join('');
}
function renderSlots(){
  $('slots').innerHTML=STATE.schedule.map((g,h)=>`
   <div class="slot ${h===STATE.hour?'now':''}">
     <div class="h">${String(h).padStart(2,'0')}:00</div>
     <select data-h="${h}" onchange="this.style.borderColor=(GENRE_COLORS[this.value]||'var(--custom)')">
       ${moodOptions(g)}
     </select>
   </div>`).join('');
  document.querySelectorAll('#slots select').forEach(s=>s.style.borderColor=(GENRE_COLORS[s.value]||'var(--custom)'));
}
function fillDay(){
  const g=STATE.baseMoods, pat=[1,1,1,2,2,2,3,3,0,0,0,1,0,0,1,0,2,2,3,3,0,2,2,1];
  document.querySelectorAll('#slots select').forEach((s,h)=>{s.value=g[pat[h]];s.style.borderColor=GENRE_COLORS[s.value];});
}
async function saveSched(){
  const sch=[...document.querySelectorAll('#slots select')].map(s=>s.value);
  const r=await fetch('/api/schedule',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({schedule:sch})});
  const j=await r.json(); msg($('palMsg'),j.ok?'Palinsesto salvato ✓ (ricordati di Pubblicare)':'Errore',j.ok);
  if(j.ok){STATE.schedule=sch;}
}

const GENERI=['techno','minimal','psytrance','trance','hardtek'];
function renderMoods(){
  $('moodList').innerHTML=STATE.moods.map(m=>{
    const col=GENRE_COLORS[m.name]||'var(--custom)';
    let ctrl='<span class="sub">base</span>';
    if(m.custom){
      const sel=`<select onchange="setGenre('${m.name}',this.value)" title="correggi il genere">${GENERI.map(g=>`<option ${g===m.genre?'selected':''}>${g}</option>`).join('')}</select>`;
      ctrl=`${sel} <button class="ghost" onclick="delMood('${m.name}')">Elimina</button>`;
    }
    return `<div class="moodrow"><div><span class="dot" style="background:${col}"></span>
      <b>${m.name}</b> <span class="sub">· ${m.bpm||'?'} BPM</span></div>
      <div style="display:flex;gap:8px;align-items:center">${ctrl}</div></div>`;
  }).join('');
}
async function setGenre(name,genre){
  const r=await fetch('/api/set-genre',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,genre})}); if((await r.json()).ok) load();
}
async function delMood(name){
  if(!confirm('Eliminare il mood '+name+'?'))return;
  const r=await fetch('/api/delete-mood',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name})}); if((await r.json()).ok) load();
}

function renderTracks(){
  const t=STATE.tracks;
  $('trkList').innerHTML=t.length?('🎵 '+t.length+' brani: '+t.map(x=>x.replace(/\.[^.]+$/,'')).join(', ')):
    'Nessun brano ancora. Premi "Apri cartella brani" e trascina i tuoi mp3.';
}
async function openFolder(){ await fetch('/api/open-folder',{method:'POST'}); }
async function analyze(){
  msg($('trkMsg'),'Analisi in corso… (analizzo ogni brano e scarico campioni simili, può richiedere un minuto)',true);
  const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
  const j=await r.json();
  if(j.ok){
    const lines=(j.created||[]).map(c=>`• ${c.name} — ${(c.genere||'?').toUpperCase()} (${c.bpm} BPM)`).join('<br>');
    const dl=(j.downloaded||[]).length;
    msg($('trkMsg'),`Creati ${j.n} mood (uno per canzone):<br>${lines}<br>Campioni simili scaricati: ${dl}.<br>Ricordati di Pubblicare.`,true);
    load();
  } else msg($('trkMsg'),j.err||'Errore',false);
}
async function deploy(){
  msg($('pubMsg'),'Pubblicazione in corso…',true); $('pubLog').style.display='none';
  const r=await fetch('/api/deploy',{method:'POST'}); const j=await r.json();
  msg($('pubMsg'),j.ok?'Pubblicato online ✓':'Errore nella pubblicazione',j.ok);
  $('pubLog').style.display='block'; $('pubLog').textContent=j.log||'';
}
// ============================ STUDIO SUONI ============================
const SR=44100;
let STAC=null; function stCtx(){ if(!STAC) STAC=new (window.AudioContext||window.webkitAudioContext)(); return STAC; }
function tanhCurve(k){ const n=1024,c=new Float32Array(n),d=Math.tanh(k)||1; for(let i=0;i<n;i++){const x=i/(n-1)*2-1;c[i]=Math.tanh(x*k)/d;} return c; }
function noiseBuf(ctx,dur){ const n=Math.max(1,Math.ceil(ctx.sampleRate*dur)),b=ctx.createBuffer(1,n,ctx.sampleRate),d=b.getChannelData(0); for(let i=0;i<n;i++)d[i]=Math.random()*2-1; return b; }

function buildKick(ctx,p,dest,t){
  const dur=p.dur;
  const o=ctx.createOscillator();o.type='sine';
  o.frequency.setValueAtTime(p.f0,t);o.frequency.exponentialRampToValueAtTime(p.f1,t+0.05);
  const ws=ctx.createWaveShaper();ws.curve=tanhCurve(p.drive);
  const g=ctx.createGain();g.gain.setValueAtTime(1,t);g.gain.exponentialRampToValueAtTime(0.0001,t+dur);
  o.connect(ws);ws.connect(g);g.connect(dest);o.start(t);o.stop(t+dur+0.05);
  const nz=ctx.createBufferSource();nz.buffer=noiseBuf(ctx,0.05);
  const hpf=ctx.createBiquadFilter();hpf.type='highpass';hpf.frequency.value=1500;
  const cg=ctx.createGain();cg.gain.setValueAtTime(p.click,t);cg.gain.exponentialRampToValueAtTime(0.0001,t+0.02);
  nz.connect(hpf);hpf.connect(cg);cg.connect(dest);nz.start(t);nz.stop(t+0.06);
  return dur;
}
function buildBass(ctx,p,dest,t){
  const dur=p.dur,f=55;
  const g=ctx.createGain();g.gain.setValueAtTime(0.0001,t);g.gain.exponentialRampToValueAtTime(0.9,t+0.006);g.gain.exponentialRampToValueAtTime(0.0001,t+dur);
  const ws=ctx.createWaveShaper();ws.curve=tanhCurve(p.drive);
  if(p.style==='fm'){
    const car=ctx.createOscillator();car.type='sine';car.frequency.value=f;
    const mod=ctx.createOscillator();mod.type='sine';mod.frequency.value=f*p.ratio;
    const mg=ctx.createGain();mg.gain.setValueAtTime(f*p.index,t);mg.gain.exponentialRampToValueAtTime(f*0.5,t+dur*0.6);
    mod.connect(mg);mg.connect(car.frequency);car.connect(ws);car.start(t);mod.start(t);car.stop(t+dur+0.05);mod.stop(t+dur+0.05);
    ws.connect(g);
  }else{
    const lp=ctx.createBiquadFilter();lp.type='lowpass';lp.Q.value=3;lp.frequency.setValueAtTime(p.cut0,t);lp.frequency.exponentialRampToValueAtTime(p.cut1,t+dur*0.5);
    const o1=ctx.createOscillator();o1.type='sawtooth';o1.frequency.value=f;
    const o2=ctx.createOscillator();o2.type='sawtooth';o2.frequency.value=f;o2.detune.value=7;
    const o3=ctx.createOscillator();o3.type='square';o3.frequency.value=f/2;
    [o1,o2,o3].forEach(o=>{o.connect(lp);o.start(t);o.stop(t+dur+0.05);});
    lp.connect(ws);ws.connect(g);
  }
  g.connect(dest);return dur;
}
function buildStab(ctx,p,dest,t){
  const dur=p.dur,f=220;
  const g=ctx.createGain();g.gain.setValueAtTime(0.0001,t);g.gain.exponentialRampToValueAtTime(0.8,t+0.006);g.gain.exponentialRampToValueAtTime(0.0001,t+dur);
  if(p.type==='supersaw'){
    const lp=ctx.createBiquadFilter();lp.type='lowpass';lp.Q.value=2;lp.frequency.setValueAtTime(p.cutoff,t);lp.frequency.exponentialRampToValueAtTime(1300,t+dur);
    [-14,-7,-3,0,3,7,14].forEach(d=>{const o=ctx.createOscillator();o.type='sawtooth';o.frequency.value=f;o.detune.value=d;o.connect(lp);o.start(t);o.stop(t+dur+0.05);});
    lp.connect(g);
  }else{
    const car=ctx.createOscillator();car.type='sine';car.frequency.value=f;
    const mod=ctx.createOscillator();mod.type='sine';mod.frequency.value=f*p.ratio;
    const mg=ctx.createGain();mg.gain.setValueAtTime(f*p.index,t);mg.gain.exponentialRampToValueAtTime(f*0.3,t+dur);
    mod.connect(mg);mg.connect(car.frequency);car.connect(g);car.start(t);mod.start(t);car.stop(t+dur+0.05);mod.stop(t+dur+0.05);
  }
  g.connect(dest);return dur;
}
function buildHat(ctx,p,dest,t){
  const dur=p.dur;
  const nz=ctx.createBufferSource();nz.buffer=noiseBuf(ctx,dur+0.05);
  const hpf=ctx.createBiquadFilter();hpf.type='highpass';hpf.frequency.value=p.cutoff;
  const g=ctx.createGain();g.gain.setValueAtTime(0.8,t);g.gain.exponentialRampToValueAtTime(0.0001,t+dur);
  nz.connect(hpf);hpf.connect(g);g.connect(dest);nz.start(t);nz.stop(t+dur+0.05);
  return dur;
}
const BUILD={kick:buildKick,bass:buildBass,stab:buildStab,hat:buildHat};
const VOICES={
 kick:{params:[{k:'f0',l:'Pitch iniziale',min:80,max:220,step:1,def:150},{k:'f1',l:'Pitch finale',min:30,max:80,step:1,def:48},{k:'dur',l:'Durata',min:0.1,max:0.6,step:0.01,def:0.34},{k:'drive',l:'Distorsione',min:1,max:5,step:0.1,def:2.6},{k:'click',l:'Click attacco',min:0,max:1,step:0.05,def:0.4}]},
 bass:{params:[{k:'style',l:'Tipo',sel:['reese','fm'],def:'reese'},{k:'dur',l:'Durata',min:0.1,max:0.6,step:0.01,def:0.36},{k:'cut0',l:'Filtro apertura',min:500,max:6000,step:50,def:3000},{k:'cut1',l:'Filtro chiusura',min:150,max:1500,step:10,def:500},{k:'drive',l:'Distorsione',min:1,max:4,step:0.1,def:2.2},{k:'ratio',l:'FM ratio',min:0.5,max:4,step:0.1,def:2},{k:'index',l:'FM index',min:1,max:8,step:0.1,def:4}]},
 stab:{params:[{k:'type',l:'Tipo',sel:['fm','supersaw'],def:'fm'},{k:'dur',l:'Durata',min:0.1,max:0.9,step:0.01,def:0.5},{k:'ratio',l:'FM ratio',min:0.5,max:5,step:0.1,def:1.5},{k:'index',l:'FM index',min:1,max:8,step:0.1,def:3},{k:'cutoff',l:'Filtro (supersaw)',min:400,max:5000,step:50,def:700}]},
 hat:{params:[{k:'dur',l:'Durata',min:0.02,max:0.4,step:0.005,def:0.05},{k:'cutoff',l:'Brillantezza',min:3000,max:9000,step:100,def:6500}]},
};
function stBuild(){
 const type=$('stType').value,cfg=VOICES[type];
 $('stKnobs').innerHTML=cfg.params.map(pr=>{
   if(pr.sel)return `<div style="display:inline-block;margin:6px 18px 6px 0"><label>${pr.l}</label><select data-k="${pr.k}">${pr.sel.map(o=>`<option ${o===pr.def?'selected':''}>${o}</option>`).join('')}</select></div>`;
   return `<div style="margin:9px 0;max-width:420px"><label>${pr.l}: <b id="v_${pr.k}">${pr.def}</b></label><input type="range" style="width:100%" data-k="${pr.k}" min="${pr.min}" max="${pr.max}" step="${pr.step}" value="${pr.def}" oninput="var e=document.getElementById('v_'+this.dataset.k);if(e)e.textContent=this.value"></div>`;
 }).join('');
 $('stName').value=type;
}
function stParams(){const p={};document.querySelectorAll('#stKnobs [data-k]').forEach(el=>{const k=el.dataset.k;p[k]=el.type==='range'?parseFloat(el.value):el.value;});return p;}
function stPlay(){const c=stCtx();c.resume();BUILD[$('stType').value](c,stParams(),c.destination,c.currentTime+0.03);}
let stTimer=null;
function stLoop(){
 if(stTimer){clearInterval(stTimer);stTimer=null;$('stLoopLbl').innerHTML='&#9654; In ritmo';return;}
 const bpm=({techno:132,minimal:126,psytrance:146,trance:138})[$('stGenre').value]||132;
 const c=stCtx();c.resume();const type=$('stType').value,beat=60/bpm;
 $('stLoopLbl').innerHTML='&#9632; Stop ritmo';
 const tick=()=>BUILD[type](c,stParams(),c.destination,c.currentTime+0.02);
 tick();stTimer=setInterval(tick,beat*1000);
}
function encodeWav(ab){
 const n=ab.length,ch=ab.getChannelData(0),buf=new ArrayBuffer(44+n*2),dv=new DataView(buf);
 const w=(o,s)=>{for(let i=0;i<s.length;i++)dv.setUint8(o+i,s.charCodeAt(i));};
 w(0,'RIFF');dv.setUint32(4,36+n*2,true);w(8,'WAVE');w(12,'fmt ');dv.setUint32(16,16,true);dv.setUint16(20,1,true);dv.setUint16(22,1,true);dv.setUint32(24,SR,true);dv.setUint32(28,SR*2,true);dv.setUint16(32,2,true);dv.setUint16(34,16,true);w(36,'data');dv.setUint32(40,n*2,true);
 let o=44;for(let i=0;i<n;i++){let s=Math.max(-1,Math.min(1,ch[i]));dv.setInt16(o,s*32767,true);o+=2;}
 return buf;
}
function toB64(bytes){let bin='';const CH=0x8000;for(let i=0;i<bytes.length;i+=CH)bin+=String.fromCharCode.apply(null,bytes.subarray(i,i+CH));return btoa(bin);}
async function stSave(){
 const type=$('stType').value,genre=$('stGenre').value,p=stParams();
 const name=($('stName').value||type);
 const dur=(p.dur||0.4)+0.15;
 const oc=new OfflineAudioContext(1,Math.ceil(SR*dur),SR);
 BUILD[type](oc,p,oc.destination,0);
 const rb=await oc.startRendering();
 const b64=toB64(new Uint8Array(encodeWav(rb)));
 msg($('stMsg'),'Salvataggio...',true);
 const r=await fetch('/api/save-sound',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({genre,name,wav:b64})});
 const j=await r.json();
 msg($('stMsg'),j.ok?('Salvato: '+j.path+' - ora premi Pubblica per mandarlo online'):(j.err||'Errore'),j.ok);
}
stBuild();
boot();
</script></body></html>"""


def main():
    os.makedirs(TRACKS_DIR, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = f"http://127.0.0.1:{PORT}"
    print("=" * 56)
    print("  REGIA TEKNOSTEPS attiva su", url)
    print("  (solo sul tuo PC — chiudi questa finestra per spegnerla)")
    print("=" * 56)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Regia spenta.")


if __name__ == "__main__":
    main()
