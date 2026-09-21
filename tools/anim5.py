# -*- coding: utf-8 -*-
"""v5 preview renderer: PNG art + smooth frame-by-frame motion (pan/zoom/parallax,
particles, flicker, sprite acting), crossfades, subs; pipes to ffmpeg."""
import numpy as np, json, os, subprocess, math, sys, imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ART = os.path.join(ROOT, "art", "v5")
TL = json.load(open(os.path.join(ROOT, "audio", "v5", "timeline.json")))
W, H, FPS = 1280, 720, 24
S = 1.5
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FF = imageio_ffmpeg.get_ffmpeg_exe()

rng = np.random.default_rng(11)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def snoise(t, seed):
    a, b, c = seed * 0.7 + 1.3, seed * 1.1 + 2.1, seed * 0.53 + 3.7
    return (math.sin(2 * math.pi * 0.11 * a * t + seed) * 0.5 +
            math.sin(2 * math.pi * 0.043 * b * t + seed * 2) * 0.35 +
            math.sin(2 * math.pi * 0.017 * c * t) * 0.15)


class Art:
    def __init__(self, path):
        im = Image.open(path).convert("RGB")
        self.img = im.resize((int(im.width * S), int(im.height * S)), Image.LANCZOS)
        self.SW, self.SH = self.img.size
        g = np.asarray(self.img, np.float32).mean(2)
        gb = Image.fromarray((g / g.max() * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30))
        self.lum = np.asarray(gb, np.float32) / 255.0

    def crop(self, z, cx, cy, ang=0.0):
        k = (self.SW / W) / z
        vw, vh = W * k, H * k
        a = k * math.cos(ang); b = -k * math.sin(ang)
        d = k * math.sin(ang); e = k * math.cos(ang)
        c = cx * self.SW - (a * W / 2 + b * H / 2)
        f = cy * self.SH - (d * W / 2 + e * H / 2)
        return self.img.transform((W, H), Image.AFFINE, (a, b, c, d, e, f), Image.BICUBIC)


def load_art():
    A = {}
    for key, fn in (("A", "shot_A_terminal.png"), ("B", "shot_B_scientist.png"),
                    ("C", "shot_C_breach.png"), ("D", "shot_D_kpp.png")):
        A[key] = Art(os.path.join(ART, fn))
    return A


def feather_mask(w, h, blur=10):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((4, 4, w - 4, h - 4), fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))


def extract_sprite(art, r):
    x0, y0, x1, y1 = [int(v * S) for v in r]
    im = art.img.crop((x0, y0, x1, y1)).convert("RGBA")
    im.putalpha(feather_mask(im.width, im.height))
    return im, (x0, y0)


def radial(size, soft=2.0):
    y, x = np.mgrid[0:size, 0:size]
    d = np.sqrt((x - size / 2) ** 2 + (y - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - d, 0, 1) ** soft
    return a


class Dust:
    def __init__(self, n=130, seed=3):
        r = np.random.default_rng(seed)
        self.p = r.uniform(0, 1, (n, 2))
        self.v = r.uniform(-0.006, 0.006, (n, 2)); self.v[:, 1] -= 0.002
        self.sz = r.uniform(2, 5, n)
        self.ph = r.uniform(0, 7, n)
        self.al = r.uniform(0.25, 0.8, n)
        self.spr = Image.fromarray((radial(16) * 255).astype(np.uint8))

    def draw(self, ov, t, lum):
        d = ImageDraw.Draw(ov)
        SW, SH = ov.size
        for i in range(len(self.p)):
            x = (self.p[i, 0] + self.v[i, 0] * t + 0.004 * math.sin(t * 0.7 + self.ph[i])) % 1
            y = (self.p[i, 1] + self.v[i, 1] * t) % 1
            xi, yi = int(x * SW), int(y * SH)
            l = lum[yi, xi]
            if l < 0.18:
                continue
            a = self.al[i] * l * (0.6 + 0.4 * math.sin(t * 1.3 + self.ph[i]))
            s = int(self.sz[i] * S)
            d.bitmap((xi - s, yi - s), self.spr.resize((2 * s, 2 * s)),
                     fill=(255, 250, 235, int(90 * a)))


GLOW = radial(256, 1.6)


def add_glow(base, x, y, size, color, inten):
    H_, W_ = base.shape[:2]
    s = size
    x0, x1 = int(x - s / 2), int(x + s / 2)
    y0, y1 = int(y - s / 2), int(y + s / 2)
    gx0, gy0 = max(0, x0), max(0, y0)
    gx1, gy1 = min(W_, x1), min(H_, y1)
    if gx1 <= gx0 or gy1 <= gy0:
        return
    g = GLOW[int((gy0 - y0) / s * 256):int((gy1 - y0) / s * 256),
             int((gx0 - x0) / s * 256):int((gx1 - x0) / s * 256)]
    g = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize(
        (gx1 - gx0, gy1 - gy0), Image.BILINEAR), np.float32) / 255.0
    for c in range(3):
        base[gy0:gy1, gx0:gx1, c] += g * color[c] * inten


class Sparks:
    def __init__(self, n=70, seed=5, up=False):
        r = np.random.default_rng(seed)
        self.n = n
        self.life = r.uniform(0.6, 1.4, n)
        self.born = r.uniform(0, 3, n)
        self.ang = r.uniform(0, 2 * np.pi, n)
        self.sp = r.uniform(60, 240, n)
        self.up = up

    def draw(self, base, t, ex, ey):
        for i in range(self.n):
            lt = (t - self.born[i]) % (self.life[i] + 0.6)
            if lt > self.life[i]:
                continue
            u = lt / self.life[i]
            a = self.ang[i]
            vx, vy = math.cos(a) * self.sp[i], math.sin(a) * self.sp[i] * (0.5 if not self.up else 0.2)
            if self.up:
                vy = -self.sp[i] * 0.4
            x = ex + vx * lt + 8 * math.sin(3 * lt + i)
            y = ey + vy * lt + (150 if not self.up else -10) * lt * lt
            add_glow(base, x, y, 8 + 6 * (1 - u), (255, 170, 70), 0.8 * (1 - u))


def paste_move(ov, spr, pos, dx=0, dy=0, rot=0, scale=1.0):
    x0, y0 = pos
    im = spr
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    ov.alpha_composite(im, (int(x0 + dx - (im.width - spr.width) / 2),
                            int(y0 + dy - (im.height - spr.height) / 2)))


PAGES_TXT = [
    (["день 12. они не спят.", "днём — тише.", "ночью — ходят", "по коридорам.", "не выходите ночью."], -3),
    (["свет костра — граница.", "за ней силуэт", "стоит и ждёт.", "сон — это то, что", "делает нас людьми."], 4),
]
PAGES_RECT = [(782, 645, 1056, 1005), (1062, 662, 1330, 995)]


def build_pages(art):
    lay = Image.new("RGBA", (art.SW, art.SH), (0, 0, 0, 0))
    for (x0, y0, x1, y1), (lines, ang) in zip(PAGES_RECT, PAGES_TXT):
        w, h = x1 - x0, y1 - y0
        pg = art.img.crop((x0, y0, x1, y1)).convert("RGBA").filter(
            ImageFilter.GaussianBlur(4))
        d = ImageDraw.Draw(pg)
        f = ImageFont.truetype(SANS, 15)
        yy = 18
        for ln in lines:
            d.text((16, yy), ln, font=f, fill=(62, 50, 38, 235))
            yy += 30
        m = Image.new("L", (w, h), 255)
        pg.putalpha(m.filter(ImageFilter.GaussianBlur(6)))
        pg = pg.rotate(ang, Image.BICUBIC, expand=True)
        lay.alpha_composite(pg, ((x0 + x1) // 2 - pg.width // 2,
                                 (y0 + y1) // 2 - pg.height // 2))
    return lay


CAM = {
    "A": dict(z=(1.18, 1.32), c=((0.455, 0.48), (0.415, 0.455))),
    "B": dict(z=(1.20, 1.34), c=((0.53, 0.46), (0.56, 0.43))),
    "C": dict(z=(1.16, 1.30), c=((0.52, 0.52), (0.49, 0.50))),
    "D": dict(z=(1.34, 1.18), c=((0.50, 0.56), (0.50, 0.50))),
}
GRADE = {"A": (0.90, 1.02, 1.08), "B": (1.05, 1.00, 0.93),
         "C": (1.08, 0.90, 0.88), "D": (0.94, 1.00, 1.08)}


class Shot:
    def __init__(self, key, art):
        self.key = key
        self.art = art
        self.dust = Dust(seed=hash(key) % 7 + 2)
        self.sparks = Sparks(seed=hash(key) % 5 + 1, up=(key == "D"))
        if key == "B":
            self.head, self.hpos = extract_sprite(art, (630, 105, 885, 335))
            self.arm, self.apos = extract_sprite(art, (555, 315, 815, 485))
        if key == "C":
            self.guard, self.gpos = extract_sprite(art, (603, 345, 757, 533))
        if key == "D":
            self.pages = build_pages(art)
            self.hand_l, self.hlpos = extract_sprite(art, (599, 791, 879, 1152))
            self.hand_r, self.hrpos = extract_sprite(art, (1223, 804, 1528, 1152))
        self.smoke = [self._smoke_tile(s) for s in (9, 13)]

    def _smoke_tile(self, sc):
        r = np.random.default_rng(sc)
        n = r.uniform(0, 1, (128, 128))
        im = Image.fromarray((n * 255).astype(np.uint8)).resize((512, 512)).filter(
            ImageFilter.GaussianBlur(sc))
        return im

    def compose(self, t, tl_abs):
        a = self.art
        cam = CAM[self.key]
        u = ease(t / SHOTLEN[self.key])
        z = cam["z"][0] + (cam["z"][1] - cam["z"][0]) * u
        cx = cam["c"][0][0] + (cam["c"][1][0] - cam["c"][0][0]) * u + 0.004 * snoise(tl_abs, 1)
        cy = cam["c"][0][1] + (cam["c"][1][1] - cam["c"][0][1]) * u + 0.004 * snoise(tl_abs, 2)
        hw = 1 / (2 * z) + 0.002
        cx = min(max(cx, hw), 1 - hw)
        cy = min(max(cy, hw), 1 - hw)
        base = np.asarray(a.crop(z, cx, cy, 0.002 * snoise(tl_abs, 3)), np.float32)
        SW, SH = a.SW, a.SH
        # additive light effects in source space
        if self.key == "A":
            fl = 0.75 + 0.2 * snoise(tl_abs, 4) + 0.05 * snoise(tl_abs, 9)
            add_glow(base, int(0.375 * SW), int(0.46 * SH), 420, (120, 255, 150), 0.10 * fl)
            add_glow(base, int(0.03 * SW), int(0.55 * SH), 500, (90, 160, 255), 0.10 + 0.03 * snoise(tl_abs, 5))
        if self.key == "B":
            add_glow(base, int(0.50 * SW), int(0.03 * SH), 700, (255, 220, 160), 0.10 + 0.03 * snoise(tl_abs, 4))
            add_glow(base, int(0.44 * SW), int(0.52 * SH), 260, (140, 240, 255), 0.10 + 0.05 * snoise(tl_abs, 6))
        if self.key == "C":
            ph = tl_abs % 1.7
            env = math.exp(-3.0 * max(0.0, ph - 0.08))
            add_glow(base, int(0.665 * SW), int(0.185 * SH), 620, (255, 60, 50), 0.28 * env)
            base += (np.array([30, 4, 4]) * (0.35 * env))[:, None, None].T.reshape(1, 1, 3) * 0.3
            self.sparks.draw(base, tl_abs, int(0.723 * SW), int(0.515 * SH))
        if self.key == "D":
            add_glow(base, int(0.30 * SW), int(0.62 * SH), 500, (255, 140, 60), 0.10 + 0.05 * snoise(tl_abs, 4))
            add_glow(base, int(0.62 * SW), int(0.30 * SH), 300, (200, 220, 255), 0.05 + 0.03 * snoise(tl_abs, 8))
            self.sparks.draw(base, tl_abs, int(0.35 * SW), int(0.75 * SH))
        # overlay canvas (world space)
        ov = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        # smoke drift
        for i, tile in enumerate(self.smoke):
            off = (int(tl_abs * (14 if i == 0 else -9)) % 512, int(tl_abs * (-4 - i)) % 512)
            layer = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
            for xx in range(-1, SW // 512 + 2):
                for yy in range(-1, SH // 512 + 2):
                    layer.alpha_composite(tile.convert("RGBA"), (xx * 512 - off[0], yy * 512 - off[1]))
            arr = np.asarray(layer, np.float32)
            arr[..., 3] *= 0.05 + 0.02 * i
            ov.alpha_composite(Image.fromarray(arr.astype(np.uint8), "RGBA"))
        self.dust.draw(ov, tl_abs, a.lum)
        if self.key == "B":
            br = 2.2 * math.sin(2 * math.pi * tl_abs / 3.4) + 0.9 * snoise(tl_abs, 7)
            paste_move(ov, self.head, self.hpos, dy=br, rot=0.7 * snoise(tl_abs, 5))
            au = ease(min(max((t - 1.0) / 4.0, 0), 1))
            paste_move(ov, self.arm, self.apos, dy=br * 0.7 - 5 * au,
                       rot=-2.2 * au + 0.5 * snoise(tl_abs, 8))
        if self.key == "C":
            walk = math.sin(2 * math.pi * 1.5 * tl_abs)
            gs = 1.0 + 0.06 * ease(t / SHOTLEN["C"])
            paste_move(ov, self.guard, self.gpos, dy=-abs(walk) ** 3 * 3 + 1.2 * snoise(tl_abs, 6),
                       dx=1.6 * snoise(tl_abs, 9), rot=0.8 * walk, scale=gs)
        if self.key == "A":
            draw_crt(ov, tl_abs, SW, SH)
        if self.key == "D":
            ov.alpha_composite(self.pages)
            paste_move(ov, self.hand_l, self.hlpos, dy=1.0 * snoise(tl_abs, 10))
            paste_move(ov, self.hand_r, self.hrpos, dy=1.0 * snoise(tl_abs, 11))
        k = (SW / W) / z
        aco = math.cos(0.002 * snoise(tl_abs, 3)); asi = math.sin(0.002 * snoise(tl_abs, 3))
        aa, bb = k * aco, -k * asi
        dd, ee = k * asi, k * aco
        cc = cx * SW - (aa * W / 2 + bb * H / 2)
        ff = cy * SH - (dd * W / 2 + ee * H / 2)
        ov_c = ov.transform((W, H), Image.AFFINE, (aa, bb, cc, dd, ee, ff), Image.BICUBIC)
        out = Image.alpha_composite(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA"), ov_c)
        arr = np.asarray(out.convert("RGB"), np.float32)
        g = GRADE[self.key]
        arr *= np.array(g, np.float32)
        return np.clip(arr, 0, 255).astype(np.uint8)


SHOTLEN = {k: s[2] - s[1] for s in TL["shots"] for k in [s[0]]}
CRTFONT = ImageFont.truetype(MONO, 12)


def draw_crt(ov, t, SW, SH):
    d = ImageDraw.Draw(ov)
    x0, y0 = int(0.345 * SW), int(0.415 * SH)
    lines = TL["crt_lines"]
    yy = y0 + 10
    for txt, t0 in lines:
        nch = int(max(0, (t - t0) / 0.09))
        d.text((x0 + 10, yy), txt[:nch], font=CRTFONT, fill=(150, 240, 170, 230))
        yy += 18


def act0_frame(t):
    img = Image.new("RGB", (W, H), (2, 4, 3))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(MONO, 29)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    dg = ImageDraw.Draw(glow)
    y = 250
    for txt, t0 in TL["act0_lines"]:
        nch = int(max(0, (t - t0) / 0.085))
        shown = txt[:nch]
        d.text((150, y), shown, font=f, fill=(120, 255, 150))
        dg.text((150, y), shown, font=f, fill=(60, 200, 90))
        if 0 < t - t0 < len(txt) * 0.085 + 0.4 and (int(t * 6) % 2 == 0):
            wpx = d.textlength(shown, font=f)
            d.rectangle((152 + wpx, y + 4, 152 + wpx + 16, y + 32), fill=(120, 255, 150))
        y += 62
    glow = glow.filter(ImageFilter.GaussianBlur(7))
    arr = np.asarray(img, np.float32) + np.asarray(glow, np.float32) * 0.9
    # scanlines
    arr[::3, :, :] *= 0.88
    return np.clip(arr, 0, 255).astype(np.uint8)


VIG = None


def vignette():
    global VIG
    if VIG is None:
        y, x = np.mgrid[0:H, 0:W]
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        VIG = (1 - 0.32 * np.clip(d - 0.55, 0, 1) ** 1.6)[..., None]
    return VIG


GRAIN = [rng.integers(0, 5, (H, W, 1), dtype=np.int16) - 2 for _ in range(4)]
SUBF = ImageFont.truetype(BOLD, 25)


def draw_subs(frame, t):
    for t0, t1, txt in TL["subs"]:
        if t0 <= t < t1:
            img = Image.fromarray(frame)
            d = ImageDraw.Draw(img, "RGBA")
            lines = txt.split("\n")
            ys = H - 40 - 34 * len(lines)
            widths = [d.textlength(l, font=SUBF) for l in lines]
            bw = max(widths) + 40
            d.rounded_rectangle(((W - bw) / 2, ys - 14, (W + bw) / 2, ys + 34 * len(lines) + 6),
                                10, fill=(0, 0, 0, 130))
            for i, l in enumerate(lines):
                d.text(((W - widths[i]) / 2, ys + 34 * i), l, font=SUBF,
                       fill=(245, 245, 240, 255))
            return np.asarray(img)
    return frame


def main():
    arts = load_art()
    shots = {k: Shot(k, arts[k]) for k in "ABCD"}
    bounds = TL["shots"]
    total = TL["total"]
    nframes = int(total * FPS)
    vf = os.path.join(ROOT, "video_tmp.mp4")
    proc = subprocess.Popen([FF, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s",
                             f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
                             "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                             "-pix_fmt", "yuv420p", vf], stdin=subprocess.PIPE)
    stills = {6: "v5_still_act0.png", 16: "v5_still_A.png", 25.5: "v5_still_B.png",
              36: "v5_still_C.png", 50: "v5_still_D.png"}
    for fi in range(nframes):
        t = fi / FPS
        seg = [s for s in bounds if s[1] <= t < s[2]][0]
        key = seg[0]
        if key == "act0":
            frame = act0_frame(t)
        elif key == "tail":
            frame = shots["D"].compose(t - 43.8, t)
        else:
            frame = shots[key].compose(t - seg[1], t)
            if t - seg[1] < 0.7:
                prev = bounds[bounds.index(seg) - 1][0]
                pframe = act0_frame(t) if prev == "act0" else shots[prev].compose(
                    t - bounds[bounds.index(seg) - 1][1], t)
                m = ease((t - seg[1]) / 0.7)
                frame = (pframe * (1 - m) + frame * m).astype(np.uint8)
        if key == "tail":
            frame = (frame * (1 - ease((t - 58.7) / 1.3))).astype(np.uint8)
        frame = draw_subs(frame, t)
        frame = (frame * vignette()).astype(np.uint8)
        frame = np.clip(frame.astype(np.int16) + GRAIN[fi % 4], 0, 255).astype(np.uint8)
        for st, name in list(stills.items()):
            if abs(t - st) < 0.5 / FPS:
                Image.fromarray(frame).save(os.path.join(ROOT, name))
                del stills[st]
        proc.stdin.write(frame.tobytes())
        if fi % 240 == 0:
            print(f"frame {fi}/{nframes}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("video ok", vf)


if __name__ == "__main__":
    main()
