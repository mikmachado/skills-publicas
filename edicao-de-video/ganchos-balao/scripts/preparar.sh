#!/bin/bash
# Prepara o vídeo:  bash <skill>/scripts/preparar.sh bruto.MOV   (rode de dentro da pasta do projeto)
# Gera base.mp4 (HDR continua HDR), quadros/NNNN.jpg (cópia SDR só para analisar) e f/todos.jpg (folha numerada).
set -e
VID="$1"; [ -z "$VID" ] && { echo "uso: preparar.sh video"; exit 1; }
mkdir -p quadros f
TRC=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 "$VID")
if [ "$TRC" = "arib-std-b67" ] || [ "$TRC" = "smpte2084" ]; then
  echo "$TRC" > hdr.txt; echo "== HDR ($TRC): a saída continua HDR"
  ffmpeg -v error -y -i "$VID" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
    -c:v libx265 -preset medium -crf 12 -pix_fmt yuv420p10le -tag:v hvc1 \
    -x265-params "colorprim=bt2020:transfer=$TRC:colormatrix=bt2020nc:range=limited:log-level=error" \
    -color_primaries bt2020 -color_trc "$TRC" -colorspace bt2020nc -c:a aac -b:a 192k base.mp4
  ffmpeg -v error -y -i base.mp4 -vf "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" -q:v 2 quadros/%04d.jpg
else
  rm -f hdr.txt
  ffmpeg -v error -y -i "$VID" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" -c:v libx264 -crf 16 -c:a aac -b:a 192k base.mp4
  ffmpeg -v error -y -i base.mp4 -q:v 2 quadros/%04d.jpg
fi
python3 -I - <<'PY'
import cv2, numpy as np, os
N = len([f for f in os.listdir('quadros') if f.endswith('.jpg')])
t = []
for n in range(1, N + 1, 5):
    im = cv2.resize(cv2.imread(f'quadros/{n:04d}.jpg'), (150, 266)); cv2.putText(im, str(n), (4, 20), 0, 0.6, (0, 0, 255), 2); t.append(im)
while len(t) % 14: t.append(np.zeros_like(t[0]))
cv2.imwrite('f/todos.jpg', np.vstack([np.hstack(t[i:i + 14]) for i in range(0, len(t), 14)]))
print(N, 'quadros -> f/todos.jpg (um a cada 5, numerados)')
PY
