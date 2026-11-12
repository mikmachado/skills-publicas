"""Desenho em traço de caneta/guache: formas com contorno colorido grosso, preenchimento com textura de pincel,
linha que "ferve" (tremidinho de animação à mão, trocando a cada 4 quadros) e transformação entre desenhos
(cada objeto é uma lista de partes; partes são interpoladas ponto a ponto).

Uma parte: {"p": array Nx2 (polígono ou linha), "f": cor de preenchimento ou None, "l": cor do contorno ou None,
            "w": espessura do contorno, "aberta": True para traço sem preenchimento}
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ----------------------------------------------------------------- paleta
VERDE = (52, 150, 92)
VERDE_E = (24, 96, 62)
VERDE_C = (150, 206, 150)
LARANJA = (243, 110, 40)
LARANJA_C = (250, 166, 92)
BEGE = (244, 230, 206)
BEGE_E = (222, 196, 160)
ROSA = (250, 214, 216)
ROSA_E = (240, 168, 178)
CEU = (140, 206, 240)
CEU_C = (196, 232, 250)
BRANCO = (255, 250, 240)
TINTA = (40, 52, 46)

N_PTS = 96  # pontos por parte depois de reamostrar


# ----------------------------------------------------------------- geometria
def ret(x0, y0, x1, y1, r=0):
    """retângulo (cantos arredondados se r>0)"""
    if r <= 0:
        return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(7):
            a = math.radians(a0 + k * 15)
            pts.append([cx + r * math.cos(a), cy + r * math.sin(a)])
    return np.array(pts, float)


def elipse(cx, cy, rx, ry, n=48, a0=0):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False) + a0
    return np.stack([cx + rx * np.cos(t), cy + ry * np.sin(t)], 1)


def poli(*xy):
    return np.array(xy, float).reshape(-1, 2)


def folha(x0, y0, x1, y1, larg=0.35):
    """folha pontuda de (x0,y0) até (x1,y1)"""
    d = np.array([x1 - x0, y1 - y0], float); L = np.hypot(*d); u = d / L; nrm = np.array([-u[1], u[0]])
    t = np.linspace(0, 1, 16)
    lado = np.sin(t * math.pi) * L * larg / 2
    a = np.array([x0, y0]) + t[:, None] * d + lado[:, None] * nrm
    b = np.array([x0, y0]) + t[::-1, None] * d - lado[::-1, None] * nrm
    return np.vstack([a, b])


def reamostra(p, n=N_PTS, fechada=True):
    p = np.asarray(p, float)
    q = np.vstack([p, p[:1]]) if fechada else p
    seg = np.hypot(*np.diff(q, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] == 0:
        return np.repeat(p[:1], n, 0)
    t = np.linspace(0, s[-1], n, endpoint=not fechada)
    return np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], 1)


def alinha(p):
    """começa no ponto mais alto-à-esquerda, sentido horário (para interpolar sem torcer)"""
    c = p.mean(0)
    area = np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    if area < 0:
        p = p[::-1]
    ang = np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0])
    k = int(np.argmin(np.abs(ang - (-math.pi * 0.75))))
    return np.roll(p, -k, 0)


def parte(p, f=None, l=TINTA, w=9, aberta=False):
    p = reamostra(p, N_PTS, fechada=not aberta)
    if not aberta:
        p = alinha(p)
    return {"p": p, "f": f, "l": l, "w": w, "aberta": aberta}


def desloca(partes, dx=0, dy=0, s=1.0, cx=0, cy=0):
    out = []
    for q in partes:
        r = dict(q); r["p"] = (q["p"] - [cx, cy]) * s + [cx + dx, cy + dy]; r["w"] = q["w"] * (s ** 0.5); out.append(r)
    return out


# ----------------------------------------------------------------- transformação
def _mistura_cor(a, b, t):
    """troca de cor seca na metade (misturar laranja com verde dá marrom)"""
    if a is None and b is None: return None
    if a is None: return b
    if b is None: return a
    return a if t < 0.5 else b


def morfa(A, B, t):
    """A → B. Partes sobrando nascem/morrem encolhidas no centro da parte correspondente."""
    t = max(0.0, min(1.0, t))
    if t <= 0: return A
    if t >= 1: return B
    e = t * t * (3 - 2 * t)
    n = max(len(A), len(B)); out = []
    for i in range(n):
        a = A[i] if i < len(A) else None
        b = B[i] if i < len(B) else None
        if a is None:
            a = dict(b); a["p"] = np.repeat(b["p"].mean(0, keepdims=True), N_PTS, 0)
        if b is None:
            b = dict(a); b["p"] = np.repeat(a["p"].mean(0, keepdims=True), N_PTS, 0)
        pa, pb = a["p"], b["p"]
        if a["aberta"] != b["aberta"]:
            pa = reamostra(pa, N_PTS, True); pb = reamostra(pb, N_PTS, True)
        out.append({"p": pa + (pb - pa) * e, "f": _mistura_cor(a["f"], b["f"], e), "l": _mistura_cor(a["l"], b["l"], e),
                    "w": a["w"] + (b["w"] - a["w"]) * e, "aberta": a["aberta"] if e < 0.5 else b["aberta"]})
    return out


# ----------------------------------------------------------------- fervura de linha
def _ruido(seed, n, amp, suave=6):
    r = np.random.default_rng(seed)
    k = max(3, n // suave)
    base = r.normal(0, 1, (k + 1, 2))
    x = np.linspace(0, k, n)
    i = np.floor(x).astype(int); f = (x - i)[:, None]
    i2 = np.minimum(i + 1, k)
    return (base[i] * (1 - f) + base[i2] * f) * amp


def ferve(p, seed, amp=2.6):
    return p + _ruido(seed, len(p), amp)


# ----------------------------------------------------------------- textura
_tex = {}


def textura(w, h, seed=7):
    """papel/guache: grão + manchas leves (multiplicativo, ~0.9–1.04)"""
    k = (w, h, seed)
    if k not in _tex:
        r = np.random.default_rng(seed)
        g = r.normal(0, 1, (h // 4 + 1, w // 4 + 1)).astype(np.float32)
        g = np.asarray(Image.fromarray(((g * 30) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).filter(
            ImageFilter.GaussianBlur(3)), np.float32) / 255
        fino = r.normal(0, 1, (h, w)).astype(np.float32)
        pinc = np.asarray(Image.fromarray(((r.normal(0, 1, (h // 2, w // 2)) * 40) + 128).clip(0, 255).astype(np.uint8)).resize(
            (w, h), Image.BILINEAR).filter(ImageFilter.BoxBlur(1)), np.float32) / 255
        t = 1.0 + (g - 0.5) * 0.10 + fino * 0.018 + (pinc - 0.5) * 0.05
        _tex[k] = np.clip(t, 0.86, 1.08)[..., None]
    return _tex[k]


# ----------------------------------------------------------------- desenhar
SS = 2  # superamostragem


def desenha(img, partes, seed, amp=2.6, alfa=1.0, ofs=(0, 0)):
    """desenha partes num RGBA (já em escala SS). seed muda a cada passo de fervura."""
    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    for i, q in enumerate(partes):
        p = (ferve(q["p"], seed * 131 + i * 17, amp) + ofs) * SS
        xy = [tuple(v) for v in p]
        if len(xy) < 2: continue
        if not q["aberta"] and q["f"] is not None:
            d.polygon(xy, fill=q["f"] + (255,))
        if q["l"] is not None and q["w"] > 0:
            w = max(1, int(q["w"] * SS))
            linha = xy + ([xy[0]] if not q["aberta"] else [])
            d.line(linha, fill=q["l"] + (255,), width=w, joint="curve")
            for v in (linha[0], linha[-1]):
                d.ellipse([v[0] - w / 2, v[1] - w / 2, v[0] + w / 2, v[1] + w / 2], fill=q["l"] + (255,))
    if alfa < 1:
        a = camada.getchannel("A").point(lambda v: int(v * alfa)); camada.putalpha(a)
    img.alpha_composite(camada)
    return img
