"""ТРЕТЬ ЖИЗНИ — полный фильм v3 (~7.5 мин): воксельный 3D, синхрон диктор↔кадр.
S0 вступление | S1 зал P1 | S2 камера P2 | S3 регенерация P3a | S4 деградация P3b |
S5 прорыв P4 | S6 записка | S7 первые дни | S8 досье | S9 финал.
ENV: T0,T1,OUT,NOMIX,ROOT."""
import os, sys, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import anim, vox, scenes3, render_v3 as R3
from vox import render_scene
ROOT=os.environ.get("ROOT","/home/user/repo")
FF=R3.FF
W,H,FPS,BAR=R3.W,R3.H,R3.FPS,R3.BAR
FONT_B="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float64)/32768.
def mp3wav(name):
    src=f"{ROOT}/audio/{name}.mp3"; dst=f"{ROOT}/audio/_vf_{name}.wav"
    if not os.path.exists(dst):
        subprocess.run([FF,"-y","-i",src,"-ar","44100","-ac","1",dst],check=True,capture_output=True)
    return rd(dst)
def fracs(sents):
    tot=sum(len(s) for s in sents); out=[]; c=0
    for s in sents: out.append((c/tot,(c+len(s))/tot,s)); c+=len(s)
    return out

P3A=["Запись сорок седьмая.","Волков попросил скальпель и сделал надрез на собственном предплечье.","Мы смотрели, как края сходятся.","Сорок секунд — и даже шрама нет.","Хан замерила активность клеток и сказала: они не заживают, они готовятся к войне.","Сон не исчез, он ушёл внутрь: тело чинит себя, пока человек бодрствует."]
P3B=["Запись сорок девятая.","Формула вышла за пределы сектора Б.","Первый заражённый — оператор ночной смены.","Он не спит и начинает забывать: сначала имя жены, потом своё.","Речь, имя, память — тело отключает их, как лишние процессы.","Снаружи лаборатория кашляет городом.","Заражённые ходят чуть зеленее, чуть меньше человека.","Оно ждёт, когда мы устанем."]
P4=["Ночь прорыва.","Волков попросил выпустить его размяться. Я отказал.","Стена камеры продержалась одиннадцать секунд.","Сирена завыла, когда он уже шёл по коридору.","Смирина подожгла лабораторию. Кравцов остался внутри.","Я записываю это, чтобы тот, кто найдёт журнал, знал: мы создали его сами."]
NOTE=["Сон — это ремонт тела.","Мы отдали ремонт самим клеткам,","а через укус формула передаётся дальше,","как инструкция продолжать.","Я приняла половину дозы три дня назад.","Я больше не хочу спать.","Простите меня."]
DAYS=["Первые дни.","Кашель в колонне эвакуации.","Пост на выезде держался четыре дня.","Город опустел за неделю.","Ночами жгли костры — не для тепла, для света: заражённые избегают огня.","Карантин сняли на четырнадцатый день.","Экономика не может спать дольше человека."]
DOSS=["Судьбы участников.","Воронин: заражён, ушёл в сектор Б и не вернулся.","Волков: на свободе.","Кравцов: съеден, судя по следам, своими же.","Смирина: ликвидирована собственным огнём.","Хан: эвакуирована, оставила слово «прощайте».","Руиз: судьба неизвестна.","Папка лежит на столе. Подписать её некому."]
FIN=["Статус на сегодня. Протокол девять.","Заражено четыре тысячи двести семнадцать.","Инкубация до семидесяти двух часов.","Сон не исчез, он ждёт.","Объект не сдержан.","Проект продолжается. Без нас."]
SUB3=fracs(P3A); SUB4=fracs(P3B); SUB5=fracs(P4); SUB6=fracs(NOTE); SUB7=fracs(DAYS); SUB8=fracs(DOSS); SUB9=fracs(FIN)

G={}
def setup():
    R3.setup(); G.update(R3.G)
    for k,n in (("p3a","v2_p3a"),("p3b","v2_p3b"),("p4","v2_p4"),("note","v2_note"),
                ("days","v2_days"),("doss","v2_dossier"),("fin","v2_final")):
        G[k]=mp3wav(n); G["d_"+k]=len(G[k])/44100
    for k in ("_w_system","_w_radio","_w_epilog"):
        G[k]=rd(f"{ROOT}/audio/{k}.wav")
    for k,n in (("pre","v2_pre"),("eth","v2_ethics")):
        G[k]=mp3wav(n); G["d_"+k]=len(G[k])/44100
    G["year"]=mp3wav("v2_year"); G["d_year"]=len(G["year"])/44100
    G["year2"]=mp3wav("v2_last"); G["d_year2"]=len(G["year2"])/44100
    G["LEAD"]=5.0; L=G["LEAD"]
    t=R3.G["TE"]+2
    G["SPRE"]=t; t+=L+G["d_pre"]+2
    G["S3"]=t; t+=L+G["d_p3a"]+2
    G["S4"]=t; t+=L+G["d_p3b"]+2
    G["SETH"]=t; t+=L+G["d_eth"]+2
    G["S5"]=t; t+=L+G["d_p4"]+2
    G["S6"]=t; t+=L+G["d_note"]+2
    G["S7"]=t; t+=L+G["d_days"]+3
    G["S8"]=t; t+=L+G["d_doss"]+2
    G["S9"]=t; t+=L+G["d_fin"]+3
    G["S10"]=t; t+=L+G["d_year"]+1+G["d_year2"]+14
    G["TEF"]=t
    G["corr"]=scenes3.corridor(); G["corr_f"]=vox.world_faces(G["corr"])
    G["street"]=scenes3.street(); G["street_f"]=vox.world_faces(G["street"])
    G["sq"]=scenes3.square_fire(); G["sq_f"]=vox.world_faces(G["sq"])
    G["desk"]=scenes3.desk_room(); G["desk_f"]=vox.world_faces(G["desk"])
    G["anim_"]=scenes3.animal_room(); G["anim_f"]=vox.world_faces(G["anim_"])
    G["meet"]=scenes3.meeting_room(); G["meet_f"]=vox.world_faces(G["meet"])
    import dossier
    G["pages"]=[dossier.page_img(P,i*7+2) for i,P in enumerate(dossier.PAGES)]

def lit(w,boxes): return R3.lit(w,boxes)

def draw_full(t):
    if t<R3.G["TE"]: return R3.draw(t)
    # ---------- вставка: 49 записей, клетки ----------
    if t<G["S3"]:
        u=(t-G["SPRE"]-G["LEAD"])/G["d_pre"]; w=G["anim_"]; faces=G["anim_f"]; cam=anim.Cam()
        v=u
        cam.set((8+0.2*math.sin(t*0.4),2.0,0.4+6*v),yaw=0.04*math.sin(t*0.3),pitch=-0.08)
        boxes=lit(w,anim.puppet("doctor",8.0,3.5+6*v,y=1.0,yaw=0.1,phase=t*7,speed=1.1,head_yaw=0.5*math.sin(t*0.7)))
        im=render_scene(cam,faces,boxes,sky=(8,12,16),fog=(7,10,13),fogd=0.03)
        return np.array(im.convert("RGB"),np.float32)
    # ---------- вставка: комитет ----------
    if t>=G["SETH"] and t<G["S5"]:
        u=(t-G["SETH"]-G["LEAD"])/G["d_eth"]; w=G["meet"]; faces=G["meet_f"]; cam=anim.Cam()
        cam.set((1.4+0.9*u,2.35,5.0),yaw=math.pi/2,pitch=-0.13)
        boxes=[]
        for i,px in enumerate((4.0,6.0,8.0)):
            boxes.append(dict(c=np.array([px,0.8,2.6],np.float32),s=np.array([0.7,0.6,0.7],np.float32),R=np.eye(3,dtype=np.float32),col=np.array([90,70,45],np.float32),e=0.0))
            boxes.append(dict(c=np.array([px,0.8,7.4],np.float32),s=np.array([0.7,0.6,0.7],np.float32),R=np.eye(3,dtype=np.float32),col=np.array([90,70,45],np.float32),e=0.0))
            boxes+=lit(w,anim.puppet("sci" if i%2 else "civil",px,3.1,y=0.85,yaw=0.0,lean=0.15,head_pitch=0.15+0.05*math.sin(t+i)))
            boxes+=lit(w,anim.puppet("civil",px,6.9,y=0.85,yaw=math.pi,lean=0.15,head_pitch=0.12+0.05*math.sin(t*0.8+i*2)))
        boxes+=lit(w,anim.puppet("doctor",11.5,5.0,y=1.0,yaw=-math.pi*0.5,arm_r=-0.7+0.2*math.sin(t*1.5)))
        im=render_scene(cam,faces,boxes,sky=(8,10,14),fog=(6,8,11),fogd=0.03)
        return np.array(im.convert("RGB"),np.float32)
    # ---------- S3 регенерация ----------
    if t<G["S4"]:
        u=(t-G["S3"]-G["LEAD"])/G["d_p3a"]; w=G["hall"]; faces=G["hall_f"]; cam=anim.Cam(); boxes=[]
        if u<0.35:   # надрез: крупно рука/предплечье
            v=u/0.35
            cam.set((13.9,1.5,8.2),yaw=-0.5,pitch=0.05)
            boxes+=lit(w,anim.puppet("subject",13.6,9.6,y=1.0,yaw=math.pi*0.6,arm_r=-1.1,glow=0.2))
            cut=max(0.0,1-max(0.0,v-0.55)/0.4)   # рана затягивается
            if cut>0:
                boxes.append(dict(c=np.array([13.35,1.45,9.1],np.float32),s=np.array([0.05,0.03,0.3*cut],np.float32),
                                  R=np.eye(3,dtype=np.float32),col=np.array([150,30,30],np.float32),e=0.3))
            boxes+=lit(w,anim.puppet("doctor",12.6,9.2,y=1.0,yaw=1.2,head_pitch=0.25,lean=0.1))
        elif u<0.7:  # у экранов: Хан и доктор, субъект в центре
            v=(u-0.35)/0.35
            cam.set((16.5,1.7,7.0),yaw=1.2,pitch=-0.03)
            boxes+=lit(w,anim.puppet("subject",14.5,9.5,y=1.0,yaw=math.pi*0.75,glow=0.3+0.25*math.sin(t*2.5)))
            boxes+=lit(w,anim.puppet("sci",21.0,9.0,y=1.0,yaw=-1.4,head_yaw=-0.4,arm_r=-0.9))
            boxes+=lit(w,anim.puppet("doctor",21.5,10.5,y=1.0,yaw=-1.3,head_yaw=-0.5))
        else:        # кулак: субъект сжимает руку
            v=(u-0.7)/0.3
            cam.set((13.2,1.55,8.0),yaw=-0.15,pitch=0.0)
            boxes+=lit(w,anim.puppet("subject",13.6,9.6,y=1.0,yaw=math.pi-0.3,arm_r=-1.4+0.9*min(v*2,1),glow=0.4,head_yaw=-0.2))
        im=render_scene(cam,faces,boxes,sky=(10,16,22),fog=(10,14,16),fogd=0.02)
        return np.array(im.convert("RGB"),np.float32)
    # ---------- S4 деградация ----------
    if t<G["S5"]:
        u=(t-G["S4"]-G["LEAD"])/G["d_p3b"]; cam=anim.Cam(); boxes=[]
        if u<0.4:    # коридор: заражённый идёт навстречу, шатаясь
            v=u/0.4
            w=G["corr"]; faces=G["corr_f"]
            zz=18-13*v
            cam.set((2.8+0.1*math.sin(t*0.7),1.6,zz-4.5),yaw=0.0,pitch=-0.02)
            boxes+=lit(w,anim.puppet("civil",3.0,zz,y=1.0,yaw=math.pi+0.15*math.sin(t*1.3),phase=t*6,speed=0.9,
                                     lean=0.12*math.sin(t*2.2),head_yaw=0.4*math.sin(t*0.9),glow=0.5))
            flick=1.0 if int(t*4)%3 else 0.55
        elif u<0.75: # улица: колонна эвакуации, один кашляет
            v=(u-0.4)/0.35
            w=G["street"]; faces=G["street_f"]
            cam.set((15.5,1.9,21-2*v),yaw=math.pi,pitch=-0.03)
            zs=14-3*v
            boxes+=lit(w,anim.puppet("civil",14.5,zs,y=1.0,yaw=math.pi,phase=t*5.5,speed=0.8))
            boxes+=lit(w,anim.puppet("civil",16.0,zs+1.2,y=1.0,yaw=math.pi,phase=t*5.5+1,speed=0.8,
                                     lean=0.35*max(0,math.sin(t*2.6))**3,head_pitch=0.3*max(0,math.sin(t*2.6))**3))
            boxes+=lit(w,anim.puppet("civil",15.2,zs+2.6,y=1.0,yaw=math.pi+0.5,phase=t*5.5+2,speed=0.8))
            boxes+=lit(w,anim.puppet("guard",15.5,6.0,y=1.0,yaw=0.0,arm_r=-1.3))
            flick=1.0
        else:        # крупно лицо заражённого
            v=(u-0.75)/0.25
            w=G["street"]; faces=G["street_f"]
            cam.set((15.0,1.62,12.5-0.5*v),yaw=0.1,pitch=0.0)
            boxes+=lit(w,anim.puppet("civil",15.3,14.0,y=1.0,yaw=math.pi-0.1,head_yaw=0.2*math.sin(t*0.8),glow=0.7,
                                     lean=0.06*math.sin(t*1.7)))
            flick=1.0
        im=render_scene(cam,faces,boxes,sky=(38,44,64),fog=(18,20,30),fogd=0.02)
        a=np.array(im.convert("RGB"),np.float32)*flick
        return a
    # ---------- S5 прорыв ----------
    if t<G["S6"]:
        u=(t-G["S5"]-G["LEAD"])/G["d_p4"]; cam=anim.Cam(); boxes=[]
        if u<0.35:   # камера: субъект дрожит, глаза пульсируют
            v=u/0.35
            w=G["cell"]; faces=G["cell_f"]
            cam.set((4+0.05*math.sin(t*30),1.6,-2.6),yaw=0,pitch=-0.03)
            jx=0.03*math.sin(t*27); jy=0.02*math.sin(t*31)
            boxes+=lit(w,anim.puppet("subject",4+jx,4.0,y=1.0+jy,yaw=math.pi,phase=0,glow=0.4+0.4*math.sin(t*6),
                                     head_yaw=0.3*math.sin(t*3)))
            im=render_scene(cam,faces,boxes,sky=(5,7,10),fog=(5,7,10),fogd=0.03)
            return np.array(im.convert("RGB"),np.float32)
        if u<0.55:   # стена рушится: обломки
            v=(u-0.35)/0.2
            w=G["cell"]; faces=G["cell_f"]
            sh=0.12*math.sin(t*40)*(1-v)
            cam.set((4+sh,1.5,-2.4),yaw=0,pitch=-0.02)
            boxes+=lit(w,anim.puppet("subject",4.5,4.5,y=1.0,yaw=math.pi*0.8,phase=t*9,speed=1.6,glow=0.8))
            rs=np.random.RandomState(11)
            for i in range(10):
                tt=v*2.2
                px=7.2+tt*(1.5+rs.rand()); py=2.5+rs.rand()*1.5-2.0*tt*tt; pz=2+rs.rand()*4
                boxes.append(dict(c=np.array([px,max(0.3,py),pz],np.float32),s=np.array([0.25,0.25,0.25],np.float32),
                                  R=np.eye(3,dtype=np.float32),col=np.array([128,86,80],np.float32),e=0.0))
            im=render_scene(cam,faces,boxes,sky=(5,7,10),fog=(5,7,10),fogd=0.03)
            return np.array(im.convert("RGB"),np.float32)
        # коридор: побег, сирена
        v=(u-0.55)/0.45
        w=G["corr"]; faces=G["corr_f"]
        zz=19-15*v
        cam.set((3+0.08*math.sin(t*3),1.6,zz-3.5),yaw=0,pitch=-0.02)
        boxes+=lit(w,anim.puppet("subject",3.0,zz,y=1.0,yaw=math.pi,phase=t*11,speed=2.2,glow=0.8,lean=0.1))
        boxes+=lit(w,anim.puppet("sci",3.2,zz+5,y=1.0,yaw=0.2,phase=t*10,speed=2.0,head_yaw=2.5))
        red=0.5+0.5*math.sin(t*8)
        im=render_scene(cam,faces,boxes,sky=(5,7,10),fog=(5,7,10),fogd=0.03)
        a=np.array(im.convert("RGB"),np.float32)
        a+= np.array([red*26,red*4,red*6],np.float32)
        return a
    # ---------- S6 записка (вставка-документ) ----------
    if t<G["S7"]:
        u=(t-G["S6"]-G["LEAD"])/G["d_note"]
        base=np.full((H,W,3),24,np.float32)
        im=Image.fromarray(base.astype(np.uint8)).convert("RGBA")
        pg=Image.new("RGBA",(1200,1600),(232,228,214,255))
        d=ImageDraw.Draw(pg)
        f=ImageFont.truetype(FONT_M,44)
        d.text((90,90),"Л. СМИРИНА — ВНУТРЕННЯЯ ЗАПИСКА",font=ImageFont.truetype(FONT_B,40),fill=(60,55,50))
        y=260
        nlines=int(u*len(NOTE)*1.15)
        for i,ln in enumerate(NOTE):
            if i<nlines: d.text((90,y),ln,font=f,fill=(35,32,30))
            y+=78
        d.text((620,1380),"Л. С.",font=ImageFont.truetype(FONT_B,60),fill=(120,40,40))
        pg=pg.rotate(-2,expand=True,fillcolor=(0,0,0,0))
        im.alpha_composite(pg,(330,-80))
        a=np.array(im.convert("RGB"),np.float32)
        return a*np.clip(1-0.45*np.abs(np.mgrid[0:H][:,None]/H-0.5)*1.6,0.55,1)[...,None]
    # ---------- S7 первые дни ----------
    if t<G["S8"]:
        u=(t-G["S7"]-G["LEAD"])/G["d_days"]; cam=anim.Cam(); boxes=[]
        if u<0.5:
            v=u/0.5
            w=G["street"]; faces=G["street_f"]
            cam.set((15.5,1.8,21-2*v),yaw=0,pitch=-0.03)
            zs=15-2.5*v
            for i,(px,off) in enumerate(((14.2,0),(15.4,0.8),(16.4,1.7),(15.0,2.6))):
                cough = i==1
                boxes+=lit(w,anim.puppet("civil",px,zs+off,y=1.0,yaw=math.pi,phase=t*5+i,speed=0.7,
                        lean=(0.4*max(0,math.sin(t*2.4))**3) if cough else 0,
                        head_pitch=(0.35*max(0,math.sin(t*2.4))**3) if cough else 0))
            boxes+=lit(w,anim.puppet("guard",13.0,7.0,y=1.0,yaw=0.3,arm_r=-1.35))
            boxes+=lit(w,anim.puppet("guard",18.0,7.0,y=1.0,yaw=-0.3,arm_l=-1.35))
            im=render_scene(cam,faces,boxes,sky=(20,24,38),fog=(12,14,22),fogd=0.025)
            return np.array(im.convert("RGB"),np.float32)
        v=(u-0.5)/0.5
        w=G["sq"]; faces=G["sq_f"]
        cam.set((12+1.5*math.sin(v*1.2),2.3,2.2),yaw=0.1*math.sin(v*1.2),pitch=-0.12)
        boxes+=lit(w,anim.puppet("civil",9.5,6.5,y=1.0,yaw=1.2,lean=0.25,head_pitch=0.15))
        boxes+=lit(w,anim.puppet("civil",14.5,6.5,y=1.0,yaw=-1.2,lean=0.25))
        boxes+=lit(w,anim.puppet("civil",12.0,5.0,y=1.0,yaw=math.pi,lean=0.3,head_pitch=0.2+0.1*max(0,math.sin(t*2.2))**3))
        rs=np.random.RandomState(5)
        for i in range(6):   # искры костра
            ph=(t*0.9+i*0.37)%1
            boxes.append(dict(c=np.array([11.5+rs.rand(),2.5+ph*2.2,9+rs.rand()],np.float32),
                              s=np.array([0.08,0.08,0.08],np.float32),R=np.eye(3,dtype=np.float32),
                              col=np.array([255,150,60],np.float32),e=1.0))
        im=render_scene(cam,faces,boxes,sky=(4,6,10),fog=(4,6,9),fogd=0.03)
        return np.array(im.convert("RGB"),np.float32)
    # ---------- S8 досье ----------
    if t<G["S9"]:
        u=(t-G["S8"]-G["LEAD"])/G["d_doss"]
        w=G["desk"]; faces=G["desk_f"]; cam=anim.Cam()
        cam.set((5+0.3*math.sin(t*0.1),1.9,1.6),yaw=0.15*math.sin(t*0.07),pitch=-0.5)
        im=render_scene(cam,faces,[],sky=(8,10,14),fog=(6,8,10),fogd=0.03)
        a=np.array(im.convert("RGB"),np.float32)
        idx=min(int(u*6.999),5)
        pg=G["pages"][idx].convert("RGBA")
        pw=int(W*0.55); pg=pg.resize((pw,int(pg.height*pw/pg.width)))
        pg=pg.rotate(-2+idx*0.7,expand=True,fillcolor=(0,0,0,0))
        canv=Image.new("RGBA",(W,H),(0,0,0,0))
        sh=Image.new("RGBA",(W,H),(0,0,0,0)); sd=ImageDraw.Draw(sh)
        x,y=(W-pg.width)//2,(H-pg.height)//2-20
        sd.rectangle([x+12,y+16,x+pg.width+12,y+pg.height+16],fill=(0,0,0,110))
        sh=sh.filter(ImageFilter.GaussianBlur(12))
        canv=Image.alpha_composite(canv,sh)
        canv.alpha_composite(pg,(x,y))
        a=Image.alpha_composite(Image.fromarray(a.astype(np.uint8)).convert("RGBA"),canv)
        return np.array(a.convert("RGB"),np.float32)
    # ---------- S10 год спустя ----------
    if t>=G["S10"]:
        u=(t-G["S10"]-G["LEAD"])/max(0.1,(G["d_year"]+G["d_year2"]+15))
        w=G["street"]; faces=G["street_f"]; cam=anim.Cam()
        v=min(max(u,0),1)
        cam.set((15.5,1.7,2.5+7*v),yaw=0.02*math.sin(t*0.15),pitch=-0.02)
        boxes=[]
        nb=int(6*min(max(u,0),1))
        for i in range(nb):
            boxes.append(dict(c=np.array([13.0+(i%2)*1.0,1.5+(i//2)*1.0,16.0],np.float32),
                              s=np.array([0.95,0.95,0.95],np.float32),R=np.eye(3,dtype=np.float32),
                              col=np.array([190,195,200],np.float32),e=0.0))
        boxes+=lit(w,anim.puppet("subject",14.6,16.0,y=1.0,yaw=math.pi*0.5,arm_r=-1.2+0.5*math.sin(t*2.0),glow=0.6))
        im=render_scene(cam,faces,boxes,sky=(90,70,55),fog=(50,42,38),fogd=0.02)
        a=np.array(im.convert("RGB"),np.float32)
        if u>1.0: a*=max(0.0,1-(u-1.0)/0.35)
        return a
    # ---------- S9 финал ----------
    u=(t-G["S9"]-G["LEAD"])/max(0.1,(G["S10"]-G["S9"]-G["LEAD"]))
    if u<0.55:
        v=u/0.55
        w=G["street"]; faces=G["street_f"]; cam=anim.Cam()
        cam.set((15.5,1.7,3+6*v),yaw=0.03*math.sin(t*0.2),pitch=-0.02)
        boxes=[]
        pz=8+9*v
        boxes.append(dict(c=np.array([14+0.5*math.sin(t*1.3),0.15+0.1*abs(math.sin(t*3)),pz],np.float32),
                          s=np.array([0.4,0.02,0.55],np.float32),R=anim._rotY(0.4*math.sin(t*0.9)),
                          col=np.array([230,228,215],np.float32),e=0.0))
        im=render_scene(cam,faces,boxes,sky=(70,60,52),fog=(40,36,34),fogd=0.02)
        return np.array(im.convert("RGB"),np.float32)
    base=np.zeros((H,W,3),np.float32)
    im=Image.fromarray(base.astype(np.uint8)); d=ImageDraw.Draw(im)
    f=ImageFont.truetype(FONT_B,54)
    lines=["ОБЪЕКТ НЕ СДЕРЖАН.","ПРОЕКТ ПРОДОЛЖАЕТСЯ.","БЕЗ НАС."]
    k=min(int((u-0.55)/0.12)+1,3)
    for i in range(k):
        d.text((W//2-330,340+i*110),lines[i],font=f,fill=(200,60,50) if i<2 else (230,230,225))
    if u>0.9:
        d.text((W//2-260,820),"ТРЕТЬ ЖИЗНИ",font=ImageFont.truetype(FONT_B,72),fill=(230,230,225))
        d.text((W//2-330,930),"дневник наблюдений // сектор Б",font=ImageFont.truetype(FONT_M,34),fill=(140,140,135))
    return np.array(im,np.float32)*min((u-0.5)*8,1)

def overlay_full(t,arr):
    im=Image.fromarray(np.clip(arr,0,255).astype(np.uint8)).convert("RGBA")
    ov=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
    sub=None; win=None
    for (t0,t1,S) in ((G["S10"],G["TEF"],fracs(["Год спустя город молчит.","Разведывательный дрон зафиксировал движение в секторе Б: кто-то аккуратно складывает блоки.","Структуры точные, как чертёж.","Город перестраивает тот, кому больше не нужен сон.","Я остаюсь в наблюдательной последней.","Мои часы говорят, что я не сплю двенадцать дней.","Но мне не страшно.","Мне просто интересно досмотреть, что он построит."])),
                      (G["SPRE"],G["S3"],fracs(["До формулы было сорок девять записей.","Мыши не спали месяц и строили гнёзда, как инженеры.","Обезьяна трое суток смотрела в зеркало, а потом улыбнулась.","Нам следовало остановиться тогда."])),
                      (G["SETH"],G["S5"],fracs(["Комитет по этике одобрил формулу закрытым голосованием.","В комитете было семеро.","К четырнадцатому дню пятеро из них не спали.","Протокол подписывали те, кто больше не мог уснуть."])),
                      (G["S3"],G["S4"],SUB3),(G["S4"],G["S5"],SUB4),(G["S5"],G["S6"],SUB5),
                      (G["S6"],G["S7"],SUB6),(G["S7"],G["S8"],SUB7),(G["S8"],G["S9"],SUB8),(G["S9"],G["TEF"],SUB9)):
        if t0<=t<t1:
            u=(t-t0-G["LEAD"])/(t1-t0)
            for a0,b0,s in S:
                if a0<=u<b0: sub=s; break
            break
    if sub:
        f=ImageFont.truetype(FONT_B,40)
        d.text((152,H-BAR-90),sub,font=f,fill=(0,0,0,200))
        d.text((150,H-BAR-92),sub,font=f,fill=(235,242,238,250))
    out=Image.alpha_composite(im,ov)
    a=np.array(out.convert("RGB"),np.float32)
    a[:BAR]=0; a[H-BAR:]=0
    a*=G["VIG"]; a+=G["grain"][int(t*8)%4]
    return np.clip(a,0,255).astype(np.uint8)

def main():
    setup()
    T0c=float(os.environ.get("T0",0)); T1c=float(os.environ.get("T1",G["TEF"]))
    out=os.environ.get("OUT",f"{ROOT}/video/TRET_JIZNI_v3.mp4")
    enc=subprocess.Popen([FF,"-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
                          "-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","22","-preset","medium",out],
                         stdin=subprocess.PIPE)
    fr=int(T0c*FPS)
    while fr<T1c*FPS:
        t=fr/FPS
        enc.stdin.write(overlay_full(t,draw_full(t)).tobytes())
        if fr%480==0: print(f"full frame {fr}",flush=True)
        fr+=1
    enc.stdin.close(); enc.wait()
    if os.environ.get("NOMIX"): print("CHUNK DONE",flush=True); return
    TE=G["TEF"]
    mix=np.zeros(int(TE*44100))
    def add(sig,t0,g=1.0):
        s=int(t0*44100); e=min(len(mix),s+len(sig)); mix[s:e]+=sig[:e-s]*g
    add(R3.sfx(),0); add(G["p1"],G["T0"]); add(G["p2"],G["T1"])
    Ld=G["LEAD"]
    add(G["pre"],G["SPRE"]+Ld); add(G["p3a"],G["S3"]+Ld); add(G["p3b"],G["S4"]+Ld); add(G["eth"],G["SETH"]+Ld); add(G["p4"],G["S5"]+Ld); add(G["note"],G["S6"]+Ld)
    add(G["days"],G["S7"]+Ld); add(G["doss"],G["S8"]+Ld); add(G["fin"],G["S9"]+Ld); add(G["year"],G["S10"]+Ld); add(G["year2"],G["S10"]+Ld+G["d_year"]+1)
    add(G["_w_system"],G["S5"],0.7); add(G["_w_radio"],G["S7"],0.5); add(G["_w_epilog"],G["S10"]+2,0.8)
    mix=np.tanh(mix*1.3)/np.tanh(1.3)*0.9
    with wave.open(f"{ROOT}/audio/_v3full_mix.wav","wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((mix*32767).astype(np.int16).tobytes())
    print("FULL DONE",flush=True)

if __name__=="__main__":
    main()
