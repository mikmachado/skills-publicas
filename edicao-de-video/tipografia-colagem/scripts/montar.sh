#!/bin/bash
# Uso: montar.sh projeto.json  -> <saida>/<nome>.mp4, <nome>-leve.mp4 (prévia) e <nome>-POSTAR.mp4 (<30 MB, para o Reels)
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
PROJ="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
read -r OUT NOME < <(python3 -c "
import json,os,sys;p=json.load(open(sys.argv[1]));d=os.path.dirname(sys.argv[1])
print(os.path.join(d,p.get('saida','saida')),p.get('nome','video'))" "$PROJ")
python3 "$AQUI/motor.py" "$PROJ"
python3 "$AQUI/audio.py" "$PROJ"
ffmpeg -v error -y -framerate 30 -i "$OUT/quadros/f%04d.png" -i "$OUT/mix.wav" -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow \
  -c:a aac -b:a 192k -ar 48000 -af "loudnorm=I=-14:TP=-1:LRA=11" -shortest -movflags +faststart "$OUT/$NOME.mp4"
ffmpeg -v error -y -i "$OUT/$NOME.mp4" -c:v libx264 -crf 27 -preset slow -maxrate 9M -bufsize 18M -c:a copy "$OUT/$NOME-leve.mp4"
ffmpeg -v error -y -i "$OUT/$NOME.mp4" -c:v libx264 -preset slow -b:v 10M -maxrate 12M -bufsize 20M -profile:v high -pix_fmt yuv420p \
  -c:a copy -movflags +faststart "$OUT/$NOME-POSTAR.mp4"
ls -la "$OUT"/*.mp4
