"""ТРЕТЬ ЖИЗНИ v3 — Minecraft-стиль: блочные 3D-локации, текстуры, z-buffer.
Превью: вступление + зал (P1) + камера (P2). ENV: ROOT,T0,T1,OUT,NOMIX."""
import os, sys, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import mc4 as mc3
ROOT=os.environ.get("ROOT","/home/user/repo")
def _find_ff():
    import shutil
    p=shutil.which("ffmpeg")
    if p: return p
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: pass
    return None
FF=_find_ff()
FPS=24; BAR=54
FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float64)/32768.
def mp3wav(name):
    src=f"{ROOT}/audio/{name}.mp3"; dst=f"{ROOT}/audio/_v3_{name}.wav"
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
def fracs(sents):
    tot=sum(len(s) for s in sents); out=[]; c=0
    for s in sents:
        out.append((c/tot,(c+len(s))/tot,s)); c+=len(s)
    return out
SUB1=fracs(P1T); SUB2=fracs(P2T)

G={}
def setup():
    G["p1"]=mp3wav("v2_p1"); G["p2"]=mp3wav("v2_p2")
    G["d1"]=len(G["p1"])/44100; G["d2"]=len(G["p2"])/44100
    G["T0"]=9.0; G["T1"]=G["T0"]+G["d1"]+1.0; G["TE"]=G["T1"]+G["d2"]+1.5

# ---------- локации ----------
def hall():
    B=[]; T=0.5
    B.append(mc3.box([0,-0.25,6],[14,0.5,24],None,"tile",tscale=T))
    B.append(mc3.box([0,3.6,6],[14,0.4,24],None,"panel",tscale=T))
    B.append(mc3.box([-7,1.7,6],[0.5,3.6,24],None,"panel",tscale=T))
    B.append(mc3.box([ 7,1.7,6],[0.5,3.6,24],None,"panel",tscale=T))
    B.append(mc3.box([0,1.7,18],[14,3.6,0.5],None,"panel",tscale=T))
    for zz in range(0,16,4):
        for xx in (-3,0,3):
            B.append(mc3.box([xx,3.35,zz],[0.7,0.1,1.2],None,"lamp",1.0))
    for zz in (3,6,9,12):
        B.append(mc3.box([5,0.45,zz],[1.2,0.9,2.0],None,"metal"))
        B.append(mc3.box([5,1.15,zz],[0.9,0.6,0.15],None,"screen",0.8))
    B.append(mc3.box([-5.5,1.4,8],[0.1,2.8,10],None,"glass",0.0,alpha=0.25))
    for zz in range(3,14,2):
        B.append(mc3.box([-5.5,1.4,zz],[0.16,2.8,0.16],None,"metal"))
    return B
def cell(night=False):
    B=[]; T=0.5
    B.append(mc3.box([0,-0.25,3],[5,0.5,7],None,"concrete",tscale=T))
    B.append(mc3.box([0,3.2,3],[5,0.4,7],None,"concrete",tscale=T))
    B.append(mc3.box([-2.5,1.5,3],[0.4,3.2,7],None,"concrete",tscale=T))
    B.append(mc3.box([ 2.5,1.5,3],[0.4,3.2,7],None,"concrete",tscale=T))
    B.append(mc3.box([0,1.5,6.5],[5,3.2,0.4],None,"concrete",tscale=T))
    B.append(mc3.box([0,3.0,1.0],[0.5,0.15,0.5],None,"lamp",1.0 if not night else 0.35))
    # койка
    B.append(mc3.box([-1.7,0.25,5.6],[0.9,0.5,1.8],None,"metal"))
    B.append(mc3.box([-1.7,0.62,5.6],[0.85,0.24,1.7],None,"bed"))
    B.append(mc3.box([-1.7,0.8,4.6],[0.7,0.18,0.5],None,"pillow"))
    # стекло спереди
    B.append(mc3.box([0,1.5,-0.6],[5,3.2,0.1],None,"glass",0.0,alpha=0.2))
    return B

def draw(t):
    cam=mc3.Cam()
    B=[]; fl=1.0
    if t<9.0:
        cam.set((0,1.6,2),yaw=0,pitch=0)
        B=[]
        base,_=mc3.render(cam,[],sky=(0,0,0))
        return base,t
    if t<G["T1"]:
        u=(t-G["T0"])/G["d1"]
        B=hall()
        if u<0.42:
            v=u/0.42; z=6.5-3.3*v
            B+=mc3.puppet("doctor",-0.5,z,yaw=0.15+0.05*math.sin(t*0.5),phase=t*7.5,speed=1.2)
            B+=[mc3.shadow(-0.5,z)]
            B+=mc3.puppet("sci",4.2,4.0,yaw=-1.4,phase=0,speed=0,arm_r=-1.0+0.15*math.sin(t*2))
            B+=[mc3.shadow(4.2,4.0)]
            B+=mc3.puppet("sci",4.4,8.0,yaw=-1.5,phase=0,speed=0,arm_l=-0.9+0.12*math.sin(t*1.6+1))
            B+=[mc3.shadow(4.4,8.0)]
            cam.set((0.3*math.sin(t*0.13),1.6,-2.6-0.5*v),yaw=0.05*math.sin(t*0.21),pitch=-0.05)
        elif u<0.75:
            v=(u-0.42)/0.33
            B+=mc3.puppet("doctor",-0.85,2.1,yaw=0.6,phase=0,speed=0,lean=0.10,arm_r=-1.3+0.12*math.sin(t*2.5))
            B+=[mc3.shadow(-0.85,2.1)]
            B+=mc3.puppet("subject",0.1,2.5,yaw=-0.2,phase=0,speed=0,head_pitch=0.10,bob_extra=0.012*math.sin(t*1.2))
            B+=[mc3.shadow(0.1,2.5)]
            cam.set((-0.25,1.5,-0.9),yaw=0.12,pitch=-0.03)
        else:
            v=(u-0.75)/0.25
            B+=mc3.puppet("subject",0.1,2.6,yaw=-0.25,phase=0,speed=0,head_yaw=0.5-0.55*v)
            B+=[mc3.shadow(0.1,2.6)]
            B+=mc3.puppet("doctor",-1.0,1.4,yaw=2.8,phase=0,speed=0)
            B+=[mc3.shadow(-1.0,1.4)]
            cam.set((-0.5,1.55,-0.6),yaw=0.25,pitch=-0.03)
    else:
        u=(t-G["T1"])/G["d2"]; night=u>=0.68
        B=cell(night)
        if u<0.48 or night:
            per=6.0; ph=t-G["T1"]; cyc=(ph%per)/per
            x=-1.2+2.4*cyc if cyc<0.5 else 1.2-2.4*(cyc-0.5)
            dirw=1 if cyc<0.5 else -1
            B+=mc3.puppet("subject",x,3.0,yaw=math.pi/2*dirw*0.95,phase=t*8,speed=1.1*dirw,
                          head_yaw=0.35*math.sin(t*0.5),glow=0.8 if night else 0.25)
            B+=[mc3.shadow(x,3.0)]
            cam.set((-0.7+1.4*min(u/0.48,1) if u<0.48 else 0.7,1.55,-2.6),yaw=0.06*math.sin(t*0.2),pitch=-0.04)
            if night: fl=0.7+0.3*(int(t*6)%2)
        else:
            v=(u-0.48)/0.20
            B+=[mc3.box([0.9,0.75,4.6],[0.5,0.7,0.5],None,"metal")]
            crush=u>0.60
            arm=-1.3 if not crush else -0.6
            B+=mc3.puppet("subject",0.2,4.4,yaw=0.8,phase=0,speed=0,lean=0.14,arm_l=arm,arm_r=arm)
            B+=[mc3.shadow(0.2,4.4)]
            if crush:
                rs=np.random.RandomState(3); tt=t-(G["T1"]+0.60*G["d2"])
                for i in range(7):
                    px=0.9+(rs.rand()-0.5)*0.6; pz=4.6+(rs.rand()-0.5)*0.5
                    py=max(0.1,1.1-2.5*tt*tt*(0.4+rs.rand()))
                    B+=[mc3.box([px,py,pz],[0.12,0.12,0.12],None,"obsidian")]
            cam.set((0.1,1.3,2.6),yaw=3.14-0.1,pitch=0.0)
    foc = 2.2 if (G["T0"]<=t<G["T1"] and (t-G["T0"])/G["d1"]>=0.42) else (3.5 if t<G["T1"] else 4.0)
    dof = 0.22 if foc<3 else 0.07
    rs=np.random.RandomState(int(t*2)%7+3)
    parts=[([rs.uniform(-4,4),rs.uniform(0.4,3.2),rs.uniform(0,9)],0.02,rs.uniform(50,130)) for _ in range(30)]
    base,_=mc3.render(cam,B,shadows=True,focus=foc,dof=dof,bloom=0.35,particles=parts)
    if fl<1: base=(base*fl).astype(np.uint8)
    return base,t

def overlay(t,arr540):
    im=Image.fromarray(arr540).resize((1920,1080),Image.NEAREST).convert("RGBA")
    ov=Image.new("RGBA",(1920,1080),(0,0,0,0)); d=ImageDraw.Draw(ov)
    sub=None
    if G["T0"]<=t<G["T1"]:
        u=(t-G["T0"])/G["d1"]
        for a,b,s in SUB1:
            if a<=u<b: sub=s; break
    elif G["T1"]<=t<G["TE"]:
        u=(t-G["T1"])/G["d2"]
        for a,b,s in SUB2:
            if a<=u<b: sub=s; break
    if sub:
        f=ImageFont.truetype(FONT_B,40)
        d.text((152,1080-BAR-88),sub,font=f,fill=(0,0,0,200))
        d.text((150,1080-BAR-90),sub,font=f,fill=(235,242,238,250))
    out=Image.alpha_composite(im,ov)
    a=np.array(out.convert("RGB"),np.float32)
    a[:BAR]=0; a[1080-BAR:]=0
    return np.clip(a,0,255).astype(np.uint8)

def sfx():
    N=int(G["TE"]*44100); buf=np.zeros(N); tt=np.arange(N)/44100
    buf+=(np.sin(2*np.pi*47*tt)+0.4*np.sin(2*np.pi*94*tt))*0.028*np.clip((tt-1)/2,0,1)*np.clip((G["TE"]-1-tt)/2,0,1)
    st=1.5
    while st<G["T1"]:   # шаги доктора: глухой удар
        i=int(st*44100); n=int(0.14*44100); a=np.arange(n)/44100
        buf[i:i+n]+=np.sin(2*np.pi*75*a)*np.exp(-a*38)*0.5
        st+=0.42
    st=G["T1"]+0.3
    while st<G["TE"]:
        i=int(st*44100); n=int(0.16*44100); a=np.arange(n)/44100
        buf[i:i+n]+=np.sin(2*np.pi*95*a)*np.exp(-a*30)*0.45
        st+=0.39
    i=int((G["T1"]+0.60*G["d2"])*44100); n=int(0.5*44100)
    rs=np.random.RandomState(9)
    buf[i:i+n]+=(rs.randn(n)*np.exp(-np.arange(n)/44100*9))*0.5
    return buf

def main():
    setup()
    T0c=float(os.environ.get("T0",0)); T1c=float(os.environ.get("T1",G["TE"]))
    out=os.environ.get("OUT",f"{ROOT}/video/v3_a.mp4")
    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s","1920x1080","-r",str(FPS),
                          "-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","22","-preset","medium",out],
                         stdin=subprocess.PIPE)
    fr=int(T0c*FPS)
    while fr<T1c*FPS:
        t=fr/FPS
        base,_=draw(t)
        enc.stdin.write(overlay(t,base).tobytes())
        if fr%240==0: print(f"v3 frame {fr}",flush=True)
        fr+=1
    enc.stdin.close(); enc.wait()
    if os.environ.get("NOMIX"): print("CHUNK DONE",flush=True); return
    mix=np.zeros(int(G["TE"]*44100))
    def add(sig,t0,g=1.0):
        s=int(t0*44100); e=min(len(mix),s+len(sig)); mix[s:e]+=sig[:e-s]*g
    add(sfx(),0); add(G["p1"],G["T0"]); add(G["p2"],G["T1"])
    mix=np.tanh(mix*1.3)/np.tanh(1.3)*0.9
    with wave.open(f"{ROOT}/audio/_v3mix.wav","wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((mix*32767).astype(np.int16).tobytes())
    print("V3PREVIEW DONE",flush=True)

if __name__=="__main__":
    main()
