#!/usr/bin/env python3
"""ТРЕТЬ ЖИЗНИ — превью 60с, 1920x1080@30. Без 3D-движка, покадровая 2D-анимация."""
from __future__ import annotations

import argparse
import math
import os
import struct
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path("/home/user/prod")
ART = ROOT / "art"
AUD = ROOT / "audio"
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

FFMPEG = "/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"

W, H, FPS = 1920, 1080, 30
SCALE = 1.75  # plate upscale for Ken Burns
PLATE_W, PLATE_H = int(1376 * SCALE), int(768 * SCALE)  # 2408 x 1344

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_HAND = str(ROOT / "fonts" / "BadScript-Regular.ttf")
FONT_HAND2 = str(ROOT / "fonts" / "MarckScript-Regular.ttf")

# Left-page quad on the ORIGINAL 1376x768 diary plate (TL, TR, BR, BL)
PAGE_QUAD_ORIG = np.array(
    [[292.0, 388.0], [572.0, 352.0], [548.0, 528.0], [248.0, 518.0]],
    dtype=np.float32,
)
NIB_ORIG = np.array([760.0, 478.0], dtype=np.float32)

DIARY_LINES = [
    "Я перестал спать",
    "три недели назад.",
    "Не из-за формулы.",
    "Из-за того, что",
    "формула нам показала.",
]

TYPE_LINES = [
    "ПРОЕКТ „БЕССОННИЦА“ // СЕКТОР Б, ЛАБ. №3",
    "ДНЕВНИК ДОКТОРА М. ВЕТРОВА",
    "ПОСЛЕДНЯЯ ЗАПИСЬ",
]

VO = [
    # file, duration, subtitle
    ("vetrov_01.mp3", 7.445, "Я перестал спать три недели назад.\nНе из-за формулы. Из-за того, что формула нам показала."),
    ("vetrov_02.mp3", 5.016, "Сектор Б, лаборатория три.\nЗдесь мы обещали вернуть людям треть жизни."),
    ("vetrov_03.mp3", 7.758, "Объект номер один — Даниэл Кро. Наёмник.\nПодписал контракт ради денег, остался из любопытства."),
    ("vetrov_04.mp3", 6.348, "Зет-ноль-один отключает сон.\nТело просто перестаёт платить за простой."),
    ("vetrov_05.mp3", 6.217, "После инъекции Кро улыбнулся и сказал:\n«я наконец выспался». Никто не смеялся."),
    ("vetrov_06.mp3", 7.706, "На третий день я перечитал протокол испытаний.\nЦифры были идеальны. Это и пугало."),
]


def ease_in_out(t: float) -> float:
    t = float(np.clip(t, 0.0, 1.0))
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def ease_out(t: float) -> float:
    t = float(np.clip(t, 0.0, 1.0))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def load_plate(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    im = im.resize((PLATE_W, PLATE_H), Image.Resampling.LANCZOS)
    return np.asarray(im)


def kenburns(plate: np.ndarray, t: float, z0: float, z1: float, p0, p1) -> np.ndarray:
    """t in [0,1], zoom >=1, pan anchors as (cx, cy) in 0-1 of plate."""
    ph, pw = plate.shape[:2]
    z = lerp(z0, z1, ease_in_out(t))
    cx = lerp(p0[0], p1[0], ease_in_out(t)) * pw
    cy = lerp(p0[1], p1[1], ease_in_out(t)) * ph
    cw, ch = W / z, H / z
    x0 = int(np.clip(cx - cw / 2, 0, pw - cw))
    y0 = int(np.clip(cy - ch / 2, 0, ph - ch))
    x1 = min(pw, x0 + int(round(cw)))
    y1 = min(ph, y0 + int(round(ch)))
    crop = plate[y0:y1, x0:x1]
    if crop.shape[1] != W or crop.shape[0] != H:
        crop = cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR)
    return crop


def overlay_rgba(base: np.ndarray, overlay: np.ndarray, x=0, y=0) -> np.ndarray:
    h, w = overlay.shape[:2]
    bh, bw = base.shape[:2]
    if x >= bw or y >= bh or x + w <= 0 or y + h <= 0:
        return base
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(bw, x + w), min(bh, y + h)
    ox0, oy0 = x0 - x, y0 - y
    sl = overlay[oy0:oy0 + (y1 - y0), ox0:ox0 + (x1 - x0)]
    if sl.shape[2] == 3:
        base[y0:y1, x0:x1] = sl
        return base
    a = sl[:, :, 3:4].astype(np.float32) / 255.0
    rgb = sl[:, :, :3].astype(np.float32)
    dst = base[y0:y1, x0:x1].astype(np.float32)
    base[y0:y1, x0:x1] = np.clip(rgb * a + dst * (1 - a), 0, 255).astype(np.uint8)
    return base


def multiply_ink(base: np.ndarray, warped_rgba: np.ndarray) -> np.ndarray:
    a = warped_rgba[:, :, 3].astype(np.float32) / 255.0
    if a.max() < 1e-4:
        return base
    ink = warped_rgba[:, :, :3].astype(np.float32) / 255.0
    img = base.astype(np.float32)
    aa = a[:, :, None]
    # darken paper where ink is
    mixed = img * (1.0 - aa * 0.82) * (1.0 - aa * (1.0 - ink) * 0.55)
    mixed = mixed + img * 0.0
    out = img * (1 - aa) + mixed * aa
    return np.clip(out, 0, 255).astype(np.uint8)


def film_grain(frame: np.ndarray, rng: np.random.Generator, strength=7.0) -> np.ndarray:
    g = rng.normal(0, strength, (H, W, 1)).astype(np.float32)
    return np.clip(frame.astype(np.float32) + g, 0, 255).astype(np.uint8)


def vignette(frame: np.ndarray, amount=0.42) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    r = np.sqrt(((xx - cx) / (W * 0.72)) ** 2 + ((cy - yy) / (H * 0.78)) ** 2)
    v = np.clip(1.0 - amount * np.clip(r ** 2.1, 0, 1), 0.45, 1.0)
    return np.clip(frame.astype(np.float32) * v[:, :, None], 0, 255).astype(np.uint8)


def dust_layer(t: float, rng_seed: int, n=90, color=(255, 230, 180), speed=18.0) -> np.ndarray:
    rng = np.random.default_rng(rng_seed)
    layer = np.zeros((H, W, 4), dtype=np.uint8)
    xs = rng.random(n)
    ys = rng.random(n)
    sz = rng.uniform(1.0, 3.2, n)
    ph = rng.random(n) * 1000
    sp = rng.uniform(0.4, 1.4, n)
    for i in range(n):
        x = int((xs[i] + 0.015 * math.sin(t * 0.7 + ph[i])) % 1.0 * W)
        y = int((ys[i] - t * 0.012 * sp[i]) % 1.0 * H)
        a = int(70 + 80 * (0.5 + 0.5 * math.sin(t * 2.2 + ph[i])))
        cv2.circle(layer, (x, y), int(sz[i]), (*color, a), -1, lineType=cv2.LINE_AA)
    return layer


def lamp_flicker(frame: np.ndarray, t: float, warm=True) -> np.ndarray:
    k = 1.0 + 0.027 * math.sin(t * 8.3) + 0.013 * math.sin(t * 21.7) + 0.008 * math.sin(t * 3.1)
    img = frame.astype(np.float32) * k
    if warm:
        img[:, :, 0] *= 1.0 + 0.015 * math.sin(t * 5.2)  # R
        img[:, :, 2] *= 0.995
    return np.clip(img, 0, 255).astype(np.uint8)


def draw_subtitles(frame: np.ndarray, text: str, alpha: float, font: ImageFont.FreeTypeFont) -> np.ndarray:
    if alpha <= 0.01 or not text:
        return frame
    im = Image.fromarray(frame)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    lines = text.split("\n")
    # measure
    bboxes = [d.textbbox((0, 0), ln, font=font) for ln in lines]
    heights = [b[3] - b[1] for b in bboxes]
    widths = [b[2] - b[0] for b in bboxes]
    total_h = sum(heights) + 8 * (len(lines) - 1)
    y = H - 78 - total_h
    a = int(255 * np.clip(alpha, 0, 1))
    for ln, tw, th in zip(lines, widths, heights):
        x = (W - tw) // 2
        # shadow / outline
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            d.text((x + dx, y + dy), ln, font=font, fill=(0, 0, 0, a))
        d.text((x, y), ln, font=font, fill=(236, 232, 220, a))
        y += th + 8
    out = Image.alpha_composite(im.convert("RGBA"), ov)
    return np.asarray(out.convert("RGB"))


# ---------------------------------------------------------------------------
# Typewriter schedule + drawing
# ---------------------------------------------------------------------------

def build_type_schedule(seed=7):
    rng = np.random.default_rng(seed)
    events = []  # (t, kind, char, line_idx, col)
    t = 0.55
    for li, line in enumerate(TYPE_LINES):
        col = 0
        for ch in line:
            dt = 0.055 if ch == " " else rng.uniform(0.068, 0.095)
            if ch in ".,/№":
                dt += 0.03
            events.append((t, "key", ch, li, col))
            t += dt
            col += 1
        events.append((t, "cr", "\n", li, col))
        t += 0.42
        if li == 0:
            events.append((t, "bell", None, li, col))
            t += 0.18
        elif li == 2:
            events.append((t, "bell", None, li, col))
            t += 0.12
    t_end = t + 0.85
    return events, t_end


def typewriter_frame(t: float, events) -> np.ndarray:
    # black phosphor CRT
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    # very dark green noise floor
    rng = np.random.default_rng(int(t * FPS) + 11)
    floor = rng.integers(0, 7, (H, W), dtype=np.uint8)
    frame[:, :, 1] = floor

    visible = [ev for ev in events if ev[0] <= t and ev[1] == "key"]
    # last flash
    flash_ch = None
    for ev in reversed(events):
        if ev[1] == "key" and 0 <= t - ev[0] < 0.07:
            flash_ch = ev
            break

    font = ImageFont.truetype(FONT_MONO, 44)
    font_sm = ImageFont.truetype(FONT_MONO, 18)
    im = Image.fromarray(frame)
    d = ImageDraw.Draw(im)
    header = "SECTOR-B / LAB.№3 / CLASSIFIED"
    d.text((160, 250), header, font=font_sm, fill=(28, 90, 48))

    # reconstruct lines
    lines = [""] * 3
    for ev in visible:
        _, _, ch, li, _ = ev
        if li < 3:
            lines[li] += ch

    y0 = 340
    lh = 72
    x0 = 160
    col_g = (156, 255, 140)
    dim = (70, 160, 80)
    for i, ln in enumerate(lines):
        fill = col_g
        d.text((x0, y0 + i * lh), ln, font=font, fill=fill)

    # cursor
    last_line = 0
    for i, ln in enumerate(lines):
        if ln:
            last_line = i
    if lines[0] or t > 0.5:
        # if all three complete, stay on last
        if lines[2]:
            last_line = 2
        elif lines[1]:
            last_line = 1
        cx = x0 + font.getlength(lines[last_line])
        cy = y0 + last_line * lh
        on = (int(t * 3.2) % 2) == 0 or (flash_ch is not None)
        if on:
            d.rectangle((cx + 4, cy + 8, cx + 26, cy + 48), fill=col_g)

    frame = np.asarray(im).astype(np.float32)

    # per-key punch bloom
    if flash_ch is not None:
        k = 1.0 + 0.35 * (1.0 - (t - flash_ch[0]) / 0.07)
        frame[:, :, 1] *= k
        frame[:, :, 0] *= 0.92 + 0.08 * k
        frame[:, :, 2] *= 0.85

    # bloom
    small = cv2.resize(frame, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(small, (0, 0), 3.2)
    blur = cv2.resize(blur, (W, H), interpolation=cv2.INTER_LINEAR)
    frame = np.clip(frame + blur * 0.55, 0, 255)

    # scanlines
    scan = np.ones((H, 1, 1), dtype=np.float32)
    scan[1::2] = 0.72
    # rolling bar
    bar_y = int((t * 140) % (H + 80)) - 40
    for dy in range(-18, 19):
        yy = bar_y + dy
        if 0 <= yy < H:
            scan[yy] *= 1.0 + 0.28 * (1 - abs(dy) / 18)
    frame *= scan

    # CRT vignette
    frame = vignette(np.clip(frame, 0, 255).astype(np.uint8), 0.55).astype(np.float32)
    # slight horizontal jitter on key
    if flash_ch is not None:
        j = int(round(1.2 * math.sin((t - flash_ch[0]) * 90)))
        frame = np.roll(frame, j, axis=1)
    return np.clip(frame, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Diary handwriting
# ---------------------------------------------------------------------------

class DiaryWriter:
    def __init__(self):
        self.font = ImageFont.truetype(FONT_HAND, 78)
        self.canvas_w, self.canvas_h = 1100, 820
        self.full = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.full)
        self.line_info = []  # list of list of (x0, x1, y)
        y = 70
        ink = (52, 34, 22, 255)
        for line in DIARY_LINES:
            x = 40
            chars = []
            # draw whole line into full
            d.text((x, y), line, font=self.font, fill=ink)
            # per-char widths
            acc = x
            for ch in line:
                w = d.textlength(ch, font=self.font)
                chars.append((acc, acc + w, y, ch))
                acc += w
            self.line_info.append(chars)
            y += 145
        self.full_np = np.asarray(self.full)
        self.n_chars = sum(len(L) for L in self.line_info)
        self.quad = PAGE_QUAD_ORIG * SCALE  # on upscaled plate
        self.src = np.array(
            [
                [0, 0],
                [self.canvas_w, 0],
                [self.canvas_w, self.canvas_h],
                [0, self.canvas_h],
            ],
            dtype=np.float32,
        )
        xs, ys = self.quad[:, 0], self.quad[:, 1]
        self.bx0 = max(0, int(xs.min()) - 6)
        self.by0 = max(0, int(ys.min()) - 6)
        self.bx1 = int(xs.max()) + 6
        self.by1 = int(ys.max()) + 6
        quad_local = self.quad - np.array([self.bx0, self.by0], dtype=np.float32)
        self.M_local = cv2.getPerspectiveTransform(self.src, quad_local.astype(np.float32))
        self.bw = self.bx1 - self.bx0
        self.bh = self.by1 - self.by0

    def overlay_on_plate(self, plate: np.ndarray, progress: float) -> np.ndarray:
        """progress 0..1 = fraction of characters written."""
        n = max(0.0, progress) * self.n_chars
        mask = np.zeros((self.canvas_h, self.canvas_w), dtype=np.uint8)
        seen = 0
        for chars in self.line_info:
            for x0, x1, y, ch in chars:
                seen += 1
                if seen <= int(n):
                    cv2.rectangle(mask, (int(x0) - 2, int(y) - 10), (int(x1) + 6, int(y) + 110), 255, -1)
                elif seen == int(n) + 1:
                    frac = n - int(n)
                    x = int(lerp(x0, x1, frac))
                    cv2.rectangle(mask, (int(x0) - 2, int(y) - 10), (x + 2, int(y) + 110), 255, -1)
                    break
            else:
                continue
            break
        mask = cv2.GaussianBlur(mask, (0, 0), 3.5)
        rgba = self.full_np.copy()
        rgba[:, :, 3] = (rgba[:, :, 3].astype(np.float32) * (mask.astype(np.float32) / 255.0)).astype(np.uint8)
        warped = cv2.warpPerspective(
            rgba,
            self.M_local,
            (self.bw, self.bh),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )
        if warped.ndim == 2:
            warped = cv2.cvtColor(warped, cv2.COLOR_GRAY2BGRA)
        if warped.shape[2] == 3:
            z = np.zeros(warped.shape[:2], dtype=np.uint8)
            warped = np.dstack([warped, z])
        y0 = self.by0
        x0 = self.bx0
        y1 = min(plate.shape[0], self.by1)
        x1 = min(plate.shape[1], self.bx1)
        roi = plate[y0:y1, x0:x1]
        wh, ww = roi.shape[:2]
        piece = multiply_ink(roi, warped[:wh, :ww])
        out = plate.copy()
        out[y0:y1, x0:x1] = piece
        return out


def local_hand_warp(plate: np.ndarray, t: float, write_u: float) -> np.ndarray:
    """Displace the hand/pen region along a writing path."""
    ph, pw = plate.shape[:2]
    nib = NIB_ORIG * SCALE
    dx = (8.0 + 22.0 * write_u) * math.sin(write_u * math.pi) + 1.6 * math.sin(t * 11.0)
    dy = 16.0 * write_u + 2.2 * math.sin(t * 13.5 + 0.4)
    rad = int(340 * SCALE / 1.75)
    cx, cy = int(nib[0]), int(nib[1])
    x0 = max(0, cx - rad)
    y0 = max(0, cy - int(rad * 0.85))
    x1 = min(pw, cx + int(rad * 1.35))
    y1 = min(ph, cy + int(rad * 0.95))
    roi = plate[y0:y1, x0:x1]
    rh, rw = roi.shape[:2]
    if rh < 8 or rw < 8:
        return plate
    yy, xx = np.mgrid[0:rh, 0:rw].astype(np.float32)
    gx = xx + x0 - cx
    gy = yy + y0 - cy
    fall = np.exp(-(gx * gx + gy * gy) / (2 * (rad * 0.55) ** 2)).astype(np.float32)
    map_x = (xx + dx * fall).astype(np.float32)
    map_y = (yy + dy * fall).astype(np.float32)
    warped = cv2.remap(roi, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = plate.copy()
    out[y0:y1, x0:x1] = warped
    spark = out.astype(np.float32)
    sx = int(np.clip(cx + dx, 0, pw - 1))
    sy = int(np.clip(cy + dy, 0, ph - 1))
    overlay = np.zeros_like(spark)
    cv2.circle(overlay, (sx, sy), 7, (40, 28, 18), -1, lineType=cv2.LINE_AA)
    overlay = cv2.GaussianBlur(overlay, (0, 0), 3.5)
    a = np.clip(overlay.max(axis=2) / 40.0, 0, 0.45)[:, :, None]
    spark = spark * (1 - a * 0.55)
    return np.clip(spark, 0, 255).astype(np.uint8)


def pulse_green(frame: np.ndarray, t: float, amount=0.12) -> np.ndarray:
    img = frame.astype(np.float32)
    k = 1.0 + amount * (0.5 + 0.5 * math.sin(t * 3.4))
    # boost near-green pixels
    g = img[:, :, 1]
    mask = (g > 90) & (g > img[:, :, 0] * 1.05) & (g > img[:, :, 2] * 1.05)
    m = mask.astype(np.float32)[:, :, None]
    img = img * (1 - m) + img * k * m
    img[:, :, 1] = np.clip(img[:, :, 1] + m[:, :, 0] * 8 * (k - 1) * 20, 0, 255)
    return np.clip(img, 0, 255).astype(np.uint8)


def crt_live(frame: np.ndarray, t: float) -> np.ndarray:
    img = frame.astype(np.float32)
    scan = np.ones((H, 1, 1), dtype=np.float32)
    scan[::2] *= 0.90
    img *= scan
    bar_y = int((t * 90) % (H + 60)) - 30
    for dy in range(-12, 13):
        yy = bar_y + dy
        if 0 <= yy < H:
            img[yy] *= 1.0 + 0.22 * (1 - abs(dy) / 12)
    # phosphor bloom on green
    g = img[:, :, 1]
    small = cv2.resize(g, (W // 5, H // 5))
    blur = cv2.GaussianBlur(small, (0, 0), 2.8)
    blur = cv2.resize(blur, (W, H))
    img[:, :, 1] = np.clip(img[:, :, 1] + blur * 0.18, 0, 255)
    img[:, :, 0] = np.clip(img[:, :, 0] + blur * 0.04, 0, 255)
    return np.clip(img, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def key_click(rng, sr):
    n = int(0.032 * sr)
    t = np.arange(n) / sr
    noise = rng.normal(0, 1, n) * np.exp(-t * 220)
    f = rng.uniform(1700, 3100)
    click = np.sin(2 * np.pi * f * t) * np.exp(-t * 85)
    thud = np.sin(2 * np.pi * rng.uniform(80, 150) * t) * np.exp(-t * 55)
    sig = 0.42 * noise + 0.55 * click + 0.35 * thud
    # tiny stereo later
    return (sig * rng.uniform(0.65, 1.0)).astype(np.float32)


def carriage(rng, sr):
    n = int(0.16 * sr)
    t = np.arange(n) / sr
    scrape = rng.normal(0, 1, n)
    # band-ish by simple leaky
    scrape = np.convolve(scrape, np.ones(12) / 12, mode="same")
    env = np.exp(-t * 8) * (t * 18)
    env = np.clip(env, 0, 1)
    bump = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 28) * 0.5
    return (0.28 * scrape * env + bump).astype(np.float32)


def bell_ding(sr):
    n = int(0.55 * sr)
    t = np.arange(n) / sr
    sig = 0.55 * np.sin(2 * np.pi * 1865 * t) * np.exp(-t * 5.5)
    sig += 0.28 * np.sin(2 * np.pi * 2480 * t) * np.exp(-t * 7.0)
    sig += 0.12 * np.sin(2 * np.pi * 3720 * t) * np.exp(-t * 10)
    return sig.astype(np.float32)


def decode_mp3(path: Path, sr=48000) -> np.ndarray:
    wav = OUT / (path.stem + "_tmp.wav")
    subprocess.check_call(
        [FFMPEG, "-y", "-i", str(path), "-ar", str(sr), "-ac", "2", "-f", "wav", str(wav)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with wave.open(str(wav), "rb") as w:
        n, c, s = w.getnframes(), w.getnchannels(), w.getframerate()
        raw = w.readframes(n)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if c == 2:
            data = data.reshape(-1, 2)
        else:
            data = np.stack([data, data], axis=1)
    wav.unlink(missing_ok=True)
    return data


def mix_audio(events, timeline, total_s, sr=48000) -> Path:
    n = int(total_s * sr) + sr
    mix = np.zeros((n, 2), dtype=np.float32)
    rng = np.random.default_rng(23)

    # room tone — ventilation air, not a musical drone
    bn = np.cumsum(rng.normal(0, 1, n))
    bn = bn - bn.mean()
    bn = bn / (np.max(np.abs(bn)) + 1e-9)
    # extra hiss
    hiss = rng.normal(0, 1, n)
    # very slow amplitude wander
    t = np.arange(n) / sr
    wander = 0.85 + 0.15 * np.sin(2 * np.pi * 0.07 * t)
    room = (0.045 * bn + 0.012 * hiss) * wander
    mix[:, 0] += room
    mix[:, 1] += room * 0.97 + 0.003 * np.roll(hiss, 17)

    # typewriter events
    for ev in events:
        te, kind, ch, *_ = ev
        i = int(te * sr)
        if kind == "key":
            sig = key_click(rng, sr)
        elif kind == "cr":
            sig = carriage(rng, sr) * 0.85
        elif kind == "bell":
            sig = bell_ding(sr) * 0.55
        else:
            continue
        j = min(n, i + len(sig))
        if i >= n or j <= i:
            continue
        pan = rng.uniform(-0.12, 0.12)
        L, R = 0.5 - pan, 0.5 + pan
        mix[i:j, 0] += sig[: j - i] * L * 0.95
        mix[i:j, 1] += sig[: j - i] * R * 0.95

    # pen scratch during diary shot
    sh02 = next(s for s in timeline if s["name"] == "sh02")
    a0, a1 = sh02["t0"] + 0.35, sh02["t1"] - 0.4
    i0, i1 = int(a0 * sr), int(a1 * sr)
    nn = i1 - i0
    scratch = rng.normal(0, 1, nn).astype(np.float32)
    # crude high-pass
    scratch = scratch - np.convolve(scratch, np.ones(30) / 30, mode="same")
    env = np.ones(nn, dtype=np.float32)
    fade = int(0.2 * sr)
    env[:fade] *= np.linspace(0, 1, fade)
    env[-fade:] *= np.linspace(1, 0, fade)
    # writing modulation
    tt = np.arange(nn) / sr
    env *= 0.55 + 0.45 * (0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * tt))
    pen = scratch * env * 0.028
    mix[i0:i1, 0] += pen
    mix[i0:i1, 1] += pen * 0.92

    # VO
    for s in timeline:
        if not s.get("vo"):
            continue
        fn, _dur, _sub = s["vo"]
        vo = decode_mp3(AUD / fn, sr)
        i = int(s["vo_t"] * sr)
        j = min(n, i + len(vo))
        mix[i:j] += vo[: j - i] * 1.05

    # fade in / out
    fi, fo = int(0.12 * sr), int(0.9 * sr)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]

    peak = np.max(np.abs(mix)) + 1e-9
    mix *= 0.89 / peak
    mix = np.clip(mix, -1, 1)
    path = OUT / "preview_mix.wav"
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print("audio", path, "peak", float(peak), "dur", n / sr)
    return path


# ---------------------------------------------------------------------------
# Timeline + renderer
# ---------------------------------------------------------------------------

def build_timeline(type_end: float):
    xf = 0.62
    sh01_end = max(8.9, type_end)
    # VO starts
    t = sh01_end + 0.35
    shots = []
    shots.append(dict(name="sh01", t0=0.0, t1=sh01_end, kind="typewriter", vo=None, vo_t=None))

    # diary + vo1
    vo = VO[0]
    t0 = sh01_end - xf
    vo_t = t0 + 1.15
    t1 = vo_t + vo[1] + 1.05
    shots.append(dict(name="sh02", t0=t0, t1=t1, kind="diary", vo=vo, vo_t=vo_t))

    vo = VO[1]
    t0 = shots[-1]["t1"] - xf
    vo_t = t0 + 0.85
    t1 = vo_t + vo[1] + 1.15
    shots.append(dict(name="sh03", t0=t0, t1=t1, kind="lab", vo=vo, vo_t=vo_t))

    vo = VO[2]
    t0 = shots[-1]["t1"] - xf
    vo_t = t0 + 0.75
    t1 = vo_t + vo[1] + 1.05
    shots.append(dict(name="sh04", t0=t0, t1=t1, kind="kro", vo=vo, vo_t=vo_t))

    vo = VO[3]
    t0 = shots[-1]["t1"] - xf
    vo_t = t0 + 0.7
    t1 = vo_t + vo[1] + 1.0
    shots.append(dict(name="sh05", t0=t0, t1=t1, kind="ampoule", vo=vo, vo_t=vo_t))

    vo = VO[4]
    t0 = shots[-1]["t1"] - xf
    vo_t = t0 + 0.7
    t1 = vo_t + vo[1] + 1.15
    shots.append(dict(name="sh06", t0=t0, t1=t1, kind="bay", vo=vo, vo_t=vo_t))

    vo = VO[5]
    t0 = shots[-1]["t1"] - xf
    vo_t = t0 + 0.7
    t1 = max(60.0, vo_t + vo[1] + 1.05)
    shots.append(dict(name="sh07", t0=t0, t1=t1, kind="crt", vo=vo, vo_t=vo_t))

    total = shots[-1]["t1"]
    print("TIMELINE total", round(total, 3))
    for s in shots:
        print(
            f"  {s['name']} {s['t0']:.2f}-{s['t1']:.2f} ({s['t1']-s['t0']:.2f}s)",
            f"vo@{s['vo_t']:.2f}" if s["vo_t"] else "",
        )
    return shots, total


class Engine:
    def __init__(self):
        print("loading plates…")
        self.diary = load_plate(ART / "sh02_diary_empty.png")
        self.diary_b = load_plate(ART / "sh02_hand_l3.png") if (ART / "sh02_hand_l3.png").exists() else self.diary
        self.lab = load_plate(ART / "sh03_lab_ug.png")
        self.kro = load_plate(ART / "sh04_kro.png")
        self.amp = load_plate(ART / "sh05_ampoule.png")
        self.bay = load_plate(ART / "sh06_bay.png")
        self.crt = load_plate(ART / "sh07_crt.png")
        self.writer = DiaryWriter()
        self.font_sub = ImageFont.truetype(FONT_SANS, 34)
        print("plates ready", self.diary.shape)

    def render_shot(self, shot, t_abs: float) -> np.ndarray:
        u = (t_abs - shot["t0"]) / max(1e-6, shot["t1"] - shot["t0"])
        u = float(np.clip(u, 0, 1))
        kind = shot["kind"]
        if kind == "typewriter":
            return typewriter_frame(t_abs, self.events)
        if kind == "diary":
            return self.shot_diary(u, t_abs, shot)
        if kind == "lab":
            return self.shot_lab(u, t_abs, shot)
        if kind == "kro":
            return self.shot_kro(u, t_abs, shot)
        if kind == "ampoule":
            return self.shot_amp(u, t_abs, shot)
        if kind == "bay":
            return self.shot_bay(u, t_abs, shot)
        if kind == "crt":
            return self.shot_crt(u, t_abs, shot)
        return np.zeros((H, W, 3), dtype=np.uint8)

    def shot_diary(self, u, t, shot):
        # blend two nearly-equal plates for micro-life
        k = 0.5 + 0.5 * math.sin(t * 1.7)
        plate = cv2.addWeighted(self.diary, 1 - 0.18 * k, self.diary_b, 0.18 * k, 0)
        # writing progress: start 0.08, end 0.86 of shot
        wp = ease_out(np.clip((u - 0.06) / 0.80, 0, 1))
        plate = self.writer.overlay_on_plate(plate, wp)
        plate = local_hand_warp(plate, t, wp)
        frame = kenburns(plate, u, 1.04, 1.16, (0.46, 0.58), (0.42, 0.54))
        frame = lamp_flicker(frame, t, warm=True)
        dust = dust_layer(t, 99, n=110, color=(255, 220, 160))
        frame = overlay_rgba(frame, dust)
        frame = vignette(frame, 0.33)
        return frame

    def shot_lab(self, u, t, shot):
        frame = kenburns(self.lab, u, 1.02, 1.10, (0.38, 0.52), (0.62, 0.48))
        frame = pulse_green(frame, t, 0.10)
        frame = lamp_flicker(frame, t * 0.85, warm=False)
        dust = dust_layer(t, 44, n=70, color=(200, 220, 230))
        frame = overlay_rgba(frame, dust)
        frame = vignette(frame, 0.36)
        return frame

    def shot_kro(self, u, t, shot):
        frame = kenburns(self.kro, u, 1.05, 1.22, (0.48, 0.46), (0.50, 0.40))
        # breathing — always scale UP then center-crop so shape stays 1080p
        k = 1.012 + 0.010 * math.sin(t * 2.4)
        h, w = frame.shape[:2]
        nh, nw = int(round(h * k)), int(round(w * k))
        big = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        y0 = max(0, (nh - h) // 2)
        x0 = max(0, (nw - w) // 2)
        frame = big[y0 : y0 + h, x0 : x0 + w]
        if frame.shape[0] != H or frame.shape[1] != W:
            frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_LINEAR)
        # glass highlight drift
        ov = np.zeros((H, W, 4), dtype=np.uint8)
        gx = int(200 + 80 * math.sin(t * 0.6))
        cv2.rectangle(ov, (gx, 0), (gx + 90, H), (180, 220, 255, 18), -1)
        ov = cv2.GaussianBlur(ov, (0, 0), 18)
        frame = overlay_rgba(frame, ov)
        dust = dust_layer(t, 12, n=40, color=(180, 210, 220))
        frame = overlay_rgba(frame, dust)
        frame = vignette(frame, 0.40)
        return frame

    def shot_amp(self, u, t, shot):
        frame = kenburns(self.amp, u, 1.06, 1.18, (0.48, 0.48), (0.52, 0.46))
        # green caustic pulse
        k = 1.0 + 0.16 * (0.5 + 0.5 * math.sin(t * 4.1))
        img = frame.astype(np.float32)
        g = img[:, :, 1]
        mask = (g > 80) & (img[:, :, 1] > img[:, :, 0] * 1.1)
        m = mask.astype(np.float32)[:, :, None]
        img[:, :, 1] = np.clip(img[:, :, 1] * (1 - m[:, :, 0]) + img[:, :, 1] * k * m[:, :, 0], 0, 255)
        img[:, :, 0] = np.clip(img[:, :, 0] + m[:, :, 0] * 12 * (k - 1) * 8, 0, 255)
        # bloom
        small = cv2.resize(img, (W // 4, H // 4))
        blur = cv2.GaussianBlur(small, (0, 0), 4.0)
        blur = cv2.resize(blur, (W, H))
        img = np.clip(img + blur * 0.12 * (k - 0.9), 0, 255)
        frame = img.astype(np.uint8)
        # bubbles
        rng = np.random.default_rng(5)
        bub = np.zeros((H, W, 4), dtype=np.uint8)
        for i in range(14):
            bx = int(W * 0.46 + rng.uniform(-40, 50))
            by = int((H * 0.62 - (t * 22 + i * 17) * 3) % int(H * 0.5) + H * 0.28)
            cv2.circle(bub, (bx, by), rng.integers(2, 5), (180, 255, 160, 90), 1, lineType=cv2.LINE_AA)
        frame = overlay_rgba(frame, bub)
        frame = vignette(frame, 0.38)
        return frame

    def shot_bay(self, u, t, shot):
        # pan from Kro (left) toward Vetrov (right) — the glance
        frame = kenburns(self.bay, u, 1.04, 1.14, (0.40, 0.50), (0.60, 0.48))
        frame = lamp_flicker(frame, t, warm=False)
        dust = dust_layer(t, 71, n=55, color=(210, 220, 230))
        frame = overlay_rgba(frame, dust)
        frame = pulse_green(frame, t, 0.07)
        frame = vignette(frame, 0.34)
        return frame

    def shot_crt(self, u, t, shot):
        frame = kenburns(self.crt, u, 1.08, 1.20, (0.48, 0.50), (0.52, 0.48))
        frame = crt_live(frame, t)
        frame = pulse_green(frame, t, 0.14)
        frame = vignette(frame, 0.46)
        return frame

    def subtitle_alpha(self, shot, t):
        if not shot.get("vo"):
            return 0.0, ""
        t0 = shot["vo_t"]
        t1 = t0 + shot["vo"][1]
        if t < t0 or t > t1 + 0.15:
            return 0.0, shot["vo"][2]
        fade = 0.22
        if t < t0 + fade:
            a = (t - t0) / fade
        elif t > t1 - fade:
            a = max(0.0, (t1 - t) / fade)
        else:
            a = 1.0
        return a, shot["vo"][2]


def crossfade(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    k = float(np.clip(k, 0, 1))
    k = ease_in_out(k)
    return cv2.addWeighted(a, 1 - k, b, k, 0)


def render(args):
    events, type_end = build_type_schedule()
    timeline, total = build_timeline(type_end)
    eng = Engine()
    eng.events = events

    if args.dump_frame is not None:
        t = args.dump_frame / FPS if args.dump_frame >= 50 else float(args.dump_frame)
        # if small number without --as-time, treat as seconds if < 100 else frame
        if args.dump_frame < 90:
            t = float(args.dump_frame)
        else:
            t = args.dump_frame / FPS
        frame = compose_frame(eng, timeline, t)
        p = OUT / f"dump_{t:.2f}.jpg"
        Image.fromarray(frame).save(p, quality=92)
        print("dumped", p)
        return

    audio_path = mix_audio(events, timeline, total)

    start = float(args.start)
    duration = float(args.duration) if args.duration else (total - start)
    t0 = start
    t1 = min(total, start + duration)
    nframes = int(round((t1 - t0) * FPS))
    out_mp4 = Path(args.out)

    log_path = OUT / "ffmpeg_preview.log"
    cmd = [
        FFMPEG, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "pipe:0",
        "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "320k",
        "-t", f"{(t1 - t0):.3f}",
        str(out_mp4),
    ]
    if t0 > 0.001:
        cmd = [
            FFMPEG, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "pipe:0",
            "-ss", f"{t0:.3f}", "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "320k",
            "-t", f"{(t1 - t0):.3f}",
            str(out_mp4),
        ]
    print("ffmpeg", " ".join(cmd))
    logf = open(log_path, "wb")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=logf)
    try:
        for i in range(nframes):
            t = t0 + i / FPS
            frame = compose_frame(eng, timeline, t)
            frame = film_grain(frame, np.random.default_rng(1000 + i), strength=4.5)
            proc.stdin.write(np.ascontiguousarray(frame).tobytes())
            if i % 30 == 0:
                print(f"  frame {i}/{nframes}  t={t:.2f}s", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        logf.close()
        print("ffmpeg rc", rc)
        if rc != 0:
            print(log_path.read_text(errors="replace")[-2500:])
            raise SystemExit(rc)
    except BrokenPipeError:
        logf.close()
        print("pipe broken")
        print(log_path.read_text(errors="replace")[-2500:])
        raise
    print("wrote", out_mp4, "size", out_mp4.stat().st_size)


def compose_frame(eng: Engine, timeline, t: float) -> np.ndarray:
    active = [s for s in timeline if s["t0"] <= t < s["t1"]]
    if not active:
        if t >= timeline[-1]["t1"]:
            active = [timeline[-1]]
        else:
            active = [timeline[0]]
    if len(active) == 1:
        fr = eng.render_shot(active[0], t)
        a, sub = eng.subtitle_alpha(active[0], t)
        fr = draw_subtitles(fr, sub, a, eng.font_sub)
        if fr.shape[0] != H or fr.shape[1] != W:
            fr = cv2.resize(fr, (W, H), interpolation=cv2.INTER_LINEAR)
        return fr
    # two shots overlapping — crossfade
    a, b = active[0], active[1]
    if a["t0"] > b["t0"]:
        a, b = b, a
    overlap = min(a["t1"], b["t1"]) - max(a["t0"], b["t0"])
    k = (t - b["t0"]) / max(1e-6, overlap)
    fa = eng.render_shot(a, t)
    fb = eng.render_shot(b, t)
    fr = crossfade(fa, fb, k)
    # subtitles from whoever has VO now
    for s in (a, b):
        al, sub = eng.subtitle_alpha(s, t)
        if al > 0:
            fr = draw_subtitles(fr, sub, al, eng.font_sub)
    if fr.shape[0] != H or fr.shape[1] != W:
        fr = cv2.resize(fr, (W, H), interpolation=cv2.INTER_LINEAR)
    return fr


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dump-frame", type=float, default=None, help="seconds (if <90) or frame index")
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--out", default=str(OUT / "TRET_JIZNI_preview_60s.mp4"))
    args = p.parse_args()
    render(args)


if __name__ == "__main__":
    main()
