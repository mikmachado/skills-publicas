"""CONTORNO DO CORPO: frase andando em volta da silhueta da pessoa (3 faixas em afastamentos diferentes,
sentidos alternados) + legenda grande no alto. Câmera quase parada (compensa tremidinha pelo muro).
uso (na pasta da cena): python3 <skill>/scripts/efeitos/contorno.py [--ver t1 t2 ...]   (--ver: só quadros de teste)
O texto vem da transcrição: a 1ª frase anda em volta do corpo; as seguintes aparecem grandes no alto.
AJUSTE (cena.json → geometria): chao_y (y dos pés), janelas_fundo ([y0,y1,x0,x1] de fundo parado, sem a pessoa,
para compensar a tremidinha), legenda_y. FAIXAS no script: afastamento, tamanho, velocidade."""
import sys, subprocess, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
A = "/System/Library/Fonts/Avenir Next.ttc"
C = "/System/Library/Fonts/Avenir Next Condensed.ttc"
F = {"a": (A, 8), "c": (C, 8)}
N = len(os.listdir("quadros"))
AMA = np.array([255, 226, 110], np.float32)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import frases, cfg, linhas, config
JAN = cfg("janelas_fundo", [[80, 1450, 20, 330], [80, 1450, 740, 1060]])   # [y0, y1, x0, x1] de fundo sem a pessoa

# ---------- câmera: deslocamento do muro (sem a pessoa) ----------
if not os.path.exists("desloc.npy"):
    g0 = cv2.imread("quadros/00001.jpg", 0).astype(np.float32)
    d = []
    for i in range(1, N + 1):
        g = cv2.imread(f"quadros/{i:05d}.jpg", 0).astype(np.float32)
        ds = [cv2.phaseCorrelate(g0[a:b, c:e], g[a:b, c:e])[0] for a, b, c, e in JAN]
        d.append((np.mean([x for x, _ in ds]), np.mean([y for _, y in ds])))
    np.save("desloc.npy", np.array(d))
DES = np.load("desloc.npy")

# ---------- máscara ----------
def masc_raw(i):
    i = min(max(i, 1), N)
    return cv2.imread(f"mask/{i:05d}.png", 0).astype(np.float32) / 255

def masc(i):
    m = masc_raw(i)
    b = (m > 0.08).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    fl = b.copy(); cv2.floodFill(fl, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    b = b | (1 - fl)
    b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return np.maximum(np.clip(m / 0.45, 0, 1), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.5))

def corpo_suave(i):
    """silhueta média de ±4 quadros, fechada e arredondada (base dos caminhos)"""
    acc = sum(masc_raw(i + k) for k in range(-4, 5)) / 9
    b = (cv2.GaussianBlur(acc, (0, 0), 6) > 0.5).astype(np.uint8)
    return cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (71, 71)))

# ---------- faixas: a 1ª frase anda em volta do corpo (3 faixas, sentidos alternados) ----------
FR = frases(config().get("max_palavras", 8))
F0 = FR[0]
FRASE = "  ".join(w["t"].upper().strip(".,!?") for w in F0) + "  •  "
CHAVES = {w["t"].upper().strip(".,!?") for w in F0 if w["chave"]}
_e = [F0[0]["s"], F0[len(F0) // 3]["s"], F0[2 * len(F0) // 3]["s"]]
#        afastamento (px), tamanho, velocidade px/s, entra, cor dominante
FAIXAS = [(48, 56, 150, _e[0], "b"), (120, 64, -130, _e[1], "y"), (200, 72, 110, _e[2], "b")]
CHAO = cfg("chao_y", 1595)   # y dos pés: corta o caminho no chão (sem texto de cabeça pra baixo)

def caminho(corpo, r, dy):
    dist = cv2.distanceTransform((1 - corpo).astype(np.uint8), cv2.DIST_L2, 5)
    reg = (dist <= r).astype(np.uint8)
    reg = cv2.GaussianBlur(reg.astype(np.float32), (0, 0), 9) > 0.5
    cs, _ = cv2.findContours(reg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :].astype(np.float32)
    # sentido horário na tela (sobe pela esquerda, desce pela direita)
    if cv2.contourArea(c, oriented=True) < 0: c = c[::-1]
    k = cv2.getGaussianKernel(61, 14)[:, 0]
    c = np.stack([np.convolve(np.r_[c[-30:, j], c[:, j], c[:30, j]], k, "same")[30:-30] for j in range(2)], 1)
    ok = c[:, 1] < CHAO + dy
    # começa no primeiro ponto válido depois de um trecho cortado (pé esquerdo)
    i0 = np.where(ok & ~np.roll(ok, 1))[0]
    c = np.roll(c, -i0[0], 0) if len(i0) else c
    ok = c[:, 1] < CHAO + dy
    c = c[: np.argmin(ok) if not ok.all() else len(c)]
    if c[0, 0] > c[-1, 0]: c = c[::-1]           # sempre da esquerda pra direita, por cima
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    return c, s

_ch = {}
def glifo(ch, s, sy=1):
    k = (ch, s)
    if k not in _ch:
        fo = ImageFont.truetype(C, s, index=8)
        l, tp, r, b = fo.getbbox("H")
        w = fo.getlength(ch)
        im = Image.new("L", (int(w) + 24, int(s * 1.25) + 24), 0)
        ImageDraw.Draw(im).text((12, 12), ch, font=fo, fill=255)
        a = np.asarray(im, np.float32) / 255
        # base da letra na altura do baseline
        asc = fo.getmetrics()[0]
        _ch[k] = (a, w, 12 + asc)
    return _ch[k]

def faixa(can, cany, c, s, size, vel, t, al, cor):
    L = s[-1]
    if L < 50: return
    top = int(np.argmin(c[:, 1])); st = s[top]
    adv = [glifo(ch, size)[1] + size * 0.02 for ch in FRASE]
    P = sum(adv)
    x0 = (vel * t) % P
    # palavras em amarelo alternadas por faixa
    pal = FRASE.split("  ")
    amarelas = CHAVES if cor == "b" else {w.strip("•") for w in FRASE.split()}
    idx_y = set(); p = 0
    for w in FRASE.split(" "):
        if w in amarelas:
            idx_y.update(range(p, p + len(w)))
        p += len(w) + 1
    n0 = int(np.floor((-st - x0) / P)) - 1
    while True:
        base = st + x0 + n0 * P
        if base > L: break
        pos = base
        for j, ch in enumerate(FRASE):
            w = adv[j]
            m = pos + w / 2
            if 0 <= m <= L and ch != " ":
                fa = min(1, m / 60, (L - m) / 60) * al        # some nas pontas (no chão)
                if fa > 0.02:
                    k = np.searchsorted(s, m); k = min(max(k, 1), len(s) - 1)
                    p0, p1 = c[k - 1], c[k]
                    ang = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
                    a, gw, bl = glifo(ch, size)
                    cx, cy = (p0 + p1) / 2
                    h_, w_ = a.shape
                    # centro do glifo deslocado pra fora: letra "em pé" sobre o caminho
                    Mr = cv2.getRotationMatrix2D((w_ / 2, bl - size * 0.36), -ang, 1)
                    Mr[0, 2] += cx - w_ / 2; Mr[1, 2] += cy - (bl - size * 0.36)
                    x1, y1 = int(cx - w_), int(cy - w_)
                    x1, y1 = max(0, x1), max(0, y1); x2, y2 = min(W, int(cx + w_)), min(H, int(cy + w_))
                    if x2 > x1 and y2 > y1:
                        Mr2 = Mr.copy(); Mr2[0, 2] -= x1; Mr2[1, 2] -= y1
                        g = cv2.warpAffine(a, Mr2, (x2 - x1, y2 - y1), flags=cv2.INTER_LINEAR) * fa
                        np.maximum(can[y1:y2, x1:x2], g, out=can[y1:y2, x1:x2])
                        if j in idx_y: np.maximum(cany[y1:y2, x1:x2], g, out=cany[y1:y2, x1:x2])
            pos += w
        n0 += 1

# ---------- legenda grande no alto: as frases seguintes, uma de cada vez ----------
LEG = []   # (texto, tam, x, y, entra, sai, cor)
END = N / FPS
LEG_Y = cfg("legenda_y", {"1": [300], "2": [200, 380], "3": [120, 265, 405]})
for k, f in enumerate(FR[1:], 1):
    sai = FR[k + 1][0]["s"] - 0.02 if k + 1 < len(FR) else END
    ls = linhas(f, 11)
    if len(ls) > 3: ls = ls[:2] + [[w for l in ls[2:] for w in l]]
    tam = {1: 320, 2: 260, 3: 220}[len(ls)]
    for y, l in zip(LEG_Y[str(len(ls))], ls):
        um = len(l) == 1 and l[0]["chave"]
        LEG.append((" ".join(w["t"].upper() for w in l), int(tam * (1.25 if um else 1)), 540, y, l[0]["s"], sai, "y" if um else "b"))
_sp = {}
def sprite(t, s):
    k = (t, s)
    if k not in _sp:
        fo = ImageFont.truetype(C, s, index=8)
        l, tp, r, b = fo.getbbox(t)
        im = Image.new("L", (r - l + 40, b - tp + 40), 0)
        ImageDraw.Draw(im).text((20 - l, 20 - tp), t, font=fo, fill=255)
        a = np.asarray(im, np.float32) / 255
        if a.shape[1] > 1000:  # cabe na largura
            k2 = 1000 / a.shape[1]; a = cv2.resize(a, (1000, int(a.shape[0] * k2)), interpolation=cv2.INTER_AREA)
        _sp[k] = a
    return _sp[k]

def anim(t, ent, sai):
    u = (t - ent) / 0.22
    if u <= 0 or t >= sai: return 0, 0
    if u < 1:
        c1 = 2.2; e = 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2
        esc, al = 0.55 + 0.45 * e, min(1, u * 3)
    else: esc, al = 1, 1
    v = (sai - t) / 0.12
    if v < 1: al *= v
    return esc, al

def cola(can, spr, cx, cy, esc, al):
    h, w = spr.shape
    s = cv2.resize(spr, (max(1, int(w * esc)), max(1, int(h * esc)))) * al
    h, w = s.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if X1 > X0 and Y1 > Y0:
        np.maximum(can[Y0:Y1, X0:X1], s[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0], out=can[Y0:Y1, X0:X1])

def compor(f, t, i):
    pes = masc(i)
    dx, dy = DES[i - 1]
    a = np.zeros((H, W), np.float32); ay = np.zeros_like(a)
    corpo = corpo_suave(i)
    for r, size, vel, ent, cor in FAIXAS:
        al = np.clip((t - ent) / 0.35, 0, 1)
        if al > 0:
            c, s = caminho(corpo, r, dy)
            faixa(a, ay, c, s, size, vel, t, al, cor)
    for tx, sz, x, y, ent, sai, cor in LEG:
        esc, al = anim(t, ent, sai)
        if al > 0:
            sp = sprite(tx, sz); cola(a, sp, x + dx, y + dy, esc, al)
            if cor == "y": cola(ay, sp, x + dx, y + dy, esc, al)
    livre = (1 - pes)[..., None]
    sh = np.maximum(cv2.GaussianBlur(np.roll(np.roll(a, 7, 0), 4, 1), (0, 0), 6) * 0.75, cv2.GaussianBlur(a, (0, 0), 2) * 0.55)
    f = f * (1 - sh[..., None] * livre)
    r_ = (ay / np.maximum(a, 1e-3))[..., None]
    cor = np.float32(252) * (1 - r_) + AMA * r_
    f = f * (1 - a[..., None] * livre) + cor * a[..., None] * livre
    return np.clip(f, 0, 255).astype(np.uint8)

if "--ver" in sys.argv:
    for ts in sys.argv[sys.argv.index("--ver") + 1:]:
        t = float(ts); i = int(round(t * FPS)) + 1
        f = cv2.cvtColor(cv2.imread(f"quadros/{i:05d}.jpg"), cv2.COLOR_BGR2RGB).astype(np.float32)
        cv2.imwrite(f"ver_{t:05.2f}.jpg", cv2.cvtColor(compor(f, t, i), cv2.COLOR_RGB2BGR))
    sys.exit()

pb = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", "base.mp4", "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", "comp.mp4"], stdin=subprocess.PIPE)
i = 0
while i < N:
    b = pb.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    i += 1
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32)
    out.stdin.write(compor(f, (i - 1) / FPS, i).tobytes())
out.stdin.close(); out.wait(); print("comp.mp4", i, "quadros")
