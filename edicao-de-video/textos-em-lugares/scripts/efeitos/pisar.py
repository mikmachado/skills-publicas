"""PISAR NO TEXTO: cada frase nasce no chão logo à frente dos pés da pessoa, que vai andando e pisa nas letras.
Câmera parada (tripé). AJUSTE (cena.json → geometria): quad_chao (trapézio do chão na tela), frente (distância à frente dos pés),
tamanho ([corrido, palavra-chave]). Frases, tempos e posição (pés no recorte) são automáticos.
uso (na pasta da cena): python3 <skill>/scripts/efeitos/pisar.py [--ver t1 t2 ...]   (--ver: só quadros de teste)"""
import sys, subprocess, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
A = "/System/Library/Fonts/Avenir Next.ttc"
C = "/System/Library/Fonts/Avenir Next Condensed.ttc"
F = {"a": (A, 8), "ai": (A, 9), "c": (C, 8), "ci": (C, 9)}

# ---------- chão: retângulo plano LW x LH -> trapézio com fuga em (540,680) ----------
LW, LH = 2000, 2000
QUAD = np.float32(__import__('json').load(open('cena.json')).get('geometria', {}).get('quad_chao', [[258, 840], [822, 840], [2040, 2050], [-960, 2050]]) if os.path.exists('cena.json') else [[258, 840], [822, 840], [2040, 2050], [-960, 2050]])   # trapézio do chão (tela)
M = cv2.getPerspectiveTransform(np.float32([[0, 0], [LW, 0], [LW, LH], [0, LH]]), QUAD)
Minv = np.linalg.inv(M)

def tela_p_chao(x, y):
    v = Minv @ np.array([x, y, 1.0]); return v[0] / v[2], v[1] / v[2]

# ---------- linha do tempo ----------
# item: (camada, texto, fonte, tamanho, x, y, entra, sai, cor)   cor "b" branco | "y" amarelo claro
IT = []
def _larg(t, f, s): return ImageFont.truetype(F[f][0], s, index=F[f][1]).getlength(t)

def largura_util(y, m=50):
    if y is None: return W - 2 * m
    a, _ = tela_p_chao(m, y); b, _ = tela_p_chao(W - m, y)
    return min(b, LW - 60) - max(a, 60)

def linha(camada, palavras, x, y, sai, gap=0.26, maxw=None):
    """palavras: [(texto, fonte, tam, entra, cor)] lado a lado, centradas em (x,y) da tela; encolhe p/ caber"""
    avail = maxw or largura_util(y if camada == "chao" else None)
    tot = lambda k: sum(_larg(t, f, int(s * k)) for t, f, s, _, _ in palavras) + sum(gap * s * k for _, _, s, _, _ in palavras[:-1])
    k = min(1.0, avail / tot(1.0))
    cx, cy = tela_p_chao(x, y) if camada == "chao" else (x, y)
    xx = cx - tot(k) / 2
    for t, f, s, ent, cor in palavras:
        s2 = int(s * k); l = _larg(t, f, s2)
        IT.append((camada, t, f, s2, xx + l / 2, cy, ent, sai, cor))
        xx += l + gap * s2

def fundo(t, f, s, x, y, ent, sai, cor="b", maxw=None):
    linha("fundo", [(t, f, s, ent, cor)], x, y, sai, maxw=maxw)

def chao(t, f, s, x, y, ent, sai, cor="b", maxw=None):
    linha("chao", [(t, f, s, ent, cor)], x, y, sai, maxw=maxw)

P = "a"
def chao_p_tela(u, v):
    p = M @ np.array([u, v, 1.0]); return p[0] / p[2], p[1] / p[2]

def bloco(x, y, linhas, sai):
    """empilha as linhas no PLANO do chão a partir de (x,y) da tela, sem encavalar"""
    u, v = tela_p_chao(x, y)
    for pal in linhas:
        s = max(p[2] for p in pal); caps = all(p[1] == "c" for p in pal)
        alt = s * (0.80 if caps else 0.95)
        v += alt / 2
        linha("chao", pal, *chao_p_tela(u, v), sai)
        v += alt / 2 + 30

# ---------- frases AUTOMÁTICAS: cada uma nasce logo à frente dos pés, no instante em que começa ----------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import frases, cfg, linhas, config
FR = frases(config().get("max_palavras", 5))   # frases curtas: cada bloco cabe no chão
END = len(os.listdir("quadros")) / FPS
FRENTE = cfg("frente", 140)          # quanto à frente dos pés (unidades do plano do chão) a frase começa
TAM = cfg("tamanho", [340, 480])    # [texto corrido, palavra-chave]
def pes(t):
    """ponto entre os pés (tela) no tempo t, pelo recorte"""
    i = min(max(int(round(t * FPS)) + 1, 1), len(os.listdir("quadros")))
    d = "mask_fina" if os.path.exists("mask_fina") else "mask"
    m = cv2.imread(f"{d}/{i:05d}.png", 0)
    ys, xs = np.where(m > 128)
    if len(ys) == 0: return W / 2, H * 0.6
    y1 = ys.max(); sel = ys > y1 - 25
    return float(np.median(xs[sel])), float(y1)
for k, f in enumerate(FR):
    sai = FR[k + 1][0]["s"] - 0.02 if k + 1 < len(FR) else END
    x, y = pes(f[0]["s"])
    u, v = tela_p_chao(x, y)
    x, y = chao_p_tela(u, v + FRENTE)
    ls = [[(w["t"].upper() if w["chave"] else w["t"], "c" if w["chave"] else P, TAM[1] if w["chave"] else TAM[0],
            w["s"], "y" if w["chave"] else "b") for w in l] for l in linhas(f, 16)][:4]
    bloco(x, y, ls, sai)

# ---------- desenho ----------
_sp = {}
def sprite(t, f, s):
    k = (t, f, s)
    if k not in _sp:
        fo = ImageFont.truetype(F[f][0], s, index=F[f][1])
        l, tp, r, b = fo.getbbox(t)
        im = Image.new("L", (r - l + 40, b - tp + 40), 0)
        ImageDraw.Draw(im).text((20 - l, 20 - tp), t, font=fo, fill=255)
        _sp[k] = np.asarray(im, np.float32) / 255
    return _sp[k]

def anim(t, ent, sai):
    u = (t - ent) / 0.22
    if u <= 0: return 0, 0
    if u < 1:
        c1 = 2.2; e = 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2   # easeOutBack
        esc, al = 0.55 + 0.45 * e, min(1, u * 3)
    else:
        esc, al = 1, 1
    v = (sai - t) / 0.12
    if v <= 0: return 0, 0
    if v < 1: al *= v; esc *= 0.94 + 0.06 * v
    return esc, al

def cola(can, spr, cx, cy, esc, al):
    if esc <= 0.02: return
    h, w = spr.shape
    s = cv2.resize(spr, (max(1, int(w * esc)), max(1, int(h * esc))), interpolation=cv2.INTER_AREA) * al
    h, w = s.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(can.shape[1], x0 + w), min(can.shape[0], y0 + h)
    if X1 <= X0 or Y1 <= Y0: return
    reg = can[Y0:Y1, X0:X1]
    np.maximum(reg, s[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0], out=reg)

def camadas(t):
    ch = np.zeros((LH, LW), np.float32); fu = np.zeros((H, W), np.float32)
    chy = np.zeros((LH, LW), np.float32); fuy = np.zeros((H, W), np.float32)
    for cam, tx, f, s, x, y, ent, sai, cor in IT:
        esc, al = anim(t, ent, sai)
        if al > 0:
            sp = sprite(tx, f, s)
            cola(ch if cam == "chao" else fu, sp, x, y, esc, al)
            if cor == "y": cola(chy if cam == "chao" else fuy, sp, x, y, esc, al)
    wp = lambda a: cv2.warpPerspective(a, M, (W, H), flags=cv2.INTER_LINEAR)
    return wp(ch), fu, wp(chy), fuy

def compor(f, t, pes):
    ac, af, acy, afy = camadas(t)
    AMA = np.array([255, 226, 110], np.float32)   # amarelo claro
    cor = lambda a, ay, base: base * (1 - (ay / np.maximum(a, 1e-3))[..., None]) + AMA * (ay / np.maximum(a, 1e-3))[..., None]
    livre = (1 - pes)[..., None]
    lum = cv2.GaussianBlur(f.mean(2), (0, 0), 3) / 200
    # fundo: sombra forte (céu claro atrás) + leve contorno
    sh = np.maximum(cv2.GaussianBlur(np.roll(np.roll(af, 10, 0), 6, 1), (0, 0), 11) * 0.7,
                    cv2.GaussianBlur(af, (0, 0), 3) * 0.55)
    f = f * (1 - sh[..., None] * livre)
    f = f * (1 - af[..., None] * livre) + cor(af, afy, np.float32(252)) * af[..., None] * livre
    # chão: sombra suave + branco que pega a luz do chão
    sc = np.maximum(cv2.GaussianBlur(np.roll(ac, 5, 0), (0, 0), 7) * 0.6, cv2.GaussianBlur(ac, (0, 0), 2.5) * 0.45)
    f = f * (1 - sc[..., None] * livre)
    luz = np.clip(lum, 0.78, 1.0)[..., None]
    f = f * (1 - ac[..., None] * livre) + cor(ac, acy, np.float32(250)) * luz * ac[..., None] * livre
    return np.clip(f, 0, 255).astype(np.uint8)

def masc(i):
    p = f"mask_fina/{i:05d}.png" if os.path.exists("mask_fina") else f"mask/{i:05d}.png"
    return cv2.imread(p, 0).astype(np.float32) / 255 if os.path.exists(p) else np.zeros((H, W), np.float32)

if "--ver" in sys.argv:
    for ts in sys.argv[sys.argv.index("--ver") + 1:]:
        t = float(ts); i = int(round(t * FPS)) + 1
        f = cv2.cvtColor(cv2.imread(f"quadros/{i:05d}.jpg"), cv2.COLOR_BGR2RGB).astype(np.float32)
        cv2.imwrite(f"ver_{t:05.2f}.jpg", cv2.cvtColor(compor(f, t, masc(i)), cv2.COLOR_RGB2BGR))
    sys.exit()

pb = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", "base.mp4", "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", "comp.mp4"], stdin=subprocess.PIPE)
i = 0
while True:
    b = pb.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    i += 1
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32)
    out.stdin.write(compor(f, (i - 1) / FPS, masc(i)).tobytes())
out.stdin.close(); out.wait(); print("comp.mp4", i, "quadros")
