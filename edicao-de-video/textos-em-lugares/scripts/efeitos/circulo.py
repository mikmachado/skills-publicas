"""TEXTO CIRCULAR: câmera de cima, frases em ANÉIS no chão em volta da pessoa. Cada frase nasce num anel novo
(de dentro pra fora), nenhuma sai de cena e todos giram devagar (sentidos alternados).
uso (na pasta da cena): python3 <skill>/scripts/efeitos/circulo.py [--ver t1 t2 ...]   (--ver: só quadros de teste)
AJUSTE (cena.json → geometria): pes ([x, y] entre os pés no quadro 1), inclinacao (graus; câmera do alto ~45),
focal, aneis_frente (quantos anéis lidos embaixo), raio_frente, raio_fundo, giro_graus_s. As frases, tamanhos e
raios saem da transcrição: anéis da frente cabem na volta, os de trás cabem na largura da tela."""
import sys, subprocess, os, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
C = "/System/Library/Fonts/Avenir Next Condensed.ttc"
FONTE = (C, 8)                                    # Condensed Heavy
AMA = np.array([255, 226, 110], np.float32)
BRA = np.array([252, 251, 246], np.float32)
HS = [np.array(h, np.float64) for h in json.load(open("homografias.json"))]
N = len(HS)

# ---------- chão (quadro 1): câmera virtual f=1550, olhando 45° pra baixo, altura = 1 ----------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import cfg
f0, cx, cy = cfg('focal', 1550), 540, 960
phi = np.radians(cfg('inclinacao', 45))        # inclinação do eixo da câmera (graus abaixo do horizonte)
dv = np.array([0, -np.sin(phi), np.cos(phi)]); uv = np.array([0, np.cos(phi), np.sin(phi)])
def proj(X, Z):
    P = np.stack([X, -np.ones_like(X), Z], -1)
    return np.stack([cx + f0 * P[..., 0] / (P @ dv), cy - f0 * (P @ uv) / (P @ dv)], -1)
PES = tuple(cfg('pes', [547, 1222]))                                # centro dos anéis: entre os pés, no chão
Zs = np.linspace(0.1, 5, 40000); Zf = Zs[np.argmin(abs(proj(np.zeros_like(Zs), Zs)[:, 1] - PES[1]))]
Xf = (PES[0] - cx) / f0 * (np.array([0, -1, Zf]) @ dv)

S, CV = 1000, 3100                                 # lona vista de cima: S px por unidade, CVxCV
CC = CV / 2
def lona2img(u, v): return proj(Xf + (u - CC) / S, Zf - (v - CC) / S)
q = np.float32([[0, 0], [CV, 0], [CV, CV], [0, CV]])
HG = cv2.getPerspectiveTransform(q, lona2img(q[:, 0], q[:, 1]).astype(np.float32))
yy, xx = np.mgrid[0:CV, 0:CV].astype(np.float32)
RR = np.hypot(xx - CC, yy - CC) / S                # raio (unidades de chão)
TT = np.arctan2(yy - CC, xx - CC)                  # ângulo (90° = embaixo, perto da câmera)
del yy, xx

# ---------- frases AUTOMÁTICAS: uma por anel, de dentro pra fora ----------
from frases import frases, cfg, config
FR = frases(config().get("max_palavras", 8))
NF = cfg("aneis_frente", min(4, (len(FR) + 1) // 2))   # os primeiros anéis são lidos na frente (embaixo)
_fo1 = ImageFont.truetype(FONTE[0], int(S * 1.18), index=FONTE[1])
def _larg(pal): return (sum(_fo1.getlength(t) for t, _, _ in pal) + _fo1.getlength(" ") * 0.9 * (len(pal) - 1)) / S
FRASES = []   # (palavras, altura da letra, raio, lado): "f" = lida na frente, "t" = lida atrás da pessoa
r = cfg("raio_frente", 0.17); alt_ant = None
for k, f in enumerate(FR):
    pal = [(w["t"].upper(), w["s"], "y" if w["chave"] else "b") for w in f]
    lp = _larg(pal)          # largura do texto (unidades de chão) por unidade de altura
    if k < NF:
        if alt_ant is not None: r = r + alt_ant / 2 + 0.012 + 0.025
        alt = float(np.clip(4.6 * r / lp, 0.034, 0.065))         # cabe na volta (passa por trás das pernas)
        if alt_ant is not None: r = r - 0.025 + alt / 2
        lado = "f"
    else:
        r = cfg("raio_fundo", 0.74) if k == NF else max(r * 1.21, r + alt_ant / 2 + alt / 2 + 0.05)
        alt = float(np.clip(1.15 * r / lp, 0.05, 0.11))           # cabe no fundo, sem sair da tela
        lado = "t"
    FRASES.append((pal, alt, r, lado)); alt_ant = alt
OMEGA = np.radians(cfg("giro_graus_s", 7))       # giro (rad/s)

_fo = {}
def fonte(px):
    if px not in _fo: _fo[px] = ImageFont.truetype(FONTE[0], px, index=FONTE[1])
    return _fo[px]

ANEIS = []
for k, (pal, alt, r, lado) in enumerate(FRASES):
    hb = int(alt * S * 1.5); px = int(alt * S * 1.18)
    fo = fonte(px); esp = fo.getlength(" ") * 0.9
    L = int(2 * np.pi * r * S)
    tira = Image.new("L", (L, hb)); tam = Image.new("L", (L, hb))
    dw, dy = ImageDraw.Draw(tira), ImageDraw.Draw(tam)
    x = 0; faixas = []
    for t, ini, cor in pal:
        l, tp, rr, b = fo.getbbox(t)
        y0 = (hb - (b - tp)) / 2 - tp
        dw.text((x - l, y0), t, font=fo, fill=255)
        if cor == "y": dy.text((x - l, y0), t, font=fo, fill=255)
        faixas.append((int(x), int(x + rr - l) + 1, ini)); x += rr - l + esp
    lt = x - esp
    a = np.asarray(tira, np.float32) / 255; ay = np.asarray(tam, np.float32) / 255
    rk = max(2, int(px * 0.045))
    ak = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rk + 1, 2 * rk + 1)))
    tmid = (pal[0][1] + pal[-1][1]) / 2
    sel = (RR > r - alt * 0.8) & (RR < r + alt * 0.8)
    ANEIS.append(dict(alt=alt, r=r, L=L, hb=hb, lt=lt, faixas=faixas, tira=np.dstack([a, ay, ak]),
                      tmid=tmid, lado=lado, sent=(1 if k % 2 == 0 else -1) * (1 if lado == "f" else -1), t0=pal[0][1], idx=np.nonzero(sel.ravel())[0]))
print("anéis:", [round(a["r"], 3) for a in ANEIS])
RRf, TTf = RR.ravel(), TT.ravel()

def anim(t, ini):
    u = (t - ini) / 0.18
    return 0.0 if u <= 0 else min(1.0, u)

def lona(t):
    out = np.zeros((CV * CV, 3), np.float32)
    for A in ANEIS:
        if t < A["t0"] - 0.01: continue
        tira = A["tira"].copy()
        for x0, x1, ini in A["faixas"]:
            tira[:, x0:x1] *= anim(t, ini)
        # centro da frase em 90° (de frente pra câmera) no meio da fala, e gira devagar
        Rm = A["r"] * S; idx = A["idx"]
        if A["lado"] == "f":   # embaixo: lê da esquerda pra direita com o topo da letra pro centro
            ac = np.pi / 2 + A["sent"] * OMEGA * 0.25 / A["r"] * (t - A["tmid"])
            xs = np.mod((ac + (A["lt"] / 2) / Rm - TTf[idx]) * Rm, A["L"]).astype(np.float32)
            ys = ((RRf[idx] - A["r"]) * S + A["hb"] / 2).astype(np.float32)
        else:                  # no fundo: topo da letra pra fora
            ac = -np.pi / 2 + A["sent"] * OMEGA * 0.08 / A["r"] * (t - A["tmid"])
            xs = np.mod((TTf[idx] - ac + (A["lt"] / 2) / Rm) * Rm, A["L"]).astype(np.float32)
            ys = ((A["r"] - RRf[idx]) * S + A["hb"] / 2).astype(np.float32)
        n = len(idx); m = -(-n // 1024) * 1024
        mx = np.zeros(m, np.float32); my = np.full(m, -10, np.float32); mx[:n] = xs; my[:n] = ys
        smp = cv2.remap(tira, mx.reshape(-1, 1024), my.reshape(-1, 1024), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        smp = smp.reshape(-1, 3)[:n]
        out[idx] = np.maximum(out[idx], smp)
    return out.reshape(CV, CV, 3)

# ---------- máscara da pessoa ----------
def masc(i):
    m = cv2.imread(f"mask/{min(max(i, 1), N):05d}.png", 0).astype(np.float32) / 255
    b = (m > 0.08).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    fl = b.copy(); cv2.floodFill(fl, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    b = b | (1 - fl)
    b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return np.maximum(np.clip(m / 0.45, 0, 1), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.5))

REF = None
def compor(f, t, i):
    global REF
    c = cv2.warpPerspective(lona(t), HS[i - 1] @ HG, (W, H), flags=cv2.INTER_LINEAR)
    a, ay, ak = c[..., 0], c[..., 1], c[..., 2]
    livre = 1 - masc(i)
    g = cv2.GaussianBlur(f.mean(2), (0, 0), 6)
    if REF is None: REF = np.percentile(g[1300:1900], 70)
    luz = np.clip(g / REF, 0.5, 1.06)[..., None]                 # a sombra dela escurece o texto
    sh = np.maximum(cv2.GaussianBlur(np.roll(ak, 6, 0), (0, 0), 6) * 0.55, ak * 0.75) * livre
    f = f * (1 - sh[..., None] * 0.85)
    r = (ay / np.maximum(a, 1e-3))[..., None]
    cor = (BRA * (1 - r) + AMA * r) * luz
    k = (a * livre)[..., None]
    f = f * (1 - k) + cor * k
    return np.clip(f, 0, 255).astype(np.uint8)

if "--ver" in sys.argv:
    for ts in sys.argv[sys.argv.index("--ver") + 1:]:
        t = float(ts); i = min(int(round(t * FPS)) + 1, N)
        f = cv2.cvtColor(cv2.imread(f"quadros/{i:05d}.jpg"), cv2.COLOR_BGR2RGB).astype(np.float32)
        cv2.imwrite(f"ver_{t:05.2f}.jpg", cv2.cvtColor(compor(f, t, i), cv2.COLOR_RGB2BGR))
    sys.exit()

pb = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", "base.mp4", "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", "comp.mp4"], stdin=subprocess.PIPE)
i = 0
while True:
    b = pb.stdout.read(W * H * 3)
    if len(b) < W * H * 3 or i >= N: break
    i += 1
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32)
    out.stdin.write(compor(f, (i - 1) / FPS, i).tobytes())
out.stdin.close(); out.wait(); print("comp.mp4", i, "quadros")
