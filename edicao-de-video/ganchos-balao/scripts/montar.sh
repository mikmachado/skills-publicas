#!/bin/bash
# Render final:  bash <skill>/scripts/montar.sh nome-do-video
# Gera: video_mudo.mov (HDR) -> nome.mov (master) + nome-leve.mp4 (para conferir no celular) + nome-POSTAR.mp4 (Instagram: -14 LUFS)
set -e
SK="$(cd "$(dirname "$0")" && pwd)"; N="$1"; [ -z "$N" ] && N=ganchos
python3 -I "$SK/audio.py" base.mp4
python3 -I "$SK/ganchos.py"
if [ -f hdr.txt ]; then
  TRC=$(cat hdr.txt)
  V="-c:v libx265 -tag:v hvc1 -pix_fmt yuv420p10le -x265-params colorprim=bt2020:transfer=$TRC:colormatrix=bt2020nc:range=limited:log-level=error -color_primaries bt2020 -color_trc $TRC -colorspace bt2020nc"
else
  V="-c:v libx264 -pix_fmt yuv420p"
fi
ffmpeg -v error -y -i video_mudo.mov -i audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart "$N.mov"
ffmpeg -v error -y -i "$N.mov" $V -crf 24 -preset medium -c:a copy "$N-leve.mp4"
ffmpeg -v error -y -i video_mudo.mov -i audio.wav -map 0:v -map 1:a $V -crf 17 -preset slow \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,volume=2.5dB,alimiter=limit=0.84:level=false" -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$N-POSTAR.mp4"
ls -la "$N.mov" "$N-leve.mp4" "$N-POSTAR.mp4"
