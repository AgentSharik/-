<<<<<<< HEAD
"""ТРЕТЬ ЖИЗНИ v3 — полноценный воксельный 3D (как майнкрафт-анимации):
мир из блоков с BFS-светом и тенями, персонажи в мире, синхрон диктор↔кадр.
Превью: вступление + зал(P1) + камера(P2). ENV: T0,T1,OUT,NOMIX."""
=======
"""ТРЕТЬ ЖИЗНИ v3 — Minecraft-стиль: блочные 3D-локации, текстуры, z-buffer.
Превью: вступление + зал (P1) + камера (P2). ENV: ROOT,T0,T1,OUT,NOMIX."""
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
import os, sys, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
<<<<<<< HEAD
import anim, vox, scenes3
from vox import render_scene
ROOT=os.environ.get("ROOT","/home/user/repo")
FF=None
def _ff():
    import shutil
    p=shutil.which("ffmpeg")
    if p: return p
    import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
FF=_ff()
W,H,FPS=1920,1080,24; BAR=96
FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
=======
import mc3
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
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)

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
<<<<<<< HEAD
    for s in sents: out.append((c/tot,(c+len(s))/tot,s)); c+=len(s)
=======
    for s in sents:
        out.append((c/tot,(c+len(s))/tot,s)); c+=len(s)
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
    return out
SUB1=fracs(P1T); SUB2=fracs(P2T)

G={}
def setup():
    G["p1"]=mp3wav("v2_p1"); G["p2"]=mp3wav("v2_p2")
    G["d1"]=len(G["p1"])/44100; G["d2"]=len(G["p2"])/44100
    G["T0"]=9.0; G["T1"]=G["T0"]+G["d1"]+1.0; G["TE"]=G["T1"]+G["d2"]+1.5
<<<<<<< HEAD
    G["hall"]=scenes3.lab_hall(); G["hall_f"]=vox.world_faces(G["hall"])
    G["cell"]=scenes3.cell(); G["cell_f"]=vox.world_faces(G["cell"])
    grs=np.random.RandomState(7); G["grain"]=[]
    for _ in range(4):
        g=np.array(Image.fromarray((grs.rand(135,480)*255).astype(np.uint8)).resize((W,H),Image.NEAREST),np.float32)/255-0.5
        G["grain"].append(g[...,None]*3)
    yy,xx=np.mgrid[0:H,0:W]; r2=((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.62))**2
    G["VIG"]=np.clip(1-0.38*np.clip((r2-0.5)/0.65,0,1)**2,0.45,1).astype(np.float32)[...,None]

def lum_at(w,x,y,z):
    xi,yi,zi=int(x),int(y),int(z)
    if 0<=xi<w.sx and 0<=yi<w.sy and 0<=zi<w.sz:
        return int(w.light[xi,yi,zi])/15.0
    return 0.3
def lit(w,boxes):
    for b in boxes: b["_lum"]=max(0.25,lum_at(w,b["c"][0],b["c"][1],b["c"][2]))
    return boxes

def draw(t):
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
        return np.array(im,np.float32)*min(t/0.5,1)*min((9-t)/0.4,1)
    if t<G["T1"]:
        u=(t-G["T0"])/G["d1"]; w=G["hall"]; faces=G["hall_f"]
        cam=anim.Cam()
        boxes=[]
        if u<0.42:   # длинный кадр: идём за доктором по залу
            v=u/0.42
            dz=2.0+6.0*v
            cam.set((12.8+0.15*math.sin(t*0.5),1.75,dz-2.6),yaw=0.03*math.sin(t*0.23),pitch=-0.045)
            boxes+=lit(w,anim.puppet("doctor",12.5,dz,y=1.0,yaw=0.1,phase=t*7.5,speed=1.25,head_yaw=0.1))
            boxes+=lit(w,anim.puppet("sci",21.0,5.0,y=1.0,yaw=-1.3,arm_r=-0.9+0.12*math.sin(t*2.0)))
            boxes+=lit(w,anim.puppet("sci",21.5,9.0,y=1.0,yaw=-1.2,arm_l=-0.8+0.1*math.sin(t*1.6+1)))
            boxes+=lit(w,anim.puppet("subject",13.6,11.0,y=1.0,yaw=math.pi-0.15,glow=0.15,head_yaw=0.4*math.sin(t*0.3)))
        elif u<0.75: # инъекция: средний план сбоку
            v=(u-0.42)/0.33
            cam.set((10.6,1.55,8.6-0.5*v),yaw=0.9,pitch=-0.03)
            boxes+=lit(w,anim.puppet("doctor",12.2,9.6,y=1.0,yaw=1.9,lean=0.12,arm_r=-1.25+0.08*math.sin(t*3)))
            boxes+=lit(w,anim.puppet("subject",13.6,9.6,y=1.0,yaw=math.pi*0.55,head_pitch=0.1,glow=0.15))
            boxes+=lit(w,anim.puppet("sci",21.0,9.0,y=1.0,yaw=-1.4,head_yaw=0.5))
        else:        # крупно: Волков поворачивается к камере
            v=(u-0.75)/0.25
            cam.set((13.4,1.62,8.0-0.4*v),yaw=0.05,pitch=-0.01)
            boxes+=lit(w,anim.puppet("subject",13.6,9.6,y=1.0,yaw=math.pi-0.15,head_yaw=0.5-0.5*v,glow=0.2,head_pitch=0.04*math.sin(t*0.9)))
            boxes+=lit(w,anim.puppet("doctor",12.0,8.8,y=1.0,yaw=0.4))
        im=render_scene(cam,faces,boxes,sky=(10,16,22),fog=(10,14,16),fogd=0.02)
        return np.array(im.convert("RGB"),np.float32)
    # камера содержания
    u=(t-G["T1"])/G["d2"]; w=G["cell"]; faces=G["cell_f"]
    cam=anim.Cam(); boxes=[]
    night=u>=0.68
    if u<0.48 or night:
        per=6.0; ph=t-G["T1"]; cyc=(ph%per)/per
        x=2+4*cyc if cyc<0.5 else 6-4*(cyc-0.5)
        dirw=1 if cyc<0.5 else -1
        yaw=(math.pi/2)*dirw*0.95
        cam.set((4+0.8*math.sin(t*0.07),1.6,-2.6),yaw=0.04*math.sin(t*0.2),pitch=-0.03)
        boxes+=lit(w,anim.puppet("subject",x,4.0,y=1.0,yaw=yaw,phase=t*8,speed=1.1*dirw,
                                 head_yaw=0.3*math.sin(t*0.5),glow=0.6 if night else 0.2))
    else:
        v=(u-0.48)/0.20
        cam.set((5.2,1.5,2.4),yaw=-0.75,pitch=-0.02)
        crush=u>0.60
        arm=-1.3 if not crush else -0.5
        boxes+=lit(w,anim.puppet("subject",2.2,5.6,y=1.0,yaw=1.9,lean=0.15,arm_l=arm,arm_r=arm,glow=0.3))
        if crush:
            rs=np.random.RandomState(3); tt=t-(G["T1"]+0.60*G["d2"])
            for i in range(7):
                px=1.2+(rs.rand()-0.5)*0.6; pz=6.2+(rs.rand()-0.5)*0.5
                py=1.2+max(0.05,0.8-2.2*tt*tt*rs.rand())
                boxes.append(dict(c=np.array([px,py,pz],np.float32),s=np.array([0.12,0.12,0.12],np.float32),
                                  R=np.eye(3,dtype=np.float32),col=np.array([25,20,32],np.float32),e=0.0))
    im=render_scene(cam,faces,boxes,sky=(6,9,13),fog=(6,9,12),fogd=0.03)
    return np.array(im.convert("RGB"),np.float32)

def overlay(t,arr):
    im=Image.fromarray(np.clip(arr,0,255).astype(np.uint8)).convert("RGBA")
    ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
=======

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
        base=mc3.render(cam,B,sky=(0,0,0))
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
    base=mc3.render(cam,B)
    if fl<1: base=(base*fl).astype(np.uint8)
    return base,t

def overlay(t,arr540):
    im=Image.fromarray(arr540).resize((1920,1080),Image.NEAREST).convert("RGBA")
    ov=Image.new("RGBA",(1920,1080),(0,0,0,0)); d=ImageDraw.Draw(ov)
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
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
<<<<<<< HEAD
        d.text((152,H-BAR-90),sub,font=f,fill=(0,0,0,200))
        d.text((150,H-BAR-92),sub,font=f,fill=(235,242,238,250))
    out=Image.alpha_composite(im,ov)
    a=np.array(out.convert("RGB"),np.float32)
    a[:BAR]=0; a[H-BAR:]=0
    a*=G["VIG"]; a+=G["grain"][int(t*8)%4]
=======
        d.text((152,1080-BAR-88),sub,font=f,fill=(0,0,0,200))
        d.text((150,1080-BAR-90),sub,font=f,fill=(235,242,238,250))
    out=Image.alpha_composite(im,ov)
    a=np.array(out.convert("RGB"),np.float32)
    a[:BAR]=0; a[1080-BAR:]=0
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
    return np.clip(a,0,255).astype(np.uint8)

def sfx():
    N=int(G["TE"]*44100); buf=np.zeros(N); tt=np.arange(N)/44100
<<<<<<< HEAD
    buf+=(np.sin(2*np.pi*46*tt)+0.4*np.sin(2*np.pi*92*tt))*0.022*np.clip((tt-1)/2,0,1)*np.clip((G["TE"]-1-tt)/2,0,1)
    def step(i,f0=72,amp=0.5,dur=0.14):
        n=int(dur*44100); s=np.arange(n)/44100
        s=(np.sin(2*np.pi*f0*s)*np.exp(-s*28)+ (np.random.randn(n)*0.25)*np.exp(-s*60))*amp
        buf[i:i+n]+=s
    st=1.5
    while st<G["T1"]: step(int(st*44100),70,0.45); st+=0.52
    st=G["T1"]+0.2
    while st<G["TE"]: step(int(st*44100),58,0.5,0.16); st+=0.45
    i=int((G["T1"]+0.60*G["d2"])*44100); n=int(0.6*44100)
    buf[i:i+n]+=(np.random.randn(n)*np.exp(-np.arange(n)/44100*7))*0.5
=======
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
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
    return buf

def main():
    setup()
    T0c=float(os.environ.get("T0",0)); T1c=float(os.environ.get("T1",G["TE"]))
<<<<<<< HEAD
    out=os.environ.get("OUT",f"{ROOT}/video/v3_preview.mp4")
    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
                          "-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","23","-preset","medium",out],
=======
    out=os.environ.get("OUT",f"{ROOT}/video/v3_a.mp4")
    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s","1920x1080","-r",str(FPS),
                          "-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","22","-preset","medium",out],
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
                         stdin=subprocess.PIPE)
    fr=int(T0c*FPS)
    while fr<T1c*FPS:
        t=fr/FPS
<<<<<<< HEAD
        enc.stdin.write(overlay(t,draw(t)).tobytes())
=======
        base,_=draw(t)
        enc.stdin.write(overlay(t,base).tobytes())
>>>>>>> 0d8210a (v3: блочный 3D-движок (z-buffer, текстуры 16x16), финальные тексты VO)
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
