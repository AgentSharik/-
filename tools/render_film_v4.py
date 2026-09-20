#!/usr/bin/env python3
"""PROJECT INSOMNIA — Part 1, cut v4: clean functional lab, natural motion."""
import subprocess, os, re, math, random, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

FF = "/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
ROOT = "/home/user"
W, H, FPS = 1920, 1080, 24
SR = 44100
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
random.seed(7); np.random.seed(7)
BAR = 118

def probe_dur(p):
    r = subprocess.run([FF, "-i", p], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    h, mi, s = m.groups(); return int(h)*3600+int(mi)*60+float(s)

def to_wav(mp3, wav, sr):
    subprocess.run([FF, "-y", "-i", mp3, "-ar", str(sr), "-ac", "1", wav], check=True, capture_output=True)

def read_wav(p):
    w = wave.open(p)
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)/32768.0

def add(buf, sig, t0, gain=1.0):
    s = int(t0*SR)
    if s >= len(buf): return
    e = min(len(buf), s+len(sig)); buf[s:e] += sig[:e-s]*gain

def lp_of(x, k):
    y = np.empty(len(x)); y[0] = x[0]
    for i in range(1, len(x)): y[i] = y[i-1] + k*(x[i]-y[i-1])
    return y

def hp_of(x, k):
    y = np.empty(len(x)); y[0] = 0.0
    for i in range(1, len(x)): y[i] = k*(y[i-1] + x[i] - x[i-1])
    return y

# ---------------- SFX: clean lab ----------------
def s_beep():
    n=int(0.12*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*880*t)*np.exp(-t*30)*0.25

def s_step():
    n=int(0.13*SR); t=np.arange(n)/SR
    nz=np.random.randn(n)*np.exp(-t*30)*0.25
    return lp_of(nz,0.12)+np.sin(2*np.pi*85*t)*np.exp(-t*25)*0.5

def s_blip():
    n=int(0.05*SR); t=np.arange(n)/SR
    f=320+np.random.randint(0,420)
    return np.sin(2*np.pi*(f+400*(t/0.05))*t)*np.exp(-t*60)*0.3

def s_click():
    n=int(0.05*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*1900*t))*np.exp(-t*220)*0.3+np.sin(2*np.pi*520*t)*np.exp(-t*90)*0.4

def s_gulp():
    n=int(0.16*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*(320-170*(t/0.16))*t)*np.exp(-t*18)*0.5+np.random.randn(n)*np.exp(-t*40)*0.1

def s_breath():
    n=int(1.6*SR); t=np.arange(n)/SR
    return lp_of(np.random.randn(n),0.02)*np.sin(np.pi*t/1.6)**1.5*0.3

def s_page():
    n=int(0.3*SR); t=np.arange(n)/SR
    nz=np.random.randn(n)*np.exp(-t*10)*(0.4+0.6*np.abs(np.sin(2*np.pi*9*t)))
    return hp_of(nz,0.4)*0.5

def s_hb():
    n=int(0.25*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*50*t)*np.exp(-t*22)*0.7

def build_sfx(T):
    buf=np.zeros(int(T*SR)); t=np.arange(len(buf))/SR
    hum=(np.sin(2*np.pi*48*t)+0.5*np.sin(2*np.pi*96*t))*(0.5+0.12*np.sin(2*np.pi*0.45*t))
    buf+=hum*0.035
    gate=np.clip((t-4.5)/2,0,1)*np.clip((T-1.0-t)/2,0,1)
    buf+=lp_of(np.random.randn(len(buf)),0.004)*0.18*gate
    add(buf,s_beep(),0.9,0.8); add(buf,s_beep(),2.3,0.6)
    tt=5.0
    while tt<13.0:
        add(buf,s_blip(),tt,0.12); tt+=random.uniform(0.25,0.7)
    for st in (10.8,11.7,12.6): add(buf,s_step(),st,0.8)
    add(buf,s_page(),14.2,0.7)
    bt=17.9
    while bt<25.2:
        add(buf,s_breath(),bt,0.45); bt+=2.2
    tt=25.6
    while tt<28.2:
        add(buf,s_blip(),tt,0.1); tt+=random.uniform(0.3,0.7)
    add(buf,s_click(),25.6,0.8)
    for g in (26.8,27.5): add(buf,s_gulp(),g,0.8)
    n=int(3.0*SR); rt=np.arange(n)/SR
    f=90+240*(rt/3.0)**2
    add(buf,(np.sin(2*np.pi*f*rt))* (rt/3.0)*0.06,29.0)
    add(buf,s_hb(),30.8,0.8)
    return buf

def pix_card(w,h,lines):
    sc=3
    img=Image.new("RGB",(w//sc,h//sc),(0,0,0)); d=ImageDraw.Draw(img)
    for text,size,color,dy in lines:
        f=ImageFont.truetype(FONT_B,size//sc)
        bb=d.textbbox((0,0),text,font=f)
        tw,th=bb[2]-bb[0],bb[3]-bb[1]
        d.text(((w//sc-tw)/2-bb[0],(h//sc+dy//sc-th)/2-bb[1]),text,font=f,fill=color)
    return img.resize((w,h),Image.NEAREST)

def smooth(u): return u*u*(3-2*u)

def pose_u(t, times, blend):
    k=sum(1 for ti in times if t>=ti)
    if k==0: return 0.0
    d=t-times[k-1]
    if d>=blend: return float(k%2)
    return (k-1)%2 + (1 if k%2 else -1)*smooth(min(d/blend,1.0))

def main():
    narr=f"{ROOT}/audio/narration_A.mp3"
    durN=probe_dur(narr)
    to_wav(narr,f"{ROOT}/audio/_narrA44.wav",SR); narrW=read_wav(f"{ROOT}/audio/_narrA44.wav")
    NSTART=1.2; T=36.0; FR=int(T*FPS)
    print("narr",round(durN,2))

    S=lambda p: np.array(Image.open(p).convert("RGB"))
    IMG={k:S(f"{ROOT}/assets/shots/{p}") for k,p in {
        "c1":"c1_hall.png","c7a":"c7_walk.png","c7b":"c7_walk_b.png",
        "c3a":"c3_glass.png","c3b":"c3_glass_b.png","c4a":"c4_profile.png","c4b":"c4_profile_b.png",
        "c5a":"c5_dispenser.png","c5b":"c5_dispenser_b.png" if os.path.exists(f"{ROOT}/assets/shots/c5_dispenser_b.png") else "c5_dispenser.png",
        "c6a":"c6_eyes.png","c6b":"c6_eyes_b.png"}.items()}

    end_card=pix_card(W,H,[("ПРОЕКТ «БЕССОННИЦА»",54,(85,255,85),-120),
                           ("ЗАПИСЬ 42 // СЛУЖЕБНАЯ ПЛЁНКА",38,(210,210,210),40),
                           ("всё только начинается...",30,(130,130,130),180)])

    SUBS=[(1.2,5.0,"Дневник наблюдений. Запись сорок вторая."),
          (5.0,8.8,"Кажется... мы наконец добились успеха."),
          (8.8,13.8,"Человечеству больше не нужно тратить треть жизни на сон."),
          (13.8,17.6,"Треть жизни — в темноте, в пустоте."),
          (17.6,21.8,"Формула «Зет-ноль-один» работает."),
          (21.8,25.4,"Должна работать.")]

    def mkfog(seed):
        r=np.random.RandomState(seed)
        g=gaussian_filter(r.rand(135,240),6)
        return (g-g.min())/(g.max()-g.min())
    FOG1,FOG2=mkfog(3),mkfog(9)

    yy,xx=np.mgrid[0:H,0:W]
    r2=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
    VIG=np.clip(1-0.42*np.clip((r2-0.55)/0.65,0,1)**2,0.5,1).astype(np.float32)[...,None]

    NP=45
    px=np.random.rand(NP); py=np.random.rand(NP)
    vx=(np.random.rand(NP)-0.5)*0.006; vy=(np.random.rand(NP)-0.5)*0.003-0.0015
    ph=np.random.rand(NP)*6.28
    # rising bubbles over flasks
    NB=26
    bx=np.random.rand(NB); boff=np.random.rand(NB)*10; bsp=0.05+np.random.rand(NB)*0.05
    grain=np.random.RandomState(11).rand(270,480)*2-1

    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
                          "-r",str(FPS),"-i","-","-c:v","libx264","-pix_fmt","yuv420p",
                          "-crf","19","-preset","medium",f"{ROOT}/video/_v4_video.mp4"],
                         stdin=subprocess.PIPE)

    def crop(img,cx,cy,z):
        h0,w0=img.shape[:2]
        cw,ch=w0/z,h0/z
        x0=min(max(cx*w0-cw/2,0),w0-cw); y0=min(max(cy*h0-ch/2,0),h0-ch)
        return np.array(Image.fromarray(img[int(y0):int(y0+ch),int(x0):int(x0+cw)]).resize((W,H),Image.NEAREST),dtype=np.float32)

    def ease(u): return u*u*(3-2*u)

    def sway(base, box, t, amp=2.0, f=0.35, rot=0.35, phase=0.0):
        h0,w0,_=base.shape
        x0,y0,x1,y1=box
        F=48
        X0,Y0=max(x0-F,0),max(y0-F,0); X1,Y1=min(x1+F,w0),min(y1+F,h0)
        reg=base[Y0:Y1,X0:X1]; h,w,_=reg.shape
        dy=amp*math.sin(2*math.pi*f*t+phase); dx=amp*0.4*math.sin(2*math.pi*f*0.63*t+phase+1.2)
        ang=rot*math.sin(2*math.pi*f*0.5*t+phase+0.5)
        rim=Image.fromarray(np.clip(reg,0,255).astype(np.uint8)).rotate(ang,resample=Image.BILINEAR,translate=(dx,dy),expand=False)
        rarr=np.array(rim,np.float32)
        ry=np.ones(h,np.float32); rx=np.ones(w,np.float32)
        for i in range(min(F,h//2)):
            ry[i]=min(ry[i],i/F); ry[h-1-i]=min(ry[h-1-i],i/F)
        for i in range(min(F,w//2)):
            rx[i]=min(rx[i],i/F); rx[w-1-i]=min(rx[w-1-i],i/F)
        m=(ry[:,None]*rx[None,:])[...,None]
        base[Y0:Y1,X0:X1]=reg*(1-m)+rarr*m

    def light(t):
        return 1.0-0.03*(0.5+0.5*math.sin(2*np.pi*6.1*t))*0.5-0.03*(0.5+0.5*math.sin(2*np.pi*0.21*t))

    TALK=[17.9,18.6,19.1,19.8,20.3,21.0,21.6,22.3,22.9,23.6,24.2,24.8]
    WALK=[10.8,11.7,12.6]

    for fr in range(FR):
        t=fr/FPS
        rec=False
        if t<5.0:
            img=Image.new("RGB",(W,H),(0,0,0)); d=ImageDraw.Draw(img)
            f2=ImageFont.truetype(FONT_B,30)
            d.text((180,H//2-150),"ПРОЕКТ «БЕССОННИЦА»",font=f2,fill=(70,190,90))
            f=ImageFont.truetype(FONT_M,44)
            txt="> СЕКТОР Б, ЛАБ. №3 // СТАТУС: ВСЁ В ПОРЯДКЕ"
            shown=txt[:int(max(0,(t-0.7))*22)]
            d.text((180,H//2-40),shown,font=f,fill=(150,220,160))
            if int(t*3)%2==0 and t>0.7:
                bbw=d.textbbox((180,H//2-40),shown,font=f)
                d.rectangle([bbw[2]+6,H//2-40,bbw[2]+30,H//2+10],fill=(150,220,160))
            f3=ImageFont.truetype(FONT_M,30)
            d.text((180,H//2+40),"служебная запись...",font=f3,fill=(90,120,95))
            base=np.array(img,dtype=np.float32)
            base*=min(t/0.5,1.0)*min((5.0-t)/0.35,1.0)
        elif t<33.6:
            rec=True
            if t<10.5:
                u0,u1=5.0,10.5; p=(0.5,0.55,1.02,0.5,0.52,1.14); fog=0.35
                u=ease(min((t-u0)/(u1-u0),1)); base=crop(IMG["c1"],*[(p[0]+(p[3]-p[0])*u),(p[1]+(p[4]-p[1])*u),(p[2]+(p[5]-p[2])*u)])
                sway(base,(int(0.52*W),int(0.42*H),int(0.74*W),int(0.86*H)),t,amp=2.0,f=0.33,phase=0.5)
                bub_area=(0.10,0.40,0.72,0.30)
            elif t<13.5:
                u0,u1=10.5,13.5; fog=0.3; bub_area=None
                u=ease(min((t-u0)/(u1-u0),1))
                u7=pose_u(t,WALK,0.18)
                a=crop(IMG["c7a"],0.5+0.0*math.sin(0),0.55,1.05+0.11*u)
                b=crop(IMG["c7b"],0.5,0.55,1.05+0.11*u)
                base=a*(1-u7)+b*u7
                base+=np.array([0, math.sin(2*np.pi*(t-10.8)/0.9)*1.6, 0],np.float32)*0  # placeholder
                dyb=1.6*math.sin(2*np.pi*(t-10.8)/0.9+math.pi/2)
                base=np.roll(base,int(dyb),axis=0)
            elif t<17.5:
                u0,u1=13.5,17.5; fog=0.3; bub_area=None
                u=ease(min((t-u0)/(u1-u0),1))
                u3=pose_u(t,[15.3],0.3)
                a=crop(IMG["c3a"],0.55-0.1*u,0.5,1.05+0.12*u)
                b=crop(IMG["c3b"],0.55-0.1*u,0.5,1.05+0.12*u)
                base=a*(1-u3)+b*u3
                sway(base,(int(0.28*W),int(0.30*H),int(0.52*W),int(0.80*H)),t,amp=1.8,f=0.3,phase=1.0)
                sway(base,(int(0.68*W),int(0.28*H),int(0.90*W),int(0.86*H)),t,amp=2.0,f=0.36,phase=2.1)
            elif t<25.4:
                u0,u1=17.5,25.4; fog=0.25; bub_area=None
                u=ease(min((t-u0)/(u1-u0),1))
                u4=pose_u(t,TALK,0.15)
                a=crop(IMG["c4a"],0.52-0.02*u,0.47,1.06+0.1*u)
                b=crop(IMG["c4b"],0.52-0.02*u,0.47,1.06+0.1*u)
                base=a*(1-u4)+b*u4
                sway(base,(int(0.25*W),int(0.05*H),int(0.78*W),int(0.95*H)),t,amp=2.2,f=0.4,phase=0.3)
            elif t<28.4:
                u0,u1=25.4,28.4; fog=0.3; bub_area=(0.44,0.62,0.75,0.35)
                u=ease(min((t-u0)/(u1-u0),1))
                u5=pose_u(t,[26.6],0.2)
                a=crop(IMG["c5a"],0.47+0.03*u,0.5,1.02+0.18*u)
                b=crop(IMG["c5b"],0.47+0.03*u,0.5,1.02+0.18*u)
                base=a*(1-u5)+b*u5
                sway(base,(int(0.60*W),int(0.30*H),int(0.98*W),int(0.85*H)),t,amp=1.8,f=0.37,phase=1.6)
            else:
                u0,u1=28.4,33.6; fog=0.3; bub_area=None
                u=ease(min((t-u0)/(u1-u0),1))
                u6=pose_u(t,[29.5,30.0],0.12)
                a=crop(IMG["c6a"],0.5,0.46,1.05+0.2*u)
                b=crop(IMG["c6b"],0.5,0.46,1.05+0.2*u)
                base=a*(1-u6)+b*u6
                sway(base,(int(0.22*W),int(0.02*H),int(0.80*W),int(0.98*H)),t,amp=1.5,f=0.3,phase=0.8)
                sp=0.5+0.5*math.sin(2*np.pi*0.5*t)
                for (ex,ey) in ((0.385,0.46),(0.645,0.46)):
                    X,Y=int(ex*W),int(ey*H)
                    base[Y-14:Y+14,X-26:X+26]+=np.array([10,45,18],np.float32)*(0.10+0.10*sp)
            # handheld (subtle)
            # (already cropped; apply small shift)
            hx=int(6*math.sin(2*np.pi*0.29*t)+3*math.sin(2*np.pi*0.71*t+1.3))
            hy=int(5*math.sin(2*np.pi*0.23*t+0.7)+2*math.sin(2*np.pi*0.63*t))
            base=np.roll(base,(hy,hx),axis=(0,1))
            # grade
            base=(base-128)*1.10+128
            luma=base.mean(axis=2,keepdims=True)
            base+=np.clip(1-luma/150,0,1)*np.array([-6,4,6],np.float32)
            base+=np.clip((luma-160)/95,0,1)*np.array([6,4,-2],np.float32)
            small=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).resize((480,270))
            bl=np.array(small.filter(ImageFilter.GaussianBlur(7)).resize((W,H),Image.BILINEAR),np.float32)
            base+=bl*np.clip((luma-170)/90,0,1)*0.5
            off1=int(t*5)%240; off2=int(-t*3)%240
            fm=np.array(Image.fromarray((np.roll(FOG1,off1,1)*0.6+np.roll(FOG2,off2,1)*0.4).astype(np.float32)).resize((W,H),Image.BILINEAR),np.float32)[...,None]
            base+=fm*fog*np.array([14,28,26],np.float32)*0.8
            for i in range(NP):
                X=int(((px[i]+vx[i]*t)%1)*W); Y=int(((py[i]+vy[i]*t)%1)*H)
                a=0.2+0.2*math.sin(5*t+ph[i])
                if 2<Y<H-2 and 2<X<W-2: base[Y-1:Y+2,X-1:X+2]+=a*26
            if bub_area:
                x0f,x1f,ytop,span=bub_area
                for i in range(NB):
                    X=int((x0f+(x1f-x0f)*bx[i])*W)
                    prog=((t*bsp[i]+boff[i])%1.0)
                    Y=int((0.78-prog*span)*H)
                    al=(1-prog)*0.5*math.sin(np.pi*min(prog*4,1))
                    if 2<Y<H-2 and 2<X<W-2:
                        base[Y-2:Y+2,X-1:X+2]+=np.array([30,90,40],np.float32)*al
            base*=light(t)
            base*=VIG
            for a,b in ((5.0,5.4),(10.4,10.6),(13.4,13.6),(17.4,17.6),(25.3,25.5),(28.3,28.5)):
                if a<=t<b:
                    u2=(t-a)/(b-a); base*=0.2+0.8*abs(1-2*u2)
        else:
            base=np.array(end_card,dtype=np.float32)
            base*=min((t-33.6)/0.6,1.0)
        canvas=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).convert("RGBA")
        ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
        if rec:
            c=(220,220,220,140)
            for (x,y,dx,dy) in ((40,BAR+34,50,0),(40,BAR+34,0,50),(W-40,BAR+34,-50,0),(W-40,BAR+34,0,50),
                                (40,H-BAR-34,50,0),(40,H-BAR-34,0,-50),(W-40,H-BAR-34,-50,0),(W-40,H-BAR-34,0,-50)):
                d.line([(x,y),(x+dx,y+dy)],fill=c,width=3)
            if int(t*2)%2==0: d.ellipse([(58,BAR+52),(74,BAR+68)],fill=(255,60,60,230))
            f1=ImageFont.truetype(FONT_B,26); f2=ImageFont.truetype(FONT_M,26)
            d.text((86,BAR+48),"REC",font=f1,fill=(230,230,230,200))
            secs=42*60+7+int(t); fr2=int((t%1)*FPS)
            tc=f"{secs//3600:02d}:{(secs//60)%60:02d}:{secs%60:02d}:{fr2:02d}"
            d.text((W-330,BAR+50),tc,font=f2,fill=(220,220,220,190))
            d.text((W-330,H-BAR-70),"CAM_03 // СЕКТОР Б",font=f2,fill=(200,200,200,150))
        sub=None
        for a,b,txt in SUBS[1:]:
            if a<=t<b+0.8:
                nch=min(len(txt),int((t-a)*26))
                if nch>0: sub=txt[:nch]
                break
        if sub and t<33.6:
            f=ImageFont.truetype(FONT_B,40)
            for ox,oy,c in ((2,2,(0,0,0,210)),(-1,-1,(0,0,0,160))):
                d.text((150+ox,H-BAR-92+oy),sub,font=f,fill=c)
            d.text((150,H-BAR-92),sub,font=f,fill=(235,242,238,250))
            if int(t*3)%2==0:
                bbw=d.textbbox((150,H-BAR-92),sub,font=f)
                d.rectangle([bbw[2]+8,H-BAR-92,bbw[2]+28,H-BAR-52],fill=(150,220,160,230))
        arr=np.array(Image.alpha_composite(canvas,ov).convert("RGB"),np.float32)
        arr[:BAR]=0; arr[H-BAR:]=0
        gx,gy=np.random.randint(0,240),np.random.randint(0,160)
        gimg=np.array(Image.fromarray((grain[gy:gy+135,gx:gx+480]*127+127).astype(np.uint8)).resize((W,H),Image.NEAREST),np.float32)/255-0.5
        arr+=gimg[...,None]*6
        enc.stdin.write(np.clip(arr,0,255).astype(np.uint8).tobytes())
        if fr%144==0: print(f"frame {fr}/{FR}")
    enc.stdin.close(); enc.wait()
    print("video done")

    sfx=build_sfx(T)
    mix=sfx.copy(); add(mix,narrW,NSTART,1.0)
    mix=np.tanh(mix*1.4)/np.tanh(1.4)*0.9
    Lch=mix; Rch=np.roll(mix,int(0.006*SR))*0.95
    with wave.open(f"{ROOT}/audio/_mixV4.wav","wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        st=np.empty(len(Lch)*2,dtype=np.int16)
        st[0::2]=(Lch*32767).astype(np.int16); st[1::2]=(Rch*32767).astype(np.int16)
        w.writeframes(st.tobytes())
    subprocess.run([FF,"-y","-i",f"{ROOT}/audio/_mixV4.wav","-c:a","libmp3lame","-b:a","192k",
                    f"{ROOT}/audio/insomnia_part1_mix.mp3"],check=True,capture_output=True)
    subprocess.run([FF,"-y","-i",f"{ROOT}/video/_v4_video.mp4","-i",f"{ROOT}/audio/_mixV4.wav",
                    "-c:v","copy","-c:a","aac","-b:a","192k","-ar","44100","-ac","2","-shortest",
                    f"{ROOT}/video/insomnia_part1_v4.mp4"],check=True,capture_output=True)
    print("muxed final v4")

if __name__=="__main__":
    main()
