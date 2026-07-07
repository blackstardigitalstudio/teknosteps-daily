# -*- coding: utf-8 -*-
"""
ANALISI COMPLETA GENERE — tonalita'/scala, melodia (chroma), ritmo, voci/medi, suoni.
TeknoSteps · Made in Italy.
Multi-segmento su TUTTA la traccia (scarta breakdown), aggrega. Per ogni traccia:
  - BPM (mediana)
  - TONALITA' + MODO (maggiore/minore) via chroma + profili Krumhansl
  - KICK colpi/beat, BASSO note/beat + profilo 16esimi (rolling/offbeat/swing)
  - VOCI/MELODIA: energia e movimento nei medi 250-3500 Hz (dove stanno voci/lead)
  - Bilancio spettrale (sub/kick/basso/low-mid/mid/alti)
Uso: python analisi_completa.py <cartella_o_file...>
"""
import os, sys, glob, subprocess, tempfile, wave
import numpy as np

SR = 22050; SEG = 35.0; POS = [0.15,0.30,0.45,0.60,0.75,0.88]
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
KMAJ = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
KMIN = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])

def ffmpeg():
    for c in (r"C:\Program Files\Wondershare\Recoverit\ffmpeg.exe","ffmpeg"):
        try: subprocess.run([c,"-version"],capture_output=True); return c
        except Exception: pass
    return None
def dur(ff,p):
    fp=ff.replace("ffmpeg","ffprobe")
    try: return float(subprocess.run([fp,"-v","error","-show_entries","format=duration","-of","default=nk=1:nw=1",p],capture_output=True,text=True).stdout.strip())
    except Exception: return 0.0
def seg(ff,p,ss):
    t=os.path.join(tempfile.gettempdir(),"acmp.wav")
    subprocess.run([ff,"-y","-v","error","-ss",str(ss),"-t",str(SEG),"-i",p,"-ac","1","-ar",str(SR),t],capture_output=True)
    try:
        w=wave.open(t,"rb"); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768.0; w.close(); return a
    except Exception: return np.zeros(0,np.float32)

def onset(x,lo,hi):
    N=1024;hop=512;fr=np.fft.rfftfreq(N,1/SR);sel=(fr>=lo)&(fr<hi);win=np.hanning(N);env=[];prev=None
    for i in range(0,len(x)-N,hop):
        m=np.abs(np.fft.rfft(x[i:i+N]*win))[sel]
        if prev is not None: env.append((m-prev).clip(0).sum())
        prev=m
    return np.array(env),SR/hop
def bpm_from(env,fps):
    e=env-env.mean();ac=np.correlate(e,e,"full")[len(e)-1:]
    lo=int(fps*60/200);hi=min(len(ac)-1,int(fps*60/118))
    return (60.0*fps/(lo+int(np.argmax(ac[lo:hi])))) if hi>lo else 0.0
def ppb(env,fps,bpm,thr=1.5):
    if bpm<=0: return 0.0,[]
    th=env.mean()+thr*env.std();beat=fps*60/bpm;mind=max(1,int(beat*0.18));pk=[];last=-mind
    for i in range(1,len(env)-1):
        if env[i]>th and env[i]>=env[i-1] and env[i]>env[i+1] and i-last>=mind: pk.append(i);last=i
    return (len(pk)/(len(env)/beat) if len(env) else 0),pk
def prof16(env,fps,bpm,kpk):
    if bpm<=0 or len(kpk)<4: return [0,0,0,0]
    beat=fps*60/bpm;step=beat/4;bins=np.zeros(4);cnt=np.zeros(4);ph=kpk[0]
    for i in range(len(env)):
        b=int(round(((i-ph)/step)%4))%4;bins[b]+=env[i];cnt[b]+=1
    pr=bins/np.maximum(cnt,1);m=pr.max() or 1
    return list(np.round(pr/m,2))
def bands(x):
    N=4096;hop=2048;fr=np.fft.rfftfreq(N,1/SR)
    B={"sub":(20,60),"kick":(60,120),"basso":(120,250),"low-mid":(250,800),"mid":(800,3000),"alti":(3000,11000)}
    acc={k:0.0 for k in B};win=np.hanning(N)
    for i in range(0,len(x)-N,hop):
        mg=np.abs(np.fft.rfft(x[i:i+N]*win))**2
        for k,(lo,hi) in B.items(): acc[k]+=mg[(fr>=lo)&(fr<hi)].sum()
    tot=sum(acc.values()) or 1
    return {k:100*v/tot for k,v in acc.items()}
def chroma_key(x):
    N=8192;hop=4096;fr=np.fft.rfftfreq(N,1/SR);sel=(fr>=100)&(fr<=2000);fs=fr[sel]
    pc=np.array([int(round(12*np.log2(f/440.0)))%12 for f in fs]);ch=np.zeros(12);win=np.hanning(N)
    for i in range(0,len(x)-N,hop):
        mg=np.abs(np.fft.rfft(x[i:i+N]*win))[sel]
        for j in range(12): ch[j]+=mg[pc==j].sum()
    if ch.sum()==0: return "?","?",ch
    chn=(ch-ch.mean())/(ch.std()+1e-9)
    best=(-9,0,"min")
    for r in range(12):
        for prof,mode in ((KMAJ,"maggiore"),(KMIN,"minore")):
            pr=np.roll(prof,r);prn=(pr-pr.mean())/(pr.std()+1e-9)
            c=np.dot(chn,prn)
            if c>best[0]: best=(c,r,mode)
    return NOTES[best[1]],best[2],ch
def mid_voice(x):
    # energia + movimento (flux) nei medi 250-3500 Hz = zona voci/lead/melodia
    e,_=onset(x,250,3500)
    N=2048;hop=1024;fr=np.fft.rfftfreq(N,1/SR);sel=(fr>=250)&(fr<3500);win=np.hanning(N);en=[]
    for i in range(0,len(x)-N,hop): en.append(np.abs(np.fft.rfft(x[i:i+N]*win))[sel].sum())
    en=np.array(en)
    return e.mean(), (en.std()/(en.mean()+1e-9))   # (movimento, variabilita' = attivita' melodica/vocale)

def analyze(ff,path):
    d=dur(ff,path);S=[]
    for fr in POS:
        x=seg(ff,path,d*fr)
        if len(x)<SR: continue
        ke,fps=onset(x,40,120);bpm=bpm_from(ke,fps);kpb,kpk=ppb(ke,fps,bpm)
        if kpb<0.7: continue
        bo,_=onset(x,60,260);bpb,_=ppb(bo,fps,bpm)
        root,mode,_=chroma_key(x);mv,mvar=mid_voice(x)
        S.append(dict(bpm=bpm,kpb=kpb,bpb=bpb,prof=prof16(bo,fps,bpm,kpk),root=root,mode=mode,mv=mv,mvar=mvar,bands=bands(x)))
    if not S: return None
    from collections import Counter
    ag=lambda k: float(np.mean([s[k] for s in S]))
    key=Counter([(s["root"],s["mode"]) for s in S]).most_common(1)[0][0]
    bd={k:float(np.mean([s["bands"][k] for s in S])) for k in S[0]["bands"]}
    prof=list(np.round(np.mean([s["prof"] for s in S],axis=0),2))
    return dict(dur=d,n=len(S),bpm=float(np.median([s["bpm"] for s in S])),key=key,
                kpb=ag("kpb"),bpb=ag("bpb"),prof=prof,mv=ag("mv"),mvar=ag("mvar"),bands=bd)

def main():
    ff=ffmpeg()
    if not ff: print("[X] ffmpeg"); sys.exit(1)
    args=sys.argv[1:]
    files=[]
    for a in args:
        if os.path.isdir(a): files+=[p for p in sorted(glob.glob(os.path.join(a,"*"))) if p.lower().endswith((".mp3",".wav",".flac",".m4a",".ogg"))]
        else: files.append(a)
    genre_stats={}
    for p in files:
        gen=os.path.basename(os.path.dirname(p))
        print("\n"+"="*68); print(f"[{gen}] {os.path.basename(p)[:52]}")
        r=analyze(ff,p)
        if not r: print("  n/d"); continue
        print(f"  BPM ~{r['bpm']:.1f} | TONALITA': {r['key'][0]} {r['key'][1]}")
        print(f"  KICK {r['kpb']:.1f}/beat | BASSO {r['bpb']:.1f}/beat | 16esimi {r['prof']}")
        print(f"  VOCI/MELODIA (medi 250-3500Hz): attivita' {r['mvar']:.2f}  -> {'VOCI/lead presenti e in movimento' if r['mvar']>0.55 else 'medi statici/pochi'}")
        low=r['bands']['sub']+r['bands']['kick']+r['bands']['basso']
        print(f"  Spettro: sub {r['bands']['sub']:.0f} kick {r['bands']['kick']:.0f} basso {r['bands']['basso']:.0f} | low-mid {r['bands']['low-mid']:.0f} mid {r['bands']['mid']:.0f} alti {r['bands']['alti']:.0f}  (low-end {low:.0f}%)")
        genre_stats.setdefault(gen,[]).append(r)
    # riepilogo per genere
    for gen,rs in genre_stats.items():
        print("\n"+"#"*68); print(f"# RIEPILOGO GENERE: {gen}  ({len(rs)} tracce)")
        med=lambda k: float(np.median([x[k] for x in rs]))
        from collections import Counter
        key=Counter([x['key'] for x in rs]).most_common(1)[0][0]
        prof=list(np.round(np.mean([x['prof'] for x in rs],axis=0),2))
        print(f"#  BPM ~{med('bpm'):.0f} | tonalita' prevalente: {key[0]} {key[1]} | modo tipico")
        print(f"#  KICK {med('kpb'):.1f}/beat | BASSO {med('bpb'):.1f}/beat | 16esimi {prof}")
        print(f"#  attivita' medi/voci {med('mvar'):.2f}")

if __name__=="__main__":
    main()
