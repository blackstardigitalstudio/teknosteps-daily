# -*- coding: utf-8 -*-
"""
ANALISI SUONI PSY — carattere di kick/acid/atmosfere. TeknoSteps · Made in Italy.
Su segmenti groove misura:
  - KICK attack: brillantezza del transiente (centroide 0-3kHz nei primi 15ms) + click
  - ACID (303): movimento (flux) e risonanza (peakiness) nella banda squelch 300-2500Hz
  - ATMOSFERE/aria: energia 7-12kHz + "riverbero" (coda sostenuta vs transiente)
Uso: python analisi_suoni_psy.py [file...]
"""
import os, sys, glob, subprocess, tempfile, wave
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__)); SR = 22050; SEG = 30.0
POS = [0.30, 0.5, 0.7]

def ffmpeg():
    for c in (r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe", "ffmpeg"):
        try: subprocess.run([c,"-version"],capture_output=True); return c
        except Exception: pass
    return None
def dur(ff,p):
    fp=ff.replace("ffmpeg","ffprobe")
    try: return float(subprocess.run([fp,"-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",p],capture_output=True,text=True).stdout.strip())
    except Exception: return 0.0
def seg(ff,p,ss):
    t=os.path.join(tempfile.gettempdir(),"snd.wav")
    subprocess.run([ff,"-y","-v","error","-ss",str(ss),"-t",str(SEG),"-i",p,"-ac","1","-ar",str(SR),t],capture_output=True)
    w=wave.open(t,"rb"); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768.0; w.close(); return a

def kick_onsets(x):
    N=1024; hop=512; fr=np.fft.rfftfreq(N,1/SR); sel=(fr>=40)&(fr<120); win=np.hanning(N)
    env=[]; prev=None
    for i in range(0,len(x)-N,hop):
        m=np.abs(np.fft.rfft(x[i:i+N]*win))[sel]
        if prev is not None: env.append(max((m-prev).clip(0).sum(),0))
        prev=m
    env=np.array(env); thr=env.mean()+1.4*env.std(); mind=int(SR/hop*0.2)
    pk=[]; last=-mind
    for i in range(1,len(env)-1):
        if env[i]>thr and env[i]>=env[i-1] and env[i]>env[i+1] and i-last>=mind: pk.append(i*hop); last=i
    return pk

def kick_char(x,onsets):
    fr=np.fft.rfftfreq(2048,1/SR); cs=[]; subclick=[]
    for o in onsets[:40]:
        s=x[o:o+int(0.015*SR)]
        if len(s)<256: continue
        s=np.pad(s,(0,2048-len(s)))[:2048]*np.hanning(2048)
        mag=np.abs(np.fft.rfft(s))
        lo=mag[(fr>=30)&(fr<160)].sum(); hi=mag[(fr>=160)&(fr<3000)].sum()
        c=(fr[(fr<3000)]*mag[(fr<3000)]).sum()/(mag[(fr<3000)].sum()+1e-9)
        cs.append(c); subclick.append(hi/(lo+1e-9))
    return (np.mean(cs) if cs else 0), (np.mean(subclick) if subclick else 0)

def band_flux_res(x,lo,hi):
    N=1024; hop=512; fr=np.fft.rfftfreq(N,1/SR); sel=(fr>=lo)&(fr<hi); win=np.hanning(N)
    flux=[]; flat=[]; prev=None
    for i in range(0,len(x)-N,hop):
        m=np.abs(np.fft.rfft(x[i:i+N]*win))[sel]
        if prev is not None: flux.append((m-prev).clip(0).sum())
        gm=np.exp(np.mean(np.log(m+1e-9))); am=m.mean()+1e-9
        flat.append(gm/am)   # bassa flatness = risonante (peaky = acid)
        prev=m
    return np.mean(flux), 1.0-np.mean(flat)   # ritorna (movimento, risonanza)

def air_reverb(x):
    N=1024; hop=512; fr=np.fft.rfftfreq(N,1/SR); sel=(fr>=7000)&(fr<12000); win=np.hanning(N)
    e=[]
    for i in range(0,len(x)-N,hop):
        e.append(np.abs(np.fft.rfft(x[i:i+N]*win))[sel].sum())
    e=np.array(e)
    air=e.mean()/(np.abs(x).mean()+1e-9)
    # "riverbero": quota di energia sostenuta (mediana/picco) -> alto = code lunghe
    rev=np.median(e)/(np.percentile(e,95)+1e-9)
    return air, rev

def main():
    ff=ffmpeg()
    if not ff: print("[X] ffmpeg"); sys.exit(1)
    files=sys.argv[1:] or [p for p in sorted(glob.glob(os.path.join(BASE,"_tracce_riferimento","*")))
                           if p.lower().endswith((".mp3",".wav",".flac",".m4a",".ogg"))]
    for p in files:
        print("\n"+"="*66); print(os.path.basename(p)[:60])
        d=dur(ff,p); C=[]; SC=[]; AF=[]; AR=[]; AIR=[]; REV=[]
        for fpos in POS:
            x=seg(ff,p,d*fpos)
            if len(x)<SR: continue
            on=kick_onsets(x); c,sc=kick_char(x,on); af,ar=band_flux_res(x,300,2500); air,rev=air_reverb(x)
            C.append(c); SC.append(sc); AF.append(af); AR.append(ar); AIR.append(air); REV.append(rev)
        if not C: print("  n/d"); continue
        print(f"  KICK attack: centroide transiente ~{np.mean(C):.0f} Hz  |  click/sub ratio {np.mean(SC):.2f}")
        print(f"    -> {'kick con CLICK brillante (tick)' if np.mean(C)>350 else 'kick SCURO/puro sub (poco click)'}")
        print(f"  ACID (303) 300-2.5kHz: movimento {np.mean(AF):.1f}  |  risonanza {np.mean(AR):.2f}")
        print(f"    -> {'acid PRESENTE e squelchy' if np.mean(AR)>0.5 else 'poco acid/risonanza'}")
        print(f"  ARIA/atmosfere 7-12kHz: {np.mean(AIR):.2f}  |  riverbero(code) {np.mean(REV):.2f}")
        print(f"    -> {'atmosfere/riverbero ricchi' if np.mean(REV)>0.35 else 'asciutto/poche code'}")

if __name__=="__main__":
    main()
