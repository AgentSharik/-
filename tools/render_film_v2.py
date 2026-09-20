#!/usr/bin/env python3
"""PROJECT INSOMNIA — Part 1, cinematic cut v2 (found-footage horror)."""
import subprocess, os, re, math, random, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

FF = "/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
ROOT = "/home/user"
W, H, FPS = 1920, 1080, 24
SR = 48000
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
random.seed(7); np.random.seed(7)
BAR = 118  # letterbox

os.makedirs(f"{ROOT}/video", exist_ok=True)

def probe_dur(p):
    r = subprocess.run([FF, "-i", p], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    h, mi, s = m.groups(); return int(h)*3600+int(mi)*60+float(s)

def to_wav(mp3, wav):
    subprocess.run([FF, "-y", "-i", mp3, "-ar", str(SR), "-ac", "1", wav], check=True, capture_output=True)

def read_wav(p):
    w = wave.open(p)
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)/32768.0

def add(buf, sig, t0, gain=1.0):
    s = int(t0*SR)
    if s >= len(buf): return
    e = min(len(buf), s+len(sig)); buf[s:e] += sig[:e-s]*gain

# ---------------- SFX ----------------
def s_drip():
    n=int(0.10*SR); t=np.arange(n)/SR
    sig=np.sin(2*np.pi*(1300-900*(t/0.10))*t)*np.exp(-t*45)*0.5
    n2=int(0.12*SR); t2=np.arange(n2)/SR
    return np.concatenate([sig, np.zeros(int(0.09*SR)), np.sin(2*np.pi*(900-500*(t2/0.12))*t2)*np.exp(-t2*60)*0.18])

def s_blip():
    n=int(0.05*SR); t=np.arange(n)/SR
    f=320+np.random.randint(0,420)
    return np.sin(2*np.pi*(f+400*(t/0.05))*t)*np.exp(-t*60)*0.35

def s_step():
    n=int(0.13*SR); t=np.arange(n)/SR
    noise=np.random.randn(n)*np.exp(-t*30)*0.25
    k=0.12; lp=np.empty(n); lp[0]=noise[0]
    for i in range(1,n): lp[i]=lp[i-1]+k*(noise[i]-lp[i-1])
    return lp+np.sin(2*np.pi*85*t)*np.exp(-t*25)*0.5

def s_click():
    n=int(0.05*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*1900*t))*np.exp(-t*220)*0.3+np.sin(2*np.pi*520*t)*np.exp(-t*90)*0.4

def s_gulp():
    n=int(0.16*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*(320-170*(t/0.16))*t)*np.exp(-t*18)*0.5+np.random.randn(n)*np.exp(-t*40)*0.1

def s_hit():
    n=int(1.3*SR); t=np.arange(n)/SR
    bass=np.sin(2*np.pi*(55-20*(t/1.3))*t)*np.exp(-t*3.2)*0.9
    nz=np.random.randn(n)*np.exp(-t*14)*0.3
    k=0.05; lp=np.empty(n); lp[0]=nz[0]
    for i in range(1,n): lp[i]=lp[i-1]+k*(nz[i]-lp[i-1])
    return bass+lp

def s_hb():  # heartbeat thump
    n=int(0.25*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*50*t)*np.exp(-t*22)*0.8

def s_breath():
    n=int(1.6*SR); t=np.arange(n)/SR
    nz=np.random.randn(n)
    k=0.02; lp=np.empty(n); lp[0]=nz[0]
    for i in range(1,n): lp[i]=lp[i-1]+k*(nz[i]-lp[i-1])
    env=np.sin(np.pi*t/1.6)**1.5
    return lp*env*0.35

def s_page():
    n=int(0.3*SR); t=np.arange(n)/SR
    nz=np.random.randn(n)*np.exp(-t*10)*(0.4+0.6*np.abs(np.sin(2*np.pi*9*t)))
    k=0.4; hp=np.empty(n); hp[0]=0
    for i in range(1,n): hp[i]=k*(hp[i-1]+nz[i]-nz[i-1])
    return hp*0.5

def build_sfx(T):
    buf=np.zeros(int(T*SR)); t=np.arange(len(buf))/SR
    hum=(np.sin(2*np.pi*48*t)+0.5*np.sin(2*np.pi*96*t)+0.2*np.sin(2*np.pi*144*t))
    hum*=0.5+0.12*np.sin(2*np.pi*0.45*t)
    buf+=hum*0.05
    nz=np.random.randn(len(buf)); k=0.004; acc=0.0; lp=np.empty(len(buf)); lp[0]=nz[0]
    for i in range(1,len(buf)): acc+=k*(nz[i]-acc); lp[i]=acc
    gate=np.clip((t-4.5)/2,0,1)*np.clip((T-1.0-t)/2,0,1)
    buf+=lp*0.28*gate
    for d in (0.9,2.4,3.9): add(buf,s_drip(),d,0.5)
    tt=5.0
    while tt<25.0:
        add(buf,s_blip(),tt,0.14); tt+=random.uniform(0.22,0.6)
    for st in (11.25,12.15,13.05): add(buf,s_step(),st,0.85)
    add(buf,s_page(),14.1,0.7)
    add(buf,s_click(),25.6,0.9)
    for g in (26.8,27.5): add(buf,s_gulp(),g,0.8)
    bt=17.8
    while bt<25.2:
        add(buf,s_breath(),bt,0.5); bt+=2.1
    n=int(2.6*SR); rt=np.arange(n)/SR
    f=110+750*(rt/2.6)**2
    add(buf,(np.sin(2*np.pi*f*rt)+0.4*np.sin(2*np.pi*f*1.01*rt))*(rt/2.6)*0.12,28.6)
    add(buf,s_hb(),30.15,0.9); add(buf,s_hb(),30.8,0.7)
    add(buf,s_hit(),31.2,1.0)
    return buf

# ---------------- text helpers ----------------
def sub_image(text, size=42):
    f=ImageFont.truetype(FONT_B,size)
    tmp=Image.new("RGBA",(10,10)); d=ImageDraw.Draw(tmp)
    bb=d.textbbox((0,0),text,font=f)
    w,h=bb[2]-bb[0]+30,bb[3]-bb[1]+22
    img=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(img)
    for ox in (-2,0,2):
        for oy in (-2,0,2):
            if ox or oy: d.text((15-bb[0]+ox,11-bb[1]+oy),text,font=f,fill=(0,0,0,200))
    d.text((15-bb[0],11-bb[1]),text,font=f,fill=(235,240,238,255))
    return img

def pix_card(w,h,lines):
    sc=3
    img=Image.new("RGB",(w//sc,h//sc),(0,0,0)); d=ImageDraw.Draw(img)
    for text,size,color,dy in lines:
        f=ImageFont.truetype(FONT_B,size//sc)
        bb=d.textbbox((0,0),text,font=f)
        tw,th=bb[2]-bb[0],bb[3]-bb[1]
        d.text(((w//sc-tw)/2-bb[0],(h//sc+dy//sc-th)/2-bb[1]),text,font=f,fill=color)
    return img.resize((w,h),Image.NEAREST)

# ---------------- main ----------------
def main():
    narr=f"{ROOT}/audio/narration_A.mp3"
    durN=probe_dur(narr)
    to_wav(narr,f"{ROOT}/audio/_narrA.wav"); narrW=read_wav(f"{ROOT}/audio/_narrA.wav")
    NSTART=1.2
    eyes_end=31.4; T=34.0; FR=int(T*FPS)
    print("narr",round(durN,2),"T",T)

    S=lambda p: np.array(Image.open(p).convert("RGB"))
    IMG={k:S(f"{ROOT}/assets/shots/{p}") for k,p in {
        "lab":"02_lab_wide.png","sci_a":"03_scientist_glass.png","sci_b":"03_scientist_glass_b.png",
        "disp_a":"01_dispenser_potion.png","disp_b":"01_dispenser_potion_b.png",
        "eyes_a":"04_extreme_closeup_eyes.png","eyes_b":"04_extreme_closeup_eyes_b.png",
        "prof_a":"05_profile_a.png","prof_b":"05_profile_b.png",
        "boots_a":"06_boots_a.png","boots_b":"06_boots_b.png"}.items()}

    end_card=pix_card(W,H,[("ПРОЕКТ «БЕССОННИЦА»",54,(85,255,85),-110),
                           ("ЧАСТЬ ПЕРВАЯ — «ФОРМУЛА Z-01»",40,(210,210,210),50),
                           ("продолжение следует...",30,(130,130,130),190)])

    SUBS=[(1.2,5.0,"Дневник наблюдений. Запись сорок вторая."),
          (5.0,8.8,"Кажется... мы наконец добились успеха."),
          (8.8,13.8,"Человечеству больше не нужно тратить треть жизни на сон."),
          (13.8,17.6,"Треть жизни — в темноте, в пустоте."),
          (17.6,21.8,"Формула «Зет-ноль-один» работает."),
          (21.8,25.4,"Должна работать.")]
    SUBI=[(a,b,sub_image(t)) for a,b,t in SUBS]

    # fog noise layers
    def mkfog(seed):
        r=np.random.RandomState(seed)
        g=r.rand(135,240)
        g=gaussian_filter(g,6)
        g=(g-g.min())/(g.max()-g.min())
        return g
    FOG1,FOG2=mkfog(3),mkfog(9)

    yy,xx=np.mgrid[0:H,0:W]
    r=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
    VIG=np.clip(1-0.5*np.clip((r-0.5)/0.65,0,1)**2,0.42,1).astype(np.float32)[...,None]

    # dust particles
    NP=55
    px=np.random.rand(NP); py=np.random.rand(NP)
    vx=(np.random.rand(NP)-0.5)*0.008; vy=(np.random.rand(NP)-0.5)*0.004-0.002
    ph=np.random.rand(NP)*6.28

    grain=np.random.RandomState(11).rand(270,480)*2-1

    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
                          "-r",str(FPS),"-i","-","-c:v","libx264","-pix_fmt","yuv420p",
                          "-crf","19","-preset","medium",f"{ROOT}/video/_v2_video.mp4"],
                         stdin=subprocess.PIPE)

    def crop(img,cx,cy,z):
        h0,w0=img.shape[:2]
        cw,ch=w0/z,h0/z
        x0=min(max(cx*w0-cw/2,0),w0-cw); y0=min(max(cy*h0-ch/2,0),h0-ch)
        im=Image.fromarray(img[int(y0):int(y0+ch),int(x0):int(x0+cw)])
        return np.array(im.resize((W,H),Image.NEAREST),dtype=np.float32)

    def cam(u,p):
        cx,cy,z=p[0]+(p[3]-p[0])*u, p[1]+(p[4]-p[1])*u, p[2]+(p[5]-p[2])*u
        return cx,cy,z

    def ease(u): return u*u*(3-2*u)

    def light(t):
        L=1.0-0.05*(0.5+0.5*math.sin(2*np.pi*7.3*t))*0.5-0.04*(0.5+0.5*math.sin(2*np.pi*0.23*t))
        for a,b,d in ((9.2,9.34,0.5),(16.8,16.92,0.45),(23.4,23.52,0.5),(29.6,29.7,0.35)):
            if a<=t<b:
                u=(t-a)/(b-a); L*=1-d*math.sin(np.pi*min(u*3,1))
        return L

    def hud(draw,t,rec_on):
        if rec_on:
            draw.line([(40,BAR+34),(90,BAR+34)],fill=(220,220,220,140),width=3)
            draw.line([(40,BAR+34),(40,BAR+84)],fill=(220,220,220,140),width=3)
            draw.line([(W-40,BAR+34),(W-90,BAR+34)],fill=(220,220,220,140),width=3)
            draw.line([(W-40,BAR+34),(W-40,BAR+84)],fill=(220,220,220,140),width=3)
            draw.line([(40,H-BAR-34),(90,H-BAR-34)],fill=(220,220,220,140),width=3)
            draw.line([(40,H-BAR-34),(40,H-BAR-84)],fill=(220,220,220,140),width=3)
            draw.line([(W-40,H-BAR-34),(W-90,H-BAR-34)],fill=(220,220,220,140),width=3)
            draw.line([(W-40,H-BAR-34),(W-40,H-BAR-84)],fill=(220,220,220,140),width=3)
            if int(t*2)%2==0:
                draw.ellipse([(58,BAR+52),(74,BAR+68)],fill=(255,60,60,230))
            f1=ImageFont.truetype(FONT_B,26); f2=ImageFont.truetype(FONT_M,26)
            draw.text((86,BAR+48),"REC",font=f1,fill=(230,230,230,200))
            secs=42*60+7+int(t); fr=int((t%1)*FPS)
            tc=f"{secs//3600:02d}:{(secs//60)%60:02d}:{secs%60:02d}:{fr:02d}"
            draw.text((W-320,BAR+50),tc,font=f2,fill=(220,220,220,190))
            draw.text((W-330,H-BAR-70),"CAM_03 // СЕКТОР Б",font=f2,fill=(200,200,200,150))

    for fr in range(FR):
        t=fr/FPS
        # -------- pick segment --------
        if t<5.0:  # title: diegetic typed log
            base=np.zeros((H,W,3),np.float32)
            txt="> СЕКТОР Б. ЛАБОРАТОРИЯ №3  //  ЗАПИСЬ 42"
            nch=int(max(0,(t-0.7))*22)
            shown=txt[:nch]
            img=Image.new("RGB",(W,H),(0,0,0)); d=ImageDraw.Draw(img)
            f=ImageFont.truetype(FONT_M,44)
            d.text((180,H//2-40),shown,font=f,fill=(150,220,160))
            if int(t*3)%2==0 and t>0.7:
                bbw=d.textbbox((180,H//2-40),shown,font=f)
                d.rectangle([bbw[2]+6,H//2-40,bbw[2]+30,H//2+10],fill=(150,220,160))
            f2=ImageFont.truetype(FONT_B,30)
            d.text((180,H//2-140),"ПРОЕКТ «БЕССОННИЦА»",font=f2,fill=(70,190,90))
            base=np.array(img,dtype=np.float32)
            base*=min(t/0.5,1.0)*min((5.0-t)/0.35,1.0)
            rec=False
        elif t<31.4:
            rec=True
            if t<11.0: seg,u0,u1,imgkey="lab",5.0,11.0,None; p=(0.5,0.56,1.02,0.5,0.47,1.22); fog=0.55
            elif t<13.6:
                seg,u0,u1,imgkey="boots",11.0,13.6,None; p=(0.5,0.55,1.05,0.5,0.5,1.16); fog=0.8
                imgkey="boots_a" if int((t-11.25)/0.9)%2==0 else "boots_b"
            elif t<17.6:
                seg,u0,u1,imgkey="sci",13.6,17.6,None; p=(0.56,0.5,1.05,0.45,0.5,1.18); fog=0.45
                imgkey="sci_a" if t<15.6 else "sci_b"
            elif t<25.4:
                seg,u0,u1,imgkey="prof",17.6,25.4,None; p=(0.52,0.47,1.06,0.5,0.47,1.16); fog=0.35
                imgkey="prof_a" if int((t-17.6)/0.36)%2==0 else "prof_b"
            elif t<28.4:
                seg,u0,u1,imgkey="disp",25.4,28.4,None; p=(0.47,0.5,1.02,0.5,0.47,1.2); fog=0.4
                imgkey="disp_a" if t<26.6 else "disp_b"
            else:
                seg,u0,u1,imgkey="eyes",28.4,31.4,None; p=(0.5,0.46,1.05,0.5,0.46,1.3); fog=0.6
                imgkey="eyes_a" if t<29.9 else "eyes_b"
            u=ease(min(max((t-u0)/(u1-u0),0),1))
            cx,cy,z=cam(u,p)
            hx=0.004*math.sin(2*np.pi*0.29*t)+0.0022*math.sin(2*np.pi*0.71*t+1.3)
            hy=0.003*math.sin(2*np.pi*0.23*t+0.7)+0.0018*math.sin(2*np.pi*0.63*t)
            base=crop(IMG[imgkey] if imgkey else IMG["lab"],cx+hx,cy+hy,z)
            # grade
            base=(base-128)*1.12+128
            luma=base.mean(axis=2,keepdims=True)
            base+=np.clip(1-luma/140,0,1)*np.array([-8,4,6],np.float32)
            base+=np.clip((luma-150)/105,0,1)*np.array([7,4,-2],np.float32)
            # bloom
            small=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).resize((480,270))
            bl=np.array(small.filter(ImageFilter.GaussianBlur(7)).resize((W,H),Image.BILINEAR),np.float32)
            base+=bl*np.clip((luma-165)/90,0,1)*0.55
            # fog drift
            off1=int(t*6)%240; off2=int(-t*4)%240
            f1=np.roll(FOG1,off1,axis=1); f2=np.roll(FOG2,off2,axis=1)
            fm=np.array(Image.fromarray((f1*0.6+f2*0.4).astype(np.float32)).resize((W,H),Image.BILINEAR),np.float32)[...,None]
            base+=fm*fog*np.array([16,34,28],np.float32)*0.9
            # dust
            for i in range(NP):
                X=int(((px[i]+vx[i]*t)%1)*W); Y=int(((py[i]+vy[i]*t)%1)*H)
                a=0.25+0.25*math.sin(6*t+ph[i])
                if 2<Y<H-2 and 2<X<W-2:
                    base[Y-1:Y+2,X-1:X+2]+=a*30
            # flicker + vignette
            base*=light(t)
            base*=VIG
            # shot dips
            for a,b in ((5.0,5.45),(10.9,11.1),(13.5,13.75),(17.5,17.72),(25.3,25.5),(28.3,28.5)):
                if a<=t<b:
                    u2=(t-a)/(b-a); base*=0.15+0.85*abs(1-2*u2)
        else:
            base=np.array(end_card,dtype=np.float32)
            base*=min((t-31.4)/0.6,1.0); rec=False
        # -------- subtitles (typed) --------
        sub=None
        for a,b,txt in SUBS[1:]:
            if a<=t<b+0.8:
                nch=min(len(txt),int((t-a)*26))
                if nch>0: sub=(txt[:nch],t)
                break
        canvas=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).convert("RGBA")
        ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
        hud(d,t,rec)
        if sub and t<31.4:
            f=ImageFont.truetype(FONT_B,40)
            txt,ts=sub
            for ox,oy,c in ((2,2,(0,0,0,210)),(-1,-1,(0,0,0,160))):
                d.text((150+ox,H-BAR-92+oy),txt,font=f,fill=c)
            d.text((150,H-BAR-92),txt,font=f,fill=(235,242,238,250))
            if int(t*3)%2==0:
                bbw=d.textbbox((150,H-BAR-92),txt,font=f)
                d.rectangle([bbw[2]+8,H-BAR-92,bbw[2]+28,H-BAR-52],fill=(150,220,160,230))
        canvas=Image.alpha_composite(canvas,ov)
        arr=np.array(canvas.convert("RGB"),np.float32)
        # letterbox
        arr[:BAR]=0; arr[H-BAR:]=0
        # grain
        gx,gy=np.random.randint(0,240),np.random.randint(0,160)
        g=np.kron(grain[gy:gy+135,gx:gx+480],np.ones((1,1)))
        gimg=np.array(Image.fromarray((g*127+127).astype(np.uint8)).resize((W,H),Image.NEAREST),np.float32)/255-0.5
        arr+=gimg[...,None]*7
        enc.stdin.write(np.clip(arr,0,255).astype(np.uint8).tobytes())
        if fr%144==0: print(f"frame {fr}/{FR}")
    enc.stdin.close(); enc.wait()
    print("video done")

    sfx=build_sfx(T)
    mix=sfx.copy(); add(mix,narrW,NSTART,1.0)
    mix=mix/np.max(np.abs(mix))*0.85
    with wave.open(f"{ROOT}/audio/_mixV2.wav","wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix*32767).astype(np.int16).tobytes())
    subprocess.run([FF,"-y","-i",f"{ROOT}/video/_v2_video.mp4","-i",f"{ROOT}/audio/_mixV2.wav",
                    "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",
                    f"{ROOT}/video/insomnia_part1_film.mp4"],check=True,capture_output=True)
    print("muxed final")

if __name__=="__main__":
    main()
