# -*- coding: utf-8 -*-
"""v6 звук: БЕЗ музыки. Реальная пишущая машинка (акт 0), шорох пера (кадр A),
рум-тон вентиляции, VO. Никаких бипов/дронов/пульса."""
import numpy as np, subprocess, os
from scipy.signal import lfilter, butter
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SR = 44100
rng = np.random.default_rng(42)

def bp(x, f0, q=6):
    b, a = butter(2, [max(40,f0*0.7)/SR*2, min(SR/2-40,f0*1.4)/SR*2], 'bandpass')
    return lfilter(b, a, x)

def key(dur=0.055, hard=1.0):
    n = int(SR*dur); t = np.arange(n)/SR
    noise = rng.standard_normal(n)*np.exp(-t/0.0045)
    clack = bp(noise, 2400+rng.uniform(-500,900), 5)*0.9
    tick = rng.standard_normal(n)*np.exp(-t/0.0016)*0.5
    thock = np.sin(2*np.pi*150*t + 2*np.sin(2*np.pi*60*t))*np.exp(-t/0.014)*0.7
    mech = bp(rng.standard_normal(n)*np.exp(-t/0.02), 900, 3)*0.35
    return (clack+tick+thock+mech)*hard

def space_key():
    n = int(SR*0.07); t = np.arange(n)/SR
    return (np.sin(2*np.pi*110*t)*np.exp(-t/0.02) + bp(rng.standard_normal(n)*np.exp(-t/0.006), 1300, 4))*0.8

def carriage():
    n = int(SR*0.55); t = np.arange(n)/SR
    zipn = bp(rng.standard_normal(n)*np.exp(-t/0.09)*(t>0.02), 1400, 3)*0.5
    ding = (np.sin(2*np.pi*1568*t)+0.6*np.sin(2*np.pi*2349*t)+0.3*np.sin(2*np.pi*3136*t))*np.exp(-t/0.5)*0.35*(t>0.12)
    thunk = np.sin(2*np.pi*95*t)*np.exp(-(t-0.2)/0.02)*0.6*(t>0.2)
    return zipn+ding+thunk

def pen_scratch(dur=0.045):
    n = int(SR*dur); t = np.arange(n)/SR
    return bp(rng.standard_normal(n)*np.exp(-t/0.012), 3800+rng.uniform(-600,600), 3)*0.16

def typewriter_track(total):
    out = np.zeros(int(SR*total))
    lines = ["ПРОЕКТ «БЕССОННИЦА» // СЕКТОР Б, ЛАБ. №3", "ДНЕВНИК ДОКТОРА М. ВЕТРОВА", "ПОСЛЕДНЯЯ ЗАПИСЬ"]
    t0s = [0.5, 4.6, 7.5]
    for ln, t0 in zip(lines, t0s):
        t = t0
        for i, ch in enumerate(ln):
            if t+0.1 > total: break
            s = key(hard=0.8+rng.uniform(0,0.4)) if ch != ' ' else space_key()
            i0 = int(t*SR)
            out[i0:i0+len(s)] += s*0.55
            t += (0.075 if ch == ' ' else 0.078+rng.uniform(-0.012,0.02))
        c = carriage(); i0 = int((t+0.25)*SR)
        if i0+len(c) < len(out): out[i0:i0+len(c)] += c*0.5
    return out

def pen_track(total, t0=10.7, t1=17.2):
    out = np.zeros(int(SR*total)); t = t0
    while t < t1:
        s = pen_scratch(); i0 = int(t*SR)
        out[i0:i0+len(s)] += s
        t += 0.05+rng.uniform(0,0.03)
    return out

def room(total):
    n = int(SR*total); t = np.arange(n)/SR
    vent = lfilter(*butter(1, 240/SR*2, 'low'), rng.standard_normal(n))*0.045
    hum = np.sin(2*np.pi*52*t)*0.010*(0.7+0.3*np.sin(2*np.pi*0.13*t))
    buzz = np.sin(2*np.pi*100*t)*0.004
    return vent+hum+buzz

def decode(path):
    raw = subprocess.run([FF, '-i', os.path.join(ROOT, path), '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64)/32768

def main():
    total = 41.5
    mix = room(total) + typewriter_track(total) + pen_track(total)
    for path, st, dur in [('audio/v5/v6_vetrov_01.mp3',10.5,6.95), ('audio/v5/v6_vetrov_02.mp3',19.2,6.77),
                          ('audio/v5/v6_vetrov_03.mp3',27.4,9.93)]:
        v = decode(path)*0.95
        i0 = int(st*SR)
        mix[i0:i0+len(v)] += v
    mix = mix/np.max(np.abs(mix))*0.92
    st = (np.stack([mix, mix])*32767).astype('<i2').T.tobytes()
    open('/home/user/v6_mix.wav','wb').write(st)
    print('mix ok', total)

if __name__ == '__main__':
    main()
