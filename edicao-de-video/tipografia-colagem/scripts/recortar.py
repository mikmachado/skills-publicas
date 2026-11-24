#!/usr/bin/env python3
"""Recorta a pessoa das fotos (Vision da Apple) e gera <nome>_cut.png em P&B contrastado.

Uso: python3 recortar.py <pasta com .jpg> [--clarear nome1,nome2]   (fotos .png/.heic: converta antes para .jpg)
Clareia sozinho quem ficou muito escuro (média < 42); --clarear força.
"""
import os, subprocess, sys
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageStat

forcar = sys.argv[sys.argv.index("--clarear") + 1].split(",") if "--clarear" in sys.argv else []
pasta = os.path.abspath(sys.argv[1]); aqui = os.path.dirname(os.path.abspath(__file__))
mdir = os.path.join(pasta, "mask"); os.makedirs(mdir, exist_ok=True)
binario = os.path.expanduser("~/.cache/tipografia-colagem/seg")
if not os.path.exists(binario):
    os.makedirs(os.path.dirname(binario), exist_ok=True)
    subprocess.run(["swiftc", "-O", os.path.join(aqui, "seg.swift"), "-o", binario], check=True)
subprocess.run([binario, pasta, mdir], check=True)
for f in sorted(os.listdir(pasta)):
    if not f.lower().endswith(".jpg"): continue
    n = f[:-4]
    im = ImageOps.exif_transpose(Image.open(os.path.join(pasta, f))).convert("RGB")
    mp = os.path.join(mdir, n + ".png")
    if not os.path.exists(mp): print("sem máscara:", f); continue
    m = Image.open(mp).convert("L").resize(im.size)
    m = m.point(lambda v: 255 if v > 110 else int(v * 255 / 110)).filter(ImageFilter.GaussianBlur(1.2))
    g = ImageOps.grayscale(im)
    media = ImageStat.Stat(g, mask=m.point(lambda v: 255 if v > 128 else 0)).mean[0]
    clarear = media < 42 or n in forcar
    if clarear: g = g.point(lambda v: int(255 * ((v / 255) ** 0.6)))  # pessoa escura: clareia
    g = ImageEnhance.Contrast(ImageOps.autocontrast(g, cutoff=1)).enhance(1.35)
    cut = Image.merge("RGBA", (g, g, g, m))
    bb = m.point(lambda v: 255 if v > 40 else 0).getbbox()
    cut.crop(bb).save(os.path.join(pasta, n + "_cut.png"))
    print(n, "ok", f"brilho {media:.0f}", "(clareada)" if clarear else "")
