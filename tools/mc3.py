"""Minecraft-стиль: настоящий 3D из текстурированных блоков, z-buffer, пиксель-текстуры 16x16.
Сцена — набор боксов с тайлингом текстур; персонажи — риг с UV-текстурами частей тела."""
import numpy as np, math

def _rotY(a):
    c,s=math.cos(a),math.sin(a); return np.array([[c,0,s],[0,1,0],[-s,0,c]],np.float32)
def _rotX(a):
    c,s=math.cos(a),math.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]],np.float32)
def _rotZ(a):
    c,s=math.cos(a),math.sin(a); return np.array([[c,-s,0],[s,c,0],[0,0,1]],np.float32)

CORN=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],np.float32)/2
# грани: нормаль, индексы углов, uv-углы (в порядке обхода)
FACES=[(np.array([0,0,-1],np.float32),[0,1,2,3]),(np.array([0,0,1],np.float32),[4,5,6,7]),
       (np.array([-1,0,0],np.float32),[0,4,7,3]),(np.array([1,0,0],np.float32),[1,5,6,2]),
       (np.array([0,1,0],np.float32),[3,2,6,7]),(np.array([0,-1,0],np.float32),[0,1,5,4])]
UVQ=np.array([[0,0],[1,0],[1,1],[0,1]],np.float32)

# ---------------- текстуры ----------------
TEX={}
def _t(name,fn):
    a=np.zeros((16,16,3),np.uint8); fn(a); TEX[name]=a; return name
def _noise(a,base,var,seed=1,chan=None):
    rs=np.random.RandomState(seed)
    n=(rs.rand(16,16)-0.5)*2*var
    for i in range(3):
        a[...,i]=np.clip(base[i]+(n if chan is None else n*(0.4 if i in chan else 0)),0,255)
def mk_textures():
    if TEX: return
    def nz(a,base,var,seed,chan=None):
        rs=np.random.RandomState(seed)
        n=(rs.rand(16,16)-0.5)*2*var
        for c in range(3):
            a[...,c]=np.clip(base[c]+(n if chan is None else n*(0.5 if c in chan else 0)),0,255)
    def T(name,fn):
        a=np.zeros((16,16,3),np.uint8); fn(a); TEX[name]=a
    R8=np.arange(16)[:,None]; C8=np.arange(16)[None,:]
    RB=np.broadcast_to((np.arange(16)%8==7)[:,None],(16,16)); CB=np.broadcast_to((np.arange(16)%8==7)[None,:],(16,16))
    R0=np.broadcast_to((np.arange(16)==0)[:,None],(16,16)); C8L=np.broadcast_to((np.arange(16)==8)[None,:],(16,16))
    R4=np.broadcast_to((np.arange(16)%4==0)[:,None],(16,16)); R43=np.broadcast_to((np.arange(16)%4==3)[:,None],(16,16))
    R3=np.broadcast_to((np.arange(16)%3==0)[:,None],(16,16)); C5=np.broadcast_to((np.arange(16)%5==0)[None,:],(16,16))
    R42=np.broadcast_to((np.arange(16)%4<2)[:,None],(16,16)); C87=np.broadcast_to((np.arange(16)%8==7)[None,:],(16,16))
    DIAG=((np.arange(16)[:,None]+np.arange(16)[None,:])%16)<2
    def tile(a): nz(a,(225,228,226),7,3); a[RB|CB]=(170,175,172)
    T("tile",tile)
    def panel(a): nz(a,(205,212,210),6,5); a[RB]=(160,168,166); a[R0]=(230,236,234)
    T("panel",panel)
    def metal(a): nz(a,(120,128,132),10,7); a[R4]=(95,102,108)
    T("metal",metal)
    def concrete(a): nz(a,(150,150,148),12,9)
    T("concrete",concrete)
    def asphalt(a): nz(a,(58,60,64),9,11)
    T("asphalt",asphalt)
    def grass(a): nz(a,(106,160,70),16,13,chan=(1,))
    T("grass",grass)
    def leaf(a): nz(a,(52,120,44),20,15,chan=(1,))
    T("leaf",leaf)
    def plank(a): nz(a,(162,130,78),10,17); a[R43]=(120,94,55)
    T("plank",plank)
    def brick(a): nz(a,(140,80,66),10,19); a[R43]=(200,196,190)
    T("brick",brick)
    def glass(a): a[...,:]=(168,205,205); a[DIAG]=(220,240,240)
    T("glass",glass)
    def lamp(a): a[...,:]=(235,255,244)
    T("lamp",lamp)
    def screen(a): nz(a,(24,60,44),8,21); a[R3]=(60,190,120); a[C5]=(30,90,60)
    T("screen",screen)
    def screen_red(a): nz(a,(70,16,16),8,22); a[R42]=(200,50,40)
    T("screen_red",screen_red)
    def door(a): nz(a,(110,116,122),6,23); a[C87]=(80,86,92); a[8:10,12:14]=(220,200,80)
    T("door",door)
    def paper(a): nz(a,(238,234,220),5,25)
    T("paper",paper)
    def obsidian(a): nz(a,(26,18,38),8,27)
    T("obsidian",obsidian)
    def fire(a): nz(a,(250,150,40),40,29,chan=(0,1))
    T("fire",fire)
    def bed(a): nz(a,(170,60,60),8,31)
    T("bed",bed)
    def pillow(a): nz(a,(235,235,230),5,33)
    T("pillow",pillow)
    def coat(a): nz(a,(238,240,238),4,35); a[C8L]=(200,205,205)
    T("coat",coat)
    def shirt_t(a): nz(a,(64,150,160),6,37)
    T("shirt_t",shirt_t)
    def shirt_g(a): nz(a,(88,110,80),6,39)
    T("shirt_g",shirt_g)
    def shirt_s(a): nz(a,(190,205,215),5,41)
    T("shirt_s",shirt_s)
    def shirt_c(a): nz(a,(120,108,96),6,43)
    T("shirt_c",shirt_c)
    def pants_d(a): nz(a,(66,74,92),5,45)
    T("pants_d",pants_d)
    def pants_g(a): nz(a,(52,60,50),5,47)
    T("pants_g",pants_g)
    def pants_c(a): nz(a,(58,58,66),5,49)
    T("pants_c",pants_c)
    def skin(a): nz(a,(214,178,140),6,51)
    T("skin",skin)
    def skin_g(a): nz(a,(150,190,140),6,53)
    T("skin_g",skin_g)
    def hair_br(a): nz(a,(70,48,30),8,55)
    T("hair_br",hair_br)
    def hair_blk(a): nz(a,(28,26,24),6,57)
    T("hair_blk",hair_blk)
    def hair_gr(a): nz(a,(120,120,118),6,59)
    T("hair_gr",hair_gr)
    def gloweye(a): a[...,:]=(210,255,200)
    T("gloweye",gloweye)
    def face(a,skn,hair,eye,pupil,mouth,seed):
        nz(a,skn,5,seed)
        a[:4,:]=hair; a[4:6,:]=np.array(hair)*0.85
        a[8:10,3:6]=eye; a[8:10,4:5]=pupil
        a[8:10,10:13]=eye; a[8:10,11:12]=pupil
        a[12:13,6:10]=mouth
    T("face_doc",lambda a:face(a,(214,178,140),(90,70,50),(235,235,235),(60,90,140),(150,110,90),61))
    T("face_sub",lambda a:face(a,(150,190,140),(60,90,60),(210,255,200),(30,80,30),(90,120,80),63))
    T("face_sci",lambda a:face(a,(210,175,145),(30,30,30),(235,235,235),(70,60,50),(150,110,90),65))
    T("face_grd",lambda a:face(a,(200,160,130),(40,40,40),(230,230,230),(50,50,55),(130,95,80),67))
    T("face_civ",lambda a:face(a,(205,170,140),(50,40,30),(230,230,230),(90,70,50),(140,100,85),69))
    def fside(a): nz(a,(214,178,140),5,71); a[:5,:]=(70,48,30); a[8:10,2:5]=(235,235,235); a[8:10,3:4]=(60,90,140)
    T("face_side",fside)
    def shadowt(a): a[...,:]=(10,12,11)
    T("shadow",shadowt)


def box(c,size,R,texs,emis=0.0,alpha=1.0,tscale=1.0):
    if isinstance(texs,str): texs=[texs]*6
    return dict(c=np.array(c,np.float32),s=np.array(size,np.float32),R=R if R is not None else np.eye(3,dtype=np.float32),
                tex=texs,e=emis,a=alpha,ts=tscale)

class Cam:
    def __init__(s,W=960,H=540,f=1.5):
        s.W,s.H,s.f=W,H,f; s.pos=np.zeros(3,np.float32); s.yaw=s.pitch=s.roll=0.0
    def set(s,pos,yaw=0.0,pitch=0.0,roll=0.0):
        s.pos=np.array(pos,np.float32); s.yaw,s.pitch,s.roll=yaw,pitch,roll
    def matrices(s):
        return _rotX(-s.pitch)@_rotY(-s.yaw)

def render(cam,boxes,light=(0.4,0.85,0.5),fogc=(14,20,19),fogd=0.03,amb=0.45,sky=(16,24,23)):
    mk_textures()
    boxes=sorted(boxes,key=lambda b:0 if b["a"]>=1 else 1)
    H,W=cam.H,cam.W
    fb=np.tile(np.array(sky,np.float32),(H,W,1))
    zb=np.zeros((H,W),np.float32)
    L=np.array(light,np.float32); L/=np.linalg.norm(L)
    M=cam.matrices(); k=cam.f*H/2
    xs_g=np.arange(W,dtype=np.float32)+0.5; ys_g=np.arange(H,dtype=np.float32)+0.5
    for b in boxes:
        w=CORN*b["s"]@b["R"].T+b["c"]
        cw=(w-cam.pos)@M.T
        if (cw[:,2]<=0.06).all(): continue
        for fi,(n,idx) in enumerate(FACES):
            wn=n@b["R"].T
            fc=w[idx].mean(axis=0)
            if wn@(fc-cam.pos)>=0: continue
            p=cw[idx]
            # near-clip в камерном пространстве
            DIM=[(0,1),(0,1),(2,1),(2,1),(0,2),(0,2)]
            da,db=DIM[fi]
            UVF=UVQ*np.array([b["s"][da],b["s"][db]],np.float64)*2*b["ts"]
            pts=p; uvs=UVF.copy()
            if (pts[:,2]<0.1).any():
                if (pts[:,2]<0.1).all(): continue
                np_=len(pts); outp=[]; outu=[]
                for i in range(np_):
                    j=(i+1)%np_
                    Pi,Pj=pts[i],pts[j]; ui,uj=uvs[i],uvs[j]
                    ini=Pi[2]>=0.1; inj=Pj[2]>=0.1
                    if ini: outp.append(Pi); outu.append(ui)
                    if ini!=inj:
                        t=(0.1-Pi[2])/(Pj[2]-Pi[2])
                        outp.append(Pi+t*(Pj-Pi)); outu.append(ui+t*(uj-ui))
                pts=np.array(outp,np.float64); uvs=np.array(outu,np.float64)
                if len(pts)<3: continue
            zc=pts[:,2]
            sx=pts[:,0]*k/zc+W/2; sy=-pts[:,1]*k/zc+H/2
            x0=int(max(0,np.floor(sx.min()))); x1=int(min(W-1,np.ceil(sx.max())))
            y0=int(max(0,np.floor(sy.min()))); y1=int(min(H-1,np.ceil(sy.max())))
            if x1<=x0 or y1<=y0: continue
            shade=amb+(1-amb)*max(0.0,float(wn@L))
            tex=TEX[b["tex"][fi]]
            for t_i in range(1,len(pts)-1):
                i0,i1,i2=0,t_i,t_i+1
                X=np.array([sx[i0],sx[i1],sx[i2]],np.float64); Y=np.array([sy[i0],sy[i1],sy[i2]],np.float64)
                Z=1.0/np.array([zc[i0],zc[i1],zc[i2]],np.float64)
                us=np.array([uvs[i0][0],uvs[i1][0],uvs[i2][0]],np.float64); vs=np.array([uvs[i0][1],uvs[i1][1],uvs[i2][1]],np.float64)
                denom=(X[0]-X[2])*(Y[1]-Y[2])-(X[1]-X[2])*(Y[0]-Y[2])
                if abs(denom)<1e-6: continue
                gx=xs_g[None,x0:x1+1].repeat(y1-y0+1,0)
                gy=ys_g[y0:y1+1,None].repeat(x1-x0+1,1)
                w0=((X[1]-gx)*(Y[2]-gy)-(X[2]-gx)*(Y[1]-gy))/denom
                w1=((X[2]-gx)*(Y[0]-gy)-(X[0]-gx)*(Y[2]-gy))/denom
                w2=1-w0-w1
                mask=(w0>=-0.02)&(w1>=-0.02)&(w2>=-0.02)
                if not mask.any(): continue
                iw=w0*Z[0]+w1*Z[1]+w2*Z[2]
                u=(w0*Z[0]*us[0]+w1*Z[1]*us[1]+w2*Z[2]*us[2])/iw
                v=(w0*Z[0]*vs[0]+w1*Z[1]*vs[1]+w2*Z[2]*vs[2])/iw
                depth=1.0/iw
                tu=np.floor(u*16).astype(int)%16; tv=(15-np.floor(v*16).astype(int))%16
                col=tex[np.clip(tv,0,15),np.clip(tu,0,15)].astype(np.float32)
                if b["e"]>0:
                    col=col*(0.6+0.4*shade)+np.array([60,90,70],np.float32)*b["e"]
                else:
                    col=col*shade
                dmean=float(depth.mean())
                fmix=min(0.9,1-math.exp(-fogd*max(0,dmean-1.5)))
                col=col*(1-fmix)+np.array(fogc,np.float32)*fmix
                sub=zb[y0:y1+1,x0:x1+1]
                m2=mask&((sub==0)|(depth<sub))
                if not m2.any(): continue
                if b["a"]<1.0:
                    reg=fb[y0:y1+1,x0:x1+1]
                    reg[m2]=reg[m2]*(1-b["a"])+col[m2]*b["a"]
                    sub[m2]=np.minimum(np.where(sub[m2]==0,9e9,sub[m2]),depth[m2])
                else:
                    fb[y0:y1+1,x0:x1+1][m2]=col[m2]
                    sub[m2]=depth[m2]
    return np.clip(fb,0,255).astype(np.uint8)

def shadow(x,z,sx=0.55,sz=0.35):
    return box([x,0.012,z],[sx,0.024,sz],None,"shadow",0.0,alpha=0.38)

# ---------------- риг персонажа ----------------
PAL={
 "doctor": dict(face="face_doc",side="face_side",hair="hair_br",top="coat",shirt="coat",pants="pants_d",skin="skin"),
 "subject":dict(face="face_sub",side="face_sub",hair="hair_gr",top="shirt_g",shirt="shirt_g",pants="pants_g",skin="skin_g"),
 "sci":    dict(face="face_sci",side="face_side",hair="hair_blk",top="shirt_s",shirt="shirt_s",pants="pants_c",skin="skin"),
 "guard":  dict(face="face_grd",side="face_side",hair="hair_blk",top="shirt_g",shirt="shirt_g",pants="pants_g",skin="skin"),
 "civil":  dict(face="face_civ",side="face_side",hair="hair_br",top="shirt_c",shirt="shirt_c",pants="pants_c",skin="skin"),
}
def puppet(kind,x,z,yaw=0.0,phase=0.0,speed=0.0,head_yaw=0.0,head_pitch=0.0,
           arm_l=None,arm_r=None,bob_extra=0.0,glow=0.0,lean=0.0):
    P=PAL[kind]; B=[]
    R=_rotY(yaw)
    sw=math.sin(phase)*min(1,abs(speed))*0.55
    bob=abs(math.cos(phase))*min(1,abs(speed))*0.05+bob_extra
    hip=0.72+bob
    def add(c,s,rot,texs,e=0.0):
        w=np.array(c,np.float32)@R.T+np.array([x,0,z],np.float32)
        B.append(box(w,s,R@rot,texs,e))
    al=arm_l if arm_l is not None else sw*0.9
    ar=arm_r if arm_r is not None else -sw*0.9
    leanR=_rotZ(lean)
    # ноги
    add([-0.13,hip-0.36,0],(0.22,0.72,0.24),_rotX(-sw*0.9),[P["pants"]]*6)
    add([ 0.13,hip-0.36,0],(0.22,0.72,0.24),_rotX( sw*0.9),[P["pants"]]*6)
    # торс
    add([0,hip+0.36,0],(0.5,0.72,0.26),leanR,[P["shirt"],P["shirt"],P["shirt"],P["shirt"],P["shirt"],P["shirt"]])
    # руки
    sh=hip+0.66
    add([-0.36,sh-0.33,0],(0.16,0.70,0.16),leanR@_rotX(al),[P["shirt"],P["shirt"],P["skin"],P["skin"],P["skin"],P["skin"]])
    add([ 0.36,sh-0.33,0],(0.16,0.70,0.16),leanR@_rotX(ar),[P["shirt"],P["shirt"],P["skin"],P["skin"],P["skin"],P["skin"]])
    # голова
    hr=_rotY(head_yaw)@_rotX(head_pitch)
    hc=np.array([0,hip+1.02,0.02],np.float32)
    B.append(box(hc@R.T+np.array([x,0,z],np.float32),(0.5,0.5,0.5),R@hr,
                 [P["side"],P["face"],P["side"],P["side"],P["hair"],P["skin"]],glow*0.0))
    # волосы-кепка
    B.append(box((hc+hr@np.array([0,0.24,-0.01],np.float32))@R.T+np.array([x,0,z],np.float32),(0.52,0.14,0.52),R@hr,[P["hair"]]*6))
    if glow>0:
        for ex in (-0.12,0.12):
            B.append(box((hc+hr@np.array([ex,0.02,0.26],np.float32))@R.T+np.array([x,0,z],np.float32),
                         (0.09,0.07,0.03),R@hr,"gloweye",glow))
    return B
