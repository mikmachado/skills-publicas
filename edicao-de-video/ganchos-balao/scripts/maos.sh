#!/bin/bash
# Pose das mãos (Vision da Apple) em um trecho:  bash <skill>/scripts/maos.sh A B saida.json [--espelhar]
#   CTA:   bash maos.sh <início do CTA> <fim do CTA> maos_cta.json --espelhar(se o CTA for espelhado)
#   1/3:   bash maos.sh 8 58 maos_13.json  -> depois python3 -I punho.py maos_13.json  (sugere o "punho" da cordinha)
set -e
SK="$(cd "$(dirname "$0")" && pwd)"
A=$1; B=$2; OUT=$3; ESP=$4
BIN="$HOME/.cache/ganchos-balao"; mkdir -p "$BIN"
[ -x "$BIN/maos" ] || swiftc -O "$SK/maos.swift" -o "$BIN/maos"
TMP=$(mktemp -d)
python3 -I -c "
import cv2, sys
for n in range($A, $B + 1):
    im = cv2.imread(f'quadros/{n:04d}.jpg')
    if '$ESP' == '--espelhar': im = im[:, ::-1]
    cv2.imwrite(f'$TMP/{n:04d}.jpg', im)
"
# o Vision às vezes trava ao carregar o modelo: vigia de 4 min
"$BIN/maos" "$TMP" "$OUT" & P=$!
for i in $(seq 1 240); do kill -0 $P 2>/dev/null || break; perl -e 'select(undef,undef,undef,1)'; done
if kill -0 $P 2>/dev/null; then kill $P; echo "AVISO: o Vision travou. Feche e abra o Terminal/Mac e tente de novo, ou marque à mão com grade.py"; exit 1; fi
rm -rf "$TMP"; echo "$OUT ($A a $B)"
