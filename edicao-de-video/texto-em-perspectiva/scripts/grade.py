#!/usr/bin/env python3
"""Tira um quadro do vídeo base e desenha uma grade com coordenadas, para ler os
4 cantos do plano (parede, chão, mesa, porta) onde o cartão vai ser colado.

  python3 grade.py base.mp4 --t 0.5 -o grade.jpg
  python3 grade.py base.mp4 --t 0.5 --cantos "120,300 520,380 520,1300 120,1500" -o conferir.jpg

As coordenadas são em pixels do vídeo base (o mesmo espaço do perspectiva.py).
"""
import argparse, subprocess, io
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--t", type=float, default=0.0)
ap.add_argument("-o", "--saida", default="grade.jpg")
ap.add_argument("--passo", type=int, default=0, help="espaço da grade em px (0 = automático)")
ap.add_argument("--cantos", help='"x,y x,y x,y x,y" (sup-esq, sup-dir, inf-dir, inf-esq) para conferir')
a = ap.parse_args()

png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a.t), "-i", a.video, "-frames:v", "1",
                      "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
im = Image.open(io.BytesIO(png)).convert("RGB")
W, H = im.size
passo = a.passo or (100 if max(W, H) <= 2000 else 200)
d = ImageDraw.Draw(im, "RGBA")
f = ImageFont.load_default(size=max(14, W // 60))
for x in range(0, W, passo):
    d.line([(x, 0), (x, H)], fill=(255, 0, 255, 150 if x % (passo * 5) == 0 else 70), width=2 if x % (passo * 5) == 0 else 1)
    d.text((x + 3, 3), str(x), font=f, fill=(255, 0, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
for y in range(0, H, passo):
    d.line([(0, y), (W, y)], fill=(0, 255, 255, 150 if y % (passo * 5) == 0 else 70), width=2 if y % (passo * 5) == 0 else 1)
    d.text((3, y + 3), str(y), font=f, fill=(0, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
if a.cantos:
    pts = [tuple(float(v) for v in p.split(",")) for p in a.cantos.split()]
    d.polygon(pts, outline=(255, 230, 0, 255), width=4)
    for i, p in enumerate(pts):
        d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], fill=(255, 230, 0, 255))
        d.text((p[0] + 12, p[1] + 4), "ABCD"[i], font=f, fill=(255, 230, 0), stroke_width=3, stroke_fill=(0, 0, 0))
im.save(a.saida, quality=88)
print(a.saida, (W, H))
