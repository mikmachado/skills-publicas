"""Recorte pelo verde, tira o verde da borda, olhos suavizados e corte do busto."""
import json
import numpy as np


def fracao_verde(a):
    f = a.astype(np.int16)
    return float(((f[..., 1] > 170) & (f[..., 1] - np.maximum(f[..., 0], f[..., 2]) > 70)).mean())


def alfa_verde(a):
    """a: uint8 HxWx3 → (alfa 0..1, rgb 0..1 sem verde na borda)"""
    f = a.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    d = g - np.maximum(r, b)
    al = np.clip((95 - d) / 60.0, 0, 1)
    return al, despill(f / 255)


def despill(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    g2 = np.minimum(g, np.maximum(np.maximum(r, b) + 0.025, (r + b) / 2))
    return np.stack([r, g2, b], -1)


class Olhos:
    """olhos.json → por quadro: [rosto x, y, w, h, olho E x, y, olho D x, y, nariz x, y], interpolado e suavizado."""
    def __init__(self, arq, n):
        raw = json.load(open(arq))
        self.v = np.full((n, 10), np.nan)
        for i, x in enumerate(raw[:n]):
            if x and min(x[4:8]) > 0: self.v[i] = x
        ok_any = ~np.isnan(self.v[:, 0])
        if ok_any.sum() == 0:
            self.v[:] = [270, 520, 540, 540, 430, 760, 650, 760, 540, 860]
        for k in range(10):
            col = self.v[:, k]; ok = ~np.isnan(col)
            col[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), col[ok])
        ker = np.ones(5) / 5
        for k in range(10):
            self.v[:, k] = np.convolve(np.pad(self.v[:, k], 2, mode="edge"), ker, "valid")

    def em(self, i): return self.v[min(max(i, 0), len(self.v) - 1)]


def corta_busto(al, ol, abaixo=0.95):
    """Corta o corpo numa linha ondulada abaixo do queixo: o busto ganha a borda de baixo de onde a tinta
    escorre (mesa, braços e cadeira ficam de fora). abaixo = alturas de rosto abaixo do queixo."""
    H, W = al.shape
    fx, fy, fw, fh = ol[:4]
    y0 = fy + fh * (1 + abaixo)
    if y0 >= H - 4: return al
    xs = np.arange(W, dtype=np.float32)
    cx = fx + fw / 2
    # ombros caem um pouco para os lados; ondula de leve
    yc = y0 + (18 * np.sin(xs / 53 + 0.7) + 10 * np.sin(xs / 23 + 2.1)) * fw / 590
    yy = np.arange(H, dtype=np.float32)[:, None]
    corte = np.clip((yc[None, :] - yy) / 4 + 0.5, 0, 1)
    return al * corte
