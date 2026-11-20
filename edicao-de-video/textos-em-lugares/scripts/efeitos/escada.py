"""ESCADA PINTADA: texto grande pintado nos degraus, a letra "dobra" em cada quina (espelho escuro + piso),
pega a textura da pedra. Título fixo em cima, legenda ao lado da pessoa, palavra-chave gigante no patamar.
Segue a câmera na mão (homografias.json de rastrear_plano.py) e quem passa fica na frente (mask_gente/).
uso (na pasta da cena): python3 <skill>/scripts/efeitos/escada.py [--ver t1 t2 ...]   (--ver: só quadros de teste)
AJUSTE (cena.json → geometria): degraus [EA, EB, EC] (borda do degrau k em y = EA + EB/(EC - k), medida na grade
do quadro 1), patamar_k, espelho [fração do espelho na tela, idem no fim], borda_x (onde a escada começa à esquerda),
titulo_x / lado_x / patamar_x ([centro, largura]) e titulo_v / lado_v / patamar_v (degraus). O texto vem da transcrição:
1ª frase = título fixo; cada frase seguinte sobe ao lado da pessoa e a palavra-chave vai gigante no patamar."""
import sys, subprocess, os, json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
A = "/System/Library/Fonts/Avenir Next.ttc"
C = "/System/Library/Fonts/Avenir Next Condensed.ttc"
F = {"a": (A, 8), "ai": (A, 9), "c": (C, 8), "ci": (C, 9)}

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import cfg
# ---------- escada: borda do degrau k está em y = EA + EB/(EC - k) (quadro 1) ----------
EA, EB, EC = cfg('degraus', [-504.61, 11839.81, 16.1])   # borda do degrau k: y = EA + EB/(EC - k)
PITCH, V0, V1 = 170, -0.6, 11.8      # camada: 1 degrau = PITCH px; de v=V0 (topo) a V1 (último degrau)
LW, LH = W, int((V1 - V0) * PITCH)
def y_de_v(v): return EA + EB / (EC - v)
ys = np.arange(H, dtype=np.float32)
vv = EC - EB / np.maximum(ys - EA, 1)
YP = y_de_v(cfg('patamar_k', 10.15))                       # patamar (chão plano): passo linear, sem explodir
vv = np.where(ys > YP, 10.15 + (ys - YP) / 300, vv)
# ---------- dobra: cada degrau = espelho (vertical, escuro) + piso. A letra é desenhada "desdobrada"
# (espelho RL do passo, piso 1-RL) e no vídeo o espelho ocupa RS -> a letra quebra em cada quina.
RL, CONV, VPX = 0.48, 0.0, 726
kk = np.floor(vv); fi = vv - kk
RS = np.where(kk >= 9, cfg('espelho', [0.33, 0.27])[1], cfg('espelho', [0.33, 0.27])[0])                      # fração do espelho na tela (medido na placa)
esp = (fi < RS) & (ys <= YP)
fl = np.where(fi < RS, fi / RS * RL, RL + (fi - RS) / (1 - RS) * (1 - RL))
vl = np.where(ys <= YP, kk + fl, vv)
uf = np.where(fi < RS, fi / RS, (fi - RS) / (1 - RS))   # 0..1 dentro da face
# escala horizontal: piso afunila pro fundo, espelho abre de volta (zigue-zague nas hastes)
esc = np.where(fi < RS, 1 - CONV * uf, 1 - CONV * (1 - uf))
esc = np.where(ys <= YP, esc, 1.0).astype(np.float32)
mapy = np.repeat(((vl - V0) * PITCH)[:, None], W, 1).astype(np.float32)
xs = np.arange(W, dtype=np.float32)[None]
mapx = (VPX + (xs - VPX) / esc[:, None]).astype(np.float32)
# luz de cada face: sombra logo abaixo do bico do degrau, espelho mais escuro, quina interna fechada
luz = np.where(esp, 0.74 + 0.14 * np.clip(uf * 3, 0, 1), 1.0)
luz = np.where(esp & (uf > 0.85), luz * 0.9, luz)
luz = np.where((~esp) & (ys <= YP) & (uf > 0.93), 1.10, luz)            # bico iluminado
LUZ = cv2.GaussianBlur(luz.astype(np.float32).reshape(-1, 1), (1, 5), 0).ravel()[:, None, None]
dentro = ((vv >= V0) & (vv <= V1)).astype(np.float32)
lado = np.clip((np.arange(W) - cfg('borda_x', 372)) / 6, 0, 1).astype(np.float32)   # parede de pedra à esquerda
ZONA = (dentro[:, None] * lado[None]).astype(np.float32)
HS = [np.array(h, np.float64) for h in json.load(open("homografias.json"))]

IT = []
def _larg(t, f, s): return ImageFont.truetype(F[f][0], s, index=F[f][1]).getlength(t)
def linha(palavras, x, v, sai, maxw, gap=0.24, sy=1.0):
    """palavras [(texto, fonte, tam, entra, cor)] centradas em x, no degrau v (centro vertical)"""
    tot = lambda k: sum(_larg(t, f, int(s * k)) for t, f, s, _, _ in palavras) + sum(gap * s * k for _, _, s, _, _ in palavras[:-1])
    k = min(1.0, maxw / tot(1.0)); xx = x - tot(k) / 2
    for t, f, s, ent, cor in palavras:
        s2 = int(s * k); l = _larg(t, f, s2)
        IT.append((t, f, s2, xx + l / 2, (v - V0) * PITCH, ent, sai, cor, sy)); xx += l + gap * s2

# ---------- texto AUTOMÁTICO (frases da transcrição; ajuste fino em cena.json) ----------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from frases import frases, cfg, linhas, config
P = "a"; END = len(os.listdir("quadros")) / FPS
XT, WT = cfg("titulo_x", [735, 600])     # centro e largura do título (escada inteira)
XD, WD = cfg("lado_x", [866, 396])        # centro e largura da coluna livre ao lado da pessoa
XP, WP = cfg("patamar_x", [735, 610])     # palavra-chave gigante no patamar
V_TIT = cfg("titulo_v", [1.85, 4.8])      # degraus (v) das 2 linhas do título
V_LADO = cfg("lado_v", [6.4, 7.8, 9.3])   # degraus das linhas ao lado da pessoa
V_PAT = cfg("patamar_v", 10.95)
FR = frases(config().get("max_palavras", 8))
L = lambda pal, v, sai, tam=200, sy=1.55: linha([(t, "c", tam, e, c) for t, e, c in pal], XD, v, sai, WD, gap=0.18, sy=sy)
# título = 1ª frase, fixo até o fim, ocupando os degraus de cima
tl = linhas(FR[0], 8)
if len(tl) > 2: tl = [tl[0], [w for l in tl[1:] for w in l]]
for j, l in enumerate(tl):
    linha([(w["t"].upper(), "c", 720 if j == 0 else 400, -0.15 if (j == 0 and w is l[0]) else w["s"], "y" if w["chave"] else "b")
           for w in l], XT, V_TIT[j], END, WT, sy=2.45 if j == 0 else 2.0)
# demais frases: palavras ao lado da pessoa (até 3 linhas) + a palavra-chave gigante no patamar
for k, f in enumerate(FR[1:], 1):
    sai = FR[k + 1][0]["s"] - 0.02 if k + 1 < len(FR) else END
    chave = [w for w in f if w["chave"]][-1:]
    resto = [w for w in f if w not in chave]
    ls = linhas([dict(w, chave=False) for w in resto], 9) if resto else []
    if len(ls) > 3: ls = ls[:2] + [[w for l in ls[2:] for w in l]]
    for v, l in zip(V_LADO if len(ls) == 3 else V_LADO[:1] + V_LADO[2:] if len(ls) == 2 else V_LADO[1:2], ls):
        L([(w["t"].upper(), w["s"], "b") for w in l], v, sai, 270 if len(l) == 1 else 210, 1.7 if len(l) == 1 else 2.0)
    if chave:
        linha([(chave[0]["t"].upper(), "c", 560, chave[0]["s"], "y")], XP, V_PAT, sai, WP)

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


_tin = {}
def tinta(tx, f, s, sy):
    """letra pintada: preenchimento + contorno/volume escuro (no plano da escada, segue a perspectiva)"""
    k = (tx, f, s, sy)
    if k not in _tin:
        sp = sprite(tx, f, s)
        pad = int(s * 0.16)
        sp = np.pad(sp, pad)
        if sy != 1: sp = cv2.resize(sp, (sp.shape[1], int(sp.shape[0] * sy)))
        r = max(3, int(s * 0.03))
        ink = cv2.dilate(sp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        d = int(s * 0.075 * sy)                                   # volume pintado pra baixo
        vol = ink.copy()
        for j in range(1, d + 1, 2): vol = np.maximum(vol, np.roll(ink, j, 0))
        _tin[k] = (sp, vol)
    return _tin[k]

def anim_tinta(t, ent, sai):
    u = (t - ent) / 0.16
    if u <= 0 or t >= sai: return 0
    v = (sai - t) / 0.10
    return min(1, u) * min(1, v)

def camada(t):
    a = np.zeros((LH, LW), np.float32); ay = np.zeros_like(a); ak = np.zeros_like(a)
    for tx, f, s, x, y, ent, sai, cor, sy in IT:
        al = anim_tinta(t, ent, sai)
        if al > 0:
            sp, vol = tinta(tx, f, s, sy)
            cola(ak, vol, x, y, 1, al); cola(a, sp, x, y, 1, al)
            if cor == "y": cola(ay, sp, x, y, 1, al)
    rm = lambda c: cv2.remap(c, mapx, mapy, cv2.INTER_LINEAR, borderValue=0) * ZONA
    return rm(a), rm(ay), rm(ak)

AMA = np.array([255, 224, 105], np.float32)
BRA = np.array([250, 249, 244], np.float32)
ESC = np.array([46, 44, 48], np.float32)
def compor(f, t, i, pes):
    a, ay, ak = camada(t)
    Hm = HS[i - 1]
    wp = lambda c: cv2.warpPerspective(c, Hm, (W, H), flags=cv2.INTER_LINEAR)
    a, ay, ak = wp(a), wp(ay), wp(ak)
    livre = (1 - pes)[..., None]
    g = cv2.GaussianBlur(f.mean(2), (0, 0), 1.2) / 255
    # tinta pega a pedra: juntas, rachaduras e o espelho (mais escuro) de cada degrau
    sh = np.clip(g / 0.80, 0.38, 1.10)[..., None] * cv2.warpPerspective(np.repeat(LUZ[:, :, 0], W, 1), Hm, (W, H), borderValue=1)[..., None]
    gr = (g - cv2.GaussianBlur(g, (0, 0), 3))[..., None]       # textura fina
    r = (ay / np.maximum(a, 1e-3))[..., None]
    cor = BRA * (1 - r) + AMA * r
    pint = lambda c: np.clip(c * sh + gr * 160, 0, 255)
    k = (ak * 0.92)[..., None] * livre
    f = f * (1 - k) + pint(ESC) * k
    k = (a * 0.96)[..., None] * livre
    f = f * (1 - k) + pint(cor) * k
    return np.clip(f, 0, 255).astype(np.uint8)

def masc(i):
    # pessoa principal (mask/, com buracos fechados) + quem passa (mask_gente/, justo nas pernas, sem preencher entre elas)
    pg = f"mask_gente/{i:05d}.png"
    gente = cv2.imread(pg, 0).astype(np.float32) / 255 if os.path.exists(pg) else np.zeros((H, W), np.float32)
    m = cv2.imread(f"mask/{i:05d}.png", 0).astype(np.float32) / 255
    m[:700] = 0          # acima disso só tem quem passa (ajuste à cena)
    b = (m > 0.08).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    fl = b.copy(); cv2.floodFill(fl, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 1)
    b = b | (1 - fl)
    b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    prin = np.maximum(np.clip(m / 0.45, 0, 1), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.5))
    return np.maximum(prin, np.clip(gente / 0.5, 0, 1))

if "--ver" in sys.argv:
    for ts in sys.argv[sys.argv.index("--ver") + 1:]:
        t = float(ts); i = int(round(t * FPS)) + 1
        f = cv2.cvtColor(cv2.imread(f"quadros/{i:05d}.jpg"), cv2.COLOR_BGR2RGB).astype(np.float32)
        cv2.imwrite(f"ver_{t:05.2f}.jpg", cv2.cvtColor(compor(f, t, i, masc(i)), cv2.COLOR_RGB2BGR))
    sys.exit()

n = len(HS)
pb = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", "base.mp4", "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", "comp.mp4"], stdin=subprocess.PIPE)
i = 0
while True:
    b = pb.stdout.read(W * H * 3)
    if len(b) < W * H * 3 or i >= n: break
    i += 1
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32)
    out.stdin.write(compor(f, (i - 1) / FPS, i, masc(i)).tobytes())
out.stdin.close(); out.wait(); print("comp.mp4", i, "quadros")
