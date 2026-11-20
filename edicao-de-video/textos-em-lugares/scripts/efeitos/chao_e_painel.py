"""CHÃO + PAINEL: texto branco deitado no CHÃO (perspectiva) e palavras GIGANTES num painel ATRÁS da pessoa
(ela fica na frente), com um pico de muito TEXTO. Câmera parada (tripé).
uso (na pasta da cena): python3 <skill>/scripts/efeitos/chao_e_painel.py [--ver t1 t2 ...]   (--ver: só quadros de teste)
AJUSTE (cena.json → geometria): quad_chao (trapézio do chão na tela), painel_y, chao_y, pico (palavra que lota a tela),
gancho (1ª frase gigante no 1º quadro). As frases e palavras-chave vêm da transcrição (comum/frases.py)."""
import sys, subprocess, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
A = "/System/Library/Fonts/Avenir Next.ttc"
C = "/System/Library/Fonts/Avenir Next Condensed.ttc"
F = {"a": (A, 8), "ai": (A, 9), "c": (C, 8), "ci": (C, 9)}

# ---------- chão: retângulo plano LW x LH -> trapézio com fuga em (540,680) ----------
LW, LH = 1600, 1780
QUAD = np.float32(__import__('json').load(open('cena.json')).get('geometria', {}).get('quad_chao', [[318, 1080], [762, 1080], [1300, 2050], [-220, 2050]]) if os.path.exists('cena.json') else [[318, 1080], [762, 1080], [1300, 2050], [-220, 2050]])   # trapézio do chão (tela)
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

# ---------- linha do tempo AUTOMÁTICA (frases da transcrição; ajuste fino em cena.json) ----------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import frases, cfg
P = "a"                                   # texto corrido: Avenir Next Heavy; "c" = Condensed Heavy (palavra-chave)
END = len(os.listdir("quadros")) / FPS
FR = frases()
PAINEL_Y = cfg("painel_y", 520)           # altura (tela) da palavra gigante atrás da pessoa
CHAO_Y = cfg("chao_y", [1470, 1690])      # alturas (tela) das 2 linhas no chão
PICO = (cfg("pico", "") or "").lower()    # palavra que vira "parede" repetida quando é falada (ex.: "texto")

def _sai(k): return FR[k + 1][0]["s"] - 0.02 if k + 1 < len(FR) else END
for k, f in enumerate(FR):
    sai = _sai(k)
    if k == 0 and cfg("gancho", True) and len(f) <= 3:
        # GANCHO: a 1ª frase gigante atrás da pessoa já no 1º quadro
        for j, w in enumerate(f):
            fundo(w["t"].upper(), "c", 420, 540, [300, 640, 985][j], -0.15 if j == 0 else w["s"], sai, "y" if w["chave"] else "b")
        continue
    pico = PICO and any(w["t"].lower().strip(".,!?") == PICO for w in f)
    chave = [w for w in f if w["chave"]][:1]
    resto = [w for w in f if w not in chave]
    if chave and not pico:
        fundo(chave[0]["t"].upper(), "c", 600, 540, PAINEL_Y, chave[0]["s"], sai, "y")
    # o resto no chão, em até 2 linhas equilibradas
    if not chave or pico: resto = f
    tam = [len(w["t"]) + 1 for w in resto]; corte = 0
    if len(resto) > 2 or sum(tam) > 16:
        corte = min(range(1, len(resto)), key=lambda i: abs(sum(tam[:i]) - sum(tam[i:])))
    for y, grupo in zip(CHAO_Y, [resto[:corte], resto[corte:]] if corte else [resto]):
        if grupo:
            linha("chao", [(w["t"].upper() if w["chave"] else w["t"], "c" if w["chave"] else P, 420 if w["chave"] else 240, w["s"], "y" if w["chave"] else "b")
                           for w in grupo], 540, y, sai)
    if pico:
        # pico: parede de PICO cobrindo a tela toda atrás da pessoa, até o fim da frase
        t0 = [w["s"] for w in f if w["t"].lower().strip(".,!?") == PICO][0]
        import random
        random.seed(7)
        pos = []
        for y, n in [(110, 3), (330, 2), (560, 3), (790, 2), (1020, 3)]:
            for x in ([180, 540, 900] if n == 3 else [275, 805]): pos.append((x, y, 320 if n == 3 else 450))
        ordem = list(range(len(pos))); random.shuffle(ordem)
        for q, j in enumerate(ordem):
            x, y, mw = pos[j]
            fundo(PICO.upper(), "c", 600, x, y, t0 + q * 0.17, sai, "y" if j in (5, 9) else "b", maxw=mw)

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
    if not os.path.exists(p): return np.zeros((H, W), np.float32)
    m = cv2.imread(p, 0).astype(np.float32) / 255
    # recorte sólido: fecha buracos (mão na bolsa, punho, tênis) que deixavam o texto vazar
    b = (m > 0.08).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    fl = b.copy(); cv2.floodFill(fl, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    b = b | (1 - fl)
    b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return np.maximum(np.clip(m / 0.45, 0, 1), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.5))

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
