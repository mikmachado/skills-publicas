#!/usr/bin/env python3
"""Prepara a narração: transcreve com tempo por palavra, corta silêncios, acelera e limpa.

Uso: python3 preparar_audio.py <audio original> <pasta do projeto> [--velocidade 1.2] [--pausa 0.14] [--texto "roteiro"]
Gera na pasta: voz.wav, palavras.json (tempos já no áudio final) e transcricao.txt
"""
import json, os, subprocess, sys, wave
import numpy as np

src, pasta = sys.argv[1], sys.argv[2]
def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
VEL = arg("--velocidade", 1.2); GAP = arg("--pausa", 0.14); TEXTO = arg("--texto", "")
os.makedirs(pasta, exist_ok=True)
tmp = os.path.join(pasta, "_mono16k.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", tmp], check=True)
w = wave.open(tmp); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

from faster_whisper import WhisperModel
m = WhisperModel(arg("--modelo", "small"), device="cpu", compute_type="int8")
segs, _ = m.transcribe(a, language=arg("--lingua", "pt"), word_timestamps=True, initial_prompt=TEXTO or None)
W = []
txt = []
for s in segs:
    txt.append(s.text.strip())
    for x in s.words: W.append({"w": x.word.strip(), "s": round(x.start, 3), "e": round(x.end, 3)})
os.remove(tmp)

# frases = blocos sem pausa > 0.28 s
ph = [[W[0]]]
for p, q in zip(W, W[1:]):
    (ph.append([q]) if q["s"] - p["e"] > 0.28 else ph[-1].append(q))
LEAD = 0.25; t = LEAD; segs2 = []; novas = []
for p in ph:
    s = max(0, p[0]["s"] - 0.06); e = p[-1]["e"] + 0.12
    segs2.append((s, e))
    for x in p: novas.append({"w": x["w"], "s": round((t + x["s"] - s) / VEL, 3), "e": round((t + x["e"] - s) / VEL, 3)})
    t += e - s + GAP
flt = [f"anullsrc=r=48000:cl=mono,atrim=0:{LEAD}[lead]"]
for i, (s, e) in enumerate(segs2):
    flt.append(f"[0:a]aformat=channel_layouts=mono,atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(0, e - s - 0.03)}:d=0.03,apad=pad_dur={GAP}[a{i}]")
flt.append("[lead]" + "".join(f"[a{i}]" for i in range(len(segs2))) + f"concat=n={len(segs2) + 1}:v=0:a=1[c]")
flt.append(f"[c]highpass=f=85,afftdn=nr=14:nf=-42,lowpass=f=12000,acompressor=threshold=-22dB:ratio=3:attack=5:release=80,atempo={VEL},loudnorm=I=-14:TP=-1.5:LRA=9[o]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(flt), "-map", "[o]", "-ac", "1", "-ar", "48000",
                os.path.join(pasta, "voz.wav")], check=True)
json.dump(novas, open(os.path.join(pasta, "palavras.json"), "w"), ensure_ascii=False, indent=0)
open(os.path.join(pasta, "transcricao.txt"), "w").write(" ".join(txt) + "\n\n" + " ".join(f"{x['w']}@{x['s']}" for x in novas) + "\n")
print(" ".join(txt)); print(); print(" ".join(f"{x['w']}@{x['s']}" for x in novas))
print(f"\nvoz.wav: {novas[-1]['e']:.2f}s")
