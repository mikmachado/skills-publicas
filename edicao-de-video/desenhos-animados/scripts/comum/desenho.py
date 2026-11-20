# Biblioteca comum da estética "desenhos animados".
# Tudo em BGR (OpenCV). Cuidado: se desenhar texto com PIL e compor direto no quadro BGR,
# passe a cor em BGR (tuple(cor)) — usar rgb() aí troca as cores (amarelo vira ciano).
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
AMAR = (110, 226, 255)     # #FFE26E
BR = (255, 255, 255)
ROSA = (163, 79, 255)      # #FF4FA3
LARANJA = (46, 122, 255)   # #FF7A2E
CIANO = (255, 211, 62)     # #3ED3FF
LIMA = (60, 255, 184)      # #B8FF3C
ROXO = (255, 107, 155)     # #9B6BFF
PAL = [AMAR, ROSA, LARANJA, CIANO, LIMA, ROXO]
CORES = {'amarelo': AMAR, 'branco': BR, 'rosa': ROSA, 'laranja': LARANJA,
         'ciano': CIANO, 'lima': LIMA, 'roxo': ROXO}
ESC = (25, 18, 20)         # borda escura de tudo
CF = "/System/Library/Fonts/Avenir Next Condensed.ttc"   # idx 8 = Heavy, 5 = Medium


def rgb(c): return (c[2], c[1], c[0])
def ease(x): x = np.clip(x, 0, 1); return 1 - (1 - x) ** 3
def fonte(s, idx=8): return ImageFont.truetype(CF, s, index=idx)


def masc(j, pasta='mask'):
    """Recorte suave da pessoa (0..1), buracos fechados."""
    m = cv2.imread(f'{pasta}/{j+1:05d}.png', 0).astype(np.float32) / 255
    h, w = m.shape
    b = (m > 0.08).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    fl = b.copy(); cv2.floodFill(fl, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1); b = b | (1 - fl)
    b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return np.maximum(np.clip(m / 0.45, 0, 1), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.5))


def suav_fech(c, s):
    """Suaviza contorno fechado (N,2)."""
    k = cv2.getGaussianKernel(4 * s + 1, s)[:, 0]
    return np.stack([np.convolve(np.r_[c[-2*s:, d], c[:, d], c[:2*s, d]], k, 'same')[2*s:-2*s] for d in range(2)], 1)


def tremer(pts, j, amp=2.2, seed=0):
    """'Boil' de desenho animado: tremida que troca a cada 3 quadros."""
    r = np.random.RandomState(seed + j // 3)
    n = len(pts); k = max(2, n // 40)
    no = r.randn(k + 1, 2) * amp
    idx = np.linspace(0, k, n); f = idx - np.floor(idx); i0 = np.floor(idx).astype(int); i1 = np.minimum(i0 + 1, k)
    return pts + no[i0] * (1 - f[:, None]) + no[i1] * f[:, None]


def parcial(pts, frac):
    """Linha se desenhando: só a fração inicial."""
    n = int(len(pts) * np.clip(frac, 0, 1)); return pts[:n]


def tracejar(pts, dash, gap, off):
    """Tracejado que anda (mude off com o tempo)."""
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    ph = ((d + off) % (dash + gap)) < dash
    segs = []; cur = []
    for p, ok in zip(pts, ph):
        if ok: cur.append(p)
        elif cur:
            if len(cur) > 1: segs.append(np.array(cur))
            cur = []
    if len(cur) > 1: segs.append(np.array(cur))
    return segs


def linha(img, pts, cor, esp):
    if len(pts) < 2: return
    cv2.polylines(img, [np.round(pts * 16).astype(np.int32)], False, cor, esp, cv2.LINE_AA, 4)


def traco(L, A, pts, cor, esp, alpha=1.0):
    """Linha colorida com borda escura (L = cor BGR uint8, A = alpha uint8)."""
    if len(pts) < 2: return
    linha(L, pts, ESC, esp + 7); linha(A, pts, int(235 * alpha), esp + 7)
    linha(L, pts, cor, esp); linha(A, pts, int(255 * alpha), esp)


def sprite(txt, sz, cor, rot=0, stroke=None, idx=8):
    """Palavra em RGBA float (canais em BGR), borda escura, girada."""
    f = fonte(sz, idx); st = stroke or max(5, sz // 16)
    l, tp, rr, b = f.getbbox(txt, stroke_width=st)
    im = Image.new('RGBA', (rr - l + 40, b - tp + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((20 - l, 20 - tp), txt, font=f, fill=tuple(cor) + (255,), stroke_width=st, stroke_fill=ESC + (255,))
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    return np.array(im).astype(np.float32) / 255


def colar(dst, sp, cx, cy, sc=1.0, alpha=1.0):
    """Cola sprite RGBA em dst (H,W,4) centrado em cx,cy com escala."""
    if sc <= 0.02 or alpha <= 0: return
    if abs(sc - 1) > 1e-3: sp = cv2.resize(sp, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
    Hh, Ww = dst.shape[:2]; h, w = sp.shape[:2]; x0 = int(cx - w / 2); y0 = int(cy - h / 2)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(Ww, x0 + w), min(Hh, y0 + h)
    if xa >= xb or ya >= yb: return
    s = sp[ya-y0:yb-y0, xa-x0:xb-x0]; a = s[..., 3:4] * alpha
    dst[ya:yb, xa:xb, :3] = dst[ya:yb, xa:xb, :3] * (1 - a) + s[..., :3] * a
    dst[ya:yb, xa:xb, 3:] = 1 - (1 - dst[ya:yb, xa:xb, 3:]) * (1 - a)


def pop(t, t0, dur=0.35):
    """Escala do 'pop' com rebote suave (0 antes de t0, 1 depois de estabilizar)."""
    p = (t - t0) / dur
    if p <= 0: return 0
    if p >= 2: return 1
    return max(0.15, (1 + 0.25 * np.exp(-5 * p) * np.cos(9 * p)) * min(1, 0.3 + p))


def texto_esp(d, txt, cy, s, track, alpha, idx=8, w=W):
    f = fonte(s, idx); ws = [f.getlength(c) for c in txt]; tot = sum(ws) + track * (len(txt) - 1)
    x = (w - tot) / 2
    for c, ww in zip(txt, ws):
        d.text((x, cy), c, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor='lm',
               stroke_width=5, stroke_fill=(30, 22, 26, int(255 * alpha))); x += ww + track
    return (w - tot) / 2, (w + tot) / 2


def titulo(t, linhas, a0=0.45, b0=4.5, y=330):
    """Título de filme: pequena / GRANDE / pequena, letras se espaçando, filetes amarelos.
    Retorna RGBA float em RGB (use [..., 2::-1] pra BGR) ou None."""
    a1 = b0 - 0.6
    if t < a0 or t > b0: return None
    fade = min(ease((t - a0) / 0.7), 1 - ease((t - a1) / (b0 - a1)) if t > a1 else 1)
    p = (t - a0) / (b0 - a0)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    l1, l2, l3 = linhas
    texto_esp(d, l1, y, 62, 20 + 12 * p, ease((t - a0) / 0.6) * fade, idx=5)
    f2 = fonte(150); sz2 = 150 if f2.getlength(l2) < W - 120 else int(150 * (W - 120) / f2.getlength(l2))
    texto_esp(d, l2, y + 115, sz2, 3 + 5 * p, ease((t - a0 - 0.25) / 0.7) * fade)
    x0, x1 = texto_esp(d, l3, y + 230, 58, 16 + 10 * p, ease((t - a0 - 0.6) / 0.7) * fade, idx=5)
    Lf = ease((t - a0 - 0.7) / 0.8) * 110
    if Lf > 1:
        for xa, xb in [(x0 - 30 - Lf, x0 - 30), (x1 + 30, x1 + 30 + Lf)]:
            d.line([(xa, y + 230), (xb, y + 230)], fill=(30, 22, 26, int(255 * fade)), width=13)
            d.line([(xa, y + 230), (xb, y + 230)], fill=(255, 226, 110, int(255 * fade)), width=6)
    return np.array(im).astype(np.float32) / 255


# rabiscos (formas centradas em 0,0)
def estrela(r_, k=5):
    a = np.linspace(-np.pi/2, 1.5*np.pi, 2*k + 1)[:-1]; rr = np.where(np.arange(2*k) % 2 == 0, r_, r_ * 0.45)
    p = np.stack([np.cos(a) * rr, np.sin(a) * rr], 1); return np.r_[p, p[:1]]
def coracao(r_):
    tt = np.linspace(0, 2*np.pi, 80); x = 16*np.sin(tt)**3; y = -(13*np.cos(tt) - 5*np.cos(2*tt) - 2*np.cos(3*tt) - np.cos(4*tt))
    return np.stack([x, y], 1) * r_ / 17
def espiral(r_):
    tt = np.linspace(0, 5*np.pi, 160); return np.stack([np.cos(tt)*tt, np.sin(tt)*tt], 1) * r_ / (5*np.pi)
def zigue(n):
    return np.array([[k*34 - (n-1)*17, (-26 if k % 2 else 26)] for k in range(int(n))], np.float32)
FORMAS = {'estrela': estrela, 'coracao': coracao, 'espiral': espiral, 'zigue': zigue}


def compor_tinta_linhas(fr, gray, PA, PC, a, col):
    """Tinta com a textura do lugar por baixo + linhas com sombra e brilho."""
    sh = cv2.GaussianBlur(a, (0, 0), 5) * 0.45
    glow = cv2.GaussianBlur(col * a[..., None], (0, 0), 9) * 1.0
    lum = gray.astype(np.float32) / 255; lm = cv2.GaussianBlur(lum, (0, 0), 25) + 1e-3
    tex = np.clip(0.8 + 0.55 * (lum / lm - 1) + 0.15 * lm, 0.45, 1.15)[..., None]
    base = fr * (1 - PA[..., None]) + PC * tex * PA[..., None]
    bg = base * (1 - sh[..., None]); bg = 1 - (1 - bg) * (1 - np.clip(glow, 0, 1))
    return bg * (1 - a[..., None]) + col * a[..., None]


def por_texto(bg, T, bgr=True, sombra=8):
    """Põe camada RGBA (H,W,4) sobre bg com sombra suave."""
    ta = T[..., 3]; tsh = cv2.GaussianBlur(ta, (0, 0), sombra) * 0.5
    c = T[..., :3] if bgr else T[..., 2::-1]
    bg = bg * (1 - tsh[..., None]); return bg * (1 - ta[..., None]) + c * ta[..., None]
