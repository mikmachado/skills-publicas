"""Fundos desenhados (atrás da Mica): parede com quadros que se mexem, céu, cidade de prédios, vista do terraço.
Cada função desenha num RGBA em escala SS e recebe t (s), passo de fervura e a câmera (escala s em torno de (ax, ay))."""
import math
import numpy as np
from desenho import *

W, H = 1080, 1920


def cam(partes, c):
    s, ax, ay = c
    if s == 1: return partes
    return desloca(partes, s=s, cx=ax, cy=ay)


def chapado(img, cor):
    img.paste(cor + (255,), [0, 0, img.size[0], img.size[1]])


# ------------------------------------------------------------------ parede
def _quadro(x, y, w, h, giro, moldura, fundo, dentro):
    """dentro: lista de partes em coordenadas locais 0..1 → posicionadas e giradas junto com a moldura"""
    cx, cy = x + w / 2, y + h / 2
    ca, sa = math.cos(giro), math.sin(giro)

    def gira(p):
        q = p - [cx, cy]
        return np.stack([q[:, 0] * ca - q[:, 1] * sa, q[:, 0] * sa + q[:, 1] * ca], 1) + [cx, cy]

    out = []
    m = parte(ret(x - 22, y - 22, x + w + 22, y + h + 22, 8), moldura, LARANJA if moldura != LARANJA else VERDE_E, 9)
    m["p"] = gira(m["p"]); out.append(m)
    f = parte(ret(x, y, x + w, y + h), fundo, None, 0); f["p"] = gira(f["p"]); out.append(f)
    for q in dentro:
        r = dict(q); r["p"] = gira(q["p"] * [w, h] + [x, y]); r["w"] = q["w"]; out.append(r)
    pr = parte(poli(cx, y - 22, cx, y - 70), None, TINTA, 5, aberta=True); pr["p"] = gira(pr["p"]); out.append(pr)
    return out


def conteudo(tipo, t):
    if tipo == "coracao":
        s = 1 + 0.12 * max(0, math.sin(t * 7)) ** 3
        th = np.linspace(0, 2 * math.pi, 60)
        x = 16 * np.sin(th) ** 3
        y = -(13 * np.cos(th) - 5 * np.cos(2 * th) - 2 * np.cos(3 * th) - np.cos(4 * th))
        p = np.stack([x, y], 1) / 40 * s + [0.5, 0.52]
        return [parte(p, LARANJA, VERDE_E, 6)]
    if tipo == "sol":
        out = [parte(poli(0, 0.78, 1, 0.78, 1, 1, 0, 1), VERDE, None, 0)]
        for k in range(8):
            a = t * 1.6 + k * math.pi / 4
            out.append(parte(poli(0.5 + 0.2 * math.cos(a), 0.42 + 0.2 * math.sin(a), 0.5 + 0.33 * math.cos(a), 0.42 + 0.33 * math.sin(a)),
                             None, LARANJA, 6, aberta=True))
        out.append(parte(elipse(0.5, 0.42, 0.14, 0.14), LARANJA_C, LARANJA, 6))
        return out
    if tipo == "onda":
        out = []
        for j, c in enumerate((CEU, VERDE_C, BRANCO)):
            xs = np.linspace(0, 1, 30)
            ys = 0.35 + j * 0.2 + 0.06 * np.sin(xs * 9 + t * 4 + j)
            out.append(parte(np.stack([xs, ys], 1), None, (CEU, VERDE, LARANJA)[j], 7, aberta=True))
        return out
    if tipo == "planta":
        sw = math.sin(t * 2.2) * 0.05
        out = [parte(poli(0.32, 0.7, 0.68, 0.7, 0.62, 0.95, 0.38, 0.95), LARANJA, VERDE_E, 6)]
        for k, (dx, dy) in enumerate(((-0.25, -0.35), (0, -0.5), (0.25, -0.35))):
            out.append(parte(folha(0.5, 0.7, 0.5 + dx + sw, 0.7 + dy), VERDE, VERDE_E, 5))
        return out
    if tipo == "montanha":
        sh = (t * 0.05) % 1
        out = [parte(poli(0, 1, 0.3, 0.45, 0.6, 1), VERDE, VERDE_E, 6), parte(poli(0.35, 1, 0.7, 0.35, 1, 1), VERDE_C, VERDE_E, 6),
               parte(elipse(0.2 + sh * 0.6, 0.25, 0.12, 0.06), BRANCO, None, 0)]
        return out
    return []


QUADROS_A = [  # x, y, w, h, moldura, fundo, conteúdo, fase
    (55, 660, 170, 210, LARANJA, BEGE, "coracao", 0.0),
    (860, 620, 170, 150, VERDE, CEU_C, "sol", 1.3),
    (870, 860, 150, 190, ROSA_E, BRANCO, "onda", 2.1),
]
QUADROS_B = [
    (60, 640, 160, 190, VERDE, CEU_C, "montanha", 0.4),
    (60, 900, 140, 140, LARANJA, BEGE, "coracao", 1.0),
    (865, 680, 160, 220, LARANJA, VERDE_C, "planta", 2.4),
]


def parede(img, t, passo, c, cor=ROSA, quadros=QUADROS_A, piso=BEGE_E, extras=True):
    chapado(img, cor)
    partes = []
    for x, y, w, h, mol, fun, tipo, fase in quadros:
        giro = math.sin(t * 1.7 + fase * 2) * 0.05
        partes += _quadro(x, y, w, h, giro, mol, fun, conteudo(tipo, t + fase))
    if extras:
        # luminária de pé (direita) e vaso com planta (esquerda)
        sw = math.sin(t * 2) * 6
        partes += [parte(poli(985, 1180, 985, 1760), None, VERDE_E, 9, aberta=True),
                   parte(poli(915, 1190, 1055, 1190, 1020, 1090, 950, 1090), LARANJA_C, LARANJA, 9),
                   parte(elipse(985, 1765, 50, 12), VERDE, VERDE_E, 7)]
        partes += [parte(poli(40, 1600, 190, 1600, 170, 1760, 60, 1760), LARANJA, VERDE_E, 9)]
        for k, (dx, dy) in enumerate(((-90, -230), (-20, -300), (60, -250), (100, -150), (-110, -120))):
            partes.append(parte(folha(115, 1600, 115 + dx + sw * (k % 2 * 2 - 1), 1600 + dy, 0.42), VERDE if k % 2 else VERDE_C, VERDE_E, 7))
    partes.append(parte(ret(-40, 1760, W + 40, H + 60), piso, LARANJA, 10))
    partes.append(parte(poli(-20, 1700, W + 20, 1700), None, cor_escura(cor), 7, aberta=True))
    desenha(img, cam(partes, c), passo)


def cor_escura(c):
    return tuple(int(v * 0.8) for v in c)


# ------------------------------------------------------------------ céu
def nuvem(cx, cy, s):
    bolas = [(-0.9, 0.15, 0.55), (-0.35, -0.2, 0.7), (0.35, -0.1, 0.62), (0.9, 0.18, 0.5), (0, 0.25, 0.7)]
    p = []
    th = np.linspace(0, 2 * math.pi, 200)
    # contorno = envelope externo das bolas (aproximação: raio máximo por ângulo a partir do centro)
    pts = []
    for a in th:
        best = 0
        d = np.array([math.cos(a), math.sin(a)])
        for bx, by, br in bolas:
            b = np.array([bx, by]); proj = b @ d; disc = proj ** 2 - (b @ b - br * br)
            if disc >= 0: best = max(best, proj + math.sqrt(disc))
        r = best if best > 0 else 0.3
        pts.append([cx + d[0] * r * s * 1.4, cy + min(d[1] * r, 0.42) * s])
    return parte(np.array(pts), BRANCO, (96, 160, 214), 9)


def ceu(img, t, passo, c, horizonte=None):
    chapado(img, CEU)
    partes = []
    # sol girando
    a0 = t * 0.6
    for k in range(10):
        a = a0 + k * math.pi / 5
        partes.append(parte(poli(900 + 90 * math.cos(a), 820 + 90 * math.sin(a), 900 + 130 * math.cos(a), 820 + 130 * math.sin(a)),
                            None, LARANJA, 11, aberta=True))
    partes.append(parte(elipse(900, 820, 64, 64), LARANJA_C, LARANJA, 11))
    for k, (y, s, v, f) in enumerate(((260, 70, 40, 0), (560, 90, 26, 400), (900, 80, 34, 800), (1150, 60, 22, 200))):
        x = ((t * v + f) % 1500) - 250
        partes.append(nuvem(x, y, s))
    # passarinhos
    for k in range(4):
        bx = ((t * 70 + k * 330) % 1400) - 150; by = 480 + k * 90 + math.sin(t * 2 + k) * 20
        asa = 18 * math.sin(t * 12 + k)
        partes.append(parte(poli(bx - 30, by - asa, bx, by, bx + 30, by - asa), None, VERDE_E, 6, aberta=True))
    desenha(img, cam(partes, c), passo)


# ------------------------------------------------------------------ cidade
CORES_PREDIO = [(VERDE, VERDE_E), (LARANJA_C, LARANJA), (ROSA_E, LARANJA), (BEGE, LARANJA), (VERDE_C, VERDE_E), (LARANJA, VERDE_E)]


def predio(x0, x1, topo, base, cor, borda, t, seed, janelas=True):
    out = [parte(ret(x0, topo, x1, base), cor, borda, 10)]
    r = np.random.default_rng(seed)
    if r.random() < 0.4:
        out.append(parte(poli((x0 + x1) / 2, topo, (x0 + x1) / 2, topo - 90), None, borda, 7, aberta=True))
        out.append(parte(elipse((x0 + x1) / 2, topo - 95, 10, 10), LARANJA if borda != LARANJA else VERDE, borda, 5))
    elif r.random() < 0.5:
        out.append(parte(poli(x0 + 10, topo, (x0 + x1) / 2, topo - 70, x1 - 10, topo), cor_escura(cor), borda, 9))
    if janelas:
        cw = 46; gap = 34
        nx = max(1, int((x1 - x0 - 40) // (cw + gap)))
        ox = x0 + ((x1 - x0) - (nx * cw + (nx - 1) * gap)) / 2
        y = topo + 50; j = 0
        while y + 60 < base:
            for i in range(nx):
                pisca = math.sin(t * 1.3 + seed * 3 + i * 1.7 + j * 2.3) > 0.55
                out.append(parte(ret(ox + i * (cw + gap), y, ox + i * (cw + gap) + cw, y + 60, 6), (255, 228, 150) if pisca else CEU_C, borda, 6))
            y += 100; j += 1
    return out


def cidade(img, t, passo, c, deriva=18):
    ceu(img, t, passo, c)
    partes = []
    dx = -t * deriva % 300
    # fundo (mais clarinho) e frente
    camadas = [
        ([(-120, 140, 900), (120, 330, 760), (310, 520, 980), (500, 700, 820), (690, 900, 700), (880, 1100, 880), (1080, 1300, 760)], 0.6),
        ([(-60, 210, 1150), (190, 420, 1320), (640, 880, 1260), (860, 1140, 1100)], 1.0),
    ]
    k = 0
    for lista, par in camadas:
        for x0, x1, topo in lista:
            cor, borda = CORES_PREDIO[k % len(CORES_PREDIO)]
            off = dx * par - 150 * par
            partes += predio(x0 + off, x1 + off, topo, 2000, cor, borda, t, k, janelas=True)
            k += 1
    # calçada com arbustos
    partes.append(parte(ret(-40, 1680, W + 40, H + 60), BEGE_E, LARANJA, 10))
    partes.append(parte(poli(-20, 1760, W + 20, 1760), None, LARANJA, 7, aberta=True))
    for x in (60, 330, 760, 1030):
        partes.append(parte(elipse(x, 1675, 90, 55), VERDE, VERDE_E, 9))
    desenha(img, cam(partes, c), passo)


def vista_terraco(img, t, passo, c):
    """céu + cidade bem lá embaixo (a Mica está no alto)"""
    ceu(img, t, passo, c)
    partes = []
    for k, (x0, x1, topo) in enumerate(((-100, 120, 2050), (100, 300, 1960), (280, 460, 2120), (640, 840, 2000), (820, 1000, 1900),
                                         (980, 1200, 2080), (-200, -20, 2300), (1150, 1350, 2250))):
        cor, borda = CORES_PREDIO[(k + 2) % len(CORES_PREDIO)]
        partes += predio(x0, x1, topo, 3200, cor, borda, t, k + 20)
    desenha(img, cam(partes, c), passo)


FUNDOS = {"parede": parede, "ceu": ceu, "cidade": cidade, "terraco": vista_terraco}
