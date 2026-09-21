# -*- coding: utf-8 -*-
"""v6 renderer: 1920x1080@30. PNG-плиты + ВОКСЕЛЬНЫЕ персонажи с суставами
(покадровая анимация из ключей: ходьба, руки, моргание), текст в книге,
частицы/строб/дым, кроссфейды, субтитры. Без музыки."""
import numpy as np, os, math, sys, json, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ART = os.path.join(ROOT, "art", "v5")
W, H, FPS = 1920, 1080, 30
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FF = imageio_ffmpeg.get_ffmpeg_exe()
rng = np.random.default_rng(7)

def ease(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)

# ---------------- фон (плиты) ----------------
class Plate:
    def __init__(self, fn):
        im = Image.open(os.path.join(ART, fn)).convert("RGB")
        S = 1.45 * W / im.width
        self.img = im.resize((int(im.width * S), int(im.height * S)), Image.LANCZOS)
        self.SW, self.SH = self.img.size
    def crop(self, z, cx, cy):
        k = (self.SW / W) / z
        vw, vh = W * k, H * k
        c = cx * self.SW - vw / 2; f = cy * self.SH - vh / 2
        return np.asarray(self.img.transform((W, H), Image.AFFINE, (k, 0, c, 0, k, f), Image.BICUBIC), np.float32)

# ---------------- воксельный персонаж ----------------
def rotm(ax, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    if ax == 'x': return np.array([[1,0,0],[0,c,-s],[0,s,c]])
    if ax == 'y': return np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])

class Box:
    def __init__(self, name, parent, pivot, dims, color, off=(0,0,0), emis=0.0):
        self.name, self.parent, self.pivot = name, parent, np.array(pivot, float)
        self.dims = np.array(dims, float); self.color = np.array(color, float)
        self.off = np.array(off, float); self.emis = emis

def build_rig(kind):
    B = []
    if kind == 'sci':
        skin=(0.78,0.56,0.40); coat=(0.90,0.91,0.93); pant=(0.25,0.27,0.32); hair=(0.35,0.30,0.26); shoe=(0.12,0.12,0.13)
        B += [Box('legL','root',(0.11,0.80,0),(0.20,0.80,0.22),pant,(0,-0.40,0)),
              Box('legR','root',(-0.11,0.80,0),(0.20,0.80,0.22),pant,(0,-0.40,0)),
              Box('shoeL','legL',(0,-0.75,0),(0.21,0.12,0.34),shoe,(0,-0.02,0.05)),
              Box('shoeR','legR',(0,-0.75,0),(0.21,0.12,0.34),shoe,(0,-0.02,0.05)),
              Box('torso','root',(0,0.80,0),(0.52,0.72,0.28),coat,(0,0.36,0)),
              Box('head','torso',(0,0.72,0),(0.42,0.44,0.42),skin,(0,0.24,0)),
              Box('hair','head',(0,0.44,0),(0.44,0.16,0.44),hair,(0,0.06,0)),
              Box('armL','torso',(0.33,0.66,0),(0.16,0.50,0.18),coat,(0,-0.25,0)),
              Box('foreL','armL',(0,-0.50,0),(0.14,0.46,0.16),skin,(0,-0.23,0)),
              Box('armR','torso',(-0.33,0.66,0),(0.16,0.50,0.18),coat,(0,-0.25,0)),
              Box('foreR','armR',(0,-0.50,0),(0.14,0.46,0.16),skin,(0,-0.23,0)),
              Box('syr','foreR',(0,-0.46,0),(0.035,0.20,0.035),(0.75,0.85,0.90),(0,-0.06,0.06)),
              Box('syrglow','syr',(0,0.10,0.06),(0.05,0.06,0.05),(0.45,1.0,0.95),(0,0.02,0),1.0)]
    else:  # guard
        uni=(0.16,0.18,0.22); blk=(0.10,0.11,0.13); skin=(0.72,0.52,0.38); helm=(0.13,0.15,0.18)
        B += [Box('legL','root',(0.11,0.80,0),(0.21,0.80,0.23),uni,(0,-0.40,0)),
              Box('legR','root',(-0.11,0.80,0),(0.21,0.80,0.23),uni,(0,-0.40,0)),
              Box('shoeL','legL',(0,-0.75,0),(0.22,0.12,0.35),blk,(0,-0.02,0.05)),
              Box('shoeR','legR',(0,-0.75,0),(0.22,0.12,0.35),blk,(0,-0.02,0.05)),
              Box('torso','root',(0,0.80,0),(0.56,0.74,0.30),uni,(0,0.37,0)),
              Box('vest','torso',(0,0.38,0),(0.58,0.36,0.34),blk,(0,0.0,0)),
              Box('head','torso',(0,0.74,0),(0.42,0.44,0.42),skin,(0,0.24,0)),
              Box('helm','head',(0,0.22,0),(0.46,0.18,0.46),helm,(0,0.05,0)),
              Box('armL','torso',(0.35,0.68,0),(0.17,0.52,0.19),uni,(0,-0.26,0)),
              Box('foreL','armL',(0,-0.52,0),(0.15,0.46,0.17),uni,(0,-0.23,0)),
              Box('armR','torso',(-0.35,0.68,0),(0.17,0.52,0.19),uni,(0,-0.26,0)),
              Box('foreR','armR',(0,-0.52,0),(0.15,0.46,0.17),uni,(0,-0.23,0)),
              Box('torch','foreR',(0,-0.46,0),(0.07,0.22,0.07),blk,(0,-0.04,0.10)),
              Box('torchl','torch',(0,0.12,0.06),(0.08,0.08,0.05),(1.0,0.95,0.75),(0,0,0),1.0)]
    return B

def eval_tracks(tracks, t):
    pose = {}
    for j, keys in tracks.items():
        if t <= keys[0][0]: v0 = v1 = keys[0][1]
        elif t >= keys[-1][0]: v0 = v1 = keys[-1][1]
        else:
            for i in range(len(keys) - 1):
                if keys[i][0] <= t <= keys[i+1][0]:
                    u = ease((t - keys[i][0]) / max(1e-6, keys[i+1][0] - keys[i][0]))
                    a, b = keys[i][1], keys[i+1][1]
                    v0 = v1 = tuple(a[k] + (b[k]-a[k]) * u for k in range(len(a)))
                    break
        pose[j] = v0
    return pose

def rig_world(boxes, pose, root):
    T = {'root': None}
    M = {}
    R0 = rotm('y', root.get('yaw', 0))
    M['root'] = R0; T['root'] = np.array([root.get('x',0), root.get('y',0), root.get('z',0)])
    out = []
    for b in boxes:
        pm = M.get(b.parent, np.eye(3)); pt = T.get(b.parent, np.zeros(3))
        j = {'legL':'hipL','legR':'hipR','armL':'shL','armR':'shR','foreL':'elL','foreR':'elR',
             'head':'neck','torso':'spine'}.get(b.name)
        Rj = np.eye(3)
        if j and j in pose:
            p = pose[j]
            Rj = rotm('x', p[0]) @ rotm('z', p[1] if len(p) > 1 else 0) @ rotm('y', p[2] if len(p) > 2 else 0)
        M[b.name] = pm @ Rj; T[b.name] = pt + pm @ b.pivot
        m, tr = M[b.name], T[b.name]
        dx, dy, dz = b.dims/2
        loc = [np.array(v) for v in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),
                                     (-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]]
        cs = [m @ (b.off + v) + tr for v in loc]
        out.append((b, cs))
    return out

FACES = [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
FNORM = [(0,-1,0),(0,1,0),(0,0,-1),(1,0,0),(0,0,1),(-1,0,0)]

def draw_char(frame, emis, boxes_pose, shot, root):
    cam_h, cam_d, f = shot['cam_h'], shot['cam_d'], shot['f']
    L = shot
    kd = np.array(L['key'], float); kd /= np.linalg.norm(kd)
    fd = np.array(L['fill'], float); fd /= np.linalg.norm(fd)
    rd = np.array([0,0.35,-1.0]); rd /= np.linalg.norm(rd)
    faces = []
    for b, cs in boxes_pose:
        for fi, fc in enumerate(FACES):
            pts = [cs[i] for i in fc]
            n0 = np.array(FNORM[fi], float)
            # normal in world
            m = None
            n = pts[1] - pts[0]; n2 = pts[3] - pts[0]
            nw = np.cross(n, n2); ln = np.linalg.norm(nw)
            if ln < 1e-9: continue
            nw /= ln
            cent = sum(pts, np.zeros(3)) / 4
            depth = cent[2] + cam_d
            if depth < 0.3: continue
            base = np.array(b.color)
            d1 = max(0.0, np.dot(nw, kd)); d2 = max(0.0, np.dot(nw, fd)); d3 = max(0.0, np.dot(nw, rd))
            hsh = (hash((b.name, fi)) % 13) / 13.0 - 0.5
            col = base * (L['amb'] + d1 * np.array(L['keyc']) + d2 * np.array(L['fillc'])) + d3**2 * np.array(L['rimc']) * 0.8
            col = col * (1.0 + 0.08 * hsh)
            if b.emis: col = base * (1.0 + b.emis * 1.6)
            faces.append((depth, pts, np.clip(col*255,0,255), b.emis))
    faces.sort(key=lambda q: -q[0])
    dr = ImageDraw.Draw(frame, "RGBA")
    de = ImageDraw.Draw(emis, "RGBA")
    def proj(p):
        d = p[2] + cam_d
        return (W/2 + f*p[0]/d, H*0.52 - f*(p[1]-cam_h)/d)
    # контактная тень
    gp = proj(np.array([root.get('x',0), 0.02, root.get('z',0)]))
    sw = f*0.42/(root.get('z',0)+cam_d)
    sh = Image.new("L", (W, H), 0); dsh = ImageDraw.Draw(sh)
    dsh.ellipse([gp[0]-sw, gp[1]-sw*0.28, gp[0]+sw, gp[1]+sw*0.28], fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(max(4, int(sw*0.35))))
    sha = np.asarray(sh, np.float32)[..., None]/255
    cur = np.asarray(frame.convert("RGB"), np.float32) * (1 - sha*0.55)
    frame.paste(Image.fromarray(np.clip(cur, 0, 255).astype(np.uint8)), (0, 0))
    for depth, pts, col, em in faces:
        poly = [proj(p) for p in pts]
        dr.polygon(poly, fill=(int(col[0]),int(col[1]),int(col[2]),255))
        if em: de.polygon(poly, fill=(255,255,255,200))
    return proj

# ---------------- утилиты кадра ----------------
def particles(frame, t, n, seed, region, col, sz=2.0, spd=1.0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    r = np.random.default_rng(seed)
    for i in range(n):
        px = r.uniform(*region[0]); py = r.uniform(*region[1])
        x = (px + 40*math.sin(t*0.11*spd + i*2.1)) % 1.0
        y = (py - t*0.008*spd*(0.5+r.uniform(0,1))) % 1.0
        a = int(60 + 60*math.sin(t*0.7 + i))
        s = sz * (0.6 + r.uniform(0, 1))
        dr.ellipse([x*W-s, y*H-s, x*W+s, y*H+s], fill=col+(max(0,a),))
    frame.alpha_composite(ov)

def subtitle(frame, text):
    if not text: return
    im = Image.fromarray(np.zeros((H, W, 3), np.uint8))
    dr = ImageDraw.Draw(im)
    fnt = ImageFont.truetype(SANS, 42)
    lines = text.split("\n")
    yy = H - 60 - 52*len(lines)
    for ln in lines:
        w = dr.textlength(ln, font=fnt)
        dr.text(((W-w)/2, yy), ln, font=fnt, fill=(235,235,235), stroke_width=3, stroke_fill=(0,0,0))
        yy += 52
    arr = np.asarray(im, np.float32)
    m = (arr.sum(2) > 10)[..., None]
    np.copyto(frame, np.where(m, arr*0.92 + frame*0.08, frame))

# ---------------- сцены ----------------
def persp_coeffs(src_quad, dst_quad):
    A = []; Bv = []
    for (x, y), (u, v) in zip(dst_quad, src_quad):
        A.append([x, y, 1, 0, 0, 0, -u*x, -u*y]); Bv.append(u)
        A.append([0, 0, 0, x, y, 1, -v*x, -v*y]); Bv.append(v)
    res = np.linalg.solve(np.array(A), np.array(Bv))
    return res

def homography(src_quad, dst_quad):
    c = persp_coeffs(src_quad, dst_quad)
    return c

def shot_act0(t, plates, env):
    frame = np.zeros((H, W, 3), np.float32)
    im = Image.fromarray(frame.astype(np.uint8)); dr = ImageDraw.Draw(im)
    fnt = ImageFont.truetype(MONO, 54)
    lines = [("ПРОЕКТ «БЕССОННИЦА» // СЕКТОР Б, ЛАБ. №3", 0.5),
             ("ДНЕВНИК ДОКТОРА М. ВЕТРОВА", 4.6),
             ("ПОСЛЕДНЯЯ ЗАПИСЬ", 7.5)]
    y = 300
    cur = ""
    for txt, t0 in lines:
        k = int(max(0, (t - t0) * 13))
        s = txt[:k]
        dr.text((240, y), s, font=fnt, fill=(120, 255, 140))
        if 0 < t - t0 < len(txt)/13 + 0.4 and int(t*2) % 2 == 0:
            wq = dr.textlength(s, font=fnt)
            dr.rectangle([240+wq+6, y+8, 240+wq+40, y+58], fill=(120,255,140))
        if t >= t0: cur = s
        y += 110
    return np.asarray(im, np.float32)

def shot_A(t, lt, plates, env):
    pl = plates['diary']
    z = 1.0 + 0.10*ease(lt/8.5); cx = 0.50 - 0.01*ease(lt/8.5); cy = 0.56
    frame = pl.crop(z, cx, cy)
    im = Image.fromarray(np.clip(frame,0,255).astype(np.uint8)).convert("RGBA")
    # текст в книге
    text_lines = ["Я перестал спать", "три недели назад.", "Не из-за формулы.", "Из-за того, что", "формула нам показала."]
    t0, t1 = 0.7, 7.2
    prog = min(max((lt - t0)/(t1 - t0), 0), 1)
    total_ch = sum(len(l) for l in text_lines)
    vis = int(prog * total_ch)
    lay = Image.new("RGBA", (760, 470), (0,0,0,0)); dr = ImageDraw.Draw(lay)
    fnt = ImageFont.truetype(SERIF, 52)
    yy = 20; last_pos = (40, 40); cnt = 0; hand_on = False
    quad = [(345,485),(915,458),(930,762),(310,792)]
    coeffs = persp_coeffs([(40,20),(720,20),(720,450),(40,450)], quad)
    Hm = np.linalg.inv(np.array([[coeffs[0],coeffs[1],coeffs[2]],[coeffs[3],coeffs[4],coeffs[5]],[coeffs[6],coeffs[7],1]]))
    for li, ln in enumerate(text_lines):
        xx = 40
        for ch in ln:
            cw = dr.textlength(ch, font=fnt)
            if cnt < vis:
                dr.text((xx, yy), ch, font=fnt, fill=(43,32,24,235))
                last_pos = (xx+cw, yy+52)
            elif cnt == vis and prog < 1:
                dr.text((xx, yy), ch, font=fnt, fill=(43,32,24,140)); hand_on = True
            cnt += 1; xx += cw
        yy += 84
    warped = lay.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    im.alpha_composite(warped)
    # рука с пером
    p = Hm @ np.array([last_pos[0], last_pos[1], 1]); p /= p[2]
    hx, hy = p[0], p[1]
    hd = ImageDraw.Draw(im, "RGBA")
    wig = 3*math.sin(lt*22) if prog < 1 else 0
    hx, hy = hx+8+wig, hy+6
    ca, sa = math.cos(0.55), math.sin(0.55)
    def P(dx, dy): return (hx + dx*ca - dy*sa, hy + dx*sa + dy*ca)
    hd.polygon([P(-4,-70),P(6,-74),P(13,10),P(-2,14)], fill=(74,48,26,255))         # перо
    hd.polygon([P(-2,14),P(4,26),P(-4,28),P(-6,16)], fill=(35,26,18,255))           # кончик
    hd.polygon([P(-22,-10),P(24,-14),P(32,20),P(-14,28)], fill=(214,164,120,255))   # кисть
    hd.polygon([P(2,16),P(46,6),P(110,140),P(34,160)], fill=(232,233,238,255))      # рукав халата
    frame = np.asarray(im.convert("RGB"), np.float32)
    particles_img = Image.fromarray(np.clip(frame,0,255).astype(np.uint8)).convert("RGBA")
    particles(particles_img, lt, 26, 3, [(0.2,0.8),(0.15,0.6)], (255,214,150), 2.2)
    frame = np.asarray(particles_img.convert("RGB"), np.float32)
    flick = 1.0 + 0.02*math.sin(lt*13.7) + 0.012*math.sin(lt*31.1)
    frame *= np.array([flick, flick*0.995, flick*0.97])[None, None, :]
    return frame

def shot_B(t, lt, plates, env):
    pl = plates['lab']
    z = 1.06 + 0.06*ease(lt/8.0); cx = 0.44 + 0.05*ease(lt/8.0); cy = 0.52
    frame = pl.crop(z, cx, cy)
    im = Image.fromarray(np.clip(frame,0,255).astype(np.uint8)).convert("RGBA")
    emis = Image.new("RGBA", (W, H), (0,0,0,0))
    boxes = build_rig('sci')
    br = 0.012*math.sin(lt*1.9)
    tracks = {
        'shR': [(0,(-18,6)),(2.2,(-18,6)),(3.6,(96,10)),(6.4,(92,8)),(8.0,(30,6))],
        'elR': [(0,(35,0)),(2.2,(35,0)),(3.6,(70,0)),(6.4,(66,0)),(8.0,(40,0))],
        'shL': [(0,(-24,-6)),(8.0,(-28,-6))],
        'elL': [(0,(55,0)),(8.0,(60,0))],
        'neck': [(0,(4,0)),(3.0,(10,0)),(6.0,(12,0)),(8.0,(6,0))],
        'spine': [(0,(3,0)),(8.0,(4,0))],
        'hipL': [(0,(0,0)),(8.0,(0,0))], 'hipR': [(0,(0,0)),(8.0,(0,0))],
    }
    pose = eval_tracks(tracks, lt)
    trem = 1.5*math.sin(lt*17) if 3.6 < lt < 6.4 else 0
    pose['shR'] = (pose['shR'][0]+trem, pose['shR'][1])
    root = {'x': -0.62, 'y': br-0.02, 'z': 2.35, 'yaw': 18}
    wp = rig_world(boxes, pose, root)
    proj = draw_char(im, emis, wp, SHOTS_LIGHT['B'], root)
    # моргание + рот
    hp = [cs for b, cs in wp if b.name == 'head'][0]
    fc = sum(hp[:4], np.zeros(3))/4
    eyes = [proj(fc+np.array([0.10,0.03,-0.02])), proj(fc+np.array([-0.10,0.03,-0.02]))]
    d2 = ImageDraw.Draw(im, "RGBA")
    blink = (lt % 3.1) < 0.12
    for ex, ey in eyes:
        if blink: d2.rectangle([ex-6, ey-2, ex+6, ey+3], fill=(200,150,110,255))
        else: d2.ellipse([ex-5, ey-6, ex+5, ey+6], fill=(30,30,34,255)); d2.ellipse([ex-2, ey-3, ex+2, ey+1], fill=(220,220,225,255))
    mv = env(min(8.0, lt)) * 5
    if mv > 1:
        xa, xb = min(eyes[0][0], eyes[1][0])+9, max(eyes[0][0], eyes[1][0])-9
        d2.rectangle([xa, (eyes[0][1]+eyes[1][1])/2+24, xb, (eyes[0][1]+eyes[1][1])/2+24+mv], fill=(110,64,56,255))
    frame = np.asarray(im.convert("RGB"), np.float32)
    em = np.asarray(emis.convert("RGB"), np.float32)
    bl = np.asarray(Image.fromarray(em.astype(np.uint8)).filter(ImageFilter.GaussianBlur(14)), np.float32)
    frame = np.clip(frame + bl*0.8, 0, 255)
    pim = Image.fromarray(np.clip(frame,0,255).astype(np.uint8)).convert("RGBA")
    particles(pim, lt, 30, 5, [(0.1,0.9),(0.1,0.7)], (200,235,235), 1.8)
    return np.asarray(pim.convert("RGB"), np.float32)

def shot_C(t, lt, plates, env):
    pl = plates['breach']
    z = 1.02 + 0.10*ease(lt/12.0); cx = 0.5; cy = 0.5
    frame = pl.crop(z, cx, cy)
    im = Image.fromarray(np.clip(frame,0,255).astype(np.uint8)).convert("RGBA")
    emis = Image.new("RGBA", (W, H), (0,0,0,0))
    boxes = build_rig('guard')
    p = lt*4.6
    bob = abs(math.cos(p))*0.045
    tracks = {
        'hipL': [(0,(0,0))], 'hipR': [(0,(0,0))],
        'shL': [(0,(0,0))], 'shR': [(0,(-58,0))], 'elR': [(0,(15,0))], 'elL': [(0,(20,0))],
        'neck': [(0,(2,0))], 'spine': [(0,(4,0))],
    }
    pose = eval_tracks(tracks, lt)
    s = math.sin(p)
    pose['hipL'] = (26*s, 0); pose['hipR'] = (-26*s, 0)
    pose['shL'] = (-18*s, 0); pose['shR'] = (-58+8*s, 0)
    root = {'x': 0.06 + 0.02*math.sin(lt*0.7), 'y': bob, 'z': 5.6 - 2.6*ease(min(lt/11.0,1)), 'yaw': -4}
    wp = rig_world(boxes, pose, root)
    proj = draw_char(im, emis, wp, SHOTS_LIGHT['C'], root)
    # светящиеся глаза + фонарь
    hp = [cs for b, cs in wp if b.name == 'head'][0]
    d2 = ImageDraw.Draw(im, "RGBA")
    fc = sum(hp[:4], np.zeros(3))/4
    e1 = proj(fc+np.array([0.10,0.03,-0.02])); e2 = proj(fc+np.array([-0.10,0.03,-0.02]))
    for ex, ey in (e1, e2):
        d2.ellipse([ex-6, ey-6, ex+6, ey+6], fill=(140,255,170,235))
    de = ImageDraw.Draw(emis, "RGBA")
    for ex, ey in (e1, e2): de.ellipse([ex-6, ey-6, ex+6, ey+6], fill=(255,255,255,255))
    # луч фонаря из реальной кисти
    fr = [cs for b, cs in wp if b.name == 'foreR'][0]
    hand_w = sum(fr[4:], np.zeros(3))/4
    hnd = proj(hand_w)
    d = hand_w[2] + SHOTS_LIGHT['C']['cam_d']
    fl = proj(hand_w + np.array([-0.75, -hand_w[1]+0.03, -1.7]))
    frr = proj(hand_w + np.array([0.35, -hand_w[1]+0.03, -1.7]))
    ovb = Image.new("RGBA", (W, H), (0, 0, 0, 0)); db = ImageDraw.Draw(ovb)
    db.polygon([hnd, fl, frr], fill=(255,232,170,46))
    db.ellipse([hnd[0]-5, hnd[1]-5, hnd[0]+5, hnd[1]+5], fill=(255,246,210,230))
    ovb = ovb.filter(ImageFilter.GaussianBlur(5))
    im.alpha_composite(ovb)
    frame = np.asarray(im.convert("RGB"), np.float32)
    em = np.asarray(emis.convert("RGB"), np.float32)
    bl = np.asarray(Image.fromarray(em.astype(np.uint8)).filter(ImageFilter.GaussianBlur(16)), np.float32)
    frame = np.clip(frame + bl*0.9, 0, 255)
    # строб
    strobe = max(0.0, math.sin(lt*2.4))**8 * 0.10
    frame = frame*(1-strobe*0.5) + np.array([255,40,40])*strobe
    # дым
    sm = Image.new("L", (W//4, H//4), 0); ds = ImageDraw.Draw(sm)
    r = np.random.default_rng(9)
    for i in range(7):
        x = (r.uniform(0.1,0.9) + lt*0.01*(1+i*0.2)) % 1.0; y = r.uniform(0.25,0.75)
        rr = 60 + i*14
        ds.ellipse([x*W//4-rr, y*H//4-rr, x*W//4+rr, y*H//4+rr], fill=34+i*6)
    sm = sm.filter(ImageFilter.GaussianBlur(18)).resize((W, H))
    sma = np.asarray(sm, np.float32)[..., None]/255*0.5
    frame = frame*(1-sma*0.6) + np.array([160,150,150])*sma*0.6
    pim = Image.fromarray(np.clip(frame,0,255).astype(np.uint8)).convert("RGBA")
    particles(pim, lt, 14, 11, [(0.3,0.7),(0.2,0.8)], (255,190,80), 1.6, 3.0)
    return np.asarray(pim.convert("RGB"), np.float32)

SHOTS_LIGHT = {
 'B': dict(key=(0.4,0.9,0.5), keyc=(0.70,0.80,0.88), fill=(-0.8,0.2,0.3), fillc=(0.08,0.30,0.30),
           rimc=(0.4,0.75,0.75), amb=0.24, cam_h=1.0, cam_d=0.6, f=940),
 'C': dict(key=(0,0.9,-0.4), keyc=(1.0,0.30,0.24), fill=(-0.6,0.3,-0.2), fillc=(0.45,0.14,0.12),
           rimc=(1.0,0.35,0.28), amb=0.24, cam_h=1.1, cam_d=0.6, f=940),
}

# таймлайн
VO = [('audio/v5/v6_vetrov_01.mp3', 10.5, 6.95), ('audio/v5/v6_vetrov_02.mp3', 19.2, 6.77),
      ('audio/v5/v6_vetrov_03.mp3', 27.4, 9.93)]
SH = [('act0', 0, 10.0), ('A', 10.0, 18.7), ('B', 18.7, 27.0), ('C', 27.0, 39.4), ('tail', 39.4, 41.0)]
SUBS = [(10.5, 17.4, "Я перестал спать три недели назад.\nНе из-за формулы. Из-за того, что формула нам показала."),
        (19.2, 25.9, "Сектор Б, лаборатория три.\nЗдесь мы обещали вернуть людям треть жизни."),
        (27.4, 37.3, "Последняя запись. Стена продержалась одиннадцать секунд.\nЕсли это читает кто-то живой — не ищите нас. Ищите, куда оно пошло.")]

def envfunc(path):
    cmd = [FF, '-i', os.path.join(ROOT, path), '-f', 's16le', '-ac', '1', '-ar', '8000', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)/32768
    win = max(1, 8000//FPS)
    env = np.abs(a[:len(a)//win*win].reshape(-1, win)).mean(1)
    return lambda t: float(np.clip(env[min(int(t*FPS), len(env)-1)]*8, 0, 1))

def main(mode):
    plates = {'diary': Plate('shot_A_diary.png'), 'lab': Plate('plate_B_lab.png'), 'breach': Plate('plate_C_breach.png')}
    envs = [envfunc(v[0]) for v in VO]
    def env_shot(i, lt): return envs[i](lt) if i >= 0 else (lambda t: 0.0)
    frames = []
    if mode == 'test':
        ts = [14.2, 23.0, 33.0]
    else:
        ts = [i/FPS for i in range(int(SH[-1][2]*FPS))]
    out = None
    if mode == 'full':
        out = subprocess.Popen([FF, '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-s', f'{W}x{H}',
                                '-pix_fmt', 'rgb24', '-r', str(FPS), '-i', '-', '-an',
                                '-vcodec', 'libx264', '-preset', 'medium', '-crf', '20',
                                '-pix_fmt', 'yuv420p', os.path.join(ROOT, 'video', 'v6_video.mp4')],
                               stdin=subprocess.PIPE)
    for t in ts:
        fr = render_t(t, plates, envs)
        if mode == 'test':
            Image.fromarray(np.clip(fr,0,255).astype(np.uint8)).save(f"/home/user/v6_t{int(t*10)}.png")
        else:
            out.stdin.write(np.clip(fr,0,255).astype(np.uint8).tobytes())
    if out: out.stdin.close(); out.wait()
    print("done", mode)

def render_t(t, plates, envs):
    for i,(name,a,b) in enumerate(SH):
        if a <= t < b:
            lt = t - a
            if name == 'act0': fr = shot_act0(lt, plates, None)
            elif name == 'A': fr = shot_A(lt, lt, plates, lambda q: envs[0](q))
            elif name == 'B': fr = shot_B(lt, lt, plates, lambda q: envs[1](q))
            elif name == 'C': fr = shot_C(lt, lt, plates, lambda q: envs[2](q))
            else: fr = np.zeros((H, W, 3), np.float32)
            # кроссфейды
            for j,(n2,a2,b2) in enumerate(SH):
                if j == i+1 and b - t < 0.8:
                    u = ease(1 - (b - t)/0.8)
                    lt2 = t - a2
                    if n2 == 'A': fr2 = shot_A(lt2, lt2, plates, lambda q: envs[0](q))
                    elif n2 == 'B': fr2 = shot_B(lt2, lt2, plates, lambda q: envs[1](q))
                    elif n2 == 'C': fr2 = shot_C(lt2, lt2, plates, lambda q: envs[2](q))
                    else: fr2 = np.zeros((H, W, 3), np.float32)
                    fr = fr*(1-u) + fr2*u
            if t > 40.2: fr *= max(0, 1-(t-40.2)/0.8)
            for (sa, sb, txt) in SUBS:
                if sa <= t < sb: subtitle(fr, txt)
            return fr
    return np.zeros((H, W, 3), np.float32)

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'test')
