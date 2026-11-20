#!/bin/bash
# Junta video_mudo.mp4 com o áudio + versão leve. Arquivo final cabe no celular (<30 MB): 2 passadas a ~10,5 Mbps.
#   bash <skill>/scripts/montar.sh nome_final [--sem-tratar-audio]   (vídeo sem fala: áudio copiado como veio)
# Se o vídeo for HDR (hdr.txt), a saída continua HEVC 10 bits HDR — nunca converter pra SDR (fica apagado).
set -e
NOME="${1:-texto-seguindo-gestos}"
AF=(-af "highpass=f=80,loudnorm=I=-16:TP=-1.5")
[ "$2" = "--sem-tratar-audio" ] && AF=()
LOG="$(mktemp -d)/x"
if [ -f hdr.txt ]; then
  TRC=$(cat hdr.txt)
  XP="colorprim=bt2020:transfer=$TRC:colormatrix=bt2020nc:range=limited:log-level=error"
  TAGS=(-pix_fmt yuv420p10le -color_primaries bt2020 -color_trc "$TRC" -colorspace bt2020nc -tag:v hvc1)
  ffmpeg -v error -y -i video_mudo.mp4 -c:v libx265 -preset slow -b:v 10500k -x265-params "pass=1:stats=$LOG:$XP" "${TAGS[@]}" -an -f mp4 /dev/null
  ffmpeg -v error -y -i video_mudo.mp4 -i base.mp4 -map 0:v -map 1:a -c:v libx265 -preset slow -b:v 10500k \
    -x265-params "pass=2:stats=$LOG:$XP" "${TAGS[@]}" -c:a aac -b:a 192k "${AF[@]}" -shortest -movflags +faststart "$NOME.mp4"
else
  for P in 1 2; do
    if [ $P = 1 ]; then OUT=(-an -f mp4 /dev/null); else OUT=(-an "$LOG.v.mp4"); fi
    ffmpeg -v error -y -i video_mudo.mp4 -c:v libx264 -preset slow -b:v 11M -maxrate 14M -bufsize 22M -pix_fmt yuv420p -pass $P -passlogfile "$LOG" "${OUT[@]}"
  done
  ffmpeg -v error -y -i "$LOG.v.mp4" -i base.mp4 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k "${AF[@]}" -shortest -movflags +faststart "$NOME.mp4"
fi
ffmpeg -v error -y -i "$NOME.mp4" -map 0:v -c:v copy -an -movflags +faststart "$NOME-sem-audio.mp4"
ls -la "$NOME.mp4" "$NOME-sem-audio.mp4"
