# -*- coding: utf-8 -*-
"""
Monta un video YouTube per ogni brano: sfondo (copertina sfocata) + copertina
centrata + onda sonora reattiva verde acido. 1920x1080. Made in Italy.

Leggero: lo sfondo 1920x1080 viene composto UNA volta con PIL (niente boxblur
per-fotogramma in ffmpeg -> niente 'Cannot allocate memory'). ffmpeg fa solo
loop dello sfondo statico + overlay onda + audio.

Uso: python crea_video_canzone.py "Cornamusa Acida"   -> un brano
     python crea_video_canzone.py --all                -> tutti (salta i gia' fatti)
"""
import os, sys, json, subprocess, shutil, tempfile
from PIL import Image, ImageFilter, ImageEnhance
PROJ=os.path.dirname(os.path.abspath(__file__))
REL=os.path.join(PROJ,"release")
OUT=os.path.join(REL,"_videos"); os.makedirs(OUT,exist_ok=True)
# lavora FUORI da OneDrive (OneDrive blocca i file mentre ffmpeg scrive).
# Portabile: cartella temporanea di sistema (va bene sia su Windows che nel cloud Linux).
WORK=os.environ.get("TS_WORK") or os.path.join(tempfile.gettempdir(), "teknosteps_vid")
os.makedirs(WORK, exist_ok=True)
TMP=os.path.join(WORK,"_bg"); os.makedirs(TMP,exist_ok=True)
# ffmpeg: quello di sistema (Linux/cloud), altrimenti quello di Mureka su Windows
FF=shutil.which("ffmpeg") or r"C:\Users\stell\AppData\Local\Mureka Co\ffmpeg.exe"
ACID="0xB6FF00"; W,H=1280,720   # 720p: leggero e adeguato (arte Mureka nativa 720px)

def build_bg(cover, dst):
    c=Image.open(cover).convert("RGB")
    # sfondo: riempi 1920x1080, sfoca, scurisci
    s=max(W/c.width, H/c.height)
    bg=c.resize((int(c.width*s)+1,int(c.height*s)+1), Image.LANCZOS)
    x=(bg.width-W)//2; y=(bg.height-H)//2
    bg=bg.crop((x,y,x+W,y+H)).filter(ImageFilter.GaussianBlur(24))
    bg=ImageEnhance.Brightness(bg).enhance(0.42)
    # copertina centrata (adatta al 720p), alzata un po'
    fgs=620
    fg=c.resize((fgs,fgs), Image.LANCZOS)
    bg.paste(fg, ((W-fgs)//2, (H-fgs)//2-24))
    bg.save(dst)
    return dst

def render(track, force=False):
    cover=os.path.join(REL,"_covers",f"cover - {track}.jpg")
    audio=os.path.join(REL,"_wav",f"TeknoSteps - {track}.wav")
    final=os.path.join(OUT,f"TeknoSteps - {track}.mp4")
    out=os.path.join(WORK,f"TeknoSteps - {track}.mp4")   # render fuori da OneDrive
    if not (os.path.exists(cover) and os.path.exists(audio)):
        print("SKIP (manca cover/audio):",track); return None
    if (not force) and os.path.exists(final) and os.path.getsize(final)>40*1048576:
        print("GIA' FATTO:",track); return final
    bg=build_bg(cover, os.path.join(TMP,f"{track}.png"))
    fc=("[1:a]showwaves=s=1280x150:mode=cline:colors=%s:rate=25,format=rgba[w];"
        "[0:v][w]overlay=0:H-160[v]" % ACID)
    cmd=[FF,"-y","-threads","1","-loop","1","-i",bg,"-i",audio,
         "-filter_complex",fc,"-map","[v]","-map","1:a",
         "-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","256k","-r","25","-shortest",out]
    r=subprocess.run(cmd,capture_output=True,text=True,errors="ignore")
    if r.returncode!=0 or not os.path.exists(out) or os.path.getsize(out)<1024:
        print("ERR",track); print(r.stderr[-800:])
        if os.path.exists(out): os.remove(out)
        return None
    try: os.remove(bg)
    except: pass
    # copia il file finito dentro il progetto (OneDrive) solo a render concluso
    shutil.copy2(out, final)
    try: os.remove(out)
    except: pass
    print("OK",track, f"({os.path.getsize(final)//1048576} MB)")
    return final

if __name__=="__main__":
    force="--force" in sys.argv
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv:
        man=json.load(open(os.path.join(REL,"manifest.json"),encoding="utf-8"))
        for t in man["tracks"]: render(t["track"], force=force)
    elif args:
        render(args[0], force=True)
    else:
        render("Cornamusa Acida", force=True)
