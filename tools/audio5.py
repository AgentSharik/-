# -*- coding: utf-8 -*-
"""v5 audio: typing schedule + procedural score (M0->M4) + final mix."""
import numpy as np, json, subprocess, os, imageio_ffmpeg

SR = 44100
FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = os.path.join(os.path.dirname(__file__), "..", "audio", "v5")
OUT = os.path.abspath(OUT)

ACT0_LINES = [
    ("ПРОЕКТ «БЕССОННИЦА» // СЕКТОР Б, ЛАБ. №3", 0.5),
    ("ДНЕВНИК ДОКТОРА М. ВЕТРОВА", 4.6),
    ("ПОСЛЕДНЯЯ ЗАПИСЬ", 7.5),
]
CHAR_DT = 0.085
CRT_LINES = [
    ("ЗАПИСЬ 168.", 13.2),
    ("Я ПЕРЕСТАЛ СПАТЬ", 14.6),
    ("ТРИ НЕДЕЛИ НАЗАД.", 16.4),
]
CRT_DT = 0.09

VO = {  # name: (start, file)
    "vetrov_01": (12.6, "vetrov_01.mp3"),
    "vetrov_02": (22.6, "vetrov_02.mp3"),
    "vetrov_03": (30.3, "vetrov_03.mp3"),
    "artem_01": (44.4, "artem_01.mp3"),
}
SHOTS = [  # key, t0, t1
    ("act0", 0.0, 12.0),
    ("A", 12.0, 22.0),
    ("B", 22.0, 29.7),
    ("C", 29.7, 43.8),
    ("D", 43.8, 58.7),
    ("tail", 58.7, 60.0),
]
SUBS = [
    (12.6, 21.0, "Я перестал спать три недели назад.\nНе из-за формулы. Из-за того, что формула нам показала."),
    (22.6, 28.6, "Сектор Б, лаборатория три.\nЗдесь мы обещали вернуть людям треть жизни."),
    (30.3, 42.7, "Последняя запись. Стена продержалась одиннадцать секунд.\nЕсли это читает кто-то живой — не ищите нас. Ищите, куда оно пошло."),
    (44.4, 57.4, "Врачи не вышли. Что было дальше, я записывал со слов тех, кто вышел.\nВирус уже ехал в колонне эвакуации — внутри инженера Брагина."),
]
TOTAL = 60.0

rng = np.random.default_rng(7)


def key_schedule():
    sched = []
    for txt, t0 in ACT0_LINES:
        t = t0
        for ch in txt:
            sched.append((round(t, 3), 1.0))
            t += CHAR_DT * rng.uniform(0.8, 1.25) + (0.12 if ch == " " else 0)
    for txt, t0 in CRT_LINES:
        t = t0
        for ch in txt:
            sched.append((round(t, 3), 0.35))
            t += CRT_DT * rng.uniform(0.8, 1.25)
    return sched


def one_pole(x, a):
    y = np.empty_like(x)
    acc = 0.0
    # vectorized approx via lfilter-like loop (fast enough at 2.6M samples? use scipy if avail)
    try:
        from scipy.signal import lfilter
        return lfilter([a], [1, a - 1], x)
    except Exception:
        for i in range(len(x)):
            acc += a * (x[i] - acc)
            y[i] = acc
        return y


def keystrokes(sched, total):
    n = int(total * SR)
    buf = np.zeros(n, np.float64)
    for ts, gain in sched:
        s0 = int(ts * SR)
        L = int(0.06 * SR)
        if s0 + L >= n:
            continue
        f = rng.uniform(1700, 2600)
        t = np.arange(L) / SR
        click = np.exp(-t / 0.006) * rng.standard_normal(L) * 0.35
        body = np.exp(-t / 0.018) * np.sin(2 * np.pi * f * t) * 0.5
        thud = np.exp(-t / 0.03) * np.sin(2 * np.pi * 150 * t) * 0.25
        buf[s0:s0 + L] += (click + body + thud) * gain * rng.uniform(0.75, 1.05)
    return buf


def ramp(t, t0, rise=1.5):
    r = np.clip((t - t0) / rise, 0, 1)
    return r * r * (3 - 2 * r)


def music(total):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float64)
    # M0 drone + ventilation
    d = 0.5 * np.sin(2 * np.pi * 41 * t) + 0.35 * np.sin(2 * np.pi * 41.8 * t + 1.0)
    d *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.05 * t)
    white = rng.standard_normal(n)
    vent = one_pole(one_pole(white * 0.35, 0.02), 0.02)
    out += 0.13 * d + 0.5 * vent
    # M1 pulse 60bpm
    g = ramp(t, 12.0)
    beat = np.zeros(n)
    tb = t - 12.0
    idx = np.where((tb > 0) & (tb % 1.0 < 0.3))[0]
    tau = tb[idx] % 1.0
    beat[idx] = np.exp(-14 * tau) * np.sin(2 * np.pi * 52 * tau)
    out += g * 0.16 * beat
    # M2 ticks + minor pad
    g2 = ramp(t, 22.0)
    tk = np.zeros(n)
    tt = t - 22.0
    m = (tt > 0) & (tt % 0.5 < 0.03)
    tk[m] = np.sin(2 * np.pi * 1900 * (tt[m] % 0.5)) * np.exp(-300 * (tt[m] % 0.5))
    saw = np.zeros(n)
    for f0, amp in ((110.0, .5), (130.8, .4), (164.8, .35)):
        ph = (f0 * t) % 1.0
        saw += amp * (2 * ph - 1)
    pad = one_pole(saw, 0.004)
    pad *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
    out += g2 * (0.05 * tk + 0.07 * pad)
    # M3 low drums + sub
    g3 = ramp(t, 29.7)
    drum = np.zeros(n)
    td = t - 29.7
    per = 0.66
    pos = td % per
    hit = (td > 0) & (pos < 0.35)
    f_sweep = 95 * np.exp(-6 * pos) + 42
    drum[hit] = np.sin(2 * np.pi * f_sweep[hit] * pos[hit]) * np.exp(-7 * pos[hit])
    rim = np.zeros(n)
    rpos = td % (per * 4)
    rh = (td > 0) & (rpos > per * 2) & (rpos < per * 2 + 0.05)
    rim[rh] = rng.standard_normal(rh.sum()) * np.exp(-200 * (rpos[rh] - per * 2))
    sub = np.sin(2 * np.pi * 32 * t)
    out += g3 * (0.2 * drum + 0.05 * rim + 0.11 * sub)
    # M4 siren swell 44..53
    gs = ramp(t, 44.0, 2.0) * (1 - ramp(t, 51.0, 2.0))
    fr = 620 + 260 * np.clip((t - 44) / 7, 0, 1)
    sir = np.sin(2 * np.pi * fr * t + 4 * np.sin(2 * np.pi * 5 * t))
    out += gs * 0.05 * sir
    # master fade out
    out *= 1 - ramp(t, 58.6, 1.3)
    return out


def decode(name):
    src = os.path.join(OUT, name)
    raw = subprocess.run([FF, "-y", "-i", src, "-f", "f32le", "-acodec", "pcm_f32le",
                          "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def main():
    sched = key_schedule()
    n = int(TOTAL * SR)
    mix = music(TOTAL) + keystrokes(sched, TOTAL)
    for key, (st, fn) in VO.items():
        v = decode(fn).astype(np.float64) * 0.9
        s0 = int(st * SR)
        mix[s0:s0 + len(v)] += v
    peak = np.abs(mix).max()
    mix = mix / peak * 0.92
    st = (np.stack([mix, mix]) * 32767).astype("<i2").T.tobytes()
    with open(os.path.join(OUT, "mix.wav"), "wb") as f:
        import wave
    w = wave.open(os.path.join(OUT, "mix.wav"), "wb")
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(st); w.close()
    tl = {"shots": SHOTS, "vo": VO, "subs": SUBS, "keys": sched,
          "act0_lines": ACT0_LINES, "crt_lines": CRT_LINES, "total": TOTAL}
    json.dump(tl, open(os.path.join(OUT, "timeline.json"), "w"), ensure_ascii=False)
    print("mix.wav ok", len(st) // 2 // SR, "s; peak", round(peak, 3))


if __name__ == "__main__":
    main()
