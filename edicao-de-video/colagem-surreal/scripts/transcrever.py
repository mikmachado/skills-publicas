#!/usr/bin/env python3
"""Transcreve a fala com o tempo de cada palavra (faster-whisper) → transcricao.json.

  python3 transcrever.py base.mp4                 → transcricao.json (português)
  python3 transcrever.py base.mp4 --lingua en --modelo small

Formato: [{"s": início, "e": fim, "t": "frase", "w": [{"s":…, "e":…, "w": "palavra"}, …]}, …]
Revise nomes próprios antes de desenhar a parede (ex.: "cloud" → "Claude"): edite o campo "w"
das palavras, mantendo a quantidade de palavras igual.
"""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

args = sys.argv[1:]
video = args[0]
lingua = args[args.index("--lingua") + 1] if "--lingua" in args else "pt"
modelo = args[args.index("--modelo") + 1] if "--modelo" in args else "large-v3-turbo"
saida = args[args.index("-o") + 1] if "-o" in args else "transcricao.json"

# áudio decodificado pelo ffmpeg (evita depender da versão do PyAV)
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768

m = WhisperModel(modelo, device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio, language=lingua, word_timestamps=True, vad_filter=True)
out = [{"s": s.start, "e": s.end, "t": s.text.strip(),
        "w": [{"s": w.start, "e": w.end, "w": w.word.strip()} for w in s.words]} for s in segs]
json.dump(out, open(saida, "w"), ensure_ascii=False, indent=1)
for i, s in enumerate(out):
    print(f"[{s['s']:6.2f}-{s['e']:6.2f}] {s['t']}")
print(f"\n{sum(len(s['w']) for s in out)} palavras → {saida}")
