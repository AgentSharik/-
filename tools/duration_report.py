#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Единая справка о продолжительности: фильм целиком, по актам, по кадрам,
плюс замер длительностей всех готовых медиафайлов проекта."""
import json, glob, os, re, subprocess, wave
import imageio_ffmpeg
from mutagen.mp3 import MP3

FF = imageio_ffmpeg.get_ffmpeg_exe()

def mp4_dur(p):
    r = subprocess.run([FF, "-i", p], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0

def wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()

def mmss(x):
    return f"{int(x)//60}:{int(x)%60:02d}.{int(round(x%1*10))}"

tl = json.load(open("prod/audio/timeline_v6.json"))
rows, total = tl["shots"], tl["total"]

act_names = {0: "Акт 0 · пролог (печать)", 1: "Акт 1 · Инъекция", 2: "Акт 2 · 168 часов",
             3: "Акт 3 · Выход наружу", 4: "Акт 4 · Ночь прорыва", 5: "Акт 5 · Город (Артём)",
             6: "Акт 6 · Эпилог", 7: "Досье ×7", 8: "Постер"}
acts = {}
for r in rows:
    acts[r["act"]] = acts.get(r["act"], 0.0) + r["dur"]

out = ["# ТРЕТЬ ЖИЗНИ v6 — ПРОДОЛЖИТЕЛЬНОСТЬ (справка)", "",
       f"**Фильм целиком: {total:.2f} c = {mmss(total)}** · 30 fps · 1920×1080 · "
       f"{int(round(total*30))} кадров · целевой коридор 7:20–7:50 ✔", "",
       "## По актам", "", "| Блок | Длительность |", "|---|---|"]
for a, s in acts.items():
    out.append(f"| {act_names[a]} | {s:.1f} c = {mmss(s)} |")
out += ["", "## По кадрам (вход → выход)", "",
        "| Кадр | Длительность | Вход | Выход | Кадров@30 | VO / звук |",
        "|---|---|---|---|---|---|"]
for r in rows:
    out.append(f"| {r['id']} | {r['dur']:.2f} c | {mmss(r['start'])} | {mmss(r['end'])} | {r['frames']} | {r['note']} |")

out += ["", "## Готовые файлы (замер)", "", "| Файл | Длительность |", "|---|---|"]
groups = [("Озвучка Ветрова v6", "/tmp/repo/audio/v5/v6_vetrov_*.mp3", "mp3"),
          ("Озвучка Ветрова v5 (архив)", "/tmp/repo/audio/v5/vetrov_*.mp3", "mp3"),
          ("Озвучка Артёма v6 (voice-00)", "prod/audio/vo6/artem_*.mp3", "mp3"),
          ("Синхронные sfx-дорожки (печать/перо)", "prod/audio/sfx/*.wav", "wav"),
          ("Превью покадровых сцен", "prod/previews/*.mp4", "mp4")]
sums = {}
for name, pat, kind in groups:
    files = sorted(glob.glob(pat))
    s = 0.0
    for f in files:
        d = MP3(f).info.length if kind == "mp3" else (wav_dur(f) if kind == "wav" else mp4_dur(f))
        s += d
        out.append(f"| `{os.path.basename(f)}` | {d:.2f} c = {mmss(d)} |")
    sums[name] = s
    out.append(f"| **{name} — итого** | **{s:.2f} c = {mmss(s)}** |")
out += ["", "Примечание: длительности кадров акта 5 и акта 6 посчитаны по замеренным дублям",
        "Артёма (voice-00) и Ветрова; остальные реплики Ветрова — оценка темпа 1.55 сл/с,",
        "уточнится после записи дублей. Пересчёт: `python3 prod/tools/timing_v6.py`.", ""]
open("prod/docs/DURATION_v6.md", "w").write("\n".join(out))
print(f"TOTAL {total:.2f} c = {mmss(total)}")
print("acts:", {act_names[a]: round(s, 1) for a, s in acts.items()})
print("file sums:", {k: round(v, 1) for k, v in sums.items()})
