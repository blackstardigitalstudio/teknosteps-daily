# -*- coding: utf-8 -*-
"""
Pubblica i singoli della release Mureka su YouTube (canale TeknoSteps), in ordine
di cascata, con miniatura + descrizione SEO. Si ferma da solo quando la quota
YouTube e' esaurita (riprende il giorno dopo dai non-pubblicati). Made in Italy.
Uso: python pubblica_release.py [--max N] [--privacy public|unlisted]
"""
import os, sys, json, shutil, subprocess, time
from googleapiclient.errors import HttpError
import youtube_upload as yu

PROJ=os.path.dirname(os.path.abspath(__file__))
REL=os.path.join(PROJ,"release")
VID=os.path.join(REL,"_videos")
# ffmpeg: quello di sistema (Linux/cloud), altrimenti quello di Mureka su Windows
FF=shutil.which("ffmpeg") or r"C:\Users\stell\AppData\Local\Mureka Co\ffmpeg.exe"
STATE=os.path.join(REL,"_published.json")

# ordine cascata (EP1 -> EP2 -> EP3)
ORDER=["Cornamusa Acida","Iron Highlands","Cornamusa Brutale","Iron Thistle",
"Cornamusa Distorta","Radura Goa","Tribal Industrial Distortion","Battito Tribale Distorto",
"Distorsione Tribale","Runa Distorta","Tribal Distorsione","Distorsione Sociale",
"Cazzuto","Cambio de Nervio","Betonfeuer"]

GENRE={"EP1_Highland_Goa":("Acid Goa / Psytrance","goa,psytrance,acid techno,goa trance"),
 "EP2_Tribal_Distortion":("Tribal / Industrial Techno","tribal techno,industrial techno,hard techno,psytrance"),
 "EP3_Hardtek_Italiano":("Hardtek / Hard Techno","hardtek,hard techno,tribecore,frenchcore")}
EPNAME={"EP1_Highland_Goa":"Highland Goa","EP2_Tribal_Distortion":"Tribal Distortion","EP3_Hardtek_Italiano":"Hardtek Italiano"}

def load_state():
    if os.path.exists(STATE): return json.load(open(STATE,encoding="utf-8"))
    return {}
def save_state(s): json.dump(s,open(STATE,"w",encoding="utf-8"),indent=2,ensure_ascii=False)

def thumb(track):
    src=os.path.join(VID,f"TeknoSteps - {track}.mp4")
    out=os.path.join(VID,f"_thumb_{abs(hash(track))%99999}.jpg")
    subprocess.run([FF,"-y","-ss","60","-i",src,"-frames:v","1","-vf","scale=1280:720","-q:v","3",out],
                   capture_output=True)
    return out if os.path.exists(out) else None

def desc(track, ep):
    g,_=GENRE[ep]; epn=EPNAME[ep]
    return f"""{track} — TeknoSteps. {g}. Dark, ipnotico, senza volto: solo passi e bassi.

Dall'EP \"{epn}\". Genere: {g} · Made in Italy.

Musica © TeknoSteps — opera originale, tutti i diritti riservati. Royalty-free: libera da usare gratis nei tuoi video, stream, podcast e progetti — basta accreditare "TeknoSteps" (teknosteps.com). / Free to use with credit to TeknoSteps.

#{g.split('/')[0].strip().replace(' ','').lower()} #psytrance #teknosteps #darkpsy #tribaltechno #madeinitaly

TeknoSteps · No faces. Just steps and bass.
Credits: Blackstar Digital Studio — blackstardigitalstudio.com"""

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--max",type=int,default=99)
    ap.add_argument("--privacy",default="public",choices=["public","unlisted","private"])
    a=ap.parse_args()
    man={t["track"]:t for t in json.load(open(os.path.join(REL,"manifest.json"),encoding="utf-8"))["tracks"]}
    state=load_state()
    yt=yu.get_service()   # canale TeknoSteps (token.json)
    from googleapiclient.http import MediaFileUpload
    done=0
    for track in ORDER:
        if track in state and state[track].get("id"):
            print(f"[skip] gia' pubblicato: {track} -> {state[track]['id']}"); continue
        if done>=a.max: print(f"[stop] raggiunto max {a.max}"); break
        ep=man[track]["ep"]; g,tags=GENRE[ep]
        video=os.path.join(VID,f"TeknoSteps - {track}.mp4")
        if not os.path.exists(video): print("[manca video]",track); continue
        title=f"TeknoSteps - {track} | {g} [Royalty Free]"
        body={"snippet":{"title":title[:100],"description":desc(track,ep)[:4900],
              "tags":[t.strip() for t in ("teknosteps,"+tags+",royalty free music,royalty free psytrance,free to use music,copyright free music,electronic music,made in italy").split(",")],
              "categoryId":"10","defaultLanguage":"en","defaultAudioLanguage":"en"},
              "status":{"privacyStatus":a.privacy,"selfDeclaredMadeForKids":False}}
        try:
            print(f"[i] carico {track} ({os.path.getsize(video)//1048576}MB)...")
            media=MediaFileUpload(video,chunksize=-1,resumable=True)
            req=yt.videos().insert(part="snippet,status",body=body,media_body=media)
            resp=None
            while resp is None:
                st,resp=req.next_chunk()
            vid=resp["id"]
            th=thumb(track)
            if th:
                try: yt.thumbnails().set(videoId=vid,media_body=MediaFileUpload(th)).execute()
                except Exception as e: print("   (thumb ko:",str(e)[:60],")")
            state[track]={"id":vid,"url":f"https://youtu.be/{vid}","privacy":a.privacy}
            save_state(state)
            print(f"[OK] {track} -> https://youtu.be/{vid}")
            done+=1
        except HttpError as e:
            msg=str(e)
            if "quota" in msg.lower():
                print(f"[QUOTA ESAURITA] mi fermo a {done} upload. Riprendo domani dai non-pubblicati.")
                break
            print("[ERR]",track,msg[:200])
    # riepilogo
    pub=[t for t in ORDER if t in state and state[t].get("id")]
    print(f"\n=== Pubblicati {len(pub)}/15 ===")
    for t in pub: print(f"  {t}: {state[t]['url']}")
    rem=[t for t in ORDER if t not in pub]
    if rem: print("Restano:",", ".join(rem))

if __name__=="__main__":
    main()
