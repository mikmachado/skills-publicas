#!/bin/bash
# uso: quadros_e_mascaras.sh <video> <pasta_do_projeto>
# extrai quadros (quadros/%05d.jpg) e recorte da pessoa pelo Vision (mask/%05d.png)
set -e
SK="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$2" && cd "$2"
cp -n "$1" base.mov 2>/dev/null || true
mkdir -p quadros mask
ffmpeg -v error -y -i base.mov -q:v 2 quadros/%05d.jpg
[ -x "$SK/seg_crop" ] || swiftc -O "$SK/seg_crop.swift" -o "$SK/seg_crop"
IFS=x read W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x quadros/00001.jpg)
"$SK/seg_crop" quadros mask 0 0 $W $H
echo "quadros: $(ls quadros | wc -l)"
