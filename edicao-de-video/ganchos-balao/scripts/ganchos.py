# Ganchos no balão — balão de mensagem destruído de 3 jeitos (1/3, 2/3, 3/3) + CTA escrito no ar com o dedo.
# Tudo que muda de um vídeo para outro fica no projeto.json da pasta do vídeo (ver exemplos/).
# Uso: python3 -I balao.py --ver 30 60 127 140 286 300 420 520   (prévias SDR por QUADRO da fonte)
#      python3 -I balao.py                                       (-> video_mudo.mov HDR HLG)
import sys, math, subprocess, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HDR = os.path.exists("hdr.txt")
SEGS = [(8, 58, "1/3"), (70, 132, "2/3"), (146, 200, "3/3"), (214, 385, None)]

TEXTO = "3 ganchos que ninguém pula"
CTA1, CTA2, SUB = "COMENTE", "GANCHO", ""
TEAL = (255, 138, 50)
TEAL_ESC = (150, 62, 8)

K = 1.04                                   # escala do balão
BX, BY, BH = 540, 380, int(170 * K)
BW = int(ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", int(60 * K)).getlength(TEXTO) + 90 * K)       # centro e tamanho do balão
PAD = 70
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
MF = "/System/Library/Fonts/MarkerFelt.ttc"
def fnt(p, s, i=0): return ImageFont.truetype(p, s, index=i)

def suave(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def ease_back(x, s=2.2):
    x = min(max(x, 0.0), 1.0) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, t): return a + (b - a) * t
def interp(keys, n):
    ks = sorted(keys)
    if n <= ks[0]: return np.array(keys[ks[0]], float)
    if n >= ks[-1]: return np.array(keys[ks[-1]], float)
    for a, b in zip(ks, ks[1:]):
        if a <= n <= b:
            t = suave((n - a) / (b - a)); return np.array(keys[a], float) * (1 - t) + np.array(keys[b], float) * t

# ---------------- balão ----------------
_bc = {}
def balao(estado, texto=True):
    if (estado, texto) in _bc: return _bc[(estado, texto)]
    S = 2
    w, h = (BW + 2 * PAD) * S, (BH + 2 * PAD) * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = PAD * S, PAD * S, (PAD + BW) * S, (PAD + BH) * S
    cor, ct, ch, cv = PALETAS[COR][estado]
    # sombra
    sh = Image.new("L", (w, h), 0); ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10 * S, x1, y1 + 10 * S), int(34 * K) * S, fill=90)
    sh = sh.filter(ImageFilter.GaussianBlur(14 * S))
    # brilho (aceso)
    gl = Image.new("L", (w, h), 0)
    if estado == "aceso":
        ImageDraw.Draw(gl).rounded_rectangle((x0 - 8 * S, y0 - 8 * S, x1 + 8 * S, y1 + 8 * S), 38 * S, fill=200)
        gl = gl.filter(ImageFilter.GaussianBlur(26 * S))
    d.rounded_rectangle((x0, y0, x1, y1), int(34 * K) * S, fill=cor + (255,))
    d.polygon([(x1 - 46 * K * S, y0), (x1 + 31 * K * S, y0), (x1 - 6 * K * S, y0 + 40 * K * S)], fill=cor + (255,))   # rabinho
    f = fnt(HN, int(60 * K) * S, 0); fh = fnt(HN, int(32 * K) * S, 0)
    bb = f.getbbox(TEXTO)
    if texto:
        d.text((x0 + 45 * K * S, y0 + 0.40 * (y1 - y0) - (bb[1] + bb[3]) / 2), TEXTO, font=f, fill=ct + (255,))
        d.text((x1 - 172 * K * S, y1 - 52 * K * S), "19:51", font=fh, fill=ch + (255,))
        # ✓✓
        for k in (0, 16):
            xx = x1 - 84 * K * S + k * K * S; yy = y1 - 32 * K * S
            d.line([(xx, yy), (xx + 9 * K * S, yy + 9 * K * S), (xx + 29 * K * S, yy - 12 * K * S)], fill=cv + (255,), width=int(4 * K * S))
    im = im.resize((w // S, h // S), Image.LANCZOS)
    sh = np.asarray(sh.resize((w // S, h // S)), np.float32) / 255
    gl = np.asarray(gl.resize((w // S, h // S)), np.float32) / 255
    A = np.asarray(im, np.float32) / 255
    out = np.zeros_like(A)
    # brilho verde-claro por baixo, depois sombra, depois o balão
    base_rgb = np.zeros(A.shape[:2] + (3,), np.float32)
    base_a = np.zeros(A.shape[:2], np.float32)
    if estado == "aceso":
        base_rgb[:] = np.array(PALETAS[COR]["brilho"], np.float32) / 255; base_a = gl * 0.75
    a_sh = sh * 0.45 * (1 - base_a)
    rgb = base_rgb * base_a[..., None] / np.maximum(base_a + a_sh, 1e-4)[..., None]
    a2 = base_a + a_sh
    a = A[..., 3]
    out[..., :3] = (A[..., :3] * a[..., None] + rgb * (a2 * (1 - a))[..., None]) / np.maximum(a + a2 * (1 - a), 1e-4)[..., None]
    out[..., 3] = a + a2 * (1 - a)
    _bc[(estado, texto)] = out
    return out

def colar(out, A, M, alpha=1.0, occl=None, hdr=False, ganho=0.38):
    """A: RGBA float; M: afim 2x3 de A -> quadro."""
    h, w = A.shape[:2]
    P = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], np.float32) @ M.T
    x0, y0 = np.floor(P.min(0)).astype(int) - 2; x1, y1 = np.ceil(P.max(0)).astype(int) + 2
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if X1 <= X0 or Y1 <= Y0 or alpha <= 0: return
    M2 = M.copy(); M2[:, 2] -= [X0, Y0]
    R = cv2.warpAffine(A, M2, (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    a = R[..., 3:4] * alpha
    if occl is not None: a = a * (1 - occl[Y0:Y1, X0:X1, None])
    cor = R[..., :3]
    if hdr: cor = srgb_para_hlg(cor, ganho)
    out[Y0:Y1, X0:X1] = out[Y0:Y1, X0:X1] * (1 - a) + cor * a

def afim(cx, cy, w, h, sx=1.0, sy=1.0, ang=0.0, ox=None, oy=None):
    """leva o centro (ox,oy) da imagem w x h para (cx,cy), com escala e rotação (graus)."""
    ox = w / 2 if ox is None else ox; oy = h / 2 if oy is None else oy
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    R = np.array([[c * sx, -s * sy], [s * sx, c * sy]], np.float32)
    t = np.array([cx, cy], np.float32) - R @ np.array([ox, oy], np.float32)
    return np.hstack([R, t[:, None]]).astype(np.float32)

M709_2020 = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]], np.float32)
def srgb_para_hlg(rgb, ganho=0.38):
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4) * ganho
    e = np.clip(lin @ M709_2020.T, 0, 1)
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    return np.where(e <= 1 / 12, np.sqrt(3 * e), a * np.log(np.maximum(12 * e - b, 1e-6)) + c).astype(np.float32)

# ---------------- máscaras ----------------
def mascara(n):
    p = f"mask/{n:04d}.png"
    if not os.path.exists(p): return np.zeros((H, W), np.float32)
    m = cv2.imread(p, 0).astype(np.float32) / 255
    m = np.clip((m - 0.35) / 0.3, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 1.5)

_fundo = {}
def pele_bruta(n):
    fr = cv2.imread(f"quadros/{n:04d}.jpg")
    if ESPELHAR_CTA: fr = fr[:, ::-1]
    ycc = cv2.cvtColor(fr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    cr, cb = ycc[..., 1], ycc[..., 2]
    return np.clip((cr - 138) / 10, 0, 1) * np.clip((122 - cb) / 10, 0, 1)

def pele_fundo():
    """pele que está lá em quase todos os quadros do CTA (pescoço, rosto) — não é a mão."""
    if "f" in _fundo: return _fundo["f"]
    if os.path.exists("pele_fundo.npy"): _fundo["f"] = np.load("pele_fundo.npy"); return _fundo["f"]
    a, b = SEGS[-1][0], SEGS[-1][1]
    st = np.stack([pele_bruta(k) for k in range(a, b + 1, 3)])
    f = np.percentile(st, 30, axis=0).astype(np.float32)
    f = cv2.dilate(f, np.ones((15, 15), np.uint8))
    np.save("pele_fundo.npy", f); _fundo["f"] = f; return f

DEDO_Y = {226: 830, 232: 830, 238: 890, 244: 830, 250: 830, 256: 794, 262: 974, 268: 974, 274: 938, 280: 974,
          286: 974, 292: 950, 298: 986, 304: 986, 310: 962, 316: 914, 322: 998, 328: 962, 334: 962, 340: 842}
# mão que escreve, pelos pontos do Vision (pulso, dedos) — nada de pescoço/rosto
_MAOS = None
def pontos_mao(n):
    global _MAOS
    if _MAOS is None:
        _MAOS = {}
        if os.path.exists("maos_cta.json"):
            d = _json.load(open("maos_cta.json")); a0 = SEGS[-1][0]
            for i, maos in enumerate(d):
                for m in maos:
                    t = m.get("indexTip")
                    if t and t[1] < 1250 and t[2] > 0.3:
                        _MAOS[a0 + i] = np.array([v[:2] for v in m.values() if v[2] > 0.2], np.float32)
    if n in _MAOS: return _MAOS[n]
    viz = [k for k in _MAOS if abs(k - n) <= 3]
    if not viz: return None
    k0 = max([k for k in viz if k < n], default=None); k1 = min([k for k in viz if k > n], default=None)
    if k0 is None or k1 is None:
        return _MAOS[k0 if k1 is None else k1]
    c0, c1 = _MAOS[k0].mean(0), _MAOS[k1].mean(0); t = (n - k0) / (k1 - k0)
    return _MAOS[k0] + (c0 * (1 - t) + c1 * t - c0)          # a mão de k0 levada até a posição interpolada

def zona_mao(n):
    """máscara da mão que escreve: casco dos pontos do Vision, um pouco engordado (só durante a escrita)."""
    jan = (LINHAS_CTA[0][4][0] - 4, LINHAS_CTA[-1][4][1] + 6)
    z = np.zeros((H, W), np.float32)
    if not (jan[0] <= n <= jan[1]): return z
    P = pontos_mao(n)
    if P is None or len(P) < 3: return z
    hull = cv2.convexHull(P.astype(np.int32))
    cv2.fillConvexPoly(z, hull, 1.0, cv2.LINE_AA)
    z = cv2.dilate(z, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
    return cv2.GaussianBlur(z, (0, 0), 5)

def pele(n, m):
    """mão (pele) na frente do texto do CTA: pele dentro da pessoa, abaixo do queixo."""
    z = zona_mao(n)
    s = np.clip(pele_bruta(n) * 1.6, 0, 1) * z
    s = np.maximum(s, np.clip((z - 0.6) / 0.4, 0, 1) * 0.0)
    pass
    s = cv2.morphologyEx(s, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    s = cv2.dilate(s, np.ones((7, 7), np.uint8))
    return cv2.GaussianBlur(s, (0, 0), 2.5)

# ---------------- contador ----------------
_cc = {}
def contador(s):
    if s in _cc: return _cc[s]
    f = fnt(HN, 50, 10); bb = f.getbbox(s)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    letra, halo = ((35, 35, 35), 1.0) if CONTADOR_ESCURO else ((255, 255, 255), 0.0)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((30 - bb[0], 30 - bb[1]), s, font=f, fill=letra + (255,))
    sh = Image.new("L", (w, h), 0); ImageDraw.Draw(sh).text((30 - bb[0], 30 - bb[1]), s, font=f, fill=200, stroke_width=6)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    T = np.asarray(im, np.float32) / 255
    A = np.zeros_like(T); ta = T[..., 3:4]; A[..., :3] = T[..., :3] * ta + halo * (1 - ta); A[..., 3] = T[..., 3] + sh * 0.8 * (1 - T[..., 3])
    _cc[s] = A; return A

# ---------------- 1/3: cordinha ----------------
ANC = np.array([BX - BW / 2 + 40, BY + BH / 2])            # recalculado em carregar_projeto()
REPOUSO = ANC + [10, 85]
PUNHO = {18: (235, 560), 20: (259, 525), 23: (267, 525), 26: (267, 535), 29: (267, 560), 32: (286, 676),
         35: (275, 844), 41: (275, 844), 44: (275, 852), 46: (278, 880)}
PEGA, SOLTA, ACENDE = 17, 46, 33

def bolinha(n):
    if n < PEGA:
        sw = math.sin(n * 0.35) * 6
        return REPOUSO + [sw, 0], False
    if n <= SOLTA:
        p = interp(PUNHO, n) + [0, -12]
        if n < 19: p = REPOUSO * (1 - (n - PEGA) / 2) + p * ((n - PEGA) / 2)
        return p, True
    p0 = interp(PUNHO, SOLTA) + [0, -12]
    t = (n - SOLTA) / FPS
    k = math.exp(-5.5 * t) * math.cos(16 * t)
    return REPOUSO + (p0 - REPOUSO) * k, False

def desenhar_corda(out, n, occl, hdr):
    p, preso = bolinha(n)
    lay = np.zeros((H, W, 4), np.float32)
    a = tuple(int(v) for v in ANC); b = tuple(int(v) for v in p)
    tmp = np.zeros((H, W, 3), np.uint8); al = np.zeros((H, W), np.uint8)
    cv2.line(al, a, b, 255, 6, cv2.LINE_AA); cv2.line(tmp, a, b, (55, 55, 55), 6, cv2.LINE_AA)
    cv2.line(tmp, a, b, (236, 236, 230), 3, cv2.LINE_AA)
    cv2.circle(al, b, 13, 255, -1, cv2.LINE_AA); cv2.circle(tmp, b, 13, (60, 60, 60), -1, cv2.LINE_AA)
    cv2.circle(tmp, b, 11, (214, 196, 150), -1, cv2.LINE_AA)            # bolinha dourada
    cv2.circle(tmp, (b[0] - 4, b[1] - 4), 4, (255, 250, 235), -1, cv2.LINE_AA)
    lay[..., :3] = tmp.astype(np.float32) / 255; lay[..., 3] = al.astype(np.float32) / 255
    colar(out, lay, np.float32([[1, 0, 0], [0, 1, 0]]), 1.0, occl, hdr)

def queda_balao(n):
    """o balão desce um pouco quando a corda é puxada e volta com mola."""
    if n < 29: return 0.0
    if n <= SOLTA:
        p, _ = bolinha(n); return min(14.0, max(0.0, (p[1] - REPOUSO[1]) * 0.05))
    t = (n - SOLTA) / FPS
    return 14 * math.exp(-6 * t) * math.cos(18 * t)

# ---------------- cacos (2/3) e pedaços (3/3) ----------------
def gerar_cacos(seed, npts, texto=True):
    rng = np.random.default_rng(seed)
    A = balao("aceso", texto); h, w = A.shape[:2]
    pts = [(PAD + x, PAD + y) for x in np.linspace(0, BW, 5) for y in (0, BH)] + [(PAD, PAD + BH / 2), (PAD + BW, PAD + BH / 2)]
    pts += [(PAD + rng.uniform(10, BW - 10), PAD + rng.uniform(8, BH - 8)) for _ in range(npts)]
    sub = cv2.Subdiv2D((0, 0, w, h))
    for p in pts: sub.insert((float(p[0]), float(p[1])))
    cacos = []
    for t in sub.getTriangleList():
        tri = t.reshape(3, 2)
        if (tri < 0).any() or (tri[:, 0] > w).any() or (tri[:, 1] > h).any(): continue
        x0, y0 = np.floor(tri.min(0)).astype(int); x1, y1 = np.ceil(tri.max(0)).astype(int) + 1
        if x1 - x0 < 3 or y1 - y0 < 3: continue
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillConvexPoly(m, np.int32(np.round(tri - [x0, y0])), 255, cv2.LINE_AA)
        P = A[y0:y1, x0:x1].copy(); P[..., 3] *= m.astype(np.float32) / 255
        # aresta de vidro: contorno claro
        e = np.zeros_like(m); cv2.polylines(e, [np.int32(np.round(tri - [x0, y0]))], True, 255, 2, cv2.LINE_AA)
        ef = e.astype(np.float32)[..., None] / 255 * 0.85
        P[..., :3] = P[..., :3] * (1 - ef) + ef
        P[..., 3] = np.maximum(P[..., 3], e.astype(np.float32) / 255 * 0.9 * (m > 0))
        if P[..., 3].max() < 0.2: continue
        c = tri.mean(0)
        cacos.append(dict(img=P, c=c - [PAD + BW / 2, PAD + BH / 2], o=c - [x0, y0], area=cv2.contourArea(tri.astype(np.float32)),
                          r=rng.uniform(-1, 1), u=rng.uniform(0, 1), v=rng.uniform(0, 1)))
    return cacos

CACOS = None; PEDACOS = None
IMPACTO, NA_CABECA = 83, 97
CABECA = np.array([575.0, 800.0])
G = 2.4

def pos_caco(k, i, n):
    dt = n - IMPACTO
    c0 = np.array([BX, BY]) + k["c"]
    if k.get("cabeca"):
        T = NA_CABECA - IMPACTO
        if dt <= T:
            v0 = (CABECA - c0 - 0.5 * np.array([0, G]) * T * T) / T
            return c0 + v0 * dt + 0.5 * np.array([0, G]) * dt * dt, k["r"] * 9 * dt
        d2 = dt - T
        return CABECA + np.array([-7, -14]) * d2 + 0.5 * np.array([0, G]) * d2 * d2, k["r"] * 9 * T - 14 * d2
    imp = np.array(PONTO_SOCO, float)
    dirv = c0 - imp; dirv = dirv / (np.linalg.norm(dirv) + 1e-6)
    a = math.radians(-160 + 140 * k["v"])            # leque para cima, espalhado
    sp = 7 + 15 * k["u"]
    v0 = 0.5 * dirv * sp + np.array([math.cos(a), math.sin(a)]) * sp
    return c0 + v0 * dt + 0.5 * np.array([0, G]) * dt * dt, k["r"] * 14 * dt

CONTATO, ESTOURO = 165, 179
def pos_pedaco(k, i, n):
    dt = n - ESTOURO
    c0 = np.array([BX, BY + 40]) + k["c"] * [1, 0.45]
    a = math.radians(-170 + 200 * k["v"])
    sp = 6 + 14 * k["u"]
    v0 = np.array([math.cos(a), math.sin(a)]) * sp + np.array([-3, 2])
    return c0 + v0 * dt + 0.5 * np.array([0, 2.6]) * dt * dt, k["r"] * 20 * dt

def fumaca(out, n, hdr):
    dt = n - ESTOURO
    if dt < 0 or dt > 30: return
    rng = np.random.default_rng(7)
    h2, w2 = H // 2, W // 2
    lay = np.zeros((h2, w2), np.float32)
    cresce = 0.35 + 0.9 * (1 - math.exp(-dt / 4))
    for j in range(26):
        ang = rng.uniform(0, 2 * math.pi); d = rng.uniform(0, 1) ** 0.6 * 150
        cx = (BX + math.cos(ang) * d * 1.3 * cresce) / 2
        cy = (BY + 30 + math.sin(ang) * d * 0.7 * cresce - dt * 2.5) / 2
        r = (38 + rng.uniform(0, 40)) * cresce / 2
        cv2.circle(lay, (int(cx), int(cy)), max(int(r), 1), 1.0, -1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 5)
    sombra = cv2.GaussianBlur(np.roll(lay, (-9, -7), (0, 1)), (0, 0), 7)       # luz de cima-esquerda
    c = np.clip(0.86 - 0.42 * (lay - sombra * 0.9).clip(0, 1) - 0.12 * cv2.GaussianBlur(lay, (0, 0), 14), 0.3, 0.95)
    fade = 1 - suave((dt - 8) / 22)
    a = cv2.resize(lay, (W, H)) * 0.97 * fade
    c = cv2.resize(c, (W, H))
    A = np.dstack([c * 0.95, c * 0.96, c, a]).astype(np.float32)
    colar(out, A, np.float32([[1, 0, 0], [0, 1, 0]]), 1.0, None, hdr)

def estrela_impacto(out, n, hdr, p, n0, cor=(255, 255, 255)):
    dt = n - n0
    if dt < 0 or dt > 5: return
    lay = np.zeros((H, W), np.uint8)
    for j in range(10):
        ang = j * math.pi / 5 + 0.3
        r0, r1 = 30 + dt * 25, 80 + dt * 40
        cv2.line(lay, (int(p[0] + math.cos(ang) * r0), int(p[1] + math.sin(ang) * r0)),
                 (int(p[0] + math.cos(ang) * r1), int(p[1] + math.sin(ang) * r1)), 255, 7 - dt, cv2.LINE_AA)
    a = lay.astype(np.float32) / 255 * (1 - dt / 6)
    A = np.dstack([np.full_like(a, cor[0] / 255), np.full_like(a, cor[1] / 255), np.full_like(a, cor[2] / 255), a])
    colar(out, A, np.float32([[1, 0, 0], [0, 1, 0]]), 1.0, None, hdr)

# ---------------- CTA escrito no ar ----------------
DEDO = {226: 590, 232: 530, 238: 650, 244: 686, 250: 770, 256: 686, 262: 482, 268: 482, 274: 494, 280: 494,
        286: 530, 292: 566, 298: 566, 304: 566, 310: 614, 316: 650, 322: 698, 328: 710, 334: 758}   # já espelhado
# (texto, tamanho, centro x, linha de base y, janela da mão, faixa x do dedo)
LINHAS_CTA = [(CTA1, 138, 615, 935, (224, 258), (440, 790)),
              (CTA2, 165, 600, 1110, (260, 336), (475, 726))]
T_SUBL, T_SUB = 337, (9999, 9999)

def preparar_cta():
    itens = []
    for txt, tam, cx, yb, jan, fx in LINHAS_CTA:
        f = fnt(MF, tam, 1)
        larg = f.getlength(txt); x = cx - larg / 2; asc = f.getbbox("H")
        letras = []
        for ch in txt:
            bb = f.getbbox(ch); w, h = int(bb[2] - bb[0] + 40), int(bb[3] - bb[1] + 40)
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((20 - bb[0], 20 - bb[1]), ch, font=f, fill=TEAL + (255,), stroke_width=3, stroke_fill=TEAL_ESC + (255,))
            T = np.asarray(im, np.float32) / 255
            sh = cv2.GaussianBlur(T[..., 3], (0, 0), 6) * 0.45
            A = np.zeros_like(T); A[..., :3] = T[..., :3]; A[..., 3] = T[..., 3] + sh * (1 - T[..., 3])
            letras.append((A, x + bb[0] - 20, yb - (asc[3] - asc[1]) + bb[1] - asc[1] - 20))
            x += f.getlength(ch)
        itens.append((letras, cx - larg / 2, cx + larg / 2, jan, fx))
    return itens

LETRAS = None
import json as _json
_TR = {int(k): np.array(v) for k, v in _json.load(open("dedo.json")).items()} if os.path.exists("dedo.json") else {}
def ponta(n):
    if not _TR: return np.array([float(interp(DEDO, n)), float(interp(DEDO_Y, n))])
    n = min(max(n, min(_TR)), max(_TR)); return _TR[n]

_prog = {}
def progresso_linha(jan):
    """progresso da escrita quadro a quadro: metade pelo quanto o dedo andou (traços), metade por até onde ele foi
    para a direita. Só avança; chega a 1 no fim da janela."""
    if jan in _prog: return _prog[jan]
    a, b = jan
    P = np.array([ponta(n) for n in range(a, b + 1)])
    passo = np.r_[0, np.linalg.norm(np.diff(P, axis=0), axis=1)]
    passo = np.where(passo > 1.5, passo, 0)                 # parada = não escreve
    cam = np.cumsum(passo); cam /= max(cam[-1], 1e-6)
    xm = np.maximum.accumulate(P[:, 0]); xr = (xm - xm[0]) / max(xm[-1] - xm[0], 1e-6)
    p = np.maximum.accumulate(0.3 * cam + 0.7 * xr)
    p = p / max(p[-1], 1e-6)
    _prog[jan] = p; return p

def frente(n, jan, fx, x0, x1):
    """até onde a linha já foi escrita (em x do texto), seguindo o dedo."""
    if n < jan[0]: return -1e9
    if n >= jan[1]: return 1e9
    p = progresso_linha(jan)[n - jan[0]]
    return x0 + (x1 - x0) * p

def revelar(A, t):
    """escrita: varredura diagonal (de cima-esquerda para baixo-direita)."""
    if t >= 1: return A
    if t <= 0: return None
    h, w = A.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    s = (xx / w * 0.75 + yy / h * 0.25)
    m = np.clip((t * 1.15 - s) / 0.08, 0, 1)
    B = A.copy(); B[..., 3] *= m; return B

_sub = {}
def sublinhado():
    if "s" in _sub: return _sub["s"]
    txt, tam, cx, yb = LINHAS_CTA[1][:4]
    f = fnt(MF, tam, 1); larg = f.getlength(txt)
    w, h = int(larg + 100), 70
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(30 + i * (w - 60) / 40, 35 + 7 * math.sin(i / 40 * 3.0) - i * 0.25) for i in range(41)]
    d.line(pts, fill=TEAL_ESC + (255,), width=17, joint="curve"); d.line(pts, fill=TEAL + (255,), width=12, joint="curve")
    A = np.asarray(im, np.float32) / 255
    _sub["s"] = (A, cx - w / 2, yb + 8); return _sub["s"]

_sb = {}
def subtitulo():
    if "s" in _sb: return _sb["s"]
    f = fnt(HN, 44, 10); bb = f.getbbox(SUB)
    w, h = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((30 - bb[0], 30 - bb[1]), SUB, font=f, fill=(255, 255, 255, 255))
    sh = Image.new("L", (w, h), 0); ImageDraw.Draw(sh).text((30 - bb[0], 32 - bb[1]), SUB, font=f, fill=200)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(7)), np.float32) / 255
    T = np.asarray(im, np.float32) / 255
    A = np.zeros_like(T); A[..., :3] = T[..., :3]; A[..., 3] = T[..., 3] + sh * (1 - T[..., 3])
    _sb["s"] = (A, W / 2 - w / 2, LINHAS_CTA[1][3] + 70); return _sb["s"]

def cta(out, n, hdr):
    global LETRAS
    if LETRAS is None: LETRAS = preparar_cta()
    sk = None   # escrita SEMPRE na frente, como se fosse escrita na lente da câmera
    for letras, x0, x1, jan, fx in LETRAS:
        fr = frente(n, jan, fx, x0, x1)
        for A, x, y in letras:
            t = (fr - x - 20) / max(A.shape[1] - 40, 1)
            B = revelar(A, t)
            if B is not None: colar(out, B, np.float32([[1, 0, x], [0, 1, y]]), 1.0, sk, hdr)
    if n >= T_SUBL:
        A, x, y = sublinhado(); t = suave((n - T_SUBL) / 13)
        B = A.copy(); B[..., 3] *= (np.arange(A.shape[1])[None, :] < t * A.shape[1])
        colar(out, B, np.float32([[1, 0, x], [0, 1, y]]), 1.0, sk, hdr)
    if n >= T_SUB[0]:
        A, x, y = subtitulo(); t = suave((n - T_SUB[0]) / (T_SUB[1] - T_SUB[0]))
        colar(out, A, np.float32([[1, 0, x], [0, 1, y + 18 * (1 - t)]]), t, None, hdr)

# ---------------- 3/3: apagar a mensagem com a mão (por trás do balão) ----------------
MAO3 = {196: 1000, 199: 940, 205: 846, 211: 729, 217: 710, 220: 700, 223: 729, 226: 719, 229: 467, 232: 457,
        235: 350, 238: 243}
def apagando(n):
    if not MAO3: return balao("aceso")
    A = balao("aceso"); B = balao("aceso", False)
    ks = [k for k in sorted(MAO3) if k <= n]
    if not ks: return A
    xm = min([MAO3[k] for k in ks] + [float(interp(MAO3, n))])
    if n >= CONTATO + 1: xm = -999
    xl = xm - 70 - (BX - BW / 2 - PAD)            # x da mão no balão (a palma apaga um pouco à frente)
    X = np.arange(A.shape[1], dtype=np.float32)
    k = np.clip((xl - X) / 50.0, 0, 1)[None, :, None]   # 1 = texto ainda lá
    return B * (1 - k) + A * k

# ---------------- 3/3: tesoura corta o balão ----------------
CORTE = [(385.0, 462.0), (430.0, 318.0)]       # da base (onde estão os dedos) até o topo
TIQUES = [166, 170, 174, 178]                   # cada "tesourada" avança o corte
def x_corte(yi, A):
    """x do corte (coordenada da imagem do balão) para a linha yi."""
    (xa, ya), (xb, yb) = CORTE
    ox, oy = BX - A.shape[1] / 2, BY - A.shape[0] / 2
    y = yi + oy
    t = (y - ya) / (yb - ya)
    zig = 7 * ((np.floor((y - yb) / 14) % 2) * 2 - 1)        # corte em zigue-zague, de tesoura
    return xa + (xb - xa) * t + zig - ox

def progresso_corte(n):
    p = 0.0
    for i, t in enumerate(TIQUES):
        if n >= t: p = (i + 1) / len(TIQUES) * suave(min(1, (n - t + 1) / 2)) + i / len(TIQUES) * (1 - suave(min(1, (n - t + 1) / 2)))
    return p

def cortando(A, n):
    p = progresso_corte(n)
    if p <= 0: return A
    h, w = A.shape[:2]
    yy = np.arange(h, dtype=np.float32)
    xc = x_corte(yy, A)
    oy = BY - h / 2
    ybase, ytopo = CORTE[0][1] - oy, CORTE[1][1] - oy
    yfim = ybase + (ytopo - ybase) * p                      # até onde já cortou (de baixo p/ cima)
    X = np.arange(w, dtype=np.float32)[None, :]
    d = np.abs(X - xc[:, None])
    fenda = np.clip(1 - (d - 1.5) / 1.5, 0, 1) * ((yy >= yfim - 2)[:, None])
    B = A.copy(); B[..., 3] *= 1 - fenda
    return B

_met = {}
def metades(A, n):
    if "m" not in _met:
        h, w = A.shape[:2]
        xc = x_corte(np.arange(h, dtype=np.float32), A)
        X = np.arange(w, dtype=np.float32)[None, :]
        esq = np.clip((xc[:, None] - X) / 1.5 + 0.5, 0, 1)
        L = A.copy(); L[..., 3] *= esq; R = A.copy(); R[..., 3] *= 1 - esq
        _met["m"] = (L, R)
    L, R = _met["m"]
    h, w = A.shape[:2]
    dt = n - ESTOURO
    piv = np.array(CORTE[0]) * 0.5 + np.array(CORTE[1]) * 0.5
    ox, oy = BX - w / 2, BY - h / 2
    res = []
    for img, sg, vx in ((L, -1, -5.0), (R, 1, 4.0)):
        cx = piv[0] + vx * dt + sg * 6 * min(dt, 3)
        cy = piv[1] + 0.5 * 2.2 * max(dt - 2, 0) ** 2 - 4 * min(dt, 3)
        ang = sg * (2.5 * dt + 0.25 * dt * dt)
        res.append((img, afim(cx, cy, w, h, 1, 1, ang, piv[0] - ox, piv[1] - oy)))
    return res

# ---------------- composição ----------------
def luz_balao(out, hdr, forca):
    """o balão aceso ilumina o boné/rosto: brilho suave verde-claro somado."""
    if forca <= 0: return
    yy, xx = np.ogrid[0:H, 0:W]
    g = np.exp(-(((xx - BX) / 420.0) ** 2 + ((yy - BY - 120) / 260.0) ** 2)).astype(np.float32) * forca
    add = np.array(PALETAS[COR]["luz"], np.float32) * (0.09 if hdr else 0.12)
    out += g[..., None] * add

def compor(n, fr, hdr, seg):
    out = fr.copy()
    lab = seg[2]
    if lab is None:
        if ESPELHAR_CTA: out = np.ascontiguousarray(out[:, ::-1])
        cta(out, n, hdr); return out
    m = mascara(n)
    # ---- 1/3: apagado -> acende com a cordinha
    if lab == "1/3":
        aceso = n >= ACENDE + 4 or n in (ACENDE, ACENDE + 2)
        if not aceso: out *= 0.86
        else: luz_balao(out, hdr, 1.0)
        dy = queda_balao(n)
        A = balao("aceso" if aceso else "apagado")
        desenhar_corda(out, n, m, hdr)
        colar(out, A, afim(BX, BY + dy, A.shape[1], A.shape[0]), 1.0, m, hdr)
    # ---- 2/3: soco -> cacos de vidro, um cai na cabeça
    elif lab == "2/3":
        global CACOS
        if n < IMPACTO:
            luz_balao(out, hdr, 1.0)
            A = balao("aceso"); sq = 1.0
            if n >= IMPACTO - 2: sq = 0.93
            colar(out, A, afim(BX, BY, A.shape[1], A.shape[0], 1 / sq ** 0.5, sq, -2 if n >= IMPACTO - 2 else 0), 1.0, m, hdr)
        else:
            if CACOS is None:
                CACOS = gerar_cacos(3, 9)
                # o caco grande mais perto do meio vai na cabeça
                j = max(range(len(CACOS)), key=lambda i: CACOS[i]["area"] - 6 * abs(CACOS[i]["c"][0] + 70))
                CACOS[j]["cabeca"] = True
            luz_balao(out, hdr, max(0.0, 1 - (n - IMPACTO) / 4))
            estrela_impacto(out, n, hdr, (PONTO_SOCO[0], PONTO_SOCO[1] - 5), IMPACTO)
            for i, k in enumerate(CACOS):
                p, ang = pos_caco(k, i, n)
                if p[1] > H + 100: continue
                colar(out, k["img"], afim(p[0], p[1], 0, 0, 1, 1, ang, k["o"][0], k["o"][1]), 1.0, None, hdr)
            if NA_CABECA <= n <= NA_CABECA + 4:
                estrela_impacto(out, n, hdr, CABECA + [0, -10], NA_CABECA, (255, 250, 200))
    # ---- 3/3: aparece; o tapa esmaga e explode
    elif lab == "3/3":
        A = balao("aceso")
        e = ease_back((n - seg[0]) / 9)
        luz_balao(out, hdr, 1.0 if n < ESTOURO else max(0.0, 1 - (n - ESTOURO) / 8))
        if MODO3 == "tesoura":                      # dedos em V cortam o balão em 2 metades
            if n < ESTOURO:
                sc = max(e, 0.02)
                colar(out, cortando(A, n), afim(BX, BY, A.shape[1], A.shape[0], sc, sc), 1.0, m, hdr)
            else:
                for p in metades(A, n): colar(out, p[0], p[1], 1.0, m, hdr)
                estrela_impacto(out, n, hdr, (CORTE[0][0], CORTE[0][1] - 10), ESTOURO, (255, 240, 220))
        else:                                       # "cutucao" (dedo estoura) ou "apagar" (mão apaga por trás)
            global PEDACOS
            if n < ESTOURO:
                sx = sy = max(e, 0.02); dy = 0; ang = 0
                if n >= CONTATO:
                    k = (n - CONTATO + 1) / max(ESTOURO - CONTATO, 1)
                    if MODO3 == "cutucao": sx, sy, dy, ang = 1 + 0.10 * k, 1 - 0.22 * k, -14 * k, 4 * k
                    else: sx, sy, dy, ang = 1 + 0.25 * k, 1 - 0.55 * k, 45 * k, -8 * k
                B = apagando(n) if MODO3 == "apagar" else A
                colar(out, B, afim(BX, BY + dy, A.shape[1], A.shape[0], sx, sy, ang), 1.0, None if MODO3 == "apagar" else m, hdr)
            else:
                if PEDACOS is None: PEDACOS = gerar_cacos(11, 6, MODO3 != "apagar")
                fumaca(out, n, hdr)
                for i, k in enumerate(PEDACOS):
                    p, ang = pos_pedaco(k, i, n)
                    if p[1] > H + 100: continue
                    colar(out, k["img"], afim(p[0], p[1], 0, 0, 1, 1, ang, k["o"][0], k["o"][1]), 1.0, None, hdr)
                estrela_impacto(out, n, hdr, tuple(PONTO_3), ESTOURO)
    C = contador(lab)
    colar(out, C, np.float32([[1, 0, W / 2 - C.shape[1] / 2], [0, 1, 40]]), 1.0, None, hdr)
    return out

# ---------------- projeto.json ----------------
PALETAS = {
    "laranja": {"aceso": ((255, 136, 48), (255, 255, 255), (255, 228, 205), (255, 255, 255)),
                "apagado": ((122, 76, 44), (78, 46, 24), (96, 60, 36), (96, 60, 36)),
                "brilho": (255, 190, 120), "luz": (1.0, 0.78, 0.55)},
    "verde": {"aceso": ((217, 253, 211), (17, 27, 33), (102, 119, 129), (83, 189, 235)),      # WhatsApp
              "apagado": ((96, 116, 98), (44, 56, 46), (70, 86, 72), (62, 84, 70)),
              "brilho": (200, 255, 210), "luz": (0.80, 1.0, 0.85)},
}
COR, MODO3, ESPELHAR_CTA, CONTADOR_ESCURO, ANCORA = "laranja", "tesoura", False, False, "esquerda"
PONTO_SOCO, PONTO_3 = [420.0, 455.0], [355.0, 455.0]

def _chaves_int(d): return {int(k): v for k, v in d.items()}
def carregar_projeto(caminho="projeto.json"):
    """lê o projeto.json e sobrescreve os ajustes deste módulo."""
    global SEGS, TEXTO, CTA1, CTA2, TEAL, TEAL_ESC, K, BX, BY, BH, BW, ANC, REPOUSO, PUNHO, PEGA, SOLTA, ACENDE
    global IMPACTO, NA_CABECA, CABECA, CONTATO, ESTOURO, CORTE, TIQUES, MAO3, LINHAS_CTA, T_SUBL, DEDO, DEDO_Y
    global COR, MODO3, ESPELHAR_CTA, CONTADOR_ESCURO, ANCORA, PONTO_SOCO, PONTO_3
    if not os.path.exists(caminho): return
    P = _json.load(open(caminho))
    SEGS = [tuple(x) for x in P["trechos"]]
    TEXTO = P.get("mensagem", TEXTO); CTA1, CTA2 = P["cta"]
    COR = P.get("cor", COR)
    TEAL = tuple(P.get("cor_escrita", TEAL)); TEAL_ESC = tuple(P.get("cor_escrita_borda", TEAL_ESC))
    CONTADOR_ESCURO = P.get("contador_escuro", CONTADOR_ESCURO)
    K = P.get("escala_balao", K); BX, BY = P.get("centro_balao", [BX, BY])
    BH = int(170 * K)
    BW = int(ImageFont.truetype(HN, int(60 * K)).getlength(TEXTO) + 90 * K)
    c = P["cordinha"]
    ANCORA = c.get("ancora", ANCORA)
    ANC = np.array([BX - BW / 2 + 40 if ANCORA == "esquerda" else BX + BW / 2 - 40, BY + BH / 2])
    REPOUSO = ANC + np.array(c.get("repouso", [10, 85]))
    PUNHO = _chaves_int(c["punho"]); PEGA, SOLTA, ACENDE = c["pega"], c["solta"], c["acende"]
    s = P["soco"]
    IMPACTO, NA_CABECA = s["impacto"], s["na_cabeca"]; CABECA = np.array(s["cabeca"], float)
    PONTO_SOCO = s["ponto"]
    t = P["terceiro"]
    MODO3 = t["modo"]; CONTATO, ESTOURO = t["contato"], t["estouro"]
    CORTE = [tuple(x) for x in t.get("corte", CORTE)]; TIQUES = t.get("tiques", TIQUES)
    MAO3 = _chaves_int(t.get("mao", {})); PONTO_3 = t.get("ponto", PONTO_3)
    e = P["escrita"]
    ESPELHAR_CTA = e.get("espelhar", ESPELHAR_CTA)
    LINHAS_CTA = [(CTA1, *e["linha1"]["tam_cx_base"], tuple(e["linha1"]["janela"]), tuple(e["linha1"]["faixa_dedo"])),
                  (CTA2, *e["linha2"]["tam_cx_base"], tuple(e["linha2"]["janela"]), tuple(e["linha2"]["faixa_dedo"]))]
    T_SUBL = e.get("sublinhado", LINHAS_CTA[1][4][1] + 1)
    if "dedo" in e: DEDO = _chaves_int(e["dedo"]); DEDO_Y = _chaves_int(e["dedo_y"])
    elif _TR:
        DEDO = {k: v[0] for k, v in _TR.items()}; DEDO_Y = {k: v[1] for k, v in _TR.items()}

carregar_projeto()

def tremer(out, n):
    for n0, amp in ((IMPACTO, 16), (ESTOURO, 5)):
        dt = n - n0
        if 0 <= dt < 7:
            a = amp * math.exp(-dt / 2.2)
            dx, dy = int(a * math.sin(dt * 2.7)), int(a * math.cos(dt * 3.3))
            out = np.roll(out, (dy, dx), (0, 1))
    return out

def seg_de(n):
    for s in SEGS:
        if s[0] <= n <= s[1]: return s
    return None

def main():
    if "--ver" in sys.argv:
        ns = [int(v) for v in sys.argv[sys.argv.index("--ver") + 1:]]
        imgs = []
        for n in ns:
            fr = cv2.imread(f"quadros/{n:04d}.jpg")[..., ::-1].astype(np.float32) / 255
            o = tremer(compor(n, fr, False, seg_de(n)), n)
            o = (np.clip(o, 0, 1) * 255).astype(np.uint8)[..., ::-1]
            cv2.imwrite(f"f/ver_{n}.jpg", o); imgs.append(cv2.resize(o, (360, 640)))
        rows = [np.hstack(imgs[i:i + 6] + [np.zeros((640, 360, 3), np.uint8)] * (6 - len(imgs[i:i + 6]))) for i in range(0, len(imgs), 6)]
        cv2.imwrite("ver.jpg", np.vstack(rows)); return
    if HDR:   # iPhone: HLG 10 bits — compõe direto no sinal HDR e entrega HDR (nunca converter para SDR)
        trc = open("hdr.txt").read().strip() or "arib-std-b67"
        rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-vf", "scale=in_range=tv:in_color_matrix=bt2020",
                               "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"], stdout=subprocess.PIPE)
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-vf", "scale=out_range=tv:out_color_matrix=bt2020",
                               "-c:v", "libx265", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
                               "-x265-params", f"colorprim=bt2020:transfer={trc}:colormatrix=bt2020nc:range=limited:log-level=error",
                               "-color_primaries", "bt2020", "-color_trc", trc, "-colorspace", "bt2020nc", "video_mudo.mov"],
                              stdin=subprocess.PIPE)
        bpp, tipo, maxv = 6, np.uint16, 65535
    else:
        rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                               "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "video_mudo.mov"], stdin=subprocess.PIPE)
        bpp, tipo, maxv = 3, np.uint8, 255
    n = 0
    while True:
        raw = rd.stdout.read(W * H * bpp)
        if len(raw) < W * H * bpp: break
        n += 1
        s = seg_de(n)
        if s is None: continue
        fr = np.frombuffer(raw, tipo).reshape(H, W, 3).astype(np.float32) / maxv
        o = tremer(compor(n, fr, HDR, s), n)
        wr.stdin.write((np.clip(o, 0, 1) * maxv).astype(tipo).tobytes())
        if n % 50 == 0: print(n, flush=True)
    wr.stdin.close(); wr.wait(); rd.wait()

if __name__ == "__main__":
    main()
