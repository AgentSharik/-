"""ТРЕТЬ ЖИЗНИ v2 — «живое» кино: 3D-персонажи ходят, длинные кадры, плотная озвучка.
Синхрон: диктор говорит о том, что в этот момент на экране.
ENV: ROOT, T0, T1 (секунды чанка), OUT."""
import os, sys, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import anim
ROOT=os.environ.get("ROOT","/home/user/repo")
FF=None
def _find_ff():
    import shutil, glob
    p=shutil.which("ffmpeg")
    if p: return p
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: pass
    g=glob.glob("/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-*")
    return g[0]
FF=_find_ff()
W,H,FPS=1920,1080,24; BAR=96
FONT_M="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float64)/32768.
def dur_wav(a): return len(a)/44100

# --- аудио: конвертация v2-реплик ---
def mp3wav(name):
    src=f"{ROOT}/audio/{name}.mp3"; dst=f"{ROOT}/audio/_v2_{name}.wav"
    if not os.path.exists(dst):
        subprocess.run([FF,"-y","-i",src,"-ar","44100","-ac","1",dst],check=True,capture_output=True)
    return rd(dst)

P1T=["Дневник наблюдений. Запись сорок вторая.","Сектор Б, лаборатория три.","Сегодня формула Зет-ноль-один впервые введена человеку.",
"Объект номер один — доброволец Волков, тридцать четыре года, солдат.","Мы обещали вернуть людям треть жизни, которую каждый отдаёт сну.",
"Хан пересчитывает дозировку три раза подряд. Я тоже боюсь.","Но страх — это цена прогресса.",
"После инъекции Волков улыбается и говорит: «я наконец выспался».","Никто не смеётся."]
P2T=["Запись сорок пятая. Седьмые сутки.","Волков не спит сто шестьдесят восемь часов.",
"Продуктивность выросла на триста процентов: он собирает механизмы быстрее, чем мы чертим чертежи.","Ест вдвое меньше, сил вдвое больше.",
"Сегодня он сжал кусок обсидиана — и тот рассыпался, как уголь.","Я спрашиваю себя, откуда берётся энергия.",
"Ответ приходит ночью: он не лежит, он ходит.","Круг за кругом, как маятник.","Телу запретили отдыхать — и оно ищет, куда деть жизнь."]

S1B=[(0.00,"a"),(0.42,"b"),(0.75,"c"),(1.0,"end")]
S2B=[(0.00,"a"),(0.48,"b"),(0.68,"c"),(1.0,"end")]

def fracs(sents):
    tot=sum(len(s) for s in sents); out=[]; c=0
    for s in sents:
        out.append((c/tot,(c+len(s))/tot,s)); c+=len(s)
    return out
SUB1=fracs(P1T); SUB2=fracs(P2T)

def setup():
    G={}
    G["p1"]=mp3wav("v2_p1"); G["p2"]=mp3wav("v2_p2")
    G["d1"]=dur_wav(G["p1"]); G["d2"]=dur_wav(G["p2"])
    G["T0"]=9.0; G["T1"]=G["T0"]+G["d1"]+1.0; G["TE"]=G["T1"]+G["d2"]+1.5
    L=lambda p: np.array(Image.open(f"{ROOT}/assets/v2/{p}").convert("RGB").resize((W,H)),np.float32)
    for k in ("b_lab_hall","b_cell","b_corridor","b_desk","b_lab_chaos","b_street_evac","b_checkpoint","b_square_fire","b_gate"):
        G[k]=L(k+".jpg")
    grs=np.random.RandomState(7); G["grain"]=[]
    for _ in range(4):
        g=np.array(Image.fromarray((grs.rand(135,480)*255).astype(np.uint8)).resize((W,H),Image.NEAREST),np.float32)/255-0.5
        G["grain"].append(g[...,None]*4)
    yy,xx=np.mgrid[0:H,0:W]; r2=((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.62))**2
    G["VIG"]=np.clip(1-0.4*np.clip((r2-0.5)/0.65,0,1)**2,0.45,1).astype(np.float32)[...,None]
    return G

def bg_view(G,key,zoom,ox,oy):
    """пан/зум фона под движение камеры"""
    im=G[key]
    zw,zh=int(W/zoom),int(H/zoom)
    x0=int(min(max((W-zw)/2+ox,0),W-zw)); y0=int(min(max((H-zh)/2+oy,0),H-zh))
    return np.array(Image.fromarray(im[y0:y0+zh,x0:x0+zw].astype(np.uint8)).resize((W,H)),np.float32)

def grade(base,warm=5):
    base=(base-128)*1.08+128
    luma=base.mean(axis=2,keepdims=True)
    base+=np.clip(1-luma/150,0,1)*np.array([-6,4,6],np.float32)
    base+=np.clip((luma-160)/95,0,1)*np.array([warm,4,-2],np.float32)
    return base

def shadow(cam,boxes,im):
    d=ImageDraw.Draw(im,"RGBA")
    for x,z,sx in boxes:
        xy,_=cam.project(np.array([[x,0.01,z]])); sxp,syp=xy[0]
        k=cam.f*cam.H/2/max(0.3,z+3.4)
        rx,ry=k*sx*0.5,k*sx*0.14
        d.ellipse([sxp-rx,syp-ry,sxp+rx,syp+ry],fill=(0,0,0,70))

def draw(G,t):
    cam=anim.Cam()
    boxes=[]; shs=[]; key=None; zoom=1.06; ox=oy=0.0; flick=1.0; glass=False
    if t<9.0:
        base=np.zeros((H,W,3),np.float32)
        im=Image.fromarray(base.astype(np.uint8)); d=ImageDraw.Draw(im)
        f=ImageFont.truetype(FONT_M,44)
        txt="> СЕКТОР Б, ЛАБ. №3 // ПРОТОКОЛ НАБЛЮДЕНИЯ"
        shown=txt[:int(max(0,t-0.6)*24)]
        d.text((180,H//2-40),shown,font=f,fill=(150,220,160))
        if int(t*3)%2==0:
            bb=d.textbbox((180,H//2-40),shown,font=f); d.rectangle([bb[2]+6,H//2-40,bb[2]+30,H//2+10],fill=(150,220,160))
        f2=ImageFont.truetype(FONT_B,30)
        d.text((180,H//2-170),"ПРОЕКТ «БЕССОННИЦА»",font=f2,fill=(70,190,90))
        base=np.array(im,np.float32)*min(t/0.5,1)*min((9-t)/0.4,1)
    elif t<G["T1"]:
        u=(t-G["T0"])/G["d1"]; shot="a" if u<0.42 else "b" if u<0.75 else "c"
        key="b_lab_hall"
        if shot=="a":
            v=min(u/0.42,1)
            cam.set((0,1.5,-3.8-0.5*v),yaw=0.04*math.sin(t*0.23),pitch=-0.05)
            zoom=1.05+0.06*v; ox=30*math.sin(t*0.11)
            z=6.5-3.2*v
            boxes+=anim.puppet("doctor",-0.45,z,yaw=0.15,phase=t*7.5,speed=1.25,head_yaw=0.15)
            shs+=[(-0.45,z,0.5)]
            boxes+=anim.puppet("sci",1.5,3.6,yaw=-0.9,phase=0,speed=0,arm_r=-0.9+0.15*math.sin(t*2.1))
            boxes+=anim.puppet("sci",2.1,4.6,yaw=-0.7,phase=0,speed=0,arm_l=-0.8+0.12*math.sin(t*1.7+1))
            shs+=[(1.5,3.6,0.45),(2.1,4.6,0.45)]
        elif shot=="b":
            v=min((u-0.42)/0.33,1)
            cam.set((-0.2,1.45,-1.5),yaw=0.10,pitch=-0.03)
            zoom=1.12+0.05*v; ox=20*math.sin(t*0.13)
            boxes+=anim.puppet("doctor",-0.75,1.9,yaw=0.5,phase=0,speed=0,lean=0.12,arm_r=-1.25+0.1*math.sin(t*3))
            boxes+=anim.puppet("subject",0.15,2.3,yaw=-0.15,phase=0,speed=0,head_pitch=0.12,bob_extra=0.01*math.sin(t*1.1))
            shs+=[(-0.75,1.9,0.5),(0.15,2.3,0.5)]
        else:
            v=min((u-0.75)/0.25,1)
            cam.set((-0.55,1.5,-2.0),yaw=0.22,pitch=-0.04)
            zoom=1.15+0.08*v
            boxes+=anim.puppet("subject",0.1,2.4,yaw=-0.2,phase=0,speed=0,head_yaw=0.5-0.5*v,head_pitch=0.05*math.sin(t*0.8))
            boxes+=anim.puppet("doctor",-0.8,1.5,yaw=2.9,phase=0,speed=0)
            shs+=[(0.1,2.4,0.5),(-0.8,1.5,0.5)]
    else:
        u=(t-G["T1"])/G["d2"]; shot="a" if u<0.48 else "b" if u<0.68 else "c"
        key="b_cell"
        night=shot=="c"
        if shot in ("a","c"):
            v=min(u/0.48,1) if shot=="a" else min((u-0.68)/0.32,1)
            per=6.0
            ph=(t-G["T1"]) if shot=="a" else (t-G["T1"])
            cyc=(ph%per)/per
            x=-1.1+2.2*cyc if cyc<0.5 else 1.1-2.2*(cyc-0.5)
            dirw=1 if cyc<0.5 else -1
            yaw=math.pi/2*dirw*0.95
            cam.set((-0.6+1.2*v,1.5,-3.2),yaw=0.05*math.sin(t*0.2),pitch=-0.04)
            zoom=1.08+0.05*math.sin(t*0.07)+0.04*v; ox=40*math.sin(t*0.09)
            boxes+=anim.puppet("subject",x,2.6,yaw=yaw,phase=t*8,speed=1.1*dirw,head_yaw=0.3*math.sin(t*0.5),glow=0.5 if night else 0.15)
            shs+=[(x,2.6,0.5)]
            if night: flick=0.75+0.25*(int(t*6)%2)
            glass=True
        else:
            v=min((u-0.48)/0.20,1)
            cam.set((0.1,1.25,-1.7),yaw=-0.05,pitch=0.02)
            zoom=1.18+0.06*v
            boxes+=[anim.box([0.55,0.55,2.6],(0.5,0.5,0.5),np.eye(3,dtype=np.float32),(25,20,30))]
            crush=u>0.60
            arm=-1.3 if not crush else -0.6
            boxes+=anim.puppet("subject",-0.35,2.5,yaw=0.7,phase=0,speed=0,lean=0.15,arm_l=arm,arm_r=arm)
            shs+=[(-0.35,2.5,0.5)]
            if crush:
                rs=np.random.RandomState(3)
                for i in range(7):
                    tt=t- (G["T1"]+0.60*G["d2"])
                    px=0.55+ (rs.rand()-0.5)*0.5; pz=2.6+(rs.rand()-0.5)*0.4
                    py=max(0.15,0.8-2.2*tt*tt*rs.rand())
                    boxes+=[anim.box([px,py,pz],(0.09,0.09,0.09),np.eye(3,dtype=np.float32),(20,16,26))]
    # фон + персонажи
    base=bg_view(G,key,zoom,ox,oy) if key is not None else np.zeros((H,W,3),np.float32)
    base*=flick
    if boxes:
        spr=anim.render(cam,boxes)
        shim=Image.new("RGBA",(W,H),(0,0,0,0)); shadow(cam,shs,shim)
        base_img=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).convert("RGBA")
        base_img=Image.alpha_composite(base_img,shim)
        base_img=Image.alpha_composite(base_img,spr)
        base=np.array(base_img.convert("RGB"),np.float32)
    base=grade(base,8 if key=="b_cell" else 5)
    if glass:
        base*=0.92; base+=np.array([6,14,12],np.float32)*0.5
    base*=G["VIG"]
    return base

def overlay(G,t,arr):
    im=Image.fromarray(np.clip(arr,0,255).astype(np.uint8)).convert("RGBA")
    ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
    sub=None
    if G["T0"]<=t<G["T1"]:
        u=(t-G["T0"]/G["d1"] if False else (t-G["T0"])/G["d1"])
        for a,b,s in SUB1:
            if a<=u<b: sub=s; break
    elif G["T1"]<=t<G["TE"]:
        u=(t-G["T1"])/G["d2"]
        for a,b,s in SUB2:
            if a<=u<b: sub=s; break
    if sub:
        f=ImageFont.truetype(FONT_B,40)
        for ox2,oy2,c in ((2,2,(0,0,0,210)),(-1,-1,(0,0,0,160))):
            d.text((150+ox2,H-BAR-92+oy2),sub,font=f,fill=c)
        d.text((150,H-BAR-92),sub,font=f,fill=(235,242,238,250))
    out=Image.alpha_composite(im,ov)
    a=np.array(out.convert("RGB"),np.float32)
    a[:BAR]=0; a[H-BAR:]=0
    a+=G["grain"][int(t*8)%4]
    return np.clip(a,0,255).astype(np.uint8)

def build_sfx_preview(G):
    N=int(G["TE"]*44100); buf=np.zeros(N)
    tt=np.arange(N)/44100
    hum=(np.sin(2*np.pi*48*tt)+0.5*np.sin(2*np.pi*96*tt))*0.03
    buf+=hum*np.clip((tt-1)/2,0,1)*np.clip((G["TE"]-1-tt)/2,0,1)
    import random
    random.seed(5)
    st=2.0
    while st<G["T1"]:  # шаги доктора в сцене a
        i=int(st*44100); n=int(0.12*44100)
        s=np.sign(np.sin(2*np.pi*700*np.arange(n)/44100))*np.exp(-np.arange(n)/44100*60)*0.25
        buf[i:i+n]+=s*0.5; st+=0.42
    st=G["T1"]+0.3
    while st<G["TE"]:  # шаги объекта в камере
        i=int(st*44100); n=int(0.15*44100)
        s=np.sin(2*np.pi*90*np.arange(n)/44100)*np.exp(-np.arange(n)/44100*25)*0.5
        buf[i:i+n]+=s*0.6; st+=0.39
    i=int((G["T1"]+0.60*G["d2"])*44100); n=int(0.5*44100)   # хруст обсидиана
    s=(np.random.randn(n)*np.exp(-np.arange(n)/44100*9))*0.6
    buf[i:i+n]+=s
    return buf

def main():
    G=setup()
    T0c=float(os.environ.get("T0",0)); T1c=float(os.environ.get("T1",G["TE"]))
    out=os.environ.get("OUT",f"{ROOT}/video/v2_preview.mp4")
    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
                          "-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","23","-preset","medium",out],
                         stdin=subprocess.PIPE)
    fr=int(T0c*FPS)
    while fr<T1c*FPS:
        t=fr/FPS
        arr=overlay(G,t,draw(G,t))
        enc.stdin.write(arr.tobytes())
        if fr%240==0: print(f"v2 frame {fr}",flush=True)
        fr+=1
    enc.stdin.close(); enc.wait()
    if os.environ.get("NOMIX"): print("CHUNK DONE",flush=True); return
    sfx=build_sfx_preview(G)
    mix=np.zeros(int(G["TE"]*44100))
    def add(sig,t0,g=1.0):
        s=int(t0*44100); e=min(len(mix),s+len(sig)); mix[s:e]+=sig[:e-s]*g
    add(sfx,0); add(G["p1"],G["T0"]); add(G["p2"],G["T1"])
    mix=np.tanh(mix*1.3)/np.tanh(1.3)*0.9
    with wave.open(f"{ROOT}/audio/_v2mix.wav","wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((mix*32767).astype(np.int16).tobytes())
    print("V2PREVIEW DONE",flush=True)

if __name__=="__main__":
    main()
