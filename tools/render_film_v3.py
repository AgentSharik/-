#!/usr/bin/env python3
"""PROJECT INSOMNIA — Part 1, cut v3: early post-apocalypse found footage."""
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

# ---------------- SFX ----------------
def lp_of(x, k):
    y = np.empty(len(x)); y[0] = x[0]
    for i in range(1, len(x)): y[i] = y[i-1] + k*(x[i]-y[i-1])
    return y

def hp_of(x, k):
    y = np.empty(len(x)); y[0] = 0.0
    for i in range(1, len(x)): y[i] = k*(y[i-1] + x[i] - x[i-1])
    return y

def s_drip():
    n=int(0.10*SR); t=np.arange(n)/SR
    sig=np.sin(2*np.pi*(1300-900*(t/0.10))*t)*np.exp(-t*45)*0.5
    n2=int(0.12*SR); t2=np.arange(n2)/SR
    return np.concatenate([sig, np.zeros(int(0.09*SR)), np.sin(2*np.pi*(900-500*(t2/0.12))*t2)*np.exp(-t2*60)*0.18])

def s_crunch():  # boot on paper/glass
    n=int(0.16*SR); t=np.arange(n)/SR
    nz=np.random.randn(n)*np.exp(-t*26)
    crack=np.where(np.random.rand(n)<0.02, np.random.randn(n)*3, 0)*np.exp(-t*20)
    return (hp_of(nz,0.5)*0.35+crack*0.3+np.sin(2*np.pi*70*t)*np.exp(-t*30)*0.35)

def s_click():
    n=int(0.05*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*1900*t))*np.exp(-t*220)*0.3+np.sin(2*np.pi*520*t)*np.exp(-t*90)*0.4

def s_hiss():
    n=int(1.4*SR); t=np.arange(n)/SR
    nz=np.random.randn(n)
    return hp_of(nz,0.3)*np.exp(-t*1.8)*0.22

def s_blip():
    n=int(0.05*SR); t=np.arange(n)/SR
    f=320+np.random.randint(0,420)
    return np.sin(2*np.pi*(f+400*(t/0.05))*t)*np.exp(-t*60)*0.3

def s_buzz():  # dying monitor
    n=int(0.9*SR); t=np.arange(n)/SR
    saw=2*((t*100)%1)-1
    return saw*np.exp(-t*2.2)*0.05*(0.6+0.4*np.sin(2*np.pi*6*t))

def s_hb():
    n=int(0.25*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*50*t)*np.exp(-t*22)*0.8

def s_breath():
    n=int(1.6*SR); t=np.arange(n)/SR
    return lp_of(np.random.randn(n),0.02)*np.sin(np.pi*t/1.6)**1.5*0.35

def s_hit():
    n=int(1.3*SR); t=np.arange(n)/SR
    bass=np.sin(2*np.pi*(55-20*(t/1.3))*t)*np.exp(-t*3.2)*0.9
    return bass+lp_of(np.random.randn(n)*np.exp(-t*14)*0.3,0.05)

def s_groan():  # distant metal
    n=int(2.2*SR); t=np.arange(n)/SR
    f=90+30*np.sin(2*np.pi*0.4*t)
    return np.sin(2*np.pi*f*t)*np.sin(np.pi*t/2.2)*0.06

def build_sfx(T):
    buf=np.zeros(int(T*SR)); t=np.arange(len(buf))/SR
    hum=(np.sin(2*np.pi*48*t)+0.5*np.sin(2*np.pi*96*t))* (0.5+0.12*np.sin(2*np.pi*0.45*t))
    buf+=hum*0.04
    gate=np.clip((t-4.5)/2,0,1)*np.clip((T-1.0-t)/2,0,1)
    buf+=lp_of(np.random.randn(len(buf)),0.004)*0.26*gate
    for d in (0.9,2.4,3.9): add(buf,s_drip(),d,0.5)
    add(buf,s_groan(),6.5,1.0); add(buf,s_groan(),20.5,0.8)
    for st in (10.8,11.7,12.6): add(buf,s_crunch(),st,0.9)
    bt=17.8
    while bt<25.2:
        add(buf,s_breath(),bt,0.5); add(buf,s_buzz(),bt+0.3,1.0); bt+=2.1
    add(buf,s_click(),25.6,0.8)
    add(buf,s_hiss(),25.7,1.0)
    tt=25.8
    while tt<28.2:
        add(buf,s_blip(),tt,0.1); tt+=random.uniform(0.3,0.7)
    n=int(2.6*SR); rt=np.arange(n)/SR
    f=110+750*(rt/2.6)**2
    add(buf,(np.sin(2*np.pi*f*rt)+0.4*np.sin(2*np.pi*f*1.01*rt))*(rt/2.6)*0.12,28.6)
    add(buf,s_hb(),29.4,0.8); add(buf,s_hb(),32.6,0.9); add(buf,s_hb(),33.2,0.7)
    add(buf,s_hit(),33.4,1.0)
    return buf

# ---------------- text ----------------
def pix_card(w,h,lines):
    sc=3
    img=Image.new("RGB",(w//sc,h//sc),(0,0,0)); d=ImageDraw.Draw(img)
    for text,size,color,dy in lines:
        f=ImageFont.truetype(FONT_B,size//sc)
        bb=d.textbbox((0,0),text,font=f)
        tw,th=bb[2]-bb[0],bb[3]-bb[1]
        d.text(((w//sc-tw)/2-bb[0],(h//sc+dy//sc-th)/2-bb[1]),text,font=f,fill=color)
    return img.resize((w,h),Image.NEAREST)

def main():
    narr=f"{ROOT}/audio/narration_A.mp3"
    durN=probe_dur(narr)
    to_wav(narr,f"{ROOT}/audio/_narrA44.wav",SR); narrW=read_wav(f"{ROOT}/audio/_narrA44.wav")
    NSTART=1.2; T=36.0; FR=int(T*FPS)
    print("narr",round(durN,2))

    S=lambda p: np.array(Image.open(p).convert("RGB"))
    names={"p1":"p1_hall.png","p7a":"p7_boots.png","p7b":"p7_boots_b.png",
           "p3":"p3_cell.png","p5a":"p5_profile.png","p5b":"p5_profile_b.png",
           "p4":"p4_spill.png","p6":"p6_vent_eyes.png","p8":"p8_figure.png"}
    p8b=f"{ROOT}/assets/shots/p8_figure_b.png"
    if os.path.exists(p8b): names["p8b"]="p8_figure_b.png"
    IMG={k:S(f"{ROOT}/assets/shots/{p}") for k,p in names.items()}

    end_card=pix_card(W,H,[("ПРОЕКТ «БЕССОННИЦА»",54,(85,255,85),-120),
                           ("ЗАПИСЬ 42 // НОСИТЕЛЬ ПОВРЕЖДЁН",38,(210,210,210),40),
                           ("продолжение следует...",30,(130,130,130),180)])

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
    VIG=np.clip(1-0.5*np.clip((r2-0.5)/0.65,0,1)**2,0.42,1).astype(np.float32)[...,None]
    # beacon radial fields
    def radial(cx,cy,s):
        d=np.sqrt(((xx-cx*W)/(W*s))**2+((yy-cy*H)/(H*s))**2)
        return np.clip(1-d,0,1)**2
    BEAC1=radial(0.86,0.35,0.5)[...,None]; BEAC8=radial(0.5,0.28,0.55)[...,None]

    NP=55
    px=np.random.rand(NP); py=np.random.rand(NP)
    vx=(np.random.rand(NP)-0.5)*0.008; vy=(np.random.rand(NP)-0.5)*0.004-0.002
    ph=np.random.rand(NP)*6.28
    grain=np.random.RandomState(11).rand(270,480)*2-1

    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
                          "-r",str(FPS),"-i","-","-c:v","libx264","-pix_fmt","yuv420p",
                          "-crf","19","-preset","medium",f"{ROOT}/video/_v3_video.mp4"],
                         stdin=subprocess.PIPE)

    def crop(img,cx,cy,z):
        h0,w0=img.shape[:2]
        cw,ch=w0/z,h0/z
        x0=min(max(cx*w0-cw/2,0),w0-cw); y0=min(max(cy*h0-ch/2,0),h0-ch)
        return np.array(Image.fromarray(img[int(y0):int(y0+ch),int(x0):int(x0+cw)]).resize((W,H),Image.NEAREST),dtype=np.float32)

    def ease(u): return u*u*(3-2*u)

    GLITCH=[(9.3,9.42),(16.8,16.9),(23.5,23.62),(30.1,30.22)]
    def light(t):
        L=1.0-0.05*(0.5+0.5*math.sin(2*np.pi*7.3*t))*0.5-0.04*(0.5+0.5*math.sin(2*np.pi*0.23*t))
        for a,b,d in ((9.2,9.34,0.5),(16.8,16.92,0.45),(23.4,23.52,0.5)):
            if a<=t<b:
                u=(t-a)/(b-a); L*=1-d*math.sin(np.pi*min(u*3,1))
        return L

    for fr in range(FR):
        t=fr/FPS
        rec=False
        if t<5.0:
            img=Image.new("RGB",(W,H),(0,0,0)); d=ImageDraw.Draw(img)
            f2=ImageFont.truetype(FONT_B,30)
            d.text((180,H//2-150),"ПРОЕКТ «БЕССОННИЦА» — АРХИВ",font=f2,fill=(70,190,90))
            f=ImageFont.truetype(FONT_M,44)
            txt="> НОСИТЕЛЬ НАЙДЕН: СЕКТОР Б, ЛАБ. №3"
            shown=txt[:int(max(0,(t-0.7))*22)]
            d.text((180,H//2-40),shown,font=f,fill=(150,220,160))
            if int(t*3)%2==0 and t>0.7:
                bbw=d.textbbox((180,H//2-40),shown,font=f)
                d.rectangle([bbw[2]+6,H//2-40,bbw[2]+30,H//2+10],fill=(150,220,160))
            f3=ImageFont.truetype(FONT_M,30)
            d.text((180,H//2+40),"воспроизведение...",font=f3,fill=(90,120,95))
            base=np.array(img,dtype=np.float32)
            base*=min(t/0.5,1.0)*min((5.0-t)/0.35,1.0)
        elif t<33.6:
            rec=True
            if t<10.5: u0,u1=5.0,10.5; p=(0.5,0.55,1.02,0.5,0.5,1.2); fog=0.6; imgkey="p1"; beacon=BEAC1
            elif t<13.5:
                u0,u1=10.5,13.5; p=(0.5,0.55,1.05,0.5,0.5,1.16); fog=0.8; beacon=None
                imgkey="p7a" if int((t-10.8)/0.9)%2==0 else "p7b"
            elif t<17.5: u0,u1=13.5,17.5; p=(0.55,0.5,1.05,0.45,0.5,1.18); fog=0.5; imgkey="p3"; beacon=None
            elif t<25.4:
                u0,u1=17.5,25.4; p=(0.52,0.47,1.06,0.5,0.47,1.16); fog=0.35; beacon=None
                imgkey="p5a" if int((t-17.5)/0.36)%2==0 else "p5b"
            elif t<28.4: u0,u1=25.4,28.4; p=(0.47,0.55,1.02,0.5,0.5,1.2); fog=0.4; imgkey="p4"; beacon=None
            elif t<30.6: u0,u1=28.4,30.6; p=(0.5,0.45,1.05,0.5,0.45,1.25); fog=0.5; imgkey="p6"; beacon=None
            else:
                u0,u1=30.6,33.6; fog=0.7; imgkey="p8"; beacon=BEAC8
                if "p8b" in IMG and t>=32.2: imgkey="p8b"
                p=(0.5,0.5,1.02,0.5,0.5,1.22)
                if 32.16<=t<32.28: p=(0.5,0.52,1.1,0.5,0.52,1.22)  # twitch jump
            u=ease(min(max((t-u0)/(u1-u0),0),1))
            cx,cy,z=p[0]+(p[3]-p[0])*u, p[1]+(p[4]-p[1])*u, p[2]+(p[5]-p[2])*u
            hx=0.004*math.sin(2*np.pi*0.29*t)+0.0022*math.sin(2*np.pi*0.71*t+1.3)
            hy=0.003*math.sin(2*np.pi*0.23*t+0.7)+0.0018*math.sin(2*np.pi*0.63*t)
            base=crop(IMG[imgkey],cx+hx,cy+hy,z)
            base=(base-128)*1.12+128
            luma=base.mean(axis=2,keepdims=True)
            base+=np.clip(1-luma/140,0,1)*np.array([-9,3,5],np.float32)
            base+=np.clip((luma-150)/105,0,1)*np.array([8,4,-3],np.float32)
            small=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).resize((480,270))
            bl=np.array(small.filter(ImageFilter.GaussianBlur(7)).resize((W,H),Image.BILINEAR),np.float32)
            base+=bl*np.clip((luma-160)/90,0,1)*0.6
            off1=int(t*6)%240; off2=int(-t*4)%240
            fm=np.array(Image.fromarray((np.roll(FOG1,off1,1)*0.6+np.roll(FOG2,off2,1)*0.4).astype(np.float32)).resize((W,H),Image.BILINEAR),np.float32)[...,None]
            base+=fm*fog*np.array([15,30,26],np.float32)*0.9
            for i in range(NP):
                X=int(((px[i]+vx[i]*t)%1)*W); Y=int(((py[i]+vy[i]*t)%1)*H)
                a=0.25+0.25*math.sin(6*t+ph[i])
                if 2<Y<H-2 and 2<X<W-2: base[Y-1:Y+2,X-1:X+2]+=a*30
            if beacon is not None:
                pb=max(0.0,math.sin(2*np.pi*t/2.8))**4
                base+=beacon*pb*np.array([70,10,8],np.float32)
            if imgkey in ("p5a","p5b"):
                base*=1.0+0.05*math.sin(2*np.pi*28*t)+ (0.15 if (int(t*8)%17==0) else 0)
            if imgkey=="p4":
                base+=np.array([10,40,15],np.float32)*(0.5+0.5*math.sin(2*np.pi*0.8*t))*0.25
            base*=light(t)
            base*=VIG
            for a,b in ((5.0,5.4),(10.4,10.6),(13.4,13.6),(17.4,17.6),(25.3,25.5),(28.3,28.5),(30.5,30.7)):
                if a<=t<b:
                    u2=(t-a)/(b-a); base*=0.15+0.85*abs(1-2*u2)
        else:
            base=np.array(end_card,dtype=np.float32)
            base*=min((t-33.6)/0.6,1.0)
        # glitch bands
        for a,b in GLITCH:
            if a<=t<b:
                y0=int(120+((hash((a,b))%600)))
                sh=int(60*math.sin(t*90))
                band=base[y0:y0+46]
                base[y0:y0+46]=np.roll(band,sh,axis=1)*1.35+20
        # HUD
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
            jump=(hash(int(t//7))%5)-2
            secs=42*60+7+int(t)+ (jump if t>7 else 0); fr2=int((t%1)*FPS)
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
        arr+=gimg[...,None]*7
        enc.stdin.write(np.clip(arr,0,255).astype(np.uint8).tobytes())
        if fr%144==0: print(f"frame {fr}/{FR}")
    enc.stdin.close(); enc.wait()
    print("video done")

    sfx=build_sfx(T)
    mix=sfx.copy(); add(mix,narrW,NSTART,1.0)
    mix=np.tanh(mix*1.4)/np.tanh(1.4)*0.92
    Lch=mix; Rch=np.roll(mix,int(0.006*SR))*0.95
    with wave.open(f"{ROOT}/audio/_mixV3.wav","wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        st=np.empty(len(Lch)*2,dtype=np.int16)
        st[0::2]=(Lch*32767).astype(np.int16); st[1::2]=(Rch*32767).astype(np.int16)
        w.writeframes(st.tobytes())
    subprocess.run([FF,"-y","-i",f"{ROOT}/audio/_mixV3.wav","-c:a","libmp3lame","-b:a","192k",
                    f"{ROOT}/audio/insomnia_part1_mix.mp3"],check=True,capture_output=True)
    subprocess.run([FF,"-y","-i",f"{ROOT}/video/_v3_video.mp4","-i",f"{ROOT}/audio/_mixV3.wav",
                    "-c:v","copy","-c:a","aac","-b:a","192k","-ar","44100","-ac","2","-shortest",
                    f"{ROOT}/video/insomnia_part1_v3.mp4"],check=True,capture_output=True)
    print("muxed final v3")

if __name__=="__main__":
    main()
