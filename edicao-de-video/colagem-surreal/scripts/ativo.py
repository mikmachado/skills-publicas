#!/usr/bin/env python3
"""Recorta um objeto gerado sobre fundo verde chapado (ex.: Gemini, "on a perfectly flat solid pure green background (#00FF00)").

  python3 -I ativo.py gerado.png nome            → ativos/nome.png na pasta do projeto (use "ativo": "nome" no roteiro)
  python3 -I ativo.py gerado.png nome --divide   → vários objetos lado a lado viram nome1.png, nome2.png, …

Recorta pela distância até a cor do fundo (funciona até com planta verde) e tira o verde das bordas.
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

a = sys.argv[1:]
if len(a) < 2: sys.exit(__doc__)
src, nome = a[0], a[1]
im = np.asarray(Image.open(src).convert("RGB"), np.float32)
bg = np.median(np.concatenate([im[:40, :40].reshape(-1, 3), im[:40, -40:].reshape(-1, 3), im[-40:, :40].reshape(-1, 3), im[-40:, -40:].reshape(-1, 3)]), 0)
d = np.sqrt(((im - bg) ** 2).sum(-1))
al = np.clip((d - 55) / 55, 0, 1)
al = np.asarray(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.GaussianBlur(0.7)), np.float32)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
rgb = np.stack([r, np.minimum(g, np.maximum(r, b) + 28), b], -1)
out = np.dstack([rgb, al]).astype(np.uint8)


def apara(o):
    ys, xs = np.nonzero(o[..., 3] > 10)
    return o[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


os.makedirs("ativos", exist_ok=True)
if "--divide" in a:
    col = (out[..., 3] > 128).sum(0) > 2
    partes, x = [], 0
    while x < len(col):
        if col[x]:
            x2, vazio = x, 0
            while x2 < len(col) and (col[x2] or vazio < 6):
                vazio = 0 if col[x2] else vazio + 1; x2 += 1
            if x2 - x > 60: partes.append((max(x - 4, 0), x2 + 4))
            x = x2
        x += 1
    for k, (x0, x1) in enumerate(partes, 1):
        Image.fromarray(apara(out[:, x0:x1])).save(f"ativos/{nome}{k}.png"); print(f"ativos/{nome}{k}.png")
else:
    Image.fromarray(apara(out)).save(f"ativos/{nome}.png"); print(f"ativos/{nome}.png")
