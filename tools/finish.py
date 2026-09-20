# Финишер: сборка звука + микс + mux для уже собранного _final_video.mp4.
# Повторяет хвост main() из render_final.py без перерисовки кадров.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, wave, subprocess
import render_final as m

FF, SR, ROOT, add, rd = m.FF, m.SR, m.ROOT, m.add, m.rd

assert os.path.getsize(f"{ROOT}/video/_final_video.mp4") > 100_000_000, "нет _final_video.mp4"

A = lambda p: rd(f"{ROOT}/audio/{p}")
narr = A("_w_narration_A.wav"); vo2 = A("_w_vo_part2.wav"); vo3 = A("_w_vo_part3.wav")
vo4 = A("_w_vo_part4.wav"); vos = A("_w_system.wav"); voe = A("_w_epilog.wav"); rad = A("_w_radio.wav")

sfx = m.build_sfx()
tt = np.arange(len(sfx))/SR
for a, b in ((194.0, 195.5), (249.3, 250.3)):
    duck = np.clip(np.minimum((tt-a)/0.2, (b-tt)/0.2), 0, 1)
    sfx *= (0.15 + 0.85*duck)
mix = sfx.copy()
add(mix, narr, 12.0, 1.0); add(mix, vo2, 76.0, 1.0); add(mix, vo3, 151.0, 1.0)
add(mix, vo4, 225.5, 1.0); add(mix, vos, 256.0, 0.9); add(mix, voe, 281.0, 1.0); add(mix, rad, 351.0, 0.8)
mix = np.tanh(mix*1.4)/np.tanh(1.4)*0.9
Lch = mix; Rch = np.roll(mix, int(0.006*SR))*0.95
with wave.open(f"{ROOT}/audio/_mixfinal.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    st = np.empty(len(Lch)*2, dtype=np.int16)
    st[0::2] = (Lch*32767).astype(np.int16); st[1::2] = (Rch*32767).astype(np.int16)
    w.writeframes(st.tobytes())
print("WAV OK", flush=True)

subprocess.run([FF, "-y", "-i", f"{ROOT}/audio/_mixfinal.wav", "-c:a", "libmp3lame", "-b:a", "192k",
                f"{ROOT}/audio/INSOMNIA_full_mix.mp3"], check=True, capture_output=True)
subprocess.run([FF, "-y", "-i", f"{ROOT}/video/_final_video.mp4", "-i", f"{ROOT}/audio/_mixfinal.wav",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-shortest",
                f"{ROOT}/video/TRET_JIZNI_full.mp4"], check=True, capture_output=True)
print("FINAL DONE", flush=True)
