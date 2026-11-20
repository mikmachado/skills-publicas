#!/bin/bash
# Prepara um vídeo para o efeito "texto seguindo gestos".
#   bash <skill>/scripts/preparar.sh bruto.MOV          (rode de dentro da pasta do projeto)
# Gera: base.mp4 (1080x1920, 30 fps), quadros/ (+ quadros_cor/ só com COR=1), transcricao.json,
#       maos.json + corpo.json (Vision da Apple) e maos2.npy (ponta das duas mãos por quadro).
set -e
SK="$(cd "$(dirname "$0")" && pwd)"
VID="$1"
[ -z "$VID" ] && { echo "uso: preparar.sh video"; exit 1; }
BIN="$HOME/.cache/texto-seguindo-gestos"; mkdir -p "$BIN"
[ -x "$BIN/maos" ]  || swiftc -O "$SK/maos.swift"  -o "$BIN/maos"
[ -x "$BIN/corpo" ] || swiftc -O "$SK/corpo.swift" -o "$BIN/corpo"

# vídeo do iPhone costuma ser HDR (HLG/Dolby Vision, 10 bits). Tratado como vídeo comum fica APAGADO.
TRC=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 "$VID")
rm -rf quadros quadros_cor; mkdir -p quadros quadros_cor
if [ "$TRC" = "arib-std-b67" ] || [ "$TRC" = "smpte2084" ]; then
  echo "== vídeo HDR ($TRC): base.mp4 continua HDR 10 bits; quadros/ = cópia SDR só para rastrear e conferir"
  echo "$TRC" > hdr.txt
  ffmpeg -v error -y -i "$VID" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
    -c:v libx265 -preset medium -crf 12 -pix_fmt yuv420p10le -tag:v hvc1 \
    -x265-params "colorprim=bt2020:transfer=$TRC:colormatrix=bt2020nc:range=limited:log-level=error" \
    -color_primaries bt2020 -color_trc "$TRC" -colorspace bt2020nc -c:a aac -b:a 192k base.mp4
  ffmpeg -v error -i base.mp4 -vf "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" -q:v 2 quadros/%04d.jpg
else
  rm -f hdr.txt
  echo "== base 1080x1920 30fps"
  ffmpeg -v error -y -i "$VID" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
    -c:v libx264 -crf 16 -c:a aac -b:a 192k base.mp4
  ffmpeg -v error -i base.mp4 -q:v 2 quadros/%04d.jpg
fi
# cor: por padrão fica a ORIGINAL do arquivo. Só valoriza se pedirem: COR=1 (usa cor.txt) ou COR="filtro ffmpeg"
if [ -n "$COR" ]; then
  [ "$COR" = "1" ] && COR="$(cat "$SK/cor.txt")"
  echo "$COR" > cor.txt
  ffmpeg -v error -i base.mp4 -vf "$COR" -q:v 2 quadros_cor/%04d.jpg
else
  rmdir quadros_cor
fi
echo "== mãos e corpo (Vision)"
"$BIN/corpo" quadros corpo.json
# pose da mão (ponta do dedo): às vezes o Vision trava ao carregar esse modelo; com vigia, e se travar
# segue só com a pose do corpo (pulso + antebraço), que é o que mais importa para as formas
NQ=$(ls quadros | wc -l | tr -d ' ')
"$BIN/maos" quadros maos.json & PM=$!
for i in $(seq 1 $((NQ / 2 + 60))); do kill -0 $PM 2>/dev/null || break; perl -e 'select(undef,undef,undef,1)'; done
if kill -0 $PM 2>/dev/null; then kill $PM; rm -f maos.json; echo "AVISO: pose da mão travou; seguindo só com a pose do corpo"; fi
python3 -I "$SK/trajeto.py"
echo "== transcrição"
python3 -I "$SK/transcrever.py" base.mp4
echo "pronto. Agora: python3 -I $SK/gestos.py  (sugere as formas)"
