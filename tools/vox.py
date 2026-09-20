"""Воксельный 3D-мир в стиле майнкрафт-анимаций: блоки, BFS-свет с тенями,
процедурные «скины» блоков, общее painter-сортирование с персонажами."""
import numpy as np, math
from PIL import Image, ImageDraw

AIR=0
CONC=1; CONCD=2; METAL=3; GLASS=4; LAMP=5; SCREEN=6; WOOD=7; LEAF=8
BRICK=9; OBSID=10; FIRE=11; TABLE=12; REDL=13; PAPER=14; CRATE=15; ASPHALT=16
TRANSP={AIR,GLASS}
EMIS={LAMP:(255,244,214,15),SCREEN:(110,220,150,7),FIRE:(255,150,60,15),REDL:(255,60,50,14)}
BASE={CONC:(205,208,206),CONCD:(120,126,128),METAL:(150,158,165),GLASS:(160,220,220),
WOOD:(146,110,66),LEAF:(58,120,44),BRICK:(128,86,80),OBSID:(30,24,40),TABLE:(170,140,95),
PAPER:(235,232,220),CRATE:(160,125,70),ASPHALT:(70,72,78)}

DIRS=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]

class World:
    def __init__(s,sx,sy,sz):
        s.sx,s.sy,s.sz=sx,sy,sz
        s.g=np.zeros((sx,sy,sz),np.uint8)
        s.light=None
    def set(s,x,y,z,v):
        if 0<=x<s.sx and 0<=y<s.sy and 0<=z<s.sz: s.g[x,y,z]=v
    def fill(s,x0,x1,y0,y1,z0,z1,v):
        x0=max(0,x0);y0=max(0,y0);z0=max(0,z0)
        x1=min(s.sx-1,x1);y1=min(s.sy-1,y1);z1=min(s.sz-1,z1)
        if x0<=x1 and y0<=y1 and z0<=z1: s.g[x0:x1+1,y0:y1+1,z0:z1+1]=v
    def box(s,x0,x1,y0,y1,z0,z1,v): s.fill(s,x0,x1,y0,y1,z0,z1,v)
    def calc_light(s,sky_top=True,sky_level=13):
        L=np.zeros((s.sx,s.sy,s.sz),np.uint8)
        from collections import deque
        q=deque()
        for x in range(s.sx):
            for y in range(s.sy):
                for z in range(s.sz):
                    b=s.g[x,y,z]
                    if b in EMIS:
                        L[x,y,z]=EMIS[b][3]; q.append((x,y,z))
        if sky_top:
            for x in range(s.sx):
                for z in range(s.sz):
                    y=s.sy-1
                    while y>=0 and s.g[x,y,z] in TRANSP:
                        L[x,y,z]=max(L[x,y,z],sky_level); q.append((x,y,z)); y-=1
        while q:
            x,y,z=q.popleft(); l=int(L[x,y,z])
            if l<=1: continue
            for dx,dy,dz in DIRS:
                nx,ny,nz=x+dx,y+dy,z+dz
                if not(0<=nx<s.sx and 0<=ny<s.sy and 0<=nz<s.sz): continue
                b=s.g[nx,ny,nz]
                cost=1 if b in TRANSP else 4
                nl=l-cost
                if nl>L[nx,ny,nz]:
                    L[nx,ny,nz]=nl; q.append((nx,ny,nz))
        s.light=L
        return L

def face_shade(n):
    l=np.array([0.35,0.8,0.35],np.float32); l/=np.linalg.norm(l)
    return 0.55+0.45*max(0.0,float(np.dot(n,l)))

def hashn(x,y,z,f):
    h=(x*73856093)^(y*19349663)^(z*83492791)^(f*2971)
    return ((h&0xffff)/65535.0-0.5)

def world_faces(w,skip_solid_outside=True):
    """Списик статических граней: (center, normal, poly_pts_world, color)."""
    out=[]
    g=w.g; L=w.light
    for x in range(w.sx):
        for y in range(w.sy):
            for z in range(w.sz):
                b=g[x,y,z]
                if b==AIR: continue
                em=EMIS.get(b)
                for f,(dx,dy,dz) in enumerate(DIRS):
                    nx,ny,nz=x+dx,y+dy,z+dz
                    nb=g[nx,ny,nz] if (0<=nx<w.sx and 0<=ny<w.sy and 0<=nz<w.sz) else AIR
                    if nb not in TRANSP and not (b==GLASS and nb!=GLASS): continue
                    if b==GLASS and nb==GLASS: continue
                    # полигон грани
                    pts=[]
                    for cx,cz in ((0,0),(1,0),(1,1),(0,1)):
                        if dy!=0: pts.append((x+cx,y+(1 if dy>0 else 0),z+cz))
                        elif dx!=0: pts.append((x+(1 if dx>0 else 0),y+cz,z+cx))
                        else: pts.append((x+cx,y+cz,z+(1 if dz>0 else 0)))
                    li=int(L[x,y,z])
                    lum=(0.16+0.84*(li/15.0))
                    n=(dx,dy,dz)
                    if em:
                        col=np.array(em[:3],np.float32)
                    else:
                        c=np.array(BASE.get(b,(150,150,150)),np.float32)
                        tex=1.0+0.10*hashn(x,y,z,f)+0.05*hashn(x*3,y*5,z*7,f+11)
                        # кромки блока чуть темнее — читаемость «блоков»
                        col=c*tex*face_shade(np.array(n,np.float32))*lum
                        if b==GLASS: col=c*0.55+np.array([120,180,180])*0.35
                    out.append(dict(pts=np.array(pts,np.float32),n=np.array(n,np.float32),
                                    col=np.clip(col,0,255),e=1.0 if em else 0.0,
                                    alpha=0.35 if b==GLASS else 1.0, d=0.0))
    return out

def render_scene(cam,faces,boxes=None,sky=(10,14,20),fog=(8,12,14),fogd=0.03):
    from PIL import Image, ImageDraw
    W,H=cam.W,cam.H
    M=cam.matrices()
    # небо-градиент
    yy=np.mgrid[0:H][:,None].astype(np.float32)/H
    hor=np.array(sky,np.float32); top=np.array(sky,np.float32)*0.35+np.array([4,8,16])*0.5
    img=(hor[None,None,:]*(yy[...,None]**1.4)+top[None,None,:]*(1-yy[...,None]**1.4))
    img=np.broadcast_to(img,(H,W,3)).copy()
    fl=[]
    for fc in faces:
        cw=(fc["pts"]-cam.pos)@M.T
        if (cw[:,2]<=0.05).all(): continue
        wn=fc["n"]
        cen=fc["pts"].mean(axis=0)
        if wn@(cen-cam.pos)>=0 and fc["e"]==0: continue
        d=cw[:,2].mean()
        poly,_=cam.project(fc["pts"])
        if (poly[:,0]<-50).all() or (poly[:,0]>W+50).all() or (poly[:,1]<-50).all() or (poly[:,1]>H+50).all(): continue
        col=fc["col"]
        fmix=min(0.8,1-math.exp(-fogd*max(0,d-2)))
        col=col*(1-fmix)+np.array(fog,np.float32)*fmix
        fl.append((d,[tuple(p) for p in poly],tuple(int(c) for c in np.clip(col,0,255)),fc["alpha"],fc["e"]))
    if boxes:
        import anim
        for b in boxes:
            wq=anim.CORN*b["s"]@b["R"].T+b["c"]
            cwc=(wq-cam.pos)@M.T
            for n,idx in anim.FACES:
                wn=n@b["R"].T
                fcen=wq[idx].mean(axis=0)
                if wn@(fcen-cam.pos)>=0: continue
                if (cwc[:,2]<=0.05).all(): continue
                d=cwc[idx][:,2].mean()
                poly,_=cam.project(wq[idx])
                shade=0.42+0.58*max(0.0,float(wn@np.array([0.35,0.8,0.35])/1.0))
                col=b["col"]*shade if b["e"]==0 else b["col"]*0.7+np.array([120,200,150])*b["e"]
                # свет мира на персонажей: берём из сетки, если есть
                if getattr(b,"_lum",None): col=col*(0.3+0.7*b["_lum"])
                fmix=min(0.8,1-math.exp(-fogd*max(0,d-2)))
                col=col*(1-fmix)+np.array(fog,np.float32)*fmix
                fl.append((d,[tuple(p) for p in poly],tuple(int(c) for c in np.clip(col,0,255)),1.0,b["e"]))
    fl.sort(key=lambda t:-t[0])
    im=Image.fromarray(np.clip(img,0,255).astype(np.uint8)).convert("RGBA")
    dr=ImageDraw.Draw(im,"RGBA")
    for d,poly,col,al,e in fl:
        if al<1: dr.polygon(poly,fill=col+(int(90*al),))
        else: dr.polygon(poly,fill=col+(255,))
    return im
