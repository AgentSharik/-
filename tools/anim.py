"""Мини-3D движок воксельных персонажей: боксы, скелет-риг, цикл ходьбы.
Персонажи честно двигаются в 3D и проецируются камерой — никаких слайдов."""
import numpy as np, math
from PIL import Image, ImageDraw

def _rotY(a):
    c,s=math.cos(a),math.sin(a); return np.array([[c,0,s],[0,1,0],[-s,0,c]],np.float32)
def _rotX(a):
    c,s=math.cos(a),math.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]],np.float32)
def _rotZ(a):
    c,s=math.cos(a),math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]],np.float32)

FACES=[(np.array([0,0,1],np.float32),[4,5,6,7]),(np.array([0,0,-1],np.float32),[0,1,2,3]),
       (np.array([1,0,0],np.float32),[1,5,6,2]),(np.array([-1,0,0],np.float32),[0,4,7,3]),
       (np.array([0,1,0],np.float32),[3,2,6,7]),(np.array([0,-1,0],np.float32),[0,1,5,4])]
CORN=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],np.float32)/2

class Cam:
    def __init__(s,W=1920,H=1080,f=1.5):
        s.W,s.H,s.f=W,H,f; s.pos=np.zeros(3,np.float32); s.yaw=s.pitch=s.roll=0.0
    def set(s,pos,yaw=0.0,pitch=0.0,roll=0.0):
        s.pos=np.array(pos,np.float32); s.yaw,s.pitch,s.roll=yaw,pitch,roll
    def matrices(s):
        return _rotX(-s.pitch)@_rotY(-s.yaw)
    def project(s,pts):
        M=s.matrices(); p=(pts-s.pos)@M.T
        z=np.clip(p[...,2],0.05,None); k=s.f*s.H/2
        x=p[...,0]*k/z+s.W/2; y=-p[...,1]*k/z+s.H/2
        return np.stack([x,y],-1), p[...,2]

def box(c,size,R=None,color=(200,200,200),emis=0.0):
    return dict(c=np.array(c,np.float32),s=np.array(size,np.float32),
                R=(R if R is not None else np.eye(3,dtype=np.float32)),col=np.array(color,np.float32),e=emis)

def _swing(bx,pivot,ang,axis):
    R=_rotX(ang) if axis=="x" else _rotZ(ang)
    c=CORN*bx["s"]; w=c@bx["R"].T+bx["c"]
    w=(w-pivot)@R.T+pivot
    return w

def render(cam,boxes,light=(0.35,0.8,0.35),fogc=(8,14,13),fogd=0.045,amb=0.42):
    L=np.array(light,np.float32); L/=np.linalg.norm(L)
    M=cam.matrices(); faces=[]
    for b in boxes:
        w=CORN*b["s"]@b["R"].T+b["c"]
        cw=(w-cam.pos)@M.T
        for n,idx in FACES:
            wn=n@b["R"].T
            fc=w[idx].mean(axis=0)
            if wn@(fc-cam.pos)>=0: continue
            d=cw[idx,::2][:,0].mean() if False else cw[idx][:,2].mean()
            poly,_=cam.project(w[idx])
            shade=amb+(1-amb)*max(0.0,float(wn@L))
            col=b["col"]*shade if b["e"]==0 else b["col"]*(0.55+0.45*shade)+np.array([140,180,150],np.float32)*b["e"]
            fmix=min(0.85,1-math.exp(-fogd*max(0,d-1)))
            col=col*(1-fmix)+np.array(fogc,np.float32)*fmix
            faces.append((d,[tuple(p) for p in poly],tuple(int(min(255,c)) for c in col)))
    faces.sort(key=lambda t:-t[0])
    im=Image.new("RGBA",(cam.W,cam.H),(0,0,0,0)); d=ImageDraw.Draw(im)
    for _,poly,col in faces:
        d.polygon(poly,fill=col+(255,))
    return im

PAL={
 "doctor": dict(head=(214,178,140),torso=(235,235,230),legs=(70,80,95),arms=(235,235,230),hair=(90,70,50)),
 "guard":  dict(head=(200,160,130),torso=(70,95,70),legs=(50,60,50),arms=(70,95,70),hair=(40,40,40)),
 "subject":dict(head=(120,170,110),torso=(95,140,95),legs=(60,75,60),arms=(110,160,100),hair=(60,90,60)),
 "sci":    dict(head=(210,175,145),torso=(190,210,220),legs=(60,70,85),arms=(190,210,220),hair=(30,30,30)),
 "civil":  dict(head=(205,170,140),torso=(120,110,100),legs=(55,55,65),arms=(120,110,100),hair=(50,40,30)),
}

def puppet(kind,x,z,yaw=0.0,phase=0.0,speed=0.0,head_yaw=0.0,head_pitch=0.0,
           arm_l=None,arm_r=None,bob_extra=0.0,glow=0.0,lean=0.0):
    P=PAL[kind]; B=[]; t=phase
    amp=min(abs(speed)/1.3,1.0)*0.55
    sw=math.sin(t)*amp; sw2=math.sin(t+math.pi)*amp
    bob=abs(math.cos(t))*0.045*min(abs(speed)/1.3+0.2,1)+bob_extra
    R=_rotY(yaw)
    def add(c0,size,O,color,e=0.0):
        B.append(box(c0,size,O,color,e))
    def part(c0,size,pivot,ang,color,e=0.0,extra=None):
        RR=_rotX(ang)
        cc=np.array(c0,np.float32)
        if ang!=0.0: cc=(cc-np.array(pivot,np.float32))@RR.T+np.array(pivot,np.float32)
        cc=cc@R.T
        O=R@(RR if extra is None else RR@extra) if extra is not None else R@RR
        add(cc,size,O,color,e)
    hip=0.80+bob
    part([-0.13,hip-0.40,0],(0.22,0.80,0.22),(-0.13,hip,0),sw,P["legs"])
    part([ 0.13,hip-0.40,0],(0.22,0.80,0.22),( 0.13,hip,0),sw2,P["legs"])
    torsoE=_rotX(lean+0.03*math.sin(t*0.5)*amp)
    cc=np.array([0,hip+0.36,0],np.float32)@R.T
    add(cc,(0.50,0.72,0.28),R@torsoE,P["torso"])
    sh=hip+0.68
    al=sw2*0.8 if arm_l is None else arm_l; ar=sw*0.8 if arm_r is None else arm_r
    part([-0.36,sh-0.33,0],(0.16,0.70,0.16),(-0.36,sh,0),al,P["arms"])
    part([ 0.36,sh-0.33,0],(0.16,0.70,0.16),( 0.36,sh,0),ar,P["arms"])
    hr=_rotY(head_yaw)@_rotX(head_pitch)
    add(np.array([0,hip+0.96,0],np.float32)@R.T,(0.44,0.44,0.44),R@hr,P["head"])
    add(np.array([0,hip+1.18,-0.01],np.float32)@R.T,(0.47,0.14,0.47),R@hr,P["hair"])
    if glow>0:
        add(np.array([-0.11,hip+1.00,0.235],np.float32)@R.T,(0.08,0.06,0.05),R@hr,(230,255,225),glow)
        add(np.array([ 0.11,hip+1.00,0.235],np.float32)@R.T,(0.08,0.06,0.05),R@hr,(230,255,225),glow)
    root=np.array([x,0,z],np.float32)
    for b in B: b["c"]=b["c"]+root
    return B

def bust(kind,head_yaw=0.0,glow=0.0):
    P=PAL[kind]; B=[]
    hr=_rotY(head_yaw); hc=np.array([0,1.62,0],np.float32)
    B.append(box(hc,(0.44,0.44,0.44),hr,P["head"]))
    B.append(box(hc+hr@np.array([0,0.20,-0.01],np.float32),(0.47,0.14,0.47),hr,P["hair"]))
    ec=(230,255,225) if glow else (50,50,55)
    B.append(box(hc+hr@np.array([-0.11,0.04,0.235],np.float32),(0.08,0.06,0.05),hr,ec,glow))
    B.append(box(hc+hr@np.array([ 0.11,0.04,0.235],np.float32),(0.08,0.06,0.05),hr,ec,glow))
    B.append(box([0,1.28,0],(0.62,0.36,0.34),np.eye(3,dtype=np.float32),P["torso"]))
    return B
