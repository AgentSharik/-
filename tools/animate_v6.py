#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ТРЕТЬ ЖИЗНИ v6 — покадровый рендер PNG-последовательностей (30 fps).
Метод: каждый кадр — отдельный PNG. Текст заполняется посимвольно (своё состояние
на каждый кадр), камера — субпиксельный pan/zoom по ease-кривой, живые слои:
мерцание света, пылинки, зерно, виньетка, чернильная вспышка под пером.
Звук событии собирается из того же расписания => идеальная синхронность стук/символ.
"""
import json, math, os, sys, wave, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

FPS = 30
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SR = 44100

def ease(t):  # ease-in-out
    return t * t * (3 - 2 * t)

def homography(src, dst):
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    h = np.linalg.lstsq(np.array(A, float), np.array(b, float), rcond=None)[0]
    return np.array([[h[0], h[1], h[2]], [h[3], h[4], h[5]], [h[6], h[7], 1.0]])

# ---------------------------------------------------------------- звук
def brown(n, rng):
    w = rng.standard_normal(n).cumsum(0)
    w -= np.linspace(w[0], w[-1], n)
    return w / (np.abs(w).max() + 1e-9)

def key_click(rng, amp=0.5):
    n = int(SR * 0.045); t = np.arange(n) / SR
    s = rng.standard_normal(n) * np.exp(-t / 0.004) * 0.7
    s += np.sin(2 * np.pi * (170 + rng.uniform(-30, 30)) * t) * np.exp(-t / 0.009) * 0.5
    return s * amp

def carriage(rng):
    n = int(SR * 0.16); t = np.arange(n) / SR
    s = rng.standard_normal(n) * np.exp(-t / 0.05) * 0.25
    s += np.sin(2 * np.pi * 140 * t) * np.exp(-((t - 0.12) ** 2) / 2e-4) * 0.4
    return s

def bell():
    n = int(SR * 0.7); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2450 * t) + 0.5 * np.sin(2 * np.pi * 3280 * t)) * np.exp(-t / 0.22) * 0.16

def pen_scratch(rng):
    n = int(SR * 0.07); t = np.arange(n) / SR
    s = rng.standard_normal(n) * np.exp(-t / 0.02) * 0.16
    return np.convolve(s, np.ones(3) / 3, "same")

def rustle(rng):
    n = int(SR * 0.14); t = np.arange(n) / SR
    return rng.standard_normal(n) * np.exp(-t / 0.05) * 0.07

def mix_events(dur, events):
    n = int(dur * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(7)
    room = brown(n, rng) * 0.022
    room = np.convolve(room, np.ones(40) / 40, "same") * 3.0
    out += room
    for time, kind in events:
        i = int(time * SR)
        if kind == "key":   s = key_click(rng)
        elif kind == "cr":  s = carriage(rng)
        elif kind == "bell":s = bell()
        elif kind == "pen": s = pen_scratch(rng)
        elif kind == "rustle": s = rustle(rng)
        else: continue
        j = min(n, i + len(s))
        out[i:j] += s[: j - i]
    pk = np.abs(out).max() + 1e-9
    out = out / pk * 0.5
    st = np.stack([out, out], 1)
    return (st * 32767).astype("<i2")

def write_wav(path, pcm):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- кадры
def grain_arr(shape, rng, sigma):
    return rng.standard_normal(shape) * sigma

class Terminal:
    def __init__(self, lines, dur, res, cps=None, seed=3):
        self.lines, self.dur, self.res = lines, dur, res
        self.rng = random.Random(seed)
        W, H = res
        self.font = ImageFont.truetype(MONO, int(H * 0.052))
        lead, tail, pause = 1.1, 1.2, 0.38
        chars = sum(len(l) for l in lines)
        cps = cps or chars / max(1.0, dur - lead - tail - pause * len(lines))
        self.sched, self.events, t = [], [], lead
        for li, line in enumerate(lines):
            self.events.append((t - 0.15, "rustle"))
            for ch in line:
                t += 1.0 / cps * self.rng.uniform(0.75, 1.25)
                self.sched.append((t, li, ch))
                self.events.append((t, "key"))
            self.events.append((t + 0.12, "cr"))
            if li == len(lines) - 1:
                self.events.append((t + 0.30, "bell"))
            t += pause
        self.t_end = t

    def frame(self, fi):
        t = fi / FPS
        W, H = self.res
        img = Image.new("RGB", (W, H), (4, 7, 5))
        d = ImageDraw.Draw(img, "RGBA")
        # фоновое свечение
        glow = Image.new("L", (W // 4, H // 4), 0)
        gd = ImageDraw.Draw(glow)
        gd.ellipse([0.1 * W // 4, 0.1 * H // 4, 0.95 * W // 4, 0.9 * H // 4], fill=26)
        glow = glow.filter(ImageFilter.GaussianBlur(30)).resize((W, H))
        img = Image.composite(Image.new("RGB", (W, H), (18, 46, 26)), img, glow)
        d = ImageDraw.Draw(img, "RGBA")
        n_shown = sum(1 for (ts, li, ch) in self.sched if ts <= t)
        grid = {}
        for (ts, li, ch) in self.sched[:n_shown]:
            grid.setdefault(li, "")
            grid[li] += ch
        y = H * 0.30
        lh = H * 0.085
        caret_pos = None
        for li, line in enumerate(self.lines):
            txt = grid.get(li, "")
            if txt:
                d.text((W * 0.12, y), txt, font=self.font, fill=(96, 255, 132, 235))
            li_cur = max((l for (ts, l, c) in self.sched[:n_shown]), default=-1)
            if li == li_cur:
                caret_pos = (W * 0.12 + d.textlength(txt, font=self.font), y)
            elif li_cur == -1 and li == 0:
                caret_pos = (W * 0.12, y)
            y += lh
        if caret_pos and t < self.t_end + 0.5 and int(t * 2.2) % 2 == 0:
            d.rectangle([caret_pos[0] + 6, caret_pos[1] + 4,
                         caret_pos[0] + 6 + H * 0.032, caret_pos[1] + H * 0.052],
                        fill=(140, 255, 170, 200))
        # свечение текста
        g = img.filter(ImageFilter.GaussianBlur(6))
        img = Image.blend(img, g, 0.35)
        a = np.asarray(img).astype(np.float32)
        # scanlines + flicker + зерно
        a[::3, :, :] *= 0.88
        a *= 1.0 + 0.02 * math.sin(t * 37) + 0.015 * math.sin(t * 91)
        a += grain_arr(a.shape, np.random.default_rng(fi), 2.0)
        return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))

class Plate:
    """База-арт + посимвольное письмо чернилами в перспективе страницы + камера.
    Текст живёт в мировых координатах арта, поэтому зум/пан камеры увлекают его."""
    def __init__(self, base, lines, quad, dur, res, zoom=1.34, cps=8.6,
                 ink=(52, 36, 22), seed=5):
        self.src = Image.open(base).convert("RGB")
        self.lines, self.quad, self.dur, self.res = lines, quad, dur, res
        self.zoom, self.ink = zoom, ink
        rng = random.Random(seed)
        self.sched, self.events, t = [], [], 0.8
        cnt = [0] * len(lines)
        for li, line in enumerate(lines):
            self.events.append((t - 0.1, "rustle"))
            for ch in line:
                t += 1.0 / cps * rng.uniform(0.7, 1.3)
                self.sched.append((t, li, cnt[li], ch))
                cnt[li] += 1
                self.events.append((t, "pen"))
            t += 0.30
        self.t_end = t
        sw, sh = self.src.size
        qp = [(q[0] * sw, q[1] * sh) for q in quad]
        qw = max(qp[1][0] - qp[0][0], qp[2][0] - qp[3][0])
        qh = max(qp[3][1] - qp[0][1], qp[2][1] - qp[1][1])
        self.fs = max(9, int(qh * 0.80 / (len(lines) * 1.55)))
        self.lh = int(self.fs * 1.55)
        self.tw = int(qw * 0.96)
        self.th = self.lh * len(lines) + 6
        H_u2s = homography([(0, 0), (1, 0), (1, 1), (0, 1)], qp)
        H_u2l = homography([(0, 0), (1, 0), (1, 1), (0, 1)],
                           [(0, 0), (self.tw, 0), (self.tw, self.th), (0, self.th)])
        M = H_u2l @ np.linalg.inv(H_u2s)   # src px -> layer px (для PIL.transform)
        self.coeffs = tuple(M.flatten()[:8])
        self.H_fwd = H_u2s
        self.jit = random.Random(11)
        self.dust = [(rng.uniform(0.05, 0.6), rng.uniform(0.05, 0.7),
                      rng.uniform(0.2, 0.9), rng.uniform(0, 6.28)) for _ in range(42)]

    def _text_layer(self, shown):
        layer = Image.new("RGBA", (self.tw, self.th), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        font = ImageFont.truetype(SERIF, self.fs)
        rng = random.Random(11)
        for li, line in enumerate(self.lines):
            x = 2
            for ch in shown.get(li, ""):
                jx, jy = rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)
                d.text((x + jx, li * self.lh + jy), ch, font=font, fill=self.ink + (228,))
                x += d.textlength(ch, font=font)
        return layer

    def frame(self, fi):
        t = fi / FPS
        W, H = self.res
        sw, sh = self.src.size
        n_shown = sum(1 for s in self.sched if s[0] <= t)
        shown, cur = {}, None
        for (ts, li, ci, ch) in self.sched[:n_shown]:
            shown[li] = shown.get(li, "") + ch
            cur = (ts, li, ci)
        world = self.src.copy()
        if n_shown:
            warped = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            txt = self._text_layer(shown).transform((sw, sh), Image.PERSPECTIVE,
                                                     self.coeffs, Image.BICUBIC)
            world.paste(txt, (0, 0), txt)
        # чернильная вспышка в точке письма
        glow_src = None
        if cur and t - cur[0] < 0.14:
            li, ci = cur[1], cur[2]
            u = (ci + 0.9) / max(1, len(self.lines[li]))
            v = (li + 0.55) / len(self.lines)
            p = self.H_fwd @ np.array([u, v, 1.0]); p /= p[2]
            glow_src = (p[0], p[1])
            d = ImageDraw.Draw(world, "RGBA")
            r = sw * 0.006
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 242, 205, 80))
        # камера: субпиксельный zoom по ease
        z = 1.0 + (self.zoom - 1.0) * ease(min(1.0, t / max(1.0, self.dur - 1.5)))
        cx, cy = sw * 0.545, sh * 0.60
        bw, bh = sw / z, sh / z
        x0, y0 = max(0.0, cx - bw / 2), max(0.0, cy - bh / 2)
        x1, y1 = min(sw, cx + bw / 2), min(sh, cy + bh / 2)
        box = (x0, y0, x1, y1)
        img = world.resize((W, H), Image.LANCZOS, box=box)
        # пылинки в луче лампы
        d = ImageDraw.Draw(img, "RGBA")
        for (px0, py0, sp, ph) in self.dust:
            xx = (px0 + 0.02 * math.sin(t * sp + ph)) * W
            yy = ((py0 - 0.012 * t * sp) % 0.9 + 0.05) * H
            al = int(34 + 26 * math.sin(t * 2 * sp + ph))
            if al > 8:
                d.ellipse([xx, yy, xx + 2.2, yy + 2.2], fill=(255, 236, 200, al))
        a = np.asarray(img).astype(np.float32)
        a *= 1.0 + 0.016 * math.sin(t * 23) + 0.011 * math.sin(t * 61 + 1.7)
        a += grain_arr(a.shape, np.random.default_rng(fi), 2.1)
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        a *= (1.0 - 0.34 * np.clip(r - 0.55, 0, 1) ** 1.6)[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))

# ---------------------------------------------------------------- сборки
def build(shots, out_root, keys_root, prev_root="prod/previews", sfx_root="prod/audio/sfx",
          keep_frames=False):
    """Конвейер: PNG-кадры -> mp4 (ffmpeg) -> очистка кадров. PNG-плиты не копятся."""
    import subprocess, shutil, imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(out_root, exist_ok=True); os.makedirs(prev_root, exist_ok=True)
    os.makedirs(sfx_root, exist_ok=True)
    tl = {s["id"]: s for s in json.load(open("prod/audio/timeline_v6.json"))["shots"]}
    for sh in shots:
        sid = sh["id"]
        dur = tl[sid]["dur"]
        n = int(round(dur * FPS))
        d = os.path.join(out_root, sid)
        os.makedirs(d, exist_ok=True)
        for fi in range(n):
            sh["obj"].frame(fi).save(os.path.join(d, f"f{fi:04d}.png"), optimize=True)
            if fi % 60 == 0:
                os.makedirs(os.path.join(keys_root, sid), exist_ok=True)
                sh["obj"].frame(fi).save(os.path.join(keys_root, sid, f"key_{fi//60:02d}.png"))
        print("rendered", sid, n, "frames", flush=True)
        pcm = mix_events(dur, sh["obj"].events)
        wav = os.path.join(sfx_root, sid + "_sfx.wav")
        write_wav(wav, pcm)
        mp4 = os.path.join(prev_root, sid + "_preview.mp4")
        subprocess.run([ff, "-y", "-framerate", str(FPS), "-i", os.path.join(d, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                        mp4], check=True, capture_output=True)
        if not keep_frames:
            shutil.rmtree(d)
        print("encoded", mp4, flush=True)

if __name__ == "__main__":
    RES = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (960, 540)
    RES_T = RES  # демо-проход 540p; мастер 1080p: python3 prod/tools/animate_v6.py 1920 1080
    DIARY = ["Я перестал спать", "три недели назад.", "Не из-за формулы.",
             "Из-за того, что", "формула нам показала."]
    shots = [
        dict(id="SH-01", obj=Terminal(
            ["ПРОЕКТ „БЕССОННИЦА“ // СЕКТОР Б, ЛАБ. №3",
             "ДНЕВНИК ДОКТОРА М. ВЕТРОВА",
             "ПОСЛЕДНЯЯ ЗАПИСЬ"], 13.0, RES_T)),
        dict(id="SH-02", obj=Plate("art_v6/SH02_diary_base.png", DIARY,
            [(0.460, 0.535), (0.660, 0.560), (0.675, 0.700), (0.470, 0.685)],
            13.05, RES, zoom=1.55, cps=8.6)),
        dict(id="SH-24", obj=Terminal(
            ["ДНЕВНИК НАЙДЕН ПОД ОБЛОМКАМИ КПП-4.",
             "ДАЛЬШЕ — ИЗ МОИХ ЗАПИСЕЙ. — А."], 7.28, RES_T)),
    ]
    build(shots, "/tmp/frames", "prod/frames_keys")
