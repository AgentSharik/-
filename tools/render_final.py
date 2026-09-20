#!/usr/bin/env python3
"""PROJECT INSOMNIA — FINAL FILM ~8:43: parts 1-4, epilogue, note, first days, dossier, status, title."""
import subprocess, os, re, math, random, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

def _find_ff():
    import shutil
    p=shutil.which("ffmpeg")
    if p: return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    import glob
    c=glob.glob("/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg*")
    return c[0] if c else "ffmpeg"
FF=_find_ff()
ROOT = "/home/user"
W, H, FPS = 1920, 1080, 24
SR = 44100
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
random.seed(7); np.random.seed(7)
BAR = 118
T = 523.0

def rd(p):
    w = wave.open(p)
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)/32768.

def add(buf, sig, t0, gain=1.0):
    s = int(t0*SR)
    if s >= len(buf): return
    e = min(len(buf), s+len(sig)); buf[s:e] += sig[:e-s]*gain

def lp_of(x,k):
    y=np.empty(len(x)); y[0]=x[0]
    for i in range(1,len(x)): y[i]=y[i-1]+k*(x[i]-y[i-1])
    return y
def hp_of(x,k):
    y=np.empty(len(x)); y[0]=0.0
    for i in range(1,len(x)): y[i]=k*(y[i-1]+x[i]-x[i-1])
    return y

# ---------------- SFX primitives ----------------
def s_beep():
    n=int(0.12*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*880*t)*np.exp(-t*30)*0.25
def s_step():
    n=int(0.13*SR); t=np.arange(n)/SR
    return lp_of(np.random.randn(n)*np.exp(-t*30)*0.25,0.12)+np.sin(2*np.pi*85*t)*np.exp(-t*25)*0.5
def s_blip():
    n=int(0.05*SR); t=np.arange(n)/SR
    f=320+np.random.randint(0,420)
    return np.sin(2*np.pi*(f+400*(t/0.05))*t)*np.exp(-t*60)*0.3
def s_tick():
    n=int(0.03*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*1400*t))*np.exp(-t*300)*0.2
def s_chop():
    n=int(0.1*SR); t=np.arange(n)/SR
    return hp_of(np.random.randn(n)*np.exp(-t*40),0.4)*0.4+np.sin(2*np.pi*180*t)*np.exp(-t*50)*0.3
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
def s_drone():
    n=int(1.6*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*(40-10*(t/1.6))*t)*np.exp(-t*1.6)*0.9
def s_rsclick():
    n=int(0.04*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*2400*t))*np.exp(-t*400)*0.25
def s_knock():
    n=int(0.12*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*220*t)*np.exp(-t*40)*0.5+hp_of(np.random.randn(n)*np.exp(-t*60),0.5)*0.3
def s_zstep():
    n=int(0.3*SR); t=np.arange(n)/SR
    return lp_of(np.random.randn(n)*np.exp(-t*12),0.05)*0.6+np.sin(2*np.pi*60*t)*np.exp(-t*10)*0.5
def s_thud():
    n=int(0.3*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*70*t)*np.exp(-t*14)*0.8+lp_of(np.random.randn(n)*np.exp(-t*20),0.1)*0.4
def s_glasshit():
    n=int(0.12*SR); t=np.arange(n)/SR
    return hp_of(np.random.randn(n)*np.exp(-t*50),0.6)*0.5+np.sin(2*np.pi*2600*t)*np.exp(-t*80)*0.2
def s_glassbreak():
    n=int(0.9*SR); t=np.arange(n)/SR
    return hp_of(np.random.randn(n)*np.exp(-t*4),0.7)*0.7+hp_of(np.random.randn(n)[::-1]*np.exp(-t*3),0.7)*0.25
def s_drop():
    n=int(0.2*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*300*t)*np.exp(-t*30)*0.4+hp_of(np.random.randn(n)*np.exp(-t*50),0.5)*0.2
def s_growl():
    n=int(1.3*SR); t=np.arange(n)/SR
    saw=2*((t*65)%1)-1; saw2=2*((t*61)%1)-1
    return (saw+saw2)*0.25*(0.5+0.5*np.sin(2*np.pi*7*t))*np.exp(-t*0.8)+lp_of(np.random.randn(n),0.02)*0.3*np.exp(-t*1.2)
def s_armor():
    n=int(0.2*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*700*t))*np.exp(-t*60)*0.3+hp_of(np.random.randn(n)*np.exp(-t*40),0.6)*0.3
def s_hurt():
    n=int(0.4*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*(600-380*(t/0.4))*t)*np.exp(-t*6)*0.4+hp_of(np.random.randn(n)*np.exp(-t*15),0.5)*0.2
def s_ring():
    n=int(5*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*3200*t+2*np.sin(2*np.pi*3*t))*np.exp(-t*0.9)*0.12
def s_groan():
    n=int(1.4*SR); t=np.arange(n)/SR
    f=75+25*np.sin(2*np.pi*0.5*t)
    return np.sin(2*np.pi*f*t)*np.sin(np.pi*t/1.4)*0.12
def s_shuff():
    n=int(0.25*SR); t=np.arange(n)/SR
    return lp_of(np.random.randn(n)*np.exp(-t*14),0.08)*0.5
def s_lampoff():
    n=int(0.25*SR); t=np.arange(n)/SR
    return np.sign(np.sin(2*np.pi*2000*t))*np.exp(-t*120)*0.2+np.sin(2*np.pi*(300-200*(t/0.25))*t)*np.exp(-t*20)*0.2
def s_crackle():
    n=int(0.06*SR); t=np.arange(n)/SR
    return hp_of(np.random.randn(n),0.7)*np.exp(-t*60)*0.15
def s_obsidian():
    n=int(0.8*SR); t=np.arange(n)/SR
    return lp_of(np.random.randn(n)*np.exp(-t*5),0.06)*0.7+np.sin(2*np.pi*50*t)*np.exp(-t*6)*0.5
def s_siren_seg():
    n=int(0.5*SR); t=np.arange(n)/SR
    return (np.sin(2*np.pi*740*t)*0.5+np.sin(2*np.pi*1047*t)*0.5)*np.sin(np.pi*t/0.5)**0.5*0.22
def s_cough():
    n=int(0.35*SR); t=np.arange(n)/SR
    burst=(hp_of(np.random.randn(n),0.5)*0.5)*(np.exp(-((t-0.05)*30)**2)+np.exp(-((t-0.18)*30)**2)*0.8)
    return burst*0.5
def s_stamp():
    n=int(0.25*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*120*t)*np.exp(-t*25)*0.6+hp_of(np.random.randn(n)*np.exp(-t*60),0.5)*0.3
def s_murmur():
    n=int(4*SR); t=np.arange(n)/SR
    m=lp_of(np.random.randn(n),0.01)
    am=(0.4+0.6*np.abs(np.sin(2*np.pi*0.31*t))+0.3*np.abs(np.sin(2*np.pi*0.77*t+1)))
    return m*am*0.12
def s_wind():
    n=int(6*SR); t=np.arange(n)/SR
    wv=hp_of(lp_of(np.random.randn(n),0.02),0.02)
    return wv*(0.4+0.6*np.abs(np.sin(2*np.pi*0.13*t)))*0.25

def build_sfx():
    buf=np.zeros(int(T*SR)); t=np.arange(len(buf))/SR
    hum=(np.sin(2*np.pi*48*t)+0.5*np.sin(2*np.pi*96*t))*(0.5+0.12*np.sin(2*np.pi*0.45*t))
    buf+=hum*0.035*np.clip((t-1)/2,0,1)*np.clip((292-t)/2,0,1)
    buf+=np.tanh(hum*4)*0.03*np.clip((t-150)/1,0,1)*np.clip((225-t)/1,0,1)
    add(buf,s_beep(),1.0,0.8); add(buf,s_beep(),2.6,0.6)
    tt=10.0
    while tt<35: add(buf,s_blip(),tt,0.12); tt+=random.uniform(0.3,0.8)
    for st in (35.8,36.9,38.0,39.1,40.2,41.3,42.4,43.5): add(buf,s_step(),st,0.75)
    add(buf,s_page(),46.0,0.7)
    bt=45.5
    while bt<55: add(buf,s_breath(),bt,0.4); bt+=2.2
    add(buf,s_click(),55.6,0.8)
    for g in (57.0,57.8): add(buf,s_gulp(),g,0.8)
    add(buf,s_hb(),70.5,0.7)
    tt=75.2
    while tt<105: add(buf,s_tick(),tt,0.5); tt+=0.5
    tc=75.5
    while tc<105: add(buf,s_chop(),tc,0.6); tc+=1.07
    add(buf,s_obsidian(),126.0,0.9); add(buf,s_obsidian(),130.5,0.8); add(buf,s_obsidian(),135.0,0.9)
    add(buf,s_drone(),148.0,1.0)
    ft=150.5
    while ft<170: add(buf,s_rsclick(),ft,0.6); ft+=random.uniform(0.6,1.1)
    for k in (172.0,174.0,176.0): add(buf,s_knock(),k,0.9)
    bt=171
    while bt<194: add(buf,s_breath(),bt,0.5); bt+=2.0
    add(buf,s_zstep(),206.0,0.9)
    add(buf,s_thud(),216.5,0.9); add(buf,s_glasshit(),216.6,0.8); add(buf,s_drone(),224.0,1.0)
    add(buf,s_drop(),226.0,0.9)
    for i,g in enumerate((236.0,238.5,241.0,243.5,246.5)): add(buf,s_glasshit(),g,0.7+0.06*i); add(buf,s_thud(),g,0.6)
    add(buf,s_glassbreak(),250.3,1.0)
    st=255.0
    while st<270: add(buf,s_siren_seg(),st,1.0); st+=0.5
    add(buf,s_growl(),261.0,1.0)
    add(buf,s_armor(),263.2,0.9); add(buf,s_armor(),264.6,0.8); add(buf,s_hurt(),266.0,0.8)
    add(buf,s_thud(),279.0,1.0); add(buf,s_ring(),279.3,1.0)
    sh=280.5
    while sh<290: add(buf,s_shuff(),sh,0.7); add(buf,s_groan(),sh+0.2,0.6); sh+=1.15
    for i,l in enumerate((290.6,291.6,292.6,293.6)): add(buf,s_lampoff(),l,0.8)
    ck=294.5
    while ck<345: add(buf,s_crackle(),ck,random.uniform(0.4,1.0)); ck+=random.uniform(0.2,0.7)
    # ---- first days ----
    add(buf,s_murmur(),349.5,1.0); add(buf,s_murmur(),355.0,0.8); add(buf,s_murmur(),361.0,0.9)
    rs=349.5
    while rs<367: add(buf,s_step(),rs,random.uniform(0.3,0.6)); rs+=random.uniform(0.25,0.5)
    add(buf,s_murmur(),367.5,0.9); add(buf,s_murmur(),374.0,0.7)
    for c in (370.0,373.5,379.0): add(buf,s_cough(),c,0.9)
    ck=367
    while ck<385: add(buf,s_crackle(),ck,random.uniform(0.3,0.7)); ck+=random.uniform(0.3,0.9)
    add(buf,s_wind(),385.0,1.0); add(buf,s_wind(),393.0,0.8)
    add(buf,s_page(),388.0,0.6); add(buf,s_page(),392.5,0.5)
    add(buf,s_drone(),386.0,0.7)
    add(buf,s_wind(),401.0,0.9)
    ck=401.5
    while ck<417: add(buf,s_crackle(),ck,random.uniform(0.6,1.3)); ck+=random.uniform(0.12,0.4)
    add(buf,s_thud(),407.0,0.6); add(buf,s_thud(),412.0,0.5)
    add(buf,s_wind(),417.0,1.0); add(buf,s_wind(),425.0,0.9)
    add(buf,s_groan(),424.0,0.7)
    add(buf,s_hb(),429.0,0.6)
    # ---- dossier ticks ----
    for i in range(6):
        t0=438.5+i*9
        add(buf,s_tick(),t0,0.7); add(buf,s_stamp(),t0+1.2,0.8)
    add(buf,s_drone(),438.0,0.6); add(buf,s_drone(),492.0,0.6)
    # tension ducks applied later
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
def ease(u): return u*u*(3-2*u)
def pose_u(t,times,blend):
    k=sum(1 for ti in times if t>=ti)
    if k==0: return 0.0
    d=t-times[k-1]
    if d>=blend: return float(k%2)
    return (k-1)%2+(1 if k%2 else -1)*smooth(min(d/blend,1.0))

NOTE_LINES=[
"═════════════════════════════════",
"  ДНЕВНИК НАБЛЮДЕНИЙ — ЗАПИСЬ 50",
"  Проект «БЕССОННИЦА» / Формула Z-01",
"  Сектор Б, Лаборатория №3",
"═════════════════════════════════",
"",
"Если вы читаете это — значит, я не успел.",
"",
"Объект №1 не спит 21 день. Я ошибся. Сон — это",
"не потеря времени. Сон — это когда тело чинит",
"то, что сломалось за день. Я отключил ремонт.",
"И тело нашло другой способ.",
"",
"Оно восстанавливается. Всегда. Но каждый раз —",
"чуть хуже. Чуть зеленее. Чуть меньше человека.",
"",
"Он больше не узнаёт меня. Не ест хлеб. Не ест",
"мясо. Вчера я видел, как он смотрит на охранника",
"у двери. Так, как я смотрю на ужин.",
"",
"Формула распространяется через укус — это",
"подтвердила проба крови крысы.",
"",
"Уничтожьте все 49 предыдущих записей.",
"Уничтожьте образцы в сундуке под алхимической",
"стойкой. Уничтожьте МЕНЯ, если найдёте — я",
"принял половину дозы три дня назад. Хотел",
"понять, что он чувствует.",
"",
"Он ничего не чувствует.",
"Он просто очень, очень устал.",
"",
"                    — д-р Э.",
"  [страница испачкана чем-то тёмным]",
]

def make_note():
    w,h=1240,940
    rnd=np.random.RandomState(5)
    noise=gaussian_filter(rnd.rand(h//4,w//4),2)
    nz=np.array(Image.fromarray((noise*40+196).astype(np.uint8)).resize((w,h),Image.BILINEAR),np.float32)
    arr=np.stack([nz,nz*0.97,nz*0.88],axis=2)
    yy,xx=np.mgrid[0:h,0:w]
    st=np.sqrt(((xx-0.82*w)/(0.16*w))**2+((yy-0.9*h)/(0.12*h))**2)
    stain=(st<1).astype(np.float32)*gaussian_filter(rnd.rand(h//2,w//2),3).repeat(2,0).repeat(2,1)[:h,:w]
    arr*=(1-stain[...,None]*0.75*np.array([0.55,0.35,0.3]))
    img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
    d=ImageDraw.Draw(img)
    f=ImageFont.truetype(FONT_M,24)
    y=36
    for ln in NOTE_LINES:
        d.text((60,y),ln,font=f,fill=(40,36,30)); y+=26
    return np.array(img)

EMPLOYEES=[
 ("ВОРОНИН Э.","зав. Сектором Б","ЗАРАЖЁН","принял 1/2 дозы на 21-й день",(196,178,150),(70,60,50),(60,160,70),"short"),
 ("ВОЛКОВ М.","объект N1, доброволец","НА СВОБОДЕ","ноль-пациент. не сдержан",(188,170,145),(60,45,35),(120,220,120),"short"),
 ("КРАВЦОВ И.","охрана, сержант","СЪЕДЕН","запись 47: пост вскрыт",(200,180,155),(50,45,40),(90,90,95),"helmet"),
 ("СМИРИНА О.","лаборант","ЛИКВИДИРОВАНА","протокол 9, при эвакуации образцов",(205,185,160),(120,80,40),(90,90,95),"long"),
 ("ХАН Л.","врач-наблюдатель","ЭВАКУИРОВАНА","не спит 72 часа. под надзором",(190,172,148),(30,28,26),(90,90,95),"long"),
 ("РУИЗ Д.","охрана, рядовой","СУДЬБА НЕИЗВЕСТНА","на связь не вышел. камера offline",(185,165,140),(80,60,30),(90,90,95),"helmet"),
]
ST_COL={"ЗАРАЖЁН":(90,220,100),"НА СВОБОДЕ":(230,70,60),"СЪЕДЕН":(180,40,40),"ЛИКВИДИРОВАНА":(210,210,210),
        "ЭВАКУИРОВАНА":(230,200,90),"СУДЬБА НЕИЗВЕСТНА":(160,160,160)}

def make_head(skin,hair,eyes,style):
    px=np.zeros((16,16,3),np.float32)
    px[:,:]=np.array(skin)/255
    rnd=np.random.RandomState(hash((skin,hair,style))%1000)
    px+= (rnd.rand(16,16,3)-0.5)*0.03
    if style in ("short","long"):
        px[0:4,:]=np.array(hair)/255
        if style=="long": px[4:12,0:2]=np.array(hair)/255; px[4:12,14:16]=np.array(hair)/255
    elif style=="helmet":
        px[0:5,:]=np.array((150,150,155))/255; px[4:6,:]=np.array((120,120,125))/255
    px[7:9,3:6]=np.array(eyes)/255; px[7:9,10:13]=np.array(eyes)/255
    px[8,4]=np.array((20,20,20))/255; px[8,11]=np.array((20,20,20))/255
    px[12,6:10]=np.array((120,90,80))/255
    img=Image.fromarray((np.clip(px,0,1)*255).astype(np.uint8)).resize((256,256),Image.NEAREST)
    return img

def make_card(i):
    w,h=1500,760
    img=Image.new("RGB",(w,h),(24,26,28)); d=ImageDraw.Draw(img)
    d.rectangle([0,0,w,8],fill=(60,200,110)); d.rectangle([0,h-8,w,h],fill=(60,200,110))
    name,role,status,note,skin,hair,eyes,style=EMPLOYEES[i]
    head=make_head(skin,hair,eyes,style)
    d.rectangle([60,60,60+280,60+280],fill=(40,44,48)); d.rectangle([70,70,70+260,70+260],fill=(15,16,18))
    img.paste(head,(70,70))
    f1=ImageFont.truetype(FONT_B,52); f2=ImageFont.truetype(FONT_M,34); f3=ImageFont.truetype(FONT_M,28)
    d.text((400,90),name,font=f1,fill=(230,230,230))
    d.text((400,170),role,font=f2,fill=(150,160,155))
    d.text((400,230),"ДОПУСК: Б-3 // СЕКТОР Б, ЛАБ. N3",font=f3,fill=(110,120,115))
    d.text((400,300),"СТАТУС:",font=f3,fill=(150,160,155))
    col=ST_COL[status]
    d.text((560,292),status,font=ImageFont.truetype(FONT_B,44),fill=col)
    d.text((400,380),note,font=f3,fill=(130,140,135))
    d.line([(400,470),(w-80,470)],fill=(60,64,66),width=3)
    d.text((400,500),f"КАРТОЧКА {i+1}/6 // АРХИВ ПРОЕКТА",font=f3,fill=(90,100,95))
    # stamp
    fs=80 if len(status)<=9 else 52
    fB=ImageFont.truetype(FONT_B,fs)
    tmp=Image.new("RGBA",(10,10)); dt=ImageDraw.Draw(tmp)
    bb=dt.textbbox((0,0),status,font=fB)
    sw,sh=bb[2]-bb[0],bb[3]-bb[1]
    st=Image.new("RGBA",(sw+120,sh+80),(0,0,0,0)); ds=ImageDraw.Draw(st)
    ds.rectangle([6,6,sw+114,sh+74],outline=col+(255,),width=8)
    ds.text((60-bb[0],40-bb[1]),status,font=fB,fill=col+(235,))
    st=st.rotate(-8,expand=True,resample=Image.BILINEAR)
    img=img.convert("RGBA"); img.alpha_composite(st,(min(w-780,w-st.size[0]-40),430))
    return np.array(img.convert("RGB"))

STATUS_LINES=[
"> ПРОЕКТ «БЕССОННИЦА» // ИТОГОВЫЙ СТАТУС",
"",
"Сектор Б: уничтожен протоколом 9.",
"Город N: карантин снят на 14-й день. Досрочно.",
"Подтверждённых заражённых: 4 217. Динамика: растёт.",
"Формула Z-01: стабильна. Инкубация: до 72 часов.",
"Передача: укус, затем — воздух при контакте 30+ мин.",
"",
"Вывод комиссии: ОБЪЕКТ НЕ СДЕРЖАН.",
"Проект продолжается. Без нас.",
]

def main():
    os.makedirs(f"{ROOT}/video", exist_ok=True)
    os.makedirs(f"{ROOT}/audio", exist_ok=True)
    A=lambda p: rd(f"{ROOT}/audio/{p}")
    narr=A("_w_narration_A.wav"); vo2=A("_w_vo_part2.wav"); vo3=A("_w_vo_part3.wav")
    vo4=A("_w_vo_part4.wav"); vos=A("_w_system.wav"); voe=A("_w_epilog.wav"); rad=A("_w_radio.wav")

    S=lambda p: np.array(Image.open(f"{ROOT}/assets/shots/{p}").convert("RGB"))
    IMG={k:S(p) for k,p in {
      "c1":"c1_hall.jpg","c7a":"c7_walk.jpg","c7b":"c7_walk_b.jpg","c3a":"c3_glass.jpg","c3b":"c3_glass_b.jpg",
      "c4a":"c4_profile.jpg","c4b":"c4_profile_b.jpg","c5a":"c5_dispenser.jpg","c6a":"c6_eyes.jpg","c6b":"c6_eyes_b.jpg",
      "t1d":"t1_day.jpg","t1n":"t1_night.jpg","t1b":"t1_day_b.jpg","t2":"t2_bed_steaks.jpg","t3":"t3_obsidian.jpg","t4":"t4_skin2.jpg",
      "m1":"m1_skin3.jpg","m2":"m2_knock.jpg","m3":"m3_head_up.jpg","m4":"m4_punch.jpg",
      "b1":"b1_book.jpg","b2":"b2_zombie_glass.jpg","b3":"b3_shatter.jpg","b4":"b4_siren.jpg",
      "b5":"b5_attack.jpg","b6":"b6_run.jpg","e1":"e1_feet.jpg","e2":"e2_dark.jpg",
      "d1":"d1_evac.jpg","d2":"d2_checkpoint.jpg","d3":"d3_city.jpg","d4":"d4_fire.jpg","d5":"d5_street.jpg"}.items()}
    NOTE=make_note()
    CARDS=[make_card(i) for i in range(6)]
    end50=pix_card(W,H,[("ЗАПИСЬ 50 ИЗ 50",72,(220,220,220),0)])
    title=pix_card(W,H,[("ТРЕТЬ ЖИЗНИ",120,(220,220,220),-60),("хоррор по материалам Сектора Б",36,(120,140,125),120)])

    P1S=["Дневник наблюдений. Запись сорок вторая.","Кажется... мы наконец добились успеха.",
         "Человечеству больше не нужно тратить треть жизни на сон.","Треть жизни — в темноте, в пустоте.",
         "Формула «Зет-ноль-один» работает.","Должна работать."]
    P2S=["Прошла неделя.","Объект номер один не спит уже сто шестьдесят восемь часов.",
         "Продуктивность выросла на триста процентов.","Потребность в пище снизилась втрое — он почти не притрагивается к стейкам.",
         "Физическая сила... невероятная.","Сегодня он голыми руками сломал обсидиан.","Быстрее, чем алмазной киркой.",
         "Я не понимаю, откуда берётся энергия."]
    P3S=["Запись... пятидесятая.","Что-то пошло не так.",
         "Регенерация клеток вышла из-под контроля — ткани восстанавливаются быстрее, чем разрушаются, но... но неправильно.",
         "Мозг перестал регистрировать высшие функции.","Он не отвечает на команды.","Не реагирует на своё имя.",
         "Он не ест то, что я даю.","Он просто... смотрит на меня.","Уже третий час."]
    P4S=["Охрана! ОХРАНА!","Включите протокол изоляции! Закройте сектор Б!","Оно... оно вырвалось!","Нет! НЕТ!","А-А-А!"]
    SYS=["Внимание. Протокол изоляции.","Прорыв в секторе Б.","Внимание. Прорыв в секторе Б."]
    EPS=["Мы хотели победить сон...","...но вместо этого проснулся кошмар."]
    def layout(sent,start,dur):
        tot=sum(len(s) for s in sent); out=[]; cur=start
        for s in sent:
            d=dur*len(s)/tot; out.append((cur,cur+d,s)); cur+=d
        return out
    SUBS=layout(P1S,12.15,22.5)+layout(P2S,76.15,30.8)+layout(P3S,151.15,32.1)+layout(P4S,225.6,12.3)+\
         [(256.1,262.4,SYS[0]),(262.4,265.6,SYS[1]),(265.6,268.8,SYS[2])]+layout(EPS,281.1,7.5)
    SYST=(256.0,268.9)
    DAYTAG=[(349,367,"ДЕНЬ 1 // ЭВАКУАЦИЯ СЕКТОРА Б"),(367,385,"ДЕНЬ 2 // КАРАНТИННЫЙ ПОСТ"),
            (385,401,"ДЕНЬ 3 // ГОРОД ПУСТЕЕТ"),(401,417,"ДЕНЬ 5 // ПЕРВЫЕ КОСТРЫ"),
            (417,435,"ДЕНЬ 7 // ОНИ ХОДЯТ СРЕДИ НАС")]

    def mkfog(seed):
        r=np.random.RandomState(seed)
        g=gaussian_filter(r.rand(135,240),6)
        return (g-g.min())/(g.max()-g.min())
    FOG1,FOG2=mkfog(3),mkfog(9)
    yy,xx=np.mgrid[0:H,0:W]
    r2=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
    VIG=np.clip(1-0.45*np.clip((r2-0.5)/0.65,0,1)**2,0.42,1).astype(np.float32)[...,None]
    NP=45
    px=np.random.rand(NP); py=np.random.rand(NP)
    vx=(np.random.rand(NP)-0.5)*0.006; vy=(np.random.rand(NP)-0.5)*0.003-0.0015
    ph=np.random.rand(NP)*6.28
    NB=26
    bx=np.random.rand(NB); boff=np.random.rand(NB)*10; bsp=0.05+np.random.rand(NB)*0.05
    grain=np.random.RandomState(11).rand(270,480)*2-1

    def crop(img,cx,cy,z):
        h0,w0=img.shape[:2]
        cw,ch=w0/z,h0/z
        x0=min(max(cx*w0-cw/2,0),w0-cw); y0=min(max(cy*h0-ch/2,0),h0-ch)
        return np.array(Image.fromarray(img[int(y0):int(y0+ch),int(x0):int(x0+cw)]).resize((W,H),Image.NEAREST),dtype=np.float32)

    def sway(base,box,t,amp=2.0,f=0.35,rot=0.35,phase=0.0):
        h0,w0,_=base.shape
        x0,y0,x1,y1=box; F=48
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

    def light(t,amt=0.03):
        return 1.0-amt*(0.5+0.5*math.sin(2*np.pi*6.1*t))*0.5-amt*(0.5+0.5*math.sin(2*np.pi*0.21*t))

    def fog_add(base,t,fog):
        off1=int(t*5)%240; off2=int(-t*3)%240
        fm=np.array(Image.fromarray((np.roll(FOG1,off1,1)*0.6+np.roll(FOG2,off2,1)*0.4).astype(np.float32)).resize((W,H),Image.BILINEAR),np.float32)[...,None]
        base+=fm*fog*np.array([14,28,26],np.float32)*0.8

    def grade(base,warm=6):
        base=(base-128)*1.10+128
        luma=base.mean(axis=2,keepdims=True)
        base+=np.clip(1-luma/150,0,1)*np.array([-6,4,6],np.float32)
        base+=np.clip((luma-160)/95,0,1)*np.array([warm,4,-2],np.float32)
        small=Image.fromarray(np.clip(base,0,255).astype(np.uint8)).resize((480,270))
        bl=np.array(small.filter(ImageFilter.GaussianBlur(7)).resize((W,H),Image.BILINEAR),np.float32)
        base+=bl*np.clip((luma-170)/90,0,1)*0.5
        return base

    def dust(base,t):
        for i in range(NP):
            X=int(((px[i]+vx[i]*t)%1)*W); Y=int(((py[i]+vy[i]*t)%1)*H)
            a=0.2+0.2*math.sin(5*t+ph[i])
            if 2<Y<H-2 and 2<X<W-2: base[Y-1:Y+2,X-1:X+2]+=a*26

    def bubbles(base,t,area):
        x0f,x1f,span=area
        for i in range(NB):
            X=int((x0f+(x1f-x0f)*bx[i])*W)
            prog=((t*bsp[i]+boff[i])%1.0)
            Y=int((0.78-prog*span)*H)
            al=(1-prog)*0.5*math.sin(np.pi*min(prog*4,1))
            if 2<Y<H-2 and 2<X<W-2:
                base[Y-2:Y+2,X-1:X+2]+=np.array([30,90,40],np.float32)*al

    FR=int(T*FPS)
    STRIDE=int(os.environ.get("STRIDE","1"))
    SEGL=30.0; NSEG=int(math.ceil(T/SEGL))
    def seg_path(s): return f"{ROOT}/video/_seg_{s:02d}.mp4"
    def seg_done(s):
        p=seg_path(s)
        return os.path.exists(p) and os.path.getsize(p)>10000
    fr=0; enc=None; cur_seg=-1
    while fr<FR:
        seg=min(int(fr//(SEGL*FPS)),NSEG-1)
        if seg!=cur_seg:
            if enc is not None:
                enc.stdin.close(); enc.wait(); enc=None
                print(f"seg {cur_seg} done",flush=True)
            if seg_done(seg):
                print(f"seg {seg} skip",flush=True)
                fr=int((seg+1)*SEGL*FPS); cur_seg=seg; continue
            enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
                                  "-r",str(FPS),"-i","-","-c:v","libx264","-pix_fmt","yuv420p",
                                  "-crf","24","-preset","medium",seg_path(seg)],
                                 stdin=subprocess.PIPE)
            cur_seg=seg
        t=fr/FPS
        rec = 10.0<=t<278.6
        if t<10.0:
            img=Image.new("RGB",(W,H),(0,0,0)); d=ImageDraw.Draw(img)
            f2=ImageFont.truetype(FONT_B,30)
            d.text((180,H//2-170),"ПРОЕКТ «БЕССОННИЦА»",font=f2,fill=(70,190,90))
            f=ImageFont.truetype(FONT_M,44)
            txt="> СЕКТОР Б, ЛАБ. №3 // СТАТУС: ВСЁ В ПОРЯДКЕ"
            shown=txt[:int(max(0,(t-0.7))*22)]
            d.text((180,H//2-40),shown,font=f,fill=(150,220,160))
            if int(t*3)%2==0 and t>0.7:
                bbw=d.textbbox((180,H//2-40),shown,font=f)
                d.rectangle([bbw[2]+6,H//2-40,bbw[2]+30,H//2+10],fill=(150,220,160))
            f3=ImageFont.truetype(FONT_M,30)
            d.text((180,H//2+40),"служебная запись...",font=f3,fill=(90,120,95))
            base=np.array(img,np.float32)*min(t/0.5,1.0)*min((10.0-t)/0.4,1.0)
        elif t<35:
            u=ease(min((t-10)/25,1))
            base=crop(IMG["c1"],0.5,0.55-0.03*u,1.02+0.22*u)
            sway(base,(int(0.52*W),int(0.42*H),int(0.74*W),int(0.86*H)),t,2.0,0.33,0.35,0.5)
            base=grade(base); fog_add(base,t,0.35); dust(base,t); bubbles(base,t,(0.10,0.40,0.30))
            base*=light(t); base*=VIG
            if t<10.4: base*=0.2+0.8*abs(1-2*min((t-10)/0.4,1))
        elif t<45:
            u=ease(min((t-35)/10,1)); u7=pose_u(t,[35.8,36.9,38.0,39.1,40.2,41.3,42.4,43.5],0.18)
            a=crop(IMG["c7a"],0.5,0.55,1.05+0.11*u); b=crop(IMG["c7b"],0.5,0.55,1.05+0.11*u)
            base=a*(1-u7)+b*u7
            base=np.roll(base,int(1.6*math.sin(2*np.pi*(t-35.8)/1.1+math.pi/2)),axis=0)
            base=grade(base); fog_add(base,t,0.3); dust(base,t); base*=light(t); base*=VIG
            if 34.9<t<35.4: base*=0.2+0.8*abs(1-2*(t-34.9)/0.5)
        elif t<55:
            u=ease(min((t-45)/10,1)); u3=pose_u(t,[49.5],0.3)
            a=crop(IMG["c3a"],0.55-0.1*u,0.5,1.05+0.12*u); b=crop(IMG["c3b"],0.55-0.1*u,0.5,1.05+0.12*u)
            base=a*(1-u3)+b*u3
            sway(base,(int(0.28*W),int(0.30*H),int(0.52*W),int(0.80*H)),t,1.8,0.3,0.35,1.0)
            sway(base,(int(0.68*W),int(0.28*H),int(0.90*W),int(0.86*H)),t,2.0,0.36,0.35,2.1)
            base=grade(base); fog_add(base,t,0.3); dust(base,t); base*=light(t); base*=VIG
            if 44.9<t<45.4: base*=0.2+0.8*abs(1-2*(t-44.9)/0.5)
        elif t<63:
            u=ease(min((t-55)/8,1))
            base=crop(IMG["c5a"],0.47+0.03*u,0.5,1.02+0.18*u)
            sway(base,(int(0.60*W),int(0.30*H),int(0.98*W),int(0.85*H)),t,1.8,0.37,0.35,1.6)
            base=grade(base); fog_add(base,t,0.3); dust(base,t); bubbles(base,t,(0.44,0.62,0.35)); base*=light(t); base*=VIG
            if 54.9<t<55.4: base*=0.2+0.8*abs(1-2*(t-54.9)/0.5)
        elif t<75:
            u=ease(min((t-63)/12,1)); u6=pose_u(t,[68.0,68.6],0.12)
            a=crop(IMG["c6a"],0.5,0.46,1.05+0.2*u); b=crop(IMG["c6b"],0.5,0.46,1.05+0.2*u)
            base=a*(1-u6)+b*u6
            sway(base,(int(0.22*W),int(0.02*H),int(0.80*W),int(0.98*H)),t,1.5,0.3,0.3,0.8)
            sp=0.5+0.5*math.sin(2*np.pi*0.5*t)
            for (ex,ey) in ((0.385,0.46),(0.645,0.46)):
                X,Y=int(ex*W),int(ey*H)
                base[Y-14:Y+14,X-26:X+26]+=np.array([10,45,18],np.float32)*(0.10+0.10*sp)
            base=grade(base); fog_add(base,t,0.3); dust(base,t); base*=light(t); base*=VIG
            if 62.9<t<63.4: base*=0.2+0.8*abs(1-2*(t-62.9)/0.5)
        elif t<105:
            cyc=(t-75)/(30.0/7); phc=cyc%1
            bl=smooth(min(max((abs(phc-0.5))/0.04,0),1)) if abs(phc-0.5)<0.04 else (0 if phc<0.5 else 1)
            z=1.06+0.02*math.sin(t*0.3)
            a=crop(IMG["t1d"],0.5,0.5,z); b=crop(IMG["t1n"],0.5,0.5,z)
            base=a*(1-bl)+b*bl
            uc=pose_u(t,[75.5+1.07*k for k in range(28)],0.12)
            bb=crop(IMG["t1b"],0.5,0.5,z)
            base=base*(1-uc)+(bb if bl<0.5 else b)*uc
            base*=1.0+0.06*math.sin(2*np.pi*8*t)*(1 if int(cyc)%2 else 0.5)
            base=grade(base); fog_add(base,t,0.25); dust(base,t); base*=light(t,0.05); base*=VIG
            if 74.9<t<75.4: base*=0.2+0.8*abs(1-2*(t-74.9)/0.5)
        elif t<125:
            u=ease(min((t-105)/20,1))
            base=crop(IMG["t2"],0.55-0.12*u,0.5,1.05+0.12*u)
            base=grade(base); fog_add(base,t,0.3); dust(base,t); base*=light(t,0.02); base*=VIG
            if 104.9<t<105.4: base*=0.2+0.8*abs(1-2*(t-104.9)/0.5)
        elif t<140:
            u=ease(min((t-125)/15,1))
            base=crop(IMG["t3"],0.5,0.5,1.05+0.15*u)
            if (abs(t-126.2)<0.3 or abs(t-130.7)<0.3 or abs(t-135.2)<0.3): base=np.roll(base,3,axis=1)
            base=grade(base); fog_add(base,t,0.3); dust(base,t); base*=light(t); base*=VIG
            if 124.9<t<125.4: base*=0.2+0.8*abs(1-2*(t-124.9)/0.5)
        elif t<150:
            tt=min(t,148.0)
            base=crop(IMG["t4"],0.5,0.47,1.1+0.08*ease(min(tt-140,8)/8))
            base=grade(base); fog_add(base,tt,0.35); base*=light(tt); base*=VIG
            if t>=148: base*=0.92
            if 139.9<t<140.4: base*=0.2+0.8*abs(1-2*(t-139.9)/0.5)
        elif t<170:
            u=ease(min((t-150)/20,1))
            base=crop(IMG["m1"],0.5,0.5,1.05+0.12*u)
            sway(base,(int(0.35*W),int(0.2*H),int(0.65*W),int(0.9*H)),t,1.2,0.25,0.2,0.4)
            fl=1.0
            for a,b in ((152.2,152.35),(156.8,156.95),(161.3,161.5),(166.0,166.12)):
                if a<=t<b: fl=0.45
            base*=fl
            base=grade(base,2); fog_add(base,t,0.45); dust(base,t); base*=light(t,0.05); base*=VIG
            if 149.9<t<150.4: base*=0.2+0.8*abs(1-2*(t-149.9)/0.5)
        elif t<194:
            u=ease(min((t-170)/24,1))
            base=crop(IMG["m2"],0.5+0.04*u,0.5,1.05+0.1*u)
            if sum(1 for k in (172.0,174.0,176.0) if abs(t-k)<0.12): base=np.roll(base,2,axis=1)
            sway(base,(int(0.55*W),int(0.2*H),int(0.95*W),int(0.9*H)),t,2.0,0.4,0.3,1.1)
            base=grade(base,2); fog_add(base,t,0.4); dust(base,t); base*=light(t,0.05); base*=VIG
            if 169.9<t<170.4: base*=0.2+0.8*abs(1-2*(t-169.9)/0.5)
        elif t<195.5:
            base=np.zeros((H,W,3),np.float32)  # tension gap: silence+black
        elif t<215:
            u=ease(min((t-195.5)/19.5,1))
            base=crop(IMG["m3"],0.5,0.47,1.05+0.3*u)
            sway(base,(int(0.3*W),int(0.1*H),int(0.7*W),int(0.95*H)),t,1.5,0.22,0.25,0.2)
            base=grade(base,0); fog_add(base,t,0.5); dust(base,t); base*=light(t,0.06); base*=VIG
            base*=min((t-195.5)/0.8,1.0)
        elif t<225:
            u=ease(min((t-215)/10,1))
            base=crop(IMG["m4"],0.5,0.5,1.05+0.15*u)
            if abs(t-215.6)<0.25: base=np.roll(base,4,axis=1)
            base=grade(base,0); fog_add(base,t,0.4); dust(base,t); base*=light(t,0.06); base*=VIG
            if 214.9<t<215.4: base*=0.2+0.8*abs(1-2*(t-214.9)/0.5)
        elif t<235:
            u=ease(min((t-225)/10,1))
            base=crop(IMG["b1"],0.5,0.6,1.05+0.15*u)
            base=grade(base,8); fog_add(base,t,0.35); dust(base,t); base*=light(t,0.06); base*=VIG
            if 224.9<t<225.4: base*=0.2+0.8*abs(1-2*(t-224.9)/0.5)
        elif t<250:
            u=ease(min((t-235)/15,1))
            base=crop(IMG["b2"],0.5,0.5,1.05+0.15*u)
            for g in (236.0,238.5,241.0,243.5,246.5):
                if abs(t-g)<0.18: base=np.roll(base,int(5*math.sin(g*13)),axis=1)
            base+=np.array([40,4,4],np.float32)*max(0.15+0.15*math.sin(2*np.pi*t),0)
            base=grade(base,8); fog_add(base,t,0.4); dust(base,t); base*=light(t,0.08); base*=VIG
            if 234.9<t<235.4: base*=0.2+0.8*abs(1-2*(t-234.9)/0.5)
        elif t<255:
            u=min((t-250)/5,1)
            base=crop(IMG["b3"],0.5,0.5,1.05+0.25*ease(u))
            if t<251.0: base=np.roll(base,int(8*math.sin(t*60)),axis=1)
            base+=np.array([45,5,5],np.float32)*(0.2+0.15*math.sin(2*np.pi*2*t))
            base=grade(base,10); fog_add(base,t,0.45); dust(base,t); base*=light(t,0.1); base*=VIG
            if 249.9<t<250.3: base*=0.3+0.7*abs(1-2*(t-249.9)/0.4)
        elif t<260:
            base=crop(IMG["b4"],0.5,0.5,1.05+0.1*ease(min((t-255)/5,1)))
            base+=np.array([60,6,6],np.float32)*(0.25+0.25*math.sin(2*np.pi*t))
            base=grade(base,12); fog_add(base,t,0.5); base*=light(t,0.12); base*=VIG
        elif t<270:
            u=ease(min((t-260)/10,1))
            base=crop(IMG["b5"],0.5,0.5,1.05+0.15*u)
            for g in (261.2,263.2,264.6,266.0):
                if abs(t-g)<0.15: base=np.roll(base,int(6*math.sin(g*7)),axis=0)
            base+=np.array([50,5,5],np.float32)*(0.2+0.2*math.sin(2*np.pi*t))
            base=grade(base,12); fog_add(base,t,0.5); dust(base,t); base*=light(t,0.12); base*=VIG
            if 259.9<t<260.4: base*=0.2+0.8*abs(1-2*(t-259.9)/0.5)
        elif t<280:
            u=ease(min((t-270)/10,1))
            base=crop(IMG["b6"],0.5,0.5,1.05+0.2*u)
            if t<272: base=np.roll(base,int(4*math.sin(t*40)),axis=1)
            redr=0.2+0.5*max(min((t-270)/10,1),0)
            base=base*(1-redr*0.4)+np.array([120,10,10],np.float32)*redr*0.4
            base=grade(base,12); fog_add(base,t,0.5); dust(base,t); base*=VIG
        elif t<290:
            u=ease(min((t-280)/10,1))
            base=crop(IMG["e1"],0.5,0.6,1.02+0.08*u)
            sway(base,(int(0.1*W),int(0.3*H),int(0.9*W),int(0.75*H)),t,1.5,0.5,0.2,0.3)
            base=grade(base,4); fog_add(base,t,0.5); dust(base,t); base*=VIG
            base*=0.9+0.1*math.sin(2*np.pi*0.3*t)
        elif t<297:
            base=crop(IMG["e2"],0.5,0.5,1.05)
            steps=[290.6,291.6,292.6,293.6]
            base*=(0.15+0.85*(1-min(sum(1 for s in steps if t>s)/4.0,1)*0.9))
            base+=np.array([80,12,8],np.float32)*(0.25+0.1*math.sin(2*np.pi*9*t))
            base*=VIG
        elif t<300.5:
            base=np.array(end50,np.float32)*min((t-297)/0.5,1.0)*min((300.5-t)/0.4,1.0)
        elif t<345:
            u=min((t-300.5)/44.5,1)
            z=1.0+0.12*u
            nh,nw=NOTE.shape[:2]
            cw,ch=nw/z,nh/z
            xi=int(max(0,min((nw-cw)/2+10*math.sin(t*0.2),nw-cw)))
            yi=int(max(0,min((nh-ch)/2,nh-ch)))
            note=Image.fromarray(NOTE[yi:yi+int(ch),xi:xi+int(cw)]).resize((int(W*0.62),int(H*0.8)),Image.LANCZOS)
            base=np.zeros((H,W,3),np.float32)
            na=np.array(note,np.float32)
            X0=(W-na.shape[1])//2; Y0=(H-na.shape[0])//2
            base[Y0:Y0+na.shape[0],X0:X0+na.shape[1]]=na
            base*=(0.85+0.15*math.sin(2*np.pi*0.5*t))
            base*=VIG
            base*=min((t-300.5)/0.8,1.0)
        elif t<349:
            img=Image.new("RGB",(W,H),(0,0,0)); d=ImageDraw.Draw(img)
            f=ImageFont.truetype(FONT_M,54)
            txt="ПЕРВЫЕ ДНИ // ХРОНИКА ВЫРЫВАВШЕГОСЯ ЗАРАЖЕНИЯ"
            shown=txt[:int(max(0,(t-345.5))*24)]
            d.text((180,H//2-30),shown,font=f,fill=(200,90,80))
            base=np.array(img,np.float32)*min((t-345)/0.5,1.0)*min((349-t)/0.4,1.0)
        elif t<435:
            key="d1" if t<367 else "d2" if t<385 else "d3" if t<401 else "d4" if t<417 else "d5"
            t0={"d1":349,"d2":367,"d3":385,"d4":401,"d5":417}[key]; t1=t0+(18 if key in("d1","d2") else 16 if key in("d3","d4") else 18)
            u=ease(min((t-t0)/(t1-t0),1))
            amp=0.008 if key=="d1" else 0.004
            hx=amp*W*math.sin(2*np.pi*1.7*t)+0.003*W*math.sin(2*np.pi*3.1*t)
            base=crop(IMG[key],0.5+hx/W,0.5,1.08+0.15*u)
            warm= 10 if key=="d4" else 4
            base=grade(base,warm); fog_add(base,t,0.5 if key!="d4" else 0.3); dust(base,t)
            if key=="d4":
                base+=np.array([50,18,4],np.float32)*(0.15+0.1*math.sin(2*np.pi*7*t)+0.05*math.sin(2*np.pi*13*t))
            base*=light(t,0.07); base*=VIG
            if t-t0<0.5: base*=0.2+0.8*abs(1-2*(t-t0)/0.5)
        elif t<438:
            base=np.zeros((H,W,3),np.float32)
        elif t<492:
            i=int((t-438)//9); i=min(i,5)
            card=CARDS[i]
            base=np.zeros((H,W,3),np.float32)
            ca=np.array(Image.fromarray(card).resize((int(W*0.78),int(H*0.78*760/1500)),Image.LANCZOS),np.float32)
            u=min((t-(438+i*9))/0.5,1)
            X0=(W-ca.shape[1])//2+int((1-ease(u))*120); Y0=(H-ca.shape[0])//2
            base[Y0:Y0+ca.shape[0],X0:X0+ca.shape[1]]=ca*ease(u)
            base*=VIG
        elif t<510:
            img=Image.new("RGB",(W,H),(5,6,6)); d=ImageDraw.Draw(img)
            f=ImageFont.truetype(FONT_M,38)
            y=180
            shown_all=int(max(0,(t-492))*60)
            cnt=0
            for ln in STATUS_LINES:
                rem=shown_all-cnt
                if rem<=0: break
                shown=ln[:rem]; cnt+=len(ln)
                col=(200,80,70) if ("НЕ СДЕРЖАН" in ln or "растёт" in ln) else (140,200,150) if ln.startswith(">") else (190,195,190)
                d.text((220,y),shown,font=f,fill=col)
                y+=56
            base=np.array(img,np.float32)
            base*=VIG
        elif t<522:
            base=np.array(title,np.float32)
            base*=min((t-510)/1.0,1.0)*min((522-t)/1.2,1.0)
            base*=0.9+0.1*math.sin(2*np.pi*0.4*t)
        else:
            base=np.zeros((H,W,3),np.float32)
        if 10<t<280 and not (148<=t<150):
            hx=int(6*math.sin(2*np.pi*0.29*t)+3*math.sin(2*np.pi*0.71*t+1.3))
            hy=int(5*math.sin(2*np.pi*0.23*t+0.7)+2*math.sin(2*np.pi*0.63*t))
            base=np.roll(base,(hy,hx),axis=(0,1))
        if 278.6<=t<279.6:
            ang=90*ease((t-278.6)/1.0)
            base=np.array(Image.fromarray(np.clip(base,0,255).astype(np.uint8)).rotate(ang,resample=Image.BILINEAR,expand=False,fillcolor=(0,0,0)),np.float32)
        elif 279.6<=t<280:
            base=np.array(Image.fromarray(np.clip(base,0,255).astype(np.uint8)).rotate(90,resample=Image.BILINEAR,expand=False,fillcolor=(0,0,0)),np.float32)
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
            secs=42*60+7+int(t)
            d.text((W-330,BAR+50),f"{secs//3600:02d}:{(secs//60)%60:02d}:{secs%60:02d}:{int((t%1)*FPS):02d}",font=f2,fill=(220,220,220,190))
            d.text((W-330,H-BAR-70),"CAM_03 // СЕКТОР Б",font=f2,fill=(200,200,200,150))
        for a,b,tag in DAYTAG:
            if a<=t<min(a+4,b):
                f=ImageFont.truetype(FONT_B,34)
                shown=tag[:int((t-a)*30)]
                for ox,oy in ((2,2),(-1,-1)): d.text((152+ox,BAR+52+oy),shown,font=f,fill=(0,0,0,200))
                d.text((152,BAR+52),shown,font=f,fill=(230,120,100,255))
        sub=None; is_sys=False
        for a,b,txt in SUBS:
            if a<=t<b+0.6:
                nch=min(len(txt),int((t-a)*26))
                if nch>0: sub=txt[:nch]; is_sys=(SYST[0]<=t<SYST[1])
                break
        if sub and t<290:
            f=ImageFont.truetype(FONT_B,40)
            col=(255,190,90,255) if is_sys else (235,242,238,250)
            for ox,oy,c in ((2,2,(0,0,0,210)),(-1,-1,(0,0,0,160))):
                d.text((150+ox,H-BAR-92+oy),sub,font=f,fill=c)
            d.text((150,H-BAR-92),sub,font=f,fill=col)
            if int(t*3)%2==0:
                bbw=d.textbbox((150,H-BAR-92),sub,font=f)
                d.rectangle([bbw[2]+8,H-BAR-92,bbw[2]+28,H-BAR-52],fill=(150,220,160,230))
        arr=np.array(Image.alpha_composite(canvas,ov).convert("RGB"),np.float32)
        arr[:BAR]=0; arr[H-BAR:]=0
        if t<300.5 or t>=435:
            gx,gy=np.random.randint(0,240),np.random.randint(0,160)
            gimg=np.array(Image.fromarray((grain[gy:gy+135,gx:gx+480]*127+127).astype(np.uint8)).resize((W,H),Image.NEAREST),np.float32)/255-0.5
            arr+=gimg[...,None]*5
        enc.stdin.write(np.clip(arr,0,255).astype(np.uint8).tobytes())
        if fr%960==0: print(f"frame {fr}/{FR} seg {cur_seg}",flush=True)
        fr+=STRIDE
    if enc is not None:
        enc.stdin.close(); enc.wait(); enc=None
        print(f"seg {cur_seg} done",flush=True)
    print("video done",flush=True)
    with open(f"{ROOT}/video/_segs.txt","w") as f:
        for s in range(NSEG): f.write(f"file '{seg_path(s)}'\n")
    subprocess.run([FF,"-y","-f","concat","-safe","0","-i",f"{ROOT}/video/_segs.txt",
                    "-c","copy",f"{ROOT}/video/_final_video.mp4"],check=True,capture_output=True)
    if STRIDE>1:
        print("SMOKE OK",flush=True); return
    sfx=build_sfx()
    # tension ducks on sfx only
    tt=np.arange(len(sfx))/SR
    for a,b in ((194.0,195.5),(249.3,250.3)):
        m=np.clip(np.minimum((tt-a)/0.2,(b-tt)/0.2),0,1)
        sfx*= (0.15+0.85*m)
    mix=sfx.copy()
    add(mix,narr,12.0,1.0); add(mix,vo2,76.0,1.0); add(mix,vo3,151.0,1.0)
    add(mix,vo4,225.5,1.0); add(mix,vos,256.0,0.9); add(mix,voe,281.0,1.0); add(mix,rad,351.0,0.8)
    mix=np.tanh(mix*1.4)/np.tanh(1.4)*0.9
    Lch=mix; Rch=np.roll(mix,int(0.006*SR))*0.95
    with wave.open(f"{ROOT}/audio/_mixfinal.wav","wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        st=np.empty(len(Lch)*2,dtype=np.int16)
        st[0::2]=(Lch*32767).astype(np.int16); st[1::2]=(Rch*32767).astype(np.int16)
        w.writeframes(st.tobytes())
    subprocess.run([FF,"-y","-i",f"{ROOT}/audio/_mixfinal.wav","-c:a","libmp3lame","-b:a","192k",
                    f"{ROOT}/audio/INSOMNIA_full_mix.mp3"],check=True,capture_output=True)
    subprocess.run([FF,"-y","-i",f"{ROOT}/video/_final_video.mp4","-i",f"{ROOT}/audio/_mixfinal.wav",
                    "-c:v","copy","-c:a","aac","-b:a","192k","-ar","44100","-ac","2","-shortest",
                    f"{ROOT}/video/TRET_JIZNI_full.mp4"],check=True,capture_output=True)
    print("FINAL DONE",flush=True)

if __name__=="__main__":
    main()
