#!/usr/bin/env python3
"""Texto seguindo gestos: cada gesto desenha uma FORMA (arco, retângulo, círculo/elipse, linha) e a frase
falada fica presa nela, no lugar. O texto aparece por onde a mão passa, a forma se fecha, fica um pouco
em cena e sai; entra a próxima. Trechos sem gesto viram um BLOCO de texto entrando com a fala.

Rode de dentro da pasta do projeto (depois do preparar.sh):
  python3 -I <skill>/scripts/formas.py --ver 1.5 4 7.2      -> ver.jpg (só esses instantes)
  python3 -I <skill>/scripts/formas.py                      -> video_mudo.mp4
Lê projeto.json (formato em <skill>/exemplos/jardim.json e no SKILL.md).
"""
import json, sys, os, subprocess, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maos_util import carregar

W, H, FPS = 1080, 1920, 30
FONTE = "/System/Library/Fonts/Avenir Next Condensed.ttc"   # índice 8 = Heavy
CFG = json.load(open(sys.argv[sys.argv.index("--projeto") + 1] if "--projeto" in sys.argv else "projeto.json"))
QUADROS = CFG.get("quadros", "quadros")
SOMBRA = CFG.get("sombra", 1.0)          # força da sombra (1 = padrão forte)

def back(x):
    x = min(max(x, 0), 1); c = 2.0; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ---------- mãos ----------
PS = carregar("maos2.npy")
N = len(PS[0])
N = min(N, len([f for f in os.listdir(QUADROS) if f.endswith(".jpg")]))

# trechos espelhados: a imagem vira, as mãos também (a da direita passa pra esquerda); o texto não
ESPELHOS = [tuple(e) for e in CFG.get("espelhar", [])]
def espelhado(f): return any(a <= f / FPS < b for a, b in ESPELHOS)
_esp = [f for f in range(N) if espelhado(f)]
if _esp:
    _p0, _p1 = PS[0][_esp].copy(), PS[1][_esp].copy()
    PS[0][_esp] = np.stack([W - _p1[:, 0], _p1[:, 1]], 1)
    PS[1][_esp] = np.stack([W - _p0[:, 0], _p0[:, 1]], 1)

# ---------- geometria das formas ----------
def elipse(cx, cy, rx, ry, a0, a1, n=900):
    """ângulos em graus: 0 = direita, 90 = embaixo, 180 = esquerda, 270 = em cima. a0 -> a1 = sentido da leitura"""
    a = np.radians(np.linspace(a0, a1, n))
    return np.stack([cx + rx * np.cos(a), cy + ry * np.sin(a)], 1)

def retangulo(x0, y0, x1, y1, r):
    """cantos arredondados; começa embaixo à esquerda, sobe, cruza por cima e desce (sentido horário)"""
    pts = []
    def lin(p, q, n=120): pts.extend(np.linspace(p, q, n, endpoint=False))
    def arc(cx, cy, a0, a1): pts.extend(elipse(cx, cy, r, r, a0, a1, 40)[:-1])
    lin((x0, y1 - r), (x0, y0 + r)); arc(x0 + r, y0 + r, 180, 270)
    lin((x0 + r, y0), (x1 - r, y0)); arc(x1 - r, y0 + r, 270, 360)
    lin((x1, y0 + r), (x1, y1 - r)); arc(x1 - r, y1 - r, 0, 90)
    lin((x1 - r, y1), (x0 + r, y1)); arc(x0 + r, y1 - r, 90, 180)
    pts.append(pts[0])
    return np.array(pts)

def arco(cx, base, rx, alt, n=900):
    """arco (U de cabeça pra baixo): base esquerda -> por cima -> base direita"""
    t = np.linspace(0, math.pi, n)
    return np.stack([cx - rx * np.cos(t), base - alt * np.sin(t) ** 0.85], 1)

def caminho(pontos, n=40):
    """curva suave (Catmull-Rom) passando pelos pontos — zigue-zague, onda, qualquer traço"""
    P = np.asarray(pontos, float)
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)

def faixas_retangulo(x0, y0, x1, y1, r, n):
    """trechos retos de cada lado (esquerda, cima, direita[, baixo]) como fração do perímetro — texto nunca no canto"""
    h, w, q = (y1 - y0) - 2 * r, (x1 - x0) - 2 * r, math.pi * r / 2
    L = 2 * h + 2 * w + 4 * q
    lados, u = [], 0
    for comp in (h, w, h, w):
        lados.append(((u + 8) / L, (u + comp - 8) / L)); u += comp + q
    return lados[:n]

class Forma:
    def __init__(s, c):
        tipo = c["tipo"]; s.c = c
        s.fechada = False
        if tipo == "arco":
            pts = arco(c["cx"], c["base"], c["rx"], c["alt"])
        elif tipo == "retangulo":
            pts = retangulo(c["x0"], c["y0"], c["x1"], c["y1"], c.get("r", 70)); s.fechada = True
        elif tipo in ("elipse", "circulo"):
            rx = c.get("rx", c.get("r")); ry = c.get("ry", c.get("r"))
            a0, a1 = c.get("a0", 180), c.get("a1", 540)
            pts = elipse(c["cx"], c["cy"], rx, ry, a0, a1); s.fechada = abs(a1 - a0) >= 359
        elif tipo == "caminho":
            if c.get("suave", True): pts = caminho(c["pontos"])
            else:   # traços retos entre os pontos
                Pp = np.asarray(c["pontos"], float)
                pts = np.vstack([np.linspace(Pp[i], Pp[i + 1], 120, endpoint=False) for i in range(len(Pp) - 1)] + [Pp[-1:]])
        elif tipo == "linha":
            pts = np.array([[c["x0"], c["y0"]], [c["x1"], c["y1"]]], float)
            pts = np.stack([np.linspace(pts[0, k], pts[1, k], 300) for k in range(2)], 1)
        else:
            raise SystemExit(f"tipo de forma desconhecido: {tipo}")
        s.pts = np.asarray(pts, float)
        s.d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(s.pts, axis=0).T))]); s.L = s.d[-1]
        s.linhas = c["linhas"]; s.maos = c.get("maos", [0, 1])
        s.g0, s.g1, s.fecha, s.sai = c["g0"], c["g1"], c.get("fecha", c["g1"]), c.get("sai", c["g1"] + 0.7)
        s.tam = c.get("tam", 96)
        s.lado = -1 if c.get("letras") == "dentro" else 1   # "dentro" = metade de baixo, texto abaixo do traço
        s.desl = c.get("desl")
        s.faixas = c.get("faixas")
        if s.faixas is None and tipo == "retangulo":
            s.faixas = faixas_retangulo(c["x0"], c["y0"], c["x1"], c["y1"], c.get("r", 70), len(s.linhas))
            s.desl = s.desl or [12] * len(s.linhas)
        if s.faixas is None and tipo == "linha" and len(s.linhas) == 2:
            s.desl = s.desl or [14, -16]                   # 1ª linha em cima do traço, 2ª embaixo
        s.faixa = tuple(c.get("faixa", (0, 1)))
        if c.get("por_traco") and tipo == "caminho":
            # uma linha de texto (palavra) por traço reto entre pontos; "" = traço sem texto
            Pp = np.asarray(c["pontos"], float)
            seg = np.hypot(*np.diff(Pp, axis=0).T); acc = np.r_[0, np.cumsum(seg)]; Lt = acc[-1]
            m = c.get("margem", 45)
            s.faixas = [((acc[i] + m) / Lt, (acc[i + 1] - m) / Lt) for i in range(len(seg))][:len(s.linhas)]
            s.desl = s.desl or [12] * len(s.linhas)
        s.traco = c.get("traco", True)
        s.revela()
        if c.get("esquerda_pra_direita"):                   # nunca aparece à direita antes de aparecer à esquerda
            s.tb = np.minimum.accumulate(s.tb[::-1])[::-1]
        if c.get("varredura"):                              # ignora a mão: varre do começo ao fim no tempo do gesto
            s.tb = np.linspace(s.g0 + 0.1, s.fecha, s.B)

    def revela(s):
        """quando cada pedaço do caminho aparece: onde a mão passa (projeção da ponta da mão no caminho);
        buracos curtos entre trechos aparecem juntos; o que faltar se completa a partir das pontas ao FECHAR"""
        B = 600; s.B = B
        tb = np.full(B, np.inf)
        bxy = np.stack([np.interp(np.linspace(0, s.L, B), s.d, s.pts[:, k]) for k in range(2)], 1)
        for k in s.maos:
            prev = None
            for f in range(int(s.g0 * FPS), min(N, int(s.g1 * FPS))):
                if not np.isfinite(PS[k][f, 0]): prev = None; continue
                dist = np.hypot(*(bxy - PS[k][f]).T)
                b = int(np.argmin(dist)); t = f / FPS
                if dist[b] > s.c.get("alcance", 175): prev = None; continue
                if prev is not None and abs(b - prev) < B * 0.2:
                    seg = range(min(b, prev), max(b, prev) + 1)
                elif prev is not None and s.fechada and B - abs(b - prev) < B * 0.2:
                    seg = list(range(max(b, prev), B)) + list(range(0, min(b, prev) + 1))
                else:
                    seg = range(max(0, b - 3), min(B, b + 4))
                for j in seg: tb[j] = min(tb[j], t)
                prev = b
        fin = np.isfinite(tb); j = 0
        while j < B:
            if not fin[j]:
                k = j
                while k < B and not fin[k]: k += 1
                if j > 0 and k < B and k - j < 90: tb[j:k] = max(tb[j - 1], tb[k])
                j = k
            else: j += 1
        falta = ~np.isfinite(tb)
        if falta.all():
            tb[:] = s.fecha + np.linspace(0, 0.5, B)
        elif falta.any():
            dd = np.full(B, 1e9)
            for j in np.nonzero(~falta)[0]:
                dj = np.abs(np.arange(B) - j)
                if s.fechada: dj = np.minimum(dj, B - dj)
                dd = np.minimum(dd, dj)
            tb[falta] = s.fecha + 0.45 * dd[falta] / dd[falta].max()
        s.tb = tb

    def t_rev(s, u):
        return s.tb[min(s.B - 1, max(0, int(u / s.L * (s.B - 1))))]

_cache = {}
def glifo(ch, tam):
    k = (ch, tam)
    if k not in _cache:
        f = ImageFont.truetype(FONTE, tam, index=8)
        im = Image.new("L", (int(f.getlength(ch)) + 14, int(tam * 1.3)))
        ImageDraw.Draw(im).text((7, tam * 0.08), ch, font=f, fill=255)
        _cache[k] = (np.array(im), f.getlength(ch))
    return _cache[k]

def larg(txt, tam): return sum(glifo(c, tam)[1] for c in txt)

FORMAS = [Forma(c) for c in CFG.get("formas", [])]

# ---------- blocos (trechos sem gesto): palavras entram no tempo da fala ----------
words = []
if os.path.exists("transcricao.json"):
    for s in json.load(open("transcricao.json")):
        for w in s["w"]:
            words.append((w["s"], w["w"].upper().strip(",.?!:;")))
TROCAS = {k.upper(): v.upper() for k, v in CFG.get("trocas", {}).items()}
words = [(t, TROCAS.get(w, w)) for t, w in words]

def palavra_t(txt, depois):
    for ws, w in words:
        if ws >= depois - 0.05 and w == txt: return ws
    return depois

# ---------- desenho ----------
def stamp(alfa, alfa_s, ch, tam, x, y, ang, sc, op, ancora=0.80):
    g, adv = glifo(ch, tam)
    gh, gw = g.shape
    M = cv2.getRotationMatrix2D((gw / 2, gh * ancora), -ang, sc)
    M[0, 2] += x - gw / 2; M[1, 2] += y - gh * ancora
    a = cv2.warpAffine(g, M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32) / 255 * op
    np.maximum(alfa, a, out=alfa)
    np.maximum(alfa_s, a * op, out=alfa_s)     # sombra some mais rápido que a letra (sem fantasma escuro)

_desl = {}
def caminho_desloc(F, dd):
    """cópia do caminho afastada dd px (texto na curva sem abrir espaço entre as letras)"""
    k = (id(F), dd)
    if k not in _desl:
        tg = np.gradient(F.pts, axis=0); tg /= np.maximum(1e-6, np.hypot(*tg.T))[:, None]
        Q = F.pts + np.stack([tg[:, 1], -tg[:, 0]], 1) * dd
        _desl[k] = (Q, np.concatenate([[0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]))
    return _desl[k]

def forma_quadro(F, t, alfa, alfa_s):
    if t < F.g0 - 0.1 or t > F.sai + 0.45: return
    op = 1.0 if t < F.sai else max(0.0, 1 - (t - F.sai) / 0.4)
    sobe = 0 if t < F.sai else (t - F.sai) * 60
    if F.traco:
        linha = np.zeros((H, W), np.float32)
        u = np.linspace(0, F.L, F.B); vis = F.tb <= t
        pts = np.stack([np.interp(u, F.d, F.pts[:, 0]), np.interp(u, F.d, F.pts[:, 1]) - sobe], 1)
        for j in range(F.B - 1):
            if vis[j] and vis[j + 1]:
                cv2.line(linha, tuple(np.int32(pts[j] * 4)), tuple(np.int32(pts[j + 1] * 4)), 1.0, 5, cv2.LINE_AA, shift=2)
        linha *= op * 0.95
        np.maximum(alfa, linha, out=alfa); np.maximum(alfa_s, linha * op, out=alfa_s)
    if F.c.get("em_pe"):
        letras_em_pe(F, t, alfa, alfa_s, op, sobe); return
    for r, txt in enumerate(F.linhas):
        a0, a1 = F.faixa if F.faixas is None else F.faixas[r]
        if F.desl is not None: dd = F.desl[r]
        elif F.lado > 0: dd = 12 + r * F.tam * 1.05
        else: dd = -(14 + r * F.tam * 0.95)
        Q, dq = caminho_desloc(F, dd)
        disp = (a1 - a0) * dq[-1] * 0.96
        if not txt.strip(): continue
        tam = F.tam; w = larg(txt, tam)
        if w > disp: tam = int(tam * disp / w); w = larg(txt, tam)
        esp = min(F.c.get("espaco_max", 1.45 if not F.c.get("por_traco") else 1.0), disp / w)
        u = a0 * dq[-1] + (disp / 0.96 - w * esp) / 2
        for ch in txt:
            g, adv = glifo(ch, tam)
            meio = u + adv * esp / 2; u += adv * esp
            if ch == " ": continue
            tr = F.t_rev(meio / dq[-1] * F.L)
            if t < tr: continue
            x = np.interp(meio, dq, Q[:, 0]); y = np.interp(meio, dq, Q[:, 1]) - sobe
            m1, m2 = max(0, meio - 18), min(dq[-1], meio + 18)
            ang = math.degrees(math.atan2(np.interp(m2, dq, Q[:, 1]) - np.interp(m1, dq, Q[:, 1]),
                                          np.interp(m2, dq, Q[:, 0]) - np.interp(m1, dq, Q[:, 0])))
            sc = back((t - tr) / 0.25) if t - tr < 0.25 else 1.0
            anc = F.c.get("ancora", 0.80 if dd >= 0 else 0.12)   # "ancora": 0.5 = letra centrada no traço (ondas)
            stamp(alfa, alfa_s, ch, tam, x, y, ang, sc, op, ancora=anc)

def letras_em_pe(F, t, alfa, alfa_s, op, sobe):
    """letras em pé quicando sobre o traço (zigue-zague apertado): espaçadas na horizontal, a base de cada
    letra encosta no traço naquele x; 2ª linha em diante vai abaixo do traço (desl)"""
    ordem = np.argsort(F.pts[:, 0])
    xs, ys = F.pts[ordem, 0], F.pts[ordem, 1]
    us = F.d[ordem]
    x0, x1 = F.pts[:, 0].min() + 20, F.pts[:, 0].max() - 20
    for r, txt in enumerate(F.linhas):
        tam = F.tam; w = larg(txt, tam)
        if w > (x1 - x0): tam = int(tam * (x1 - x0) / w); w = larg(txt, tam)
        esp = min(1.3, (x1 - x0) / w)
        x = x0 + ((x1 - x0) - w * esp) / 2
        dd = 14 if r == 0 else -(14 + (r - 1) * tam * 1.05)
        if F.desl is not None: dd = F.desl[r]
        for ch in txt:
            g, adv = glifo(ch, tam)
            meio = x + adv * esp / 2; x += adv * esp
            if ch == " ": continue
            y = np.interp(meio, xs, ys)
            tr = F.t_rev(np.interp(meio, xs, us))
            if t < tr: continue
            sc = back((t - tr) / 0.25) if t - tr < 0.25 else 1.0
            if dd >= 0: stamp(alfa, alfa_s, ch, tam, meio, y - dd - sobe, 0, sc, op, ancora=0.80)
            else: stamp(alfa, alfa_s, ch, tam, meio, y - dd - sobe, 0, sc, op, ancora=0.12)

def bloco_quadro(B, t, alfa, alfa_s):
    if t < B["t0"] or t > B["sai"] + 0.45: return
    op = 1.0 if t < B["sai"] else max(0.0, 1 - (t - B["sai"]) / 0.4)
    y = B.get("y0", 250); depois = B["t0"]
    for txt, tam in B["linhas"]:
        x = (W - larg(txt, tam)) / 2
        for w in txt.split(" "):
            ws = palavra_t(w, depois); depois = ws
            for ch in w:
                g, adv = glifo(ch, tam)
                if t >= ws:
                    sc = back((t - ws) / 0.25) if t - ws < 0.25 else 1.0
                    stamp(alfa, alfa_s, ch, tam, x + adv / 2, y + tam, 0, sc, op)
                x += adv
            x += glifo(" ", tam)[1]
        y += tam * 1.08

def quadro(f):
    t = f / FPS
    alfa = np.zeros((H, W), np.float32); alfa_s = np.zeros((H, W), np.float32)
    for F in FORMAS: forma_quadro(F, t, alfa, alfa_s)
    for B in CFG.get("blocos", []): bloco_quadro(B, t, alfa, alfa_s)
    brilho = np.zeros((H, W), np.float32)                      # luz na ponta das mãos durante o gesto
    if CFG.get("luz_na_mao", True):
        for F in FORMAS:
            if F.g0 <= t <= F.g1:
                for k in F.maos:
                    if np.isfinite(PS[k][f, 0]):
                        cv2.circle(brilho, (int(PS[k][f, 0]), int(PS[k][f, 1])), 10, 1.0, -1, cv2.LINE_AA)
        brilho = cv2.GaussianBlur(brilho, (0, 0), 7) * 0.9
    return alfa, alfa_s, brilho

BRANCO = 255.0
def compor(f, img, crua=False):
    if espelhado(f): img = cv2.flip(img, 1)
    alfa, alfa_s, brilho = quadro(f)
    im = img.astype(np.float32); B = BRANCO
    # sombra forte: halo largo + sombra projetada + contorno escuro justo (lê em fundo colorido)
    halo = cv2.GaussianBlur(alfa_s, (0, 0), 14) * 1.6
    proj = np.roll(cv2.GaussianBlur(alfa_s, (0, 0), 5), (7, 4), (0, 1)) * 0.85
    borda = cv2.GaussianBlur(cv2.dilate(alfa_s, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))), (0, 0), 1.2) * 0.7
    sombra = np.clip(np.maximum(np.maximum(halo, proj), borda) * SOMBRA, 0, 0.82)
    im *= (1 - sombra[..., None])
    im = im * (1 - brilho[..., None]) + B * brilho[..., None]
    im = im * (1 - alfa[..., None]) + B * alfa[..., None]
    if crua: return im
    return np.clip(im, 0, 255).astype(np.uint8)

def render_hdr(trc):
    """compõe direto nos valores HLG/PQ do base.mp4 (10 bits, BT.2020), sem passar por SDR.
    Branco do texto = 100% do sinal (HLG): com 85% o texto parecia acinzentado."""
    global BRANCO
    BRANCO = CFG.get("branco_hdr", 1.0) * 255
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-vf", "scale=in_range=tv:in_color_matrix=bt2020",
                           "-f", "rawvideo", "-pix_fmt", "bgr48le", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr48le", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-vf", "scale=out_range=tv:out_color_matrix=bt2020",
                           "-c:v", "libx265", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
                           "-x265-params", f"colorprim=bt2020:transfer={trc}:colormatrix=bt2020nc:range=limited:log-level=error",
                           "-color_primaries", "bt2020", "-color_trc", trc, "-colorspace", "bt2020nc",
                           "video_mudo.mp4"], stdin=subprocess.PIPE)
    tam = W * H * 6
    for f in range(N):
        buf = rd.stdout.read(tam)
        if len(buf) < tam: break
        img = np.frombuffer(buf, np.uint16).reshape(H, W, 3).astype(np.float32) / 257.0
        wr.stdin.write(np.clip(compor(f, img, crua=True) * 257.0, 0, 65535).astype(np.uint16).tobytes())
        if f % 100 == 0: print(f, "/", N, "(HDR)", flush=True)
    wr.stdin.close(); wr.wait(); rd.kill()

def ler(f): return cv2.imread(f"{QUADROS}/{f+1:04d}.jpg")

if __name__ == "__main__":
    if "--ver" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--ver") + 1:] if not x.startswith("--")]
        ims = [cv2.resize(compor(min(N - 1, int(t * FPS)), ler(min(N - 1, int(t * FPS)))), (432, 768)) for t in ts]
        for im, t in zip(ims, ts):
            cv2.putText(im, f"{t:.1f}s", (12, 40), 0, 1.1, (0, 0, 0), 5); cv2.putText(im, f"{t:.1f}s", (12, 40), 0, 1.1, (255, 255, 255), 2)
        cv2.imwrite("ver.jpg", np.hstack(ims)); print("ver.jpg"); sys.exit()
    if os.path.exists("hdr.txt") and QUADROS == "quadros":
        render_hdr(open("hdr.txt").read().strip()); print("video_mudo.mp4 (HDR)"); sys.exit()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "medium",
                          "-pix_fmt", "yuv420p", "video_mudo.mp4"], stdin=subprocess.PIPE)
    for f in range(N):
        p.stdin.write(compor(f, ler(f)).tobytes())
        if f % 100 == 0: print(f, "/", N, flush=True)
    p.stdin.close(); p.wait()
    print("video_mudo.mp4")
