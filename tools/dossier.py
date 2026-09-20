"""Досье v2: страницы-документы (фото 3D-бюста, машинопись, штампы)."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import anim
ROOT=os.environ.get("ROOT","/home/user/repo")
FM="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PAGES=[
 dict(n=1,name="ВОРОНИН А. П.",role="старший научный сотрудник",status="НЕ СПИТ 11 ДНЕЙ",stamp="ЗАРАЖЁН",
      note="ввёл себе двойную дозу.\nсчитает, что сон украдёт у него\nоткрытие.",glow=0.5),
 dict(n=2,name="ВОЛКОВ Д. М.",role="объект №1, доброволец",status="РАЗРУШИЛ СТЕНУ КАМЕРЫ",stamp="НА СВОБОДЕ",
      note="«я наконец выспался».\nпоследняя фраза в протоколе.",glow=0.8),
 dict(n=3,name="КРАВЦОВ И. С.",role="оператор сектора Б",status="ПРОПАЛ В НОЧЬ ПРОРЫВА",stamp="СЪЕДЕН",
      note="на стене камеры найдены\nследы. ногти. не его.",glow=0.0),
 dict(n=4,name="СМИРИНА Л. Ф.",role="врач-наблюдатель",status="ПОДОЖГЛА ЛАБОРАТОРИЮ",stamp="ЛИКВИДИРОВАНА",
      note="«лучше сжечь, чем дописать».\nзаписка приложена к делу.",glow=0.0),
 dict(n=5,name="ХАН Ю.",role="химик, дозиметрист",status="ЭВАКУИРОВАНА 14-ГО ДНЯ",stamp="ЭВАКУИРОВАНА",
      note="на выходе написала мелом:\n«ПРОЩАЙТЕ». не спала 9 дней.",glow=0.2),
 dict(n=6,name="РУИЗ М.",role="техник связи",status="НЕ ВЫШЛА НА СВЯЗЬ",stamp="НЕИЗВЕСТНА",
      note="последний пакет: 4 секунды\nзвука. в нём кто-то дышит.",glow=0.4),
]

def paper_tex(w,h,seed):
    rs=np.random.RandomState(seed)
    p=np.full((h,w,3),236,np.float32)
    n=rs.rand(h//4,w//4)*10-5
    p+=np.array(Image.fromarray((n-n.min()).astype(np.uint8)).resize((w,h),Image.BILINEAR))[...,None]*0.6
    yy,xx=np.mgrid[0:h,0:w]
    p-=np.clip(((xx/w-0.5)**2+(yy/h-0.5)**2)-0.2,0,1)[...,None]*22
    return p

def stamp_img(text,seed):
    f=ImageFont.truetype(FB,64)
    im=Image.new("RGBA",(len(text)*46+60,120),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rectangle([4,4,im.width-4,im.height-4],outline=(178,32,40,235),width=6)
    d.text((30,22),text,font=f,fill=(178,32,40,235))
    rs=np.random.RandomState(seed)
    m=np.array(im)
    mask=(rs.rand(*m.shape[:2])>0.12).astype(np.uint8)*255
    m[...,3]=np.minimum(m[...,3],Image.fromarray(mask).filter(ImageFilter.GaussianBlur(0.6)))
    return Image.fromarray(m)

def page_img(P,seed):
    w,h=1100,1500
    im=Image.fromarray(np.clip(paper_tex(w,h,seed),0,255).astype(np.uint8)).convert("RGBA")
    d=ImageDraw.Draw(im)
    fb=ImageFont.truetype(FB,44); fm=ImageFont.truetype(FM,34); fs=ImageFont.truetype(FM,26)
    d.text((60,50),"ПРОЕКТ «БЕССОННИЦА»",font=fb,fill=(40,40,45))
    d.text((60,110),f"ЛИЧНОЕ ДЕЛО № 0{P['n']}-З / СЕКТОР Б",font=fm,fill=(70,70,75))
    d.line([(60,170),(w-60,170)],fill=(60,60,60),width=3)
    # фото-полароид
    kind="subject" if P["glow"]>0.3 else ("doctor" if P["n"]%2 else "sci")
    cam=anim.Cam(); cam.set((0.15,1.5,-2.4),yaw=0.10,pitch=0.0)
    spr=anim.render(cam,anim.bust(kind,head_yaw=math.pi-0.3,glow=P["glow"]))
    a=np.array(spr); ys,xs=np.where(a[...,3]>10)
    y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    m=int((y1-y0)*0.18); y0=max(0,y0-m); x0=max(0,x0-m); x1=min(1920,x1+m); y1=min(1080,y1+m)
    gg=np.zeros((1080,1920,4),np.uint8); gg[...,3]=255
    col=(90+(np.mgrid[0:1080][:,None]/1080*60)).astype(np.uint8)
    gg[...,:3]=col[:,None,:]
    base=Image.fromarray(gg,"RGBA"); base=Image.alpha_composite(base,spr)
    bust=base.crop((x0,y0,x1,y1)).convert("RGB")
    bust=Image.fromarray((np.array(bust,np.float32)*np.array([0.9,1.0,0.92])).clip(0,255).astype(np.uint8))
    ph=Image.new("RGBA",(420,470),(250,250,248,255)); pd=ImageDraw.Draw(ph)
    ph.paste(bust.resize((380,380)),(20,20))
    pd.text((30,410),f"ОБЪЕКТ 0{P['n']}",font=fs,fill=(50,50,50))
    ph=ph.rotate(-3,expand=True,fillcolor=(0,0,0,0))
    sh=Image.new("RGBA",im.size,(0,0,0,0)); sd=ImageDraw.Draw(sh)
    sd.rectangle([640,210,640+ph.width,210+ph.height],fill=(0,0,0,60)); sh=sh.filter(ImageFilter.GaussianBlur(8))
    im=Image.alpha_composite(im,sh)
    im.alpha_composite(ph,(650,200))
    # машинопись
    y=760
    for lab,val in (("ИМЯ:",P["name"]),("РОЛЬ:",P["role"]),("СТАТУС:",P["status"])):
        d=ImageDraw.Draw(im)
        d.text((70,y),lab,font=fm,fill=(60,60,65)); d.text((260,y),val,font=fm,fill=(25,25,28)); y+=62
    d.text((70,y+10),"ОСОБЫЕ ОТМЕТКИ:",font=fm,fill=(60,60,65)); y+=58
    for ln in P["note"].split("\n"):
        d.text((90,y),ln,font=fm,fill=(25,25,28)); y+=48
    # штамп
    st=stamp_img(P["stamp"],seed+9).rotate(-14,expand=True,fillcolor=(0,0,0,0))
    im.alpha_composite(st,(120,1080))
    # подпись-закорючка
    rs=np.random.RandomState(seed+3)
    d=ImageDraw.Draw(im)
    pts=[(700+i*8,1300+int(14*math.sin(i*0.9)+rs.rand()*8)) for i in range(24)]
    d.line(pts,fill=(30,30,90),width=3)
    d.text((700,1340),"куратор проекта",font=fs,fill=(80,80,85))
    # скрепка
    d.rounded_rectangle([520,40,560,180],radius=20,outline=(120,120,130),width=7)
    d.rounded_rectangle([532,52,548,170],radius=8,outline=(140,140,150),width=5)
    return im

def on_desk(page,seed,ang):
    desk=Image.open(f"{ROOT}/assets/v2/b_desk.jpg").convert("RGB").resize((1920,1080))
    pg=page.rotate(ang,expand=True,fillcolor=(0,0,0,0))
    sh=Image.new("RGBA",(1920,1080),(0,0,0,0)); d=ImageDraw.Draw(sh)
    x,y=(1920-pg.width)//2-20,(1080-pg.height)//2+10
    d.rectangle([x+14,y+18,x+pg.width+14,y+pg.height+18],fill=(0,0,0,90)); sh=sh.filter(ImageFilter.GaussianBlur(14))
    out=Image.alpha_composite(desk.convert("RGBA"),sh)
    out.alpha_composite(pg,(x,y))
    # виньетка
    a=np.array(out.convert("RGB"),np.float32)
    yy,xx=np.mgrid[0:1080,0:1920]; r2=((xx-960)/1180)**2+((yy-540)/660)**2
    a*=np.clip(1-0.35*np.clip((r2-0.5)/0.6,0,1)**2,0.5,1)[...,None]
    return np.clip(a,0,255).astype(np.uint8)

if __name__=="__main__":
    os.makedirs("/home/user/.qc",exist_ok=True)
    for i,P in enumerate(PAGES):
        arr=on_desk(page_img(P,i*7+2),i*7+2,ang=-2.5+i*0.8)
        Image.fromarray(arr).save(f"/home/user/.qc/dossier_{i}.png")
    print("DOSSIER OK")
