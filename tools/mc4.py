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
    def face2(a,skn,hair,iris,seed,beard=None,lips=(190,90,90)):
        rs=np.random.RandomState(seed)
        base=np.array(skn,np.float32)
        for y in range(16):
            for x in range(16):
                v=base*(0.92+0.16*rs.rand())
                v*=1.0-0.10*min(1,(abs(x-7.5)/8)**2+(abs(y-9)/8)**2)
                a[y,x]=np.clip(v,0,255)
        for y in range(6):
            for x in range(16):
                v=np.array(hair,np.float32)*(0.75+0.5*rs.rand())
                a[y,x]=np.clip(v,0,255)
        a[6,:]=np.clip(np.array(hair,np.float32)*0.6,0,255)
        a[7,2:5]=(np.array(hair)*0.5); a[7,10:13]=(np.array(hair)*0.5)      # брови
        for ex in (2,9):
            a[8:11,ex+1:ex+3]=(240,240,240)                                   # белок 2x3
            a[9:11,ex+1:ex+2]=iris                                            # радужка
            a[9:11,ex+2:ex+3]=(25,25,30)                                      # зрачок
            a[8,ex+1]=(255,255,255)                                           # блик
        a[12,6:10]=lips; a[13,7:9]=np.array(lips)*0.7
        a[10:12,1]=(np.array(skn)*0.8); a[10:12,14]=(np.array(skn)*0.8)
        if beard: a[11:16,4:12]=np.clip((np.array(beard,np.float32)[None,None,:]*(0.8+0.3*rs.rand(5,8))[...,None]),0,255).astype(np.uint8)
    T("face_doc",lambda a:face2(a,(222,180,146),(88,64,40),(70,110,170),61))
    T("face_sub",lambda a:face2(a,(168,205,150),(70,100,66),(120,230,120),63))
    T("face_sci",lambda a:face2(a,(216,178,148),(30,28,26),(90,70,50),65))
    T("face_grd",lambda a:face2(a,(205,165,132),(40,40,42),(60,60,70),67))
    T("face_civ",lambda a:face2(a,(212,175,142),(60,44,30),(110,80,50),69))
    T("face_old",lambda a:face2(a,(225,195,170),(200,200,198),(120,90,60),70,beard=(205,205,200)))
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

def _boxblur(a,r):
    k=2*r+1
    padw=((0,0),(r,r))+((0,0),)*(a.ndim-2)
    ap=np.pad(a,padw)
    c=np.concatenate([np.zeros((ap.shape[0],1)+ap.shape[2:],np.float32),np.cumsum(ap,axis=1)],axis=1)
    x=(c[:,k:]-c[:,:-k])/k
    ap=np.pad(x,((r,r),)+((0,0),)*(x.ndim-1))
    c=np.concatenate([np.zeros((1,)+ap.shape[1:],np.float32),np.cumsum(ap,axis=0)],axis=0)
    return (c[k:]-c[:-k])/k

def render(cam,boxes,light=(0.4,0.85,0.5),fogc=(14,20,19),fogd=0.03,amb=0.38,sky=(16,24,23),
           shadows=False,focus=None,dof=0.0,bloom=0.0,particles=None,rim_dir=(-0.6,0.25,-0.75),rim_col=(70,120,170),grade=True):
    mk_textures()
    H,W=cam.H,cam.W
    L=np.array(light,np.float32); L/=np.linalg.norm(L)
    Rr=np.array(rim_dir,np.float32); Rr/=np.linalg.norm(Rr)
    # shadow map
    shmap=None; camL=None; ML=None
    if shadows:
        camL=Cam(256,256,f=1.2)
        yaw=math.atan2(-L[0],-L[2]); pitch=math.asin(max(-1,min(1,-L[1])))
        camL.set(np.array([0,1.2,4],np.float32)-L*22,yaw=yaw,pitch=pitch)
        ML=camL.matrices(); kL=camL.f*128
        shmap=np.zeros((256,256),np.float32)
        for b in boxes:
            if b["a"]<1: continue
            w=CORN*b["s"]@b["R"].T+b["c"]
            cw=(w-camL.pos)@ML.T
            if (cw[:,2]<=0.1).all(): continue
            for n,idx in FACES:
                wn=n@b["R"].T
                if wn@L>=-0.2: continue
                p=cw[idx]; zc=np.clip(p[:,2],0.1,None)
                sx=(p[:,0]*kL/zc+128).astype(int); sy=(-p[:,1]*kL/zc+128).astype(int)
                x0=max(0,sx.min()); x1=min(255,sx.max()); y0=max(0,sy.min()); y1=min(255,sy.max())
                if x1<=x0 or y1<=y0: continue
                d=zc.mean()
                reg=shmap[y0:y1+1,x0:x1+1]
                reg[:]=np.where(reg==0,d,np.minimum(reg,d))
    fb=np.tile(np.array(sky,np.float32),(H,W,1))
    zb=np.zeros((H,W),np.float32)
    M=cam.matrices(); k=cam.f*H/2
    Minv=M.T
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
            DIM=[(0,1),(0,1),(2,1),(2,1),(0,2),(0,2)]
            da,db=DIM[fi]
            UVF=UVQ*np.array([b["s"][da],b["s"][db]],np.float64)*2*b["ts"]
            pts=p; uvs=UVF.copy()
            if (pts[:,2]<0.1).any():
                if (pts[:,2]<0.1).all(): continue
                outp=[]; outu=[]
                for i in range(len(pts)):
                    j2=(i+1)%len(pts)
                    Pi,Pj=pts[i],pts[j2]; ui,uj=uvs[i],uvs[j2]
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
            dirl=max(0.0,float(wn@L)); riml=max(0.0,float(wn@Rr))
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
                sh=1.0
                if shmap is not None and b["e"]==0:
                    pc=np.stack([(gx-W/2)*depth/k,(H/2-gy)*depth/k,depth],axis=-1)
                    pw=pc@Minv+cam.pos
                    pl=(pw-camL.pos)@ML.T
                    lz=np.clip(pl[:, :,2],0.1,None)
                    lx=(pl[:,:,0]*256*1.2/lz+128).astype(int); ly=(-pl[:,:,1]*256*1.2/lz+128).astype(int)
                    lx=np.clip(lx,0,255); ly=np.clip(ly,0,255)
                    sd=shmap[ly,lx]
                    sh=np.where((sd>0)&(sd<pl[:,:,2]-0.08),0.42,1.0)
                shade=amb+(1-amb)*dirl*sh
                if np.ndim(shade): shade=shade[...,None]
                if b["e"]>0:
                    col=col*(0.6+0.4*shade)+np.array([60,90,70],np.float32)*b["e"]
                else:
                    col=col*shade+np.array(rim_col,np.float32)*(riml*0.30)
                dmean=float(depth.mean())
                fmix=min(0.9,1-math.exp(-fogd*max(0,dmean-1.5)))
                col=col*(1-fmix)+np.array(fogc,np.float32)*fmix
                sub=zb[y0:y1+1,x0:x1+1]
                m2=mask&((sub==0)|(depth<sub))
                if not m2.any(): continue
                if b["a"]<1.0:
                    reg=fb[y0:y1+1,x0:x1+1]
                    reg[m2]=reg[m2]*(1-b["a"])+col[m2]*b["a"]
                else:
                    fb[y0:y1+1,x0:x1+1][m2]=col[m2]
                    sub[m2]=depth[m2]
    if particles:
        for (pp,sz,br) in particles:
            pc=(np.array(pp,np.float32)-cam.pos)@M.T
            if pc[2]<=0.1: continue
            qx=int(pc[0]*k/pc[2]+W/2); qy=int(-pc[1]*k/pc[2]+H/2)
            if 0<=qx<W and 0<=qy<H and zb[qy,qx]>pc[2]-0.3:
                r=max(1,int(sz*k/pc[2]))
                yy,xx=np.ogrid[max(0,qy-r):min(H,qy+r+1),max(0,qx-r):min(W,qx+r+1)]
                d2=(yy-qy)**2+(xx-qx)**2
                m=d2<=r*r
                add=np.array([br,br,br*0.9],np.float32)*np.clip(1-d2[m]/(r*r+1e-3),0,1)[:,None]
                fb[max(0,qy-r):min(H,qy+r+1),max(0,qx-r):min(W,qx+r+1)][m]+=add
    # пост: DOF + bloom + grade
    if focus is not None and dof>0:
        b1=_boxblur(fb,1); b2=_boxblur(fb,3)
        coc=np.clip(np.abs(zb-focus)*dof,0,1)
        fb=fb*(1-coc[...,None]*0.85)+ (b1*0.6+b2*0.4)*coc[...,None]*0.85
    if bloom>0:
        brt=np.clip(fb-170,0,85)
        fb+= (_boxblur(brt,2)+_boxblur(brt,5))*bloom
    if grade:
        c=fb/255
        luma=c.mean(axis=2,keepdims=True)
        c=np.clip((c-0.5)*1.16+0.5,0,1)
        c=luma+(c-luma)*1.33
        c+= np.clip(0.35-luma,0,0.35)*np.array([0.0,0.05,0.09])
        c+= np.clip(luma-0.6,0,0.4)*np.array([0.06,0.03,0.0])
        yy,xx=np.mgrid[0:H,0:W]
        vig=1-0.35*np.clip((((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.62))**2)-0.45,0,1)
        c*=vig[...,None]
        fb=c*255
    return np.clip(fb,0,255).astype(np.uint8), zb

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
    B.append(box((hc+hr@np.array([0,0.26,-0.01],np.float32))@R.T+np.array([x,0,z],np.float32),(0.52,0.12,0.52),R@hr,[P["hair"]]*6))
    if glow>0:
        for ex in (-0.12,0.12):
            B.append(box((hc+hr@np.array([ex,0.02,0.26],np.float32))@R.T+np.array([x,0,z],np.float32),
                         (0.09,0.07,0.03),R@hr,"gloweye",glow))
    return B
