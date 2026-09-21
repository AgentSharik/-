#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Цельное видео v6 (монтажный блок): SH-01 → SH-02 → SH-03 → SH-06 → SH-07 → SH-24.
Камера на платах — покадрово (pan/zoom по ease), склейки — кроссфейды 0.6 c,
звуковая постель единая: рум-тон + событийные sfx из расписаний + VO в глобальных точках.
"""
import json, math, os, subprocess, wave, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import sys
sys.path.insert(0, "prod/tools")
from animate_v6 import (FPS, ease, grain_arr, mix_events, write_wav,
                        Terminal, Plate, MONO)
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()

RES = (960, 540)
X = 0.6  # кроссфейд

class PlateCam:
    """Плата + покадровая камера (pan/zoom), живые слои, без текста."""
    def __init__(self, base, dur, res, z0=1.0, z1=1.25, c0=(0.5, 0.5), c1=(0.5, 0.5), seed=9):
        self.src = Image.open(base).convert("RGB")
        self.dur, self.res = dur, res
        self.z0, self.z1, self.c0, self.c1 = z0, z1, c0, c1
        import random
        rng = random.Random(seed)
        self.dust = [(rng.uniform(0.05, 0.95), rng.uniform(0.05, 0.9),
                      rng.uniform(0.2, 0.9), rng.uniform(0, 6.28)) for _ in range(36)]

    def frame(self, fi):
        t = fi / FPS
        W, H = self.res
        sw, sh = self.src.size
        u = ease(min(1.0, t / max(1.0, self.dur - 0.5)))
        z = self.z0 + (self.z1 - self.z0) * u
        cx = (self.c0[0] + (self.c1[0] - self.c0[0]) * u) * sw
        cy = (self.c0[1] + (self.c1[1] - self.c0[1]) * u) * sh
        bw, bh = sw / z, sh / z
        x0, y0 = max(0.0, min(cx - bw / 2, sw - bw)), max(0.0, min(cy - bh / 2, sh - bh))
        img = self.src.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + bw, y0 + bh))
        d = ImageDraw.Draw(img, "RGBA")
        for (px0, py0, sp, ph) in self.dust:
            xx = (px0 + 0.015 * math.sin(t * sp + ph)) * W
            yy = ((py0 - 0.01 * t * sp) % 0.9 + 0.05) * H
            al = int(26 + 20 * math.sin(t * 2 * sp + ph))
            if al > 6:
                d.ellipse([xx, yy, xx + 2.0, yy + 2.0], fill=(230, 235, 225, al))
        a = np.asarray(img).astype(np.float32)
        a *= 1.0 + 0.015 * math.sin(t * 21) + 0.01 * math.sin(t * 57 + 1.3)
        a += grain_arr(a.shape, np.random.default_rng(fi), 2.0)
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        a *= (1.0 - 0.32 * np.clip(r - 0.55, 0, 1) ** 1.6)[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))

def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)

def main():
    tl = {s["id"]: s for s in json.load(open("prod/audio/timeline_v6.json"))["shots"]}
    os.makedirs("/tmp/asm", exist_ok=True)
    seq = [
        ("SH-01", None),
        ("SH-02", None),
        ("SH-03", PlateCam("art_v6/SH03_lab_wide.png", tl["SH-03"]["dur"], RES,
                           z0=1.35, z1=1.35, c0=(0.32, 0.5), c1=(0.68, 0.5))),
        ("SH-06", PlateCam("art_v6/SH06_cot_clipboard.png", 8.0, RES,
                           z0=1.0, z1=1.22, c0=(0.5, 0.5), c1=(0.47, 0.47))),
        ("SH-07", PlateCam("art_v6/SH07_monitor.png", tl["SH-07"]["dur"], RES,
                           z0=1.05, z1=1.42, c0=(0.55, 0.47), c1=(0.58, 0.45))),
        ("SH-24", None),
    ]
    durs = [tl[s]["dur"] if o else tl[s]["dur"] for s, o in seq]
    durs[3] = 8.0  # SH-06 в сборке — немая драматическая пауза
    vids = []
    for (sid, obj), dur in zip(seq, durs):
        out = f"/tmp/asm/{sid}.mp4"
        n = int(round(dur * FPS))
        if obj is None:  # видео из готового превью, без звука, точное число кадров
            run([FF, "-y", "-i", f"prod/previews/{sid}_preview.mp4", "-an",
                 "-vf", "scale=960:540:flags=lanczos", "-r", str(FPS),
                 "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p", out])
        else:            # покадровый рендер платы с камерой
            d = f"/tmp/asm/{sid}"
            os.makedirs(d, exist_ok=True)
            for fi in range(n):
                obj.frame(fi).save(f"{d}/f{fi:04d}.png", optimize=True)
            run([FF, "-y", "-framerate", str(FPS), "-i", f"{d}/f%04d.png",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-pix_fmt", "yuv420p", out])
            shutil.rmtree(d)
        vids.append(out)
        print("video", sid, dur, flush=True)
    # кроссфейды
    offs, acc = [], 0.0
    for dur in durs[:-1]:
        acc += dur - X
        offs.append(round(acc, 3))
    fc = []
    prev = "[0:v]"
    for i, off in enumerate(offs):
        nxt = f"[x{i+1}]" if i < len(offs) - 1 else "[vout]"
        fc.append(f"{prev}[{i+1}:v]xfade=transition=fade:duration={X}:offset={off}{nxt}")
        prev = nxt
    vonly = "/tmp/asm/assembly_video.mp4"
    run([FF, "-y"] + sum([["-i", v] for v in vids], []) +
        ["-filter_complex", ";".join(fc), "-map", "[vout]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", vonly])
    # единая звуковая постель
    T = sum(durs) - X * len(offs)
    starts = [0.0]
    for dur in durs[:-1]:
        starts.append(starts[-1] + dur - X)
    DIARY = ["Я перестал спать", "три недели назад.", "Не из-за формулы.",
             "Из-за того, что", "формула нам показала."]
    t1 = Terminal(["ПРОЕКТ „БЕССОННИЦА“ // СЕКТОР Б, ЛАБ. №3", "ДНЕВНИК ДОКТОРА М. ВЕТРОВА",
                   "ПОСЛЕДНЯЯ ЗАПИСЬ"], durs[0], RES)
    t24 = Terminal(["ДНЕВНИК НАЙДЕН ПОД ОБЛОМКАМИ КПП-4.", "ДАЛЬШЕ — ИЗ МОИХ ЗАПИСЕЙ. — А."],
                   durs[5], RES)
    p2 = Plate("art_v6/SH02_diary_base.png", DIARY,
               [(0.460, 0.535), (0.660, 0.560), (0.675, 0.700), (0.470, 0.685)],
               durs[1], RES, zoom=1.55, cps=8.6)
    events = ([(t + starts[0], k) for t, k in t1.events] +
              [(t + starts[1], k) for t, k in p2.events] +
              [(t + starts[5], k) for t, k in t24.events])
    pcm = mix_events(T, events).astype(np.float32) / 32767.0
    # VO в глобальных точках
    def read_mono(path):
        w = "/tmp/asm/vo.wav"
        run([FF, "-y", "-i", path, "-ac", "1", "-ar", "44100", w])
        with wave.open(w) as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
        return np.frombuffer(raw, "<i2").astype(np.float32) / 32767.0
    for path, at in [("/tmp/repo/audio/v5/v6_vetrov_01.mp3", starts[1] + 4.5),
                     ("/tmp/repo/audio/v5/v6_vetrov_02.mp3", starts[2] + 1.2),
                     ("/tmp/repo/audio/v5/v6_vetrov_03.mp3", starts[4] + 1.2)]:
        s = read_mono(path) * 0.9
        i = int(at * 44100)
        j = min(len(pcm), i + len(s))
        pcm[i:j, 0] += s[: j - i]
        pcm[i:j, 1] += s[: j - i]
    pk = np.abs(pcm).max() + 1e-9
    write_wav("/tmp/asm/bed.wav", (pcm / pk * 0.55 * 32767).astype("<i2"))
    final = "prod/previews/TRET_ZHIZNI_assembly_v6.mp4"
    run([FF, "-y", "-i", vonly, "-i", "/tmp/asm/bed.wav", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-shortest", final])
    print("ASSEMBLY", final, round(T, 2), "s", flush=True)

if __name__ == "__main__":
    main()
