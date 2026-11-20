"""CHÃO CHEIO (ótimo pro fechamento/CTA): chão inteiro coberto de fileiras de TEXTO (deslizando, sentidos
alternados) que surgem em cascata, + chamada grande pintada no chão. A pessoa anda por cima.
uso (na pasta da cena): python3 <skill>/scripts/efeitos/chao_cheio.py [--ver t1 t2 ...]   (--ver: só quadros de teste)
O texto vem da transcrição: a 1ª palavra-chave da 1ª frase (ex.: "Comenta TEXTO") fica gigante perto da câmera e é a
palavra que cobre o chão quando é falada; o resto da fala sobe em até 4 linhas mais ao fundo.
AJUSTE (cena.json → geometria): fuga ([x, y] ponto de fuga do chão no quadro 1), focal, chao_poligono (onde é chão),
palavra_chao (outra palavra pras fileiras)."""
import sys, subprocess, os, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
C = "/System/Library/Fonts/Avenir Next Condensed.ttc"
AMA = np.array([255, 226, 110], np.float32); BRA = np.array([251, 250, 245], np.float32)
HS = [np.array(h, np.float64) for h in json.load(open("homografias.json"))]
N = len(HS)

# ---------- chão (quadro 1): ponto de fuga (553,720), f=1550, altura 1 ----------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import frases, cfg, config
FR = frases(config().get("max_palavras", 8))
F0W = FR[0]
_k = [j for j, w in enumerate(F0W) if w["chave"]]
KJ = _k[0] if _k else len(F0W) - 1                    # palavra GIGANTE da chamada (1ª palavra-chave da 1ª frase)
PALAVRA = cfg("palavra_chao", F0W[KJ]["t"].upper().strip(".,!?"))   # a palavra que cobre o chão
T_FIL = F0W[KJ]["s"]                                   # o chão se enche quando ela é falada
VX, VY = cfg("fuga", [553.0, 720.0]); F0 = cfg("focal", 1550.0)   # ponto de fuga do chão (quadro 1)
def proj(X, Z): return np.stack([VX + F0 * X / Z, VY + F0 / Z], -1)
CHAO = np.zeros((H, W), np.uint8)
cv2.fillPoly(CHAO, [np.int32(cfg("chao_poligono", [[0, 1290], [150, 1140], [300, 1000], [380, 905], [430, 800], [445, 765],
                                                  [760, 782], [1080, 900], [1080, 1920], [0, 1920]]))], 1)   # onde é chão
CHAO = cv2.GaussianBlur(CHAO.astype(np.float32), (0, 0), 2)

def fonte(px): return ImageFont.truetype(C, px, index=8)
def sprite(t, px):
    fo = fonte(px); l, tp, r, b = fo.getbbox(t)
    im = Image.new("L", (r - l + 8, b - tp + 8)); ImageDraw.Draw(im).text((4 - l, 4 - tp), t, font=fo, fill=255)
    return np.asarray(im, np.float32) / 255

# ---------- fileiras de TEXTO (mapa em supersample 2x) ----------
SS = 2
yy, xx = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32) / SS
abaixo = yy > VY + 25
ZZ = np.where(abaixo, F0 / np.maximum(yy - VY, 1), 99).astype(np.float32)
XX = ((xx - VX) * ZZ / F0).astype(np.float32)
del yy, xx
Z0, RZ, GZ, PX = 1.22, 0.27, 0.10, 0.50        # 1ª fileira, comprimento da letra no chão, folga, passo em X
PER = RZ + GZ
TS = sprite(PALAVRA, 240); TH, TW = TS.shape
TW2 = int(TW * 1.3)                              # tile com espaço
TILE = np.zeros((TH, TW2), np.float32); TILE[:, :TW] = TS
RI = np.floor((ZZ - Z0) / PER).astype(np.int32)
VV = ((RZ - (ZZ - Z0 - RI * PER)) / RZ * TH).astype(np.float32)   # topo da letra = longe
NR = int((8.0 - Z0) / PER) + 1
def fileiras(t, tirar=None):
    if t < T_FIL - 0.02: return None, None
    sent = np.where(RI % 2 == 0, 1.0, -1.0)
    off = (RI % 2) * PX / 2 + sent * 0.10 * (t - T_FIL)
    u = (XX - off) / PX
    k = np.floor(u).astype(np.int32)
    U = ((u - k) * TW2).astype(np.float32)
    a = cv2.remap(TILE, U, VV, cv2.INTER_LINEAR, borderValue=0)
    a = np.where((VV >= 0) & (VV < TH) & (RI >= 0) & (RI < NR) & abaixo, a, 0)
    # cascata: fileira mais perto primeiro
    ta = T_FIL + 0.02 + 0.03 * RI
    a = a * np.clip((t - ta) / 0.12, 0, 1)
    a = a * np.clip((8.0 - ZZ) / 2.0, 0, 1)          # some suave lá no fundo
    if tirar is not None:   # tira a palavra inteira que encosta na chamada
        tid = RI * 4096 + (k + 2048)
        ruim = np.unique(tid[(cv2.resize(tirar, (W * SS, H * SS)) > 0.02) & (a > 0.01)])
        a = np.where(np.isin(tid, ruim), 0, a)
    ama = ((k * 7 + RI * 3) % 6 == 0).astype(np.float32)        # algumas em amarelo
    ay = a * ama
    return cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA), cv2.resize(ay, (W, H), interpolation=cv2.INTER_AREA)

# ---------- chamada AUTOMÁTICA: palavra gigante perto, o que vem antes dela logo acima, o resto mais ao fundo ----------
def _quebra(ws, mx=22):
    out, cur = [], []
    for w in ws:
        if cur and len(" ".join(x["t"] for x in cur + [w])) > mx: out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    if len(out) > 4: out = out[:3] + [[w for l in out[3:] for w in l]]
    return out
fundo = _quebra(F0W[KJ + 1:] + [w for f in FR[1:] for w in f])
LINHAS = []   # (palavras, Z perto, Z longe, largura X, tudo amarelo?)
for i, l in enumerate(fundo):
    zn = 2.62 + (len(fundo) - 1 - i) * 0.68
    LINHAS.append((l, zn, zn + 0.48, float(np.clip(0.075 * len(" ".join(w["t"] for w in l)), 0.8, 1.6)), False))
if KJ > 0: LINHAS.append((F0W[:KJ], 1.98, 2.48, float(np.clip(0.13 * len(" ".join(w["t"] for w in F0W[:KJ])), 0.6, 1.2)), False))
LINHAS.append(([F0W[KJ]], 1.30, 1.88, 0.98, True))
CHAM = []
for pal, zn, zf, wx, tudo_y in LINHAS:
    fo = fonte(300); txts = [w["t"].upper() for w in pal]; esp = fo.getlength(" ") * 0.8
    larg = [fo.getbbox(p)[2] - fo.getbbox(p)[0] for p in txts]
    tot = sum(larg) + esp * (len(txts) - 1); l, tp, r, b = fo.getbbox(" ".join(txts))
    hh = b - tp + 20
    a = Image.new("L", (int(tot) + 20, hh)); ay = Image.new("L", a.size)
    x = 10; faixas = []
    for j, (p, w) in enumerate(zip(txts, pal)):
        pl, ptp, _, _ = fo.getbbox(p)
        ImageDraw.Draw(a).text((x - pl, 10 - tp), p, font=fo, fill=255)
        if tudo_y or w["chave"]: ImageDraw.Draw(ay).text((x - pl, 10 - tp), p, font=fo, fill=255)
        faixas.append((int(x), int(x + larg[j]) + 1, w["s"])); x += larg[j] + esp     # palavra a palavra, no tempo da fala
    a = np.asarray(a, np.float32) / 255; ay = np.asarray(ay, np.float32) / 255
    sw, sh = a.shape[1], a.shape[0]
    src = np.float32([[0, 0], [sw, 0], [sw, sh], [0, sh]])
    X0 = (540 - VX) / F0 * (zn + zf) / 2
    dst = proj(np.array([X0 - wx / 2, X0 + wx / 2, X0 + wx / 2, X0 - wx / 2]), np.array([zf, zf, zn, zn])).astype(np.float32)
    CHAM.append(dict(a=a, ay=ay, M=cv2.getPerspectiveTransform(src, dst), faixas=faixas))

def chamada(t):
    A = np.zeros((H, W), np.float32); AY = np.zeros_like(A)
    for c in CHAM:
        al = np.zeros_like(c["a"])
        for x0, x1, s in c["faixas"]:
            al[:, x0:x1] = np.clip((t - s) / 0.12, 0, 1)
        if al.max() == 0: continue
        A = np.maximum(A, cv2.warpPerspective(c["a"] * al, c["M"], (W, H)))
        AY = np.maximum(AY, cv2.warpPerspective(c["ay"] * al, c["M"], (W, H)))
    return A, AY

def masc(i):
    m = cv2.imread(f"mask/{min(max(i, 1), N):05d}.png", 0).astype(np.float32) / 255
    b = (m > 0.08).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    fl = b.copy(); cv2.floodFill(fl, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    b = b | (1 - fl)
    b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    return np.maximum(np.clip(m / 0.45, 0, 1), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.5))

AFIM = None
def camada(t):
    global AFIM
    if AFIM is None: AFIM = chamada(99)[0]      # espaço da chamada inteira (reservado desde o início)
    A, AY = chamada(t)
    fa, fy = fileiras(t)
    if fa is not None:   # fileiras viram textura do chão; a chamada abre um respiro justo em volta das letras
        livre = 1 - np.clip(cv2.GaussianBlur(cv2.dilate(A, np.ones((19, 19), np.uint8)), (0, 0), 4) * 1.3, 0, 1)
        fa, fy = fa * livre * 0.62, fy * livre * 0.62
    else:
        fa = fy = np.zeros_like(A)
    return A, AY, fa, fy

def compor(f, t, i):
    A, AY, FA, FY = camada(t)
    Hm = HS[i - 1]; wp = lambda c: cv2.warpPerspective(c, Hm, (W, H)) * cv2.warpPerspective(CHAO, Hm, (W, H))
    A, AY, FA, FY = wp(A), wp(AY), wp(FA), wp(FY)
    livre = (1 - masc(i))
    lum = cv2.GaussianBlur(f.mean(2), (0, 0), 4)
    luz = np.clip(lum / np.percentile(lum[1300:1900], 75), 0.6, 1.04)[..., None]
    for a, ay, forte in [(FA, FY, 0.18), (A, AY, 0.75)]:
        sh = np.maximum(cv2.GaussianBlur(np.roll(a, 6, 0), (0, 0), 7) * forte, cv2.GaussianBlur(a, (0, 0), 2.5) * forte * 0.8)
        f = f * (1 - (sh * livre)[..., None])
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
