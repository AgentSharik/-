#!/usr/bin/env python3
"""PROJECT INSOMNIA — Part 1 preview renderer (Minecraft-style horror short)."""
import subprocess, os, re, math, random, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FF = "/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
ROOT = "/home/user"
W, H, FPS = 1920, 1080, 24
SR = 48000
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
random.seed(42); np.random.seed(42)

os.makedirs(f"{ROOT}/video", exist_ok=True)
os.makedirs(f"{ROOT}/audio", exist_ok=True)

# ---------------- helpers ----------------
def probe_dur(p):
    r = subprocess.run([FF, "-i", p], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)

def to_wav(mp3, wav):
    subprocess.run([FF, "-y", "-i", mp3, "-ar", str(SR), "-ac", "1", wav],
                   check=True, capture_output=True)

def read_wav(p):
    w = wave.open(p)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
    return a

def add(buf, sig, t0, gain=1.0):
    s = int(t0 * SR)
    if s >= len(buf): return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[:e - s] * gain

# ---------------- SFX synthesis ----------------
def s_drip():
    n = int(0.10 * SR); t = np.arange(n) / SR
    f = 1300 - 900 * (t / 0.10)
    sig = np.sin(2 * np.pi * (f * t)) * np.exp(-t * 45) * 0.5
    n2 = int(0.14 * SR); t2 = np.arange(n2) / SR
    echo = np.sin(2 * np.pi * (900 - 500 * (t2 / 0.14)) * t2) * np.exp(-t2 * 60) * 0.18
    return np.concatenate([sig, np.zeros(int(0.09 * SR)), echo])

def s_blip():
    n = int(0.05 * SR); t = np.arange(n) / SR
    f = 320 + np.random.randint(0, 420)
    return np.sin(2 * np.pi * (f + 400 * (t / 0.05)) * t) * np.exp(-t * 60) * 0.35

def s_step():
    n = int(0.13 * SR); t = np.arange(n) / SR
    noise = np.random.randn(n) * np.exp(-t * 30) * 0.25
    thud = np.sin(2 * np.pi * 85 * t) * np.exp(-t * 25) * 0.5
    # crude lowpass
    k = 0.12; lp = np.empty(n); lp[0] = noise[0]
    for i in range(1, n): lp[i] = lp[i-1] + k * (noise[i] - lp[i-1])
    return lp + thud

def s_click():
    n = int(0.05 * SR); t = np.arange(n) / SR
    met = np.sign(np.sin(2 * np.pi * 1900 * t)) * np.exp(-t * 220) * 0.3
    cl = np.sin(2 * np.pi * 520 * t) * np.exp(-t * 90) * 0.4
    return met + cl

def s_gulp():
    n = int(0.16 * SR); t = np.arange(n) / SR
    f = 320 - 170 * (t / 0.16)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 18) * 0.5 + np.random.randn(n) * np.exp(-t * 40) * 0.1

def s_hit():
    n = int(1.3 * SR); t = np.arange(n) / SR
    f = 55 - 20 * (t / 1.3)
    bass = np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2) * 0.9
    nz = np.random.randn(n) * np.exp(-t * 14) * 0.3
    k = 0.05; lp = np.empty(n); lp[0] = nz[0]
    for i in range(1, n): lp[i] = lp[i-1] + k * (nz[i] - lp[i-1])
    return bass + lp

def build_sfx(T):
    buf = np.zeros(int(T * SR))
    t = np.arange(len(buf)) / SR
    # piston/generator hum with slow AM
    hum = (np.sin(2*np.pi*48*t) + 0.5*np.sin(2*np.pi*96*t) + 0.2*np.sin(2*np.pi*144*t))
    hum *= 0.5 + 0.12*np.sin(2*np.pi*0.45*t)
    buf += hum * 0.055
    # cave rumble (lowpassed noise)
    nz = np.random.randn(len(buf))
    k = 0.004; lp = np.empty(len(buf)); lp[0] = nz[0]
    acc = 0.0
    for i in range(1, len(buf)):
        acc += k * (nz[i] - acc); lp[i] = acc
    rumble_gate = np.clip((t - 4.5) / 2, 0, 1) * np.clip((T - 1.0 - t) / 2, 0, 1)
    buf += lp * 14 * 0.02 * rumble_gate
    # drips during title
    for d in (0.9, 2.4, 3.9, 15.6):
        add(buf, s_drip(), d, 0.5)
    # potion bubbling 5..24.5
    tt = 5.0
    while tt < 24.5:
        add(buf, s_blip(), tt, 0.16)
        tt += random.uniform(0.22, 0.6)
    # footsteps on quartz
    for i, st in enumerate((13.0, 14.7, 16.4, 18.1)):
        add(buf, s_step(), st, 0.8 if i % 2 == 0 else 0.65)
    # dispenser + drinking
    add(buf, s_click(), 19.8, 0.9)
    for g in (21.2, 22.0, 22.8):
        add(buf, s_gulp(), g, 0.8)
    # rising drone over close-up
    riser_t0, riser_t1 = 24.8, T - 2.6
    n = int((riser_t1 - riser_t0) * SR); rt = np.arange(n) / SR
    f = 110 + 750 * (rt / (riser_t1 - riser_t0)) ** 2
    riser = (np.sin(2*np.pi*f*rt) + 0.4*np.sin(2*np.pi*f*1.01*rt)) * (rt / (riser_t1 - riser_t0)) * 0.12
    add(buf, riser, riser_t0)
    add(buf, s_hit(), T - 2.5, 1.0)
    return buf

# ---------------- video ----------------
def pix_text_card(w, h, lines, bg=(0, 0, 0)):
    """lines: list of (text, size, color, dy). Drawn small then NEAREST-upscaled for chunky pixels."""
    sc = 3
    img = Image.new("RGB", (w // sc, h // sc), bg)
    d = ImageDraw.Draw(img)
    for text, size, color, dy in lines:
        f = ImageFont.truetype(FONT_B, size // sc)
        bb = d.textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text(((w // sc - tw) / 2 - bb[0], (h // sc + dy // sc - th) / 2 - bb[1]), text, font=f, fill=color)
    return img.resize((w, h), Image.NEAREST)

def sub_image(text, size=50):
    sc = 2
    f = ImageFont.truetype(FONT_B, size // sc)
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0] + 24, bb[3] - bb[1] + 20
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for ox in (-2, 0, 2):
        for oy in (-2, 0, 2):
            if ox or oy:
                d.text((12 - bb[0] + ox, 10 - bb[1] + oy), text, font=f, fill=(0, 0, 0, 235))
    d.text((12 - bb[0], 10 - bb[1]), text, font=f, fill=(245, 245, 245, 255))
    return img.resize((w * sc, h * sc), Image.NEAREST)

def load_shot(path):
    im = Image.open(path).convert("RGB")
    return im

def cam_crop(im, cx, cy, zoom):
    w0, h0 = im.size
    cw, ch = w0 / zoom, h0 / zoom
    x0 = min(max(cx * w0 - cw / 2, 0), w0 - cw)
    y0 = min(max(cy * h0 - ch / 2, 0), h0 - ch)
    return im.crop((int(x0), int(y0), int(x0 + cw), int(h0 / zoom * 0 + y0 + ch))).resize((W, H), Image.NEAREST)

def lerp(a, b, u): return a + (b - a) * u

def ease(u): return u * u * (3 - 2 * u)

def main():
    narrA_mp3 = f"{ROOT}/audio/narration_A.mp3"
    narrB_mp3 = f"{ROOT}/audio/narration_B.mp3"
    durA = probe_dur(narrA_mp3); durB = probe_dur(narrB_mp3)
    print("narration durations:", round(durA, 2), round(durB, 2))
    to_wav(narrA_mp3, f"{ROOT}/audio/_narrA.wav")
    to_wav(narrB_mp3, f"{ROOT}/audio/_narrB.wav")
    narrA = read_wav(f"{ROOT}/audio/_narrA.wav")
    narrB = read_wav(f"{ROOT}/audio/_narrB.wav")

    NSTART = 1.2
    eyes_end = max(29.5, NSTART + max(durA, durB) + 1.2)
    T = eyes_end + 2.5
    TOTAL_FRAMES = int(T * FPS)
    print("total T =", round(T, 2))

    # shots
    SH = {
        "lab": load_shot(f"{ROOT}/assets/shots/02_lab_wide.png"),
        "sci": load_shot(f"{ROOT}/assets/shots/03_scientist_glass.png"),
        "disp": load_shot(f"{ROOT}/assets/shots/01_dispenser_potion.png"),
        "eyes": load_shot(f"{ROOT}/assets/shots/04_extreme_closeup_eyes.png"),
    }
    title_card = pix_text_card(W, H, [
        ("ПРОЕКТ «БЕССОННИЦА»", 42, (85, 255, 85), -260),
        ("СЕКТОР Б. ЛАБОРАТОРИЯ №3", 84, (235, 235, 235), 0),
        ("// ДНЕВНИК НАБЛЮДЕНИЙ //", 36, (140, 140, 140), 220),
    ])
    end_card = pix_text_card(W, H, [
        ("ПРОЕКТ «БЕССОННИЦА»", 60, (85, 255, 85), -120),
        ("ЧАСТЬ 1 — ЧЕРНОВОЙ МОНТАЖ", 44, (220, 220, 220), 60),
        ("сравните дубли озвучки A и B", 34, (140, 140, 140), 220),
    ])

    SUBS = [
        (NSTART + 0.0, NSTART + 3.8, "Дневник наблюдений. Запись сорок вторая."),
        (NSTART + 3.8, NSTART + 7.6, "Кажется... мы наконец добились успеха."),
        (NSTART + 7.6, NSTART + 12.6, "Человечеству больше не нужно тратить треть жизни на сон."),
        (NSTART + 12.6, NSTART + 16.4, "Треть жизни — в темноте, в пустоте."),
        (NSTART + 16.4, NSTART + 20.6, "Формула «Зет-ноль-один» работает."),
        (NSTART + 20.6, NSTART + 24.0, "Должна работать."),
    ]
    sub_imgs = [(a, b, sub_image(txt)) for a, b, txt in SUBS]

    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    VIG = np.clip(1 - 0.42 * np.clip((r - 0.55) / 0.6, 0, 1) ** 2, 0.5, 1).astype(np.float32)[..., None]

    enc = subprocess.Popen([FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                            "-preset", "medium", f"{ROOT}/video/_video_only.mp4"],
                           stdin=subprocess.PIPE)

    def fade_at(t, t0, t1, f=0.45):
        m = 1.0
        if t - t0 < f: m = min(m, (t - t0) / f)
        if t1 - t < f: m = min(m, (t1 - t) / f)
        return max(m, 0.0)

    for fr in range(TOTAL_FRAMES):
        t = fr / FPS
        if t < 5.0:
            base = np.array(title_card, dtype=np.float32)
            flick = 0.75 + 0.25 * (0.5 + 0.5 * math.sin(t * 9.1)) * random.uniform(0.85, 1.0)
            base *= flick
            m = min(t / 0.6, 1.0) * min((5.0 - t) / 0.4, 1.0)
            base *= max(m, 0)
        elif t < eyes_end and t >= 24.5:
            u = ease(min((t - 24.5) / (eyes_end - 24.5), 1))
            z = lerp(1.02, 1.28, u)
            base = np.array(cam_crop(SH["eyes"], 0.5, 0.46, z), dtype=np.float32)
            g = 0.10 * u
            base = base * (1 - g) + np.array([20, 90, 35], dtype=np.float32) * g
            base *= VIG
            base *= fade_at(t, 24.5, eyes_end)
        elif t < 24.5 and t >= 19.5:
            u = ease((t - 19.5) / 5.0)
            z = lerp(1.0, 1.22, u)
            base = np.array(cam_crop(SH["disp"], lerp(0.47, 0.50, u), lerp(0.5, 0.48, u), z), dtype=np.float32)
            base *= VIG
            base *= fade_at(t, 19.5, 24.5)
        elif t < 19.5 and t >= 12.5:
            u = ease((t - 12.5) / 7.0)
            z = lerp(1.04, 1.16, u)
            base = np.array(cam_crop(SH["sci"], lerp(0.55, 0.44, u), 0.5, z), dtype=np.float32)
            base *= VIG
            base *= fade_at(t, 12.5, 19.5)
        elif t < 12.5:
            u = ease((t - 5.0) / 7.5)
            z = lerp(1.0, 1.18, u)
            base = np.array(cam_crop(SH["lab"], 0.5, lerp(0.56, 0.5, u), z), dtype=np.float32)
            base *= VIG
            base *= fade_at(t, 5.0, 12.5)
        else:
            base = np.array(end_card, dtype=np.float32)
            m = min((t - eyes_end) / 0.5, 1.0)
            base *= max(m, 0)
        # subtitles
        for a, b, sim in sub_imgs:
            if a <= t < b:
                sa = np.array(sim)
                al = (sa[:, :, 3:4] / 255.0)
                x0 = (W - sa.shape[1]) // 2; y0 = H - sa.shape[0] - 70
                reg = base[y0:y0 + sa.shape[0], x0:x0 + sa.shape[1], :]
                base[y0:y0 + sa.shape[0], x0:x0 + sa.shape[1], :] = reg * (1 - al) + sa[:, :, :3] * al
                break
        enc.stdin.write(np.clip(base, 0, 255).astype(np.uint8).tobytes())
        if fr % 120 == 0:
            print(f"frame {fr}/{TOTAL_FRAMES}")
    enc.stdin.close(); enc.wait()
    print("video encoded")

    # -------- audio mixes --------
    sfx = build_sfx(T)
    for name, narr in (("A", narrA), ("B", narrB)):
        mix = sfx.copy()
        add(mix, narr, NSTART, 1.0)
        # normalize
        peak = np.max(np.abs(mix))
        mix = mix / peak * 0.85
        mi = (mix * 32767).astype(np.int16)
        with wave.open(f"{ROOT}/audio/_mix_{name}.wav", "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(mi.tobytes())
        subprocess.run([FF, "-y", "-i", f"{ROOT}/video/_video_only.mp4",
                        "-i", f"{ROOT}/audio/_mix_{name}.wav",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        f"{ROOT}/video/preview_chast1_take{name}.mp4"],
                       check=True, capture_output=True)
        print("muxed", name)

if __name__ == "__main__":
    main()
