#!/usr/bin/env python3
"""Colagem derretendo: pessoa recortada sobre papel bege, tinta preta escorrendo do busto e colagem editorial
(grade pontilhada, palavras gigantes, meio-tom, frases em volta da cabeça, cenas nas lentes dos óculos).

Rode na pasta do projeto (depois do preparar.py):
  python3 -I motor.py roteiro.json --palavras        → lista as palavras com tempo
  python3 -I motor.py roteiro.json --ver 3.2 10.9    → quadros de teste em ver/
  python3 -I motor.py roteiro.json --rascunho        → rascunho.mp4 em meia resolução
  python3 -I motor.py roteiro.json                   → <saida>.mp4 + <saida>-camada-textos.mov + <saida>-sfx.wav
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from chave import despill, Olhos, corta_busto
from tinta import Tinta
import nucleo as K

W, H, FPS = 1080, 1920, 30


# ================================================================== utilidades
def hexrgb(c):
    if isinstance(c, (list, tuple)): return tuple(int(v) for v in c[:3])
    c = K.PALETA.get(c, c).lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def cl(x): return min(max(x, 0.0), 1.0)
def sai(p): p = cl(p); return 1 - (1 - p) ** 3
def suave(p): p = cl(p); return p * p * (3 - 2 * p)
def mola(p):
    p = cl(p)
    return 1 + 2.2 * (p - 1) ** 3 + 1.2 * (p - 1) ** 2 if p < 1 else 1.0


FONTES = {"cond": ("/System/Library/Fonts/HelveticaNeue.ttc", 9), "serif_i": ("/System/Library/Fonts/Supplemental/Baskerville.ttc", 2),
          "mono": ("/System/Library/Fonts/Menlo.ttc", 0)}
_fc, _cache = {}, {}


def fonte(nome, tam):
    k = (nome, int(tam))
    if k not in _fc:
        p, i = FONTES[nome]; _fc[k] = ImageFont.truetype(p, max(6, int(tam)), index=i)
    return _fc[k]


def cache(k, fn):
    if k not in _cache:
        if len(_cache) > 2500: _cache.clear()
        _cache[k] = fn()
    return _cache[k]


def txt_img(txt, nome, tam, corr, borda=0, borda_cor=None, track=0):
    f = fonte(nome, tam)
    ws = [f.getlength(c) for c in txt] if track else None
    w = int(sum(ws) + track * (len(txt) - 1)) + 4 if track else int(f.getlength(txt)) + 4
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (w + 2 * borda + 4, asc + desc + 2 * borda + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if track:
        x = borda + 2
        for c, cw in zip(txt, ws):
            d.text((x, borda + 2), c, font=f, fill=corr, stroke_width=borda, stroke_fill=borda_cor); x += cw + track
    else:
        d.text((borda + 2, borda + 2), txt, font=f, fill=corr, stroke_width=borda, stroke_fill=borda_cor)
    bb = im.getbbox()
    return im.crop(bb) if bb else im


def cola(lay, im, cx, cy, esc=1.0, giro=0.0, alfa=1.0, ancora="c"):
    if alfa <= 0.003 or esc <= 0.01 or im is None: return
    if abs(esc - 1) > 0.004:
        im = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))), Image.BILINEAR)
    if abs(giro) > 0.05: im = im.rotate(giro, Image.BICUBIC, expand=True)
    if alfa < 0.999:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * alfa)))
    x, y = {"c": (cx - im.width / 2, cy - im.height / 2), "l": (cx, cy - im.height / 2), "r": (cx - im.width, cy - im.height / 2),
            "lt": (cx, cy)}[ancora]
    x, y = int(round(x)), int(round(y))
    if x > W or y > H or x + im.width < 0 or y + im.height < 0: return
    sub = im.crop((max(0, -x), max(0, -y), min(im.width, W - x), min(im.height, H - y)))
    lay.alpha_composite(sub, (max(0, x), max(0, y)))


# ================================================================== projeto
args = sys.argv[1:]
if not args or not args[0].endswith(".json"): sys.exit(__doc__)
ROT = json.load(open(args[0]))
PASTA = os.path.dirname(os.path.abspath(args[0]))
P = lambda *a: os.path.join(PASTA, *a)
INFO = json.load(open(P("info.json")))
N = INFO["quadros"]; DUR = N / FPS
VERDE = set(INFO.get("verde", []))
PAL = K.Palavras(P(ROT.get("transcricao", "transcricao.json")))
if "--palavras" in args: PAL.lista(); sys.exit()

ACENTO = hexrgb(ROT.get("acento", "#1F3DC7"))
TINTA_C = (20, 20, 22)
FUNDO = np.array(hexrgb(ROT.get("fundo", "#F6F0E6")), np.float32) / 255
OLHOS = Olhos(P("olhos.json"), N)
FW = INFO.get("rosto_largura", 520)
BUSTO = ROT.get("busto", 0.95)


def _medidas():
    """largura do corpo (busto cortado) e se há óculos escuros, em ~12 quadros"""
    larg, escuro = [], []
    for i in np.linspace(0, N - 1, 12).astype(int):
        ol = OLHOS.em(i); fx, fy, fw, fh = ol[:4]
        al = corta_busto(np.asarray(Image.open(P("mask", f"{i + 1:05d}.png")).convert("L"), np.float32) / 255, ol, BUSTO)
        cols = np.flatnonzero(al[int(fy):].max(0) > 0.5) if fy < H else []
        if len(cols): larg.append(cols[-1] - cols[0])
        a = np.asarray(Image.open(P("quadros", f"{i + 1:05d}.jpg")).convert("L"), np.float32) / 255
        for ex, ey in (ol[4:6], ol[6:8]):
            y0, x0 = int(max(0, ey - fw * 0.06)), int(max(0, ex - fw * 0.1))
            escuro.append(a[y0:int(ey + fw * 0.06), x0:int(ex + fw * 0.1)].mean())
    return (float(np.median(larg)) if larg else FW * 1.8), float(np.median(escuro)) < ROT.get("lente_escura", 0.42) * 0.62


CORPO, OCULOS = _medidas()
ESC = ROT.get("tamanho", 1.0) * min(437 / FW, 900 / CORPO)   # escala da pessoa na tela
if "--trecho" not in args and any(it.get("tipo") == "lentes" for it in ROT.get("efeitos", [])) and not OCULOS and not ROT.get("forcar_lentes"):
    print("aviso: não achei óculos escuros no vídeo; os efeitos de lentes serão ignorados (\"forcar_lentes\": true para usar mesmo assim)")
FCX, FTOP = INFO.get("rosto_centro_x", 540), INFO.get("rosto_topo", 600)
TOPO = ROT.get("rosto_y", 0.28) * H                  # onde fica o topo do rosto na tela
TINTA = Tinta(escala=FW / 590, comprimento=ROT.get("tinta_comprimento", 1.0), seed=ROT.get("semente", 7), modo=ROT.get("tinta_modo", "atras"))
H_OUT = 1920 + int(720 * FW / 590 * ROT.get("tinta_comprimento", 1.0))


def fonte_mundo(x, y): return 540 + (x - FCX) * ESC, TOPO + (y - FTOP) * ESC


def tempo(v, depois=0.0): return PAL.tempo(v, depois)


# --- normaliza os itens do roteiro
ITENS = []
for k, it in enumerate(ROT.get("efeitos", [])):
    it = dict(it); it["_k"] = k
    a = it.get("de", it.get("em"))
    it["_de"] = tempo(a) if a is not None else 0.0
    if "em" in it: it["_em"] = tempo(it["em"])
    else: it["_em"] = it["_de"]
    if "ate" in it: it["_ate"] = tempo(it["ate"], it["_de"])
    else: it["_ate"] = it["_de"] + it.get("dur", 2.0)
    ITENS.append(it)


def palavras_entre(a, b):
    return [(w, s) for s, e, w in PAL.w if a - 1e-3 <= s < b - 1e-3]


# ================================================================== câmera
class Cam:
    def __init__(self, t):
        z, fy = 1.0, 960.0
        for it in ITENS:
            if it["tipo"] == "parede":
                a, b = it["_de"], it["_ate"]
                w = min(suave((t - a - 0.1) / 0.9), 1 - suave((t - (b - 0.85)) / 0.85))
                if w > 0: z = z + (it.get("zoom", 0.52) - 1) * w; fy = 960 - 60 * w
        self.dx = self.dy = 0.0
        for it in ITENS:
            if it["tipo"] == "soco" and it["_em"] <= t < it["_em"] + it.get("dur", 1.0):
                z *= it.get("zoom", 1.06)
            if it["tipo"] in ("soco", "gigante") and it.get("treme", it["tipo"] == "soco") and it["_em"] <= t < it["_em"] + 0.35:
                k = 1 - (t - it["_em"]) / 0.35
                self.dx += math.sin(t * 91) * 14 * k; self.dy += math.cos(t * 77) * 10 * k
        if ROT.get("aproxima_no_fim", True): z *= 1 + 0.05 * suave((t - (DUR - 1.6)) / 1.6)
        self.z, self.fx, self.fy = z, 540.0, fy

    def p(self, X, Y): return ((X - self.fx) * self.z + W / 2 + self.dx, (Y - self.fy) * self.z + H / 2 + self.dy)


def cola_mundo(lay, cam, im, X, Y, esc=1.0, giro=0.0, alfa=1.0, ancora="c"):
    x, y = cam.p(X, Y); cola(lay, im, x, y, esc * cam.z, giro, alfa, ancora)


# ================================================================== fundo
_g = np.random.default_rng(3).normal(0, 1, (H // 2, W // 2)).astype(np.float32)
GRAO = (np.asarray(Image.fromarray(_g).resize((W, H), Image.BICUBIC)) * 0.010)[..., None]
GRADE = ROT.get("grade", True)


def fundo(cam):
    base = np.empty((H, W, 3), np.float32); base[:] = FUNDO; base += GRAO
    im = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    if not GRADE: return im
    d = ImageDraw.Draw(im, "RGBA"); c = ACENTO + (95,)
    xs, ys = (150, 930, -420, 1500), (250, 1720, -560, 2480)
    for X in xs:
        x, _ = cam.p(X, 0); y = -18
        while y < H: d.line([(x, y), (x, y + 8)], fill=c, width=2); y += 18
    for Y in ys:
        _, y = cam.p(0, Y); x = -18
        while x < W: d.line([(x, y), (x + 8, y)], fill=c, width=2); x += 18
    for X in xs:
        for Y in ys:
            x, y = cam.p(X, Y)
            d.line([(x - 12, y), (x + 12, y)], fill=ACENTO + (200,), width=2); d.line([(x, y - 12), (x, y + 12)], fill=ACENTO + (200,), width=2)
    return im


# ================================================================== tratamentos
def meio_tom(rgb, cel=7.0):
    lum = np.clip((rgb @ np.array([0.3, 0.59, 0.11], np.float32) - 0.08) * 1.35, 0, 1)
    yy, xx = np.mgrid[0:lum.shape[0], 0:lum.shape[1]].astype(np.float32)
    u = (xx + yy) * 0.7071 / cel; v = (xx - yy) * 0.7071 / cel
    d = np.sqrt((u - np.floor(u) - 0.5) ** 2 + (v - np.floor(v) - 0.5) ** 2) * cel
    dot = np.clip(cel * 0.62 * np.sqrt(1 - lum) - d + 0.5, 0, 1)
    g = (0.95 - dot * 0.86) * 0.62 + (0.1 + 0.85 * lum) * 0.38
    return np.repeat(g[..., None], 3, -1)


DUO = {"azul": ((0.03, 0.06, 0.32), (0.78, 0.84, 1.0)), "laranja": ((0.35, 0.06, 0.02), (1.0, 0.62, 0.38)),
       "verde": ((0.02, 0.18, 0.12), (0.72, 0.95, 0.80)), "rosa": ((0.35, 0.03, 0.18), (1.0, 0.75, 0.86))}


def trata(rgb, modo):
    if modo == "meio": return meio_tom(rgb)
    if modo in DUO:
        e, c = DUO[modo]
        lum = np.clip((rgb @ np.array([0.3, 0.59, 0.11], np.float32) - 0.05) * 1.25, 0, 1)[..., None]
        return np.array(e, np.float32) * (1 - lum) + np.array(c, np.float32) * lum
    if modo == "pb":
        l = rgb.mean(-1, keepdims=True); return np.repeat(np.clip((l - 0.1) * 1.3, 0, 1), 3, -1)
    lum = (rgb @ np.array([0.3, 0.59, 0.11], np.float32))[..., None]
    return np.clip((lum + (rgb - lum) * ROT.get("saturacao", 1.18)) * 1.02, 0, 1)


# ================================================================== quadros e recortes
def quadro_rgb(i, meia=False):
    im = Image.open(P("quadros", f"{i + 1:05d}.jpg"))
    if meia: im.draft("RGB", (540, 960)); return im.convert("RGB").resize((540, 960))
    return im.convert("RGB")


def mascara(i, meia=False):
    m = Image.open(P("mask", f"{i + 1:05d}.png")).convert("L")
    if meia: m = m.resize((540, 960), Image.BILINEAR)
    return np.asarray(m, np.float32) / 255


def peca(i, w, h, modo="meio", recorta=True):
    """rosto do quadro i num retângulo w×h (fundo de papel quando recortado)"""
    a = np.asarray(quadro_rgb(i, True)).astype(np.float32) / 255
    al = mascara(i, True) if recorta else np.ones(a.shape[:2], np.float32)
    if i in VERDE: a = despill(a)
    fx, fy, fw, fh = OLHOS.em(i)[:4] / 2
    ar = w / h; ch = fh * 2.3; cw = ch * ar
    cx, cy = fx + fw / 2, fy + fh * 0.6
    box = [int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2)]
    out = np.empty((box[3] - box[1], box[2] - box[0], 3), np.float32); out[:] = (0.93, 0.9, 0.84)
    alo = np.zeros(out.shape[:2], np.float32)
    sy0, sx0 = max(0, box[1]), max(0, box[0]); sy1, sx1 = min(960, box[3]), min(540, box[2])
    out[sy0 - box[1]:sy1 - box[1], sx0 - box[0]:sx1 - box[0]] = a[sy0:sy1, sx0:sx1]
    alo[sy0 - box[1]:sy1 - box[1], sx0 - box[0]:sx1 - box[0]] = al[sy0:sy1, sx0:sx1]
    rgb = trata(out, modo)
    rgb = rgb * alo[..., None] + np.array((0.93, 0.9, 0.84), np.float32) * (1 - alo[..., None])
    return Image.fromarray((rgb * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS).convert("RGBA")


# ================================================================== óculos
def mascara_lentes(rgb, ol):
    Hh, Ww = rgb.shape[:2]
    fx, fy, fw, fh, ex1, ey1, ex2, ey2 = ol[:8]
    y0, y1 = max(0, int(min(ey1, ey2) - fw * 0.24)), min(Hh, int(max(ey1, ey2) + fw * 0.24))
    x0, x1 = max(0, int(min(ex1, ex2) - fw * 0.32)), min(Ww, int(max(ex1, ex2) + fw * 0.32))
    if x1 <= x0 or y1 <= y0: return (0, 0, 0, 0), None
    lum = rgb[y0:y1, x0:x1].mean(-1)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    m = np.zeros_like(lum)
    rx, ry = fw * 0.215, fw * 0.150
    for ex, ey in ((ex1, ey1), (ex2, ey2)):
        m = np.maximum(m, np.clip((1 - ((xx - ex) / rx) ** 4 - ((yy - ey) / ry) ** 4) * 6, 0, 1))
    esc = Image.fromarray(((lum < ROT.get("lente_escura", 0.42)) * 255).astype(np.uint8))
    esc = esc.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(13)).filter(ImageFilter.GaussianBlur(1.5))
    return (x0, y0, x1, y1), m * np.asarray(esc).astype(np.float32) / 255


def lente_conteudo(it, w, h, t, ol, org):
    modo = it.get("modo", "letreiro")
    fundo_c = hexrgb(it.get("fundo", ACENTO)); tc = hexrgb(it.get("cor", "#F6F0E6"))
    im = Image.new("RGB", (w, h), fundo_c); d = ImageDraw.Draw(im)
    if modo == "letreiro":
        f = fonte("cond", h * 0.34); unit = it.get("texto", "") + "   "; uw = max(f.getlength(unit), 1)
        x = -((t * it.get("velocidade", 230)) % uw)
        while x < w: d.text((x, h * 0.5), unit, font=f, fill=tc, anchor="lm"); x += uw
    elif modo == "palavras":
        for txt, (ex, ey) in ((it.get("esquerda", ""), ol[4:6]), (it.get("direita", ""), ol[6:8])):
            tam = ol[2] * 0.2; f = fonte("cond", tam)
            while f.getlength(txt) > ol[2] * 0.38 and tam > 10: tam *= 0.92; f = fonte("cond", tam)
            d.text((ex - org[0], ey - org[1]), txt, font=f, fill=tc, anchor="mm")
    elif modo == "filme":
        fh = int(h * 0.8); fw_ = int(fh * 1.25); passo = fw_ + 10
        de, ate = it.get("cenas_de", 0), it.get("cenas_ate", DUR)
        qs = [int(s * FPS) for s in np.linspace(tempo(de), min(tempo(ate), DUR - 0.1), 9)]
        x = -((t * 180) % passo) - passo; k = int(t * 180 // passo); j = 0
        while x < w:
            q = qs[(k + j) % len(qs)]
            fr = cache(("filme", q, fw_, fh), lambda: peca(q, fw_, fh, "cor", recorta=q in VERDE).convert("RGB"))
            im.paste(fr, (int(x), (h - fh) // 2)); x += passo; j += 1
        for xx in range(0, w, 14):
            d.rectangle([xx, 2, xx + 6, (h - fh) // 2 - 3], fill=(230, 225, 210))
            d.rectangle([xx, h - (h - fh) // 2 + 3, xx + 6, h - 3], fill=(230, 225, 210))
    elif modo == "coracoes":
        s = 1 + 0.12 * math.sin(t * 12)
        for ex, ey in (ol[4:6], ol[6:8]):
            tam = int(ol[2] * 0.26 * s)
            c = cache(("cor", tam), lambda: K.coracao_img(tam, (255, 255, 255, 255)))
            im.paste(c, (int(ex - org[0] - c.width / 2), int(ey - org[1] - c.height / 2)), c)
    elif modo == "emoji":
        for ex, ey in (ol[4:6], ol[6:8]):
            tam = int(ol[2] * 0.3)
            c = cache(("emo", it.get("emoji", "⭐"), tam), lambda: K.emoji(it.get("emoji", "⭐"), tam))
            im.paste(c, (int(ex - org[0] - c.width / 2), int(ey - org[1] - c.height / 2)), c)
    return im


def lentes(rgb, ol, it, t, forca):
    (x0, y0, x1, y1), m = mascara_lentes(rgb, ol)
    if m is None: return rgb
    c = np.asarray(lente_conteudo(it, x1 - x0, y1 - y0, t, ol, (x0, y0))).astype(np.float32) / 255
    sub = rgb[y0:y1, x0:x1]
    novo = np.clip(c * 0.95 + np.clip(sub.mean(-1, keepdims=True) - 0.35, 0, 1) * 0.5, 0, 1)
    k = (m * forca)[..., None]
    rgb = rgb.copy(); rgb[y0:y1, x0:x1] = sub * (1 - k) + novo * k
    return rgb


# ================================================================== frase em volta da cabeça
class Contorno:
    def __init__(self): self.prev = {}

    def caminho(self, k, al, cx, cy, margem=46):
        a = al[::4, ::4]; Hh, Ww = a.shape
        angs = np.radians(np.linspace(205, -25, 160)); rs = np.arange(10, 330, 2.0)
        r = []
        for th in angs:
            xs = (cx / 4 + math.cos(th) * rs).astype(int); ys = (cy / 4 - math.sin(th) * rs).astype(int)
            ok = (xs >= 0) & (xs < Ww) & (ys >= 0) & (ys < Hh)
            dentro = np.zeros_like(rs, bool); dentro[ok] = a[ys[ok], xs[ok]] > 0.4
            r.append(rs[np.flatnonzero(dentro)[-1]] * 4 if dentro.any() else 200)
        r = np.convolve(np.pad(np.array(r), 6, mode="edge"), np.ones(13) / 13, "valid")
        if k in self.prev: r = self.prev[k] * 0.75 + r * 0.25
        self.prev[k] = r
        return [(cx + math.cos(th) * (rr + margem), cy - math.sin(th) * (rr + margem)) for th, rr in zip(angs, r)]

    def desenha(self, lay, pts, texto, t, t0, tam, cor_, vel, alfa):
        seg = [0.0]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]): seg.append(seg[-1] + math.hypot(x1 - x0, y1 - y0))
        total = seg[-1]; f = fonte("cond", tam); unit = texto + "  "
        rev = sai((t - t0) / 0.9)
        s = -((t - t0) * vel) % f.getlength(unit) - f.getlength(unit); i = 0
        while s < total:
            ch = unit[i % len(unit)]; cw = f.getlength(ch); sc = s + cw / 2
            if 0 <= sc <= total * rev and ch != " ":
                j = min(max(int(np.searchsorted(seg, sc)) - 1, 0), len(pts) - 2)
                p = (sc - seg[j]) / max(seg[j + 1] - seg[j], 1e-6)
                x = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * p; y = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * p
                ang = math.degrees(math.atan2(pts[j + 1][1] - pts[j][1], pts[j + 1][0] - pts[j][0]))
                g = cache(("ch", ch, tam, cor_), lambda: txt_img(ch, "cond", tam, cor_ + (255,)))
                cola(lay, g, x, y, 1.0, -ang, alfa)
            s += cw; i += 1


CONT = Contorno()


# ================================================================== efeitos
def alfa_item(it, t, ent=0.2, sai_=0.2):
    return min(sai((t - it["_de"]) / ent) if ent else 1, 1 - cl((t - (it["_ate"] - sai_)) / max(sai_, 1e-3)))


def quebra(txt, maxc=34):
    linhas, at = [], ""
    for p in txt.split():
        if len(at) + len(p) + 1 > maxc and at: linhas.append(at); at = p
        else: at = (at + " " + p).strip()
    if at: linhas.append(at)
    return linhas


def fx_rotulo(c, it):
    t = c.t; a = alfa_item(it, t, 0.01, 0.15)
    if "texto" in it: txt = it["texto"] if t >= it["_em"] else ""
    else: txt = " ".join(w.upper() for w, s in palavras_entre(it["_de"], it["_ate"]) if t >= s)
    if not txt: return
    fundo_ = it.get("fundo", any(o["tipo"] == "parede" and o["_de"] <= t < o["_ate"] for o in ITENS))
    for n, linha in enumerate(quebra(txt)):
        im = cache(("rot", linha, fundo_), lambda: com_fundo(txt_img(linha, "mono", it.get("tam", 25), hexrgb(it.get("cor", ACENTO)) + (255,), track=3), fundo_))
        cola(c.frente_txt, im, it.get("x", 0.156) * W, it.get("y", 0.104) * H + n * 36, 1.0, 0, a, "lt")


def com_fundo(im, f):
    if not f: return im
    b = Image.new("RGBA", (im.width + 28, im.height + 22), tuple(int(v * 255) for v in FUNDO) + (255,))
    b.alpha_composite(im, (14, 11)); return b


def fx_italico(c, it):
    t = c.t; k = sai((t - it["_em"]) / 0.3) * alfa_item(it, t, 0.01, 0.2)
    if k <= 0: return
    tam = it.get("tam", 64); cor_ = hexrgb(it.get("cor", TINTA_C))
    im = cache(("it", it["texto"], tam, cor_), lambda: txt_img(it["texto"], "serif_i", tam, cor_ + (255,)))
    if im.width > W * 0.9: im = im.resize((int(W * 0.9), int(im.height * W * 0.9 / im.width)), Image.LANCZOS)
    cola(c.frente_txt, im, it.get("x", 0.5) * W, it.get("y", 0.156) * H + (1 - k) * 18, 1.0, 0, k)


def fx_gigante(c, it):
    t = c.t; k = sai((t - it["_em"]) / 0.22) * alfa_item(it, t, 0.01, 0.15)
    if k <= 0: return
    tam = it.get("tam", 330); cor_ = hexrgb(it.get("cor", ACENTO))
    if it.get("contorno"): im = cache(("gco", it["texto"], tam, cor_), lambda: txt_img(it["texto"], "cond", tam, (0, 0, 0, 0), 3, cor_ + (255,)))
    else: im = cache(("g", it["texto"], tam, cor_), lambda: txt_img(it["texto"], "cond", tam, cor_ + (255,)))
    esc = (1.18 - 0.18 * mola((t - it["_em"]) / 0.3)) * min(1, 1010 / im.width)
    lay = c.frente_txt if it.get("frente") else c.tras_txt
    cola_mundo(lay, c.cam, im, it.get("x", 0.5) * W, it.get("y", 0.80) * H, esc, it.get("giro", 0), k)


def fx_fileiras(c, it):
    t = c.t; t0 = it["_em"]; a = alfa_item(it, t, 0.01, 0.12)
    cor_ = hexrgb(it.get("cor", ACENTO)); tam = it.get("tam", 250)
    cheia = cache(("fc", it["texto"], tam, cor_), lambda: txt_img(it["texto"], "cond", tam, cor_ + (255,)))
    vaz = cache(("fv", it["texto"], tam, cor_), lambda: txt_img(it["texto"], "cond", tam, (0, 0, 0, 0), 3, cor_ + (255,)))
    passo = cheia.width + 40
    for r in range(9):
        off = ((t - t0) * 220 * (1 if r % 2 else -1)) % passo
        k = sai((t - t0 - r * 0.03) / 0.2)
        for j in range(-2, 4):
            cola_mundo(c.tras_txt, c.cam, cheia if r % 2 == 0 else vaz, -300 + j * passo + off, -60 + r * tam, 1.0, 0, a * k)


def fx_contorno(c, it):
    if c.cabeca is None: return
    t = c.t; a = alfa_item(it, t, 0.01, 0.25)
    pts = CONT.caminho(it["_k"], c.al_cabeca, c.cabeca[0], c.cabeca[1] + 40 * c.cam.z, 40 * c.cam.z)
    CONT.desenha(c.frente_txt, pts, it["texto"] + " •", t, it["_de"], int(it.get("tam", 54) * c.cam.z), hexrgb(it.get("cor", ACENTO)), it.get("velocidade", 150), a)


def fx_parede(c, it):
    t = c.t; a = alfa_item(it, t, 0.01, 0.4)
    tratos = it.get("tratamentos", ["meio", "azul", "cor", "meio", "laranja"])
    rng = np.random.default_rng(it["_k"] + 1)
    slots = [(-480 + gx * 330 + 540, -620 + gy * 440 + 300) for gx in range(-3, 5) for gy in range(-2, 5)]
    slots = [(X, Y) for X, Y in slots if not (120 < X < 960 and 120 < Y < 1800)]
    base_q = np.linspace(0, N - 1, 23).astype(int)
    for n, (X, Y) in enumerate(slots):
        q = int(base_q[(n * 5 + it["_k"]) % len(base_q)]); modo = tratos[n % len(tratos)]
        if n % 3 == 0: q = (q + c.i) % N  # alguns quadros tocam (vídeo)
        im = cache(("pc", q, modo), lambda: peca(q, 300, 400, modo))
        kk = sai((t - it["_de"] - 0.2 - rng.uniform(0, 0.4)) / 0.5)
        if kk <= 0: continue
        cola_mundo(c.tras_img, c.cam, im, X + math.sin(t * 0.6 + n) * 10, Y + math.cos(t * 0.5 + n * 1.7) * 10 + (1 - kk) * 60, 1.0, 0, kk * a)


def fx_foto(c, it):
    t = c.t; k = sai((t - it["_de"]) / 0.35); a = alfa_item(it, t, 0.01, 0.2)
    fr = Image.fromarray((trata(np.asarray(quadro_rgb(c.i)).astype(np.float32) / 255, "cor") * 255).astype(np.uint8))
    cw = 760; ch = int(cw * 1.46)
    fr = fr.crop((0, 115, 1080, 115 + int(1080 * ch / cw))).resize((cw, ch))
    card = Image.new("RGBA", (cw + 36, ch + 110), (252, 250, 245, 255)); card.paste(fr, (18, 18))
    ImageDraw.Draw(card).text((22, ch + 38), it.get("legenda", "REC ● BASTIDORES"), font=fonte("mono", 26), fill=(200, 40, 40))
    card = K.sombra(card, 18, (0, 14), 0.3)
    y = 920 + (1 - k) * 1200
    cola(c.frente_img, card, 540, y, 1.0, -2.5 + (1 - k) * 8, a)
    fi = cache("fita", lambda: K.fita(200, 56, "#F2B134", 2))
    cola(c.frente_img, fi, 330, y - ch / 2 - 40, 1.0, 14, a); cola(c.frente_img, fi, 760, y - ch / 2 - 30, 1.0, -10, a)
    c.esconde_pessoa = True


def fx_adesivos(c, it):
    t = c.t; t0 = it["_de"]; sai_k = cl((t - (it["_ate"] - 0.45)) / 0.45)
    itens = it.get("itens", ["lampada", "foguete", "estrela", "paleta", "lapis", "ia", "video", "musica", "camera", "chat",
                             {"tipo": "emoji", "nome": "💡"}, {"tipo": "emoji", "nome": "✨"}, {"tipo": "forma", "forma": "brilho", "cor": "#1F3DC7"}])
    rng = np.random.default_rng(11 + it["_k"])
    for n, spec in enumerate(itens):
        tn = t0 + 0.12 + n * it.get("intervalo", 0.14)
        X = rng.choice([rng.uniform(40, 260), rng.uniform(820, 1040)]); Y = rng.uniform(380, 1500)
        tam = rng.uniform(120, 190); giro = rng.uniform(-18, 18)
        if t < tn: continue
        im = cache(("ad", it["_k"], n), lambda: K.elemento(spec, int(tam), n))
        k = mola((t - tn) / 0.3)
        lay = c.tras_img if n % 3 == 0 else c.frente_img
        cola_mundo(lay, c.cam, im, X + (X - 540) * 2.2 * sai_k, Y - 900 * sai_k * (n % 2), k, giro + math.sin(t * 2 + n) * 4)


def fx_adesivo(c, it):
    t = c.t; k = mola((t - it["_em"]) / 0.35); a = alfa_item(it, t, 0.01, 0.2)
    tam = it.get("tam", 300)
    if "imagem" in it: im = cache(("adi", it["imagem"], tam), lambda: K.rasgado(K.imagem(P(it["imagem"]), tam), 16, 4))
    else: im = cache(("ade", it.get("emoji", "⭐"), tam), lambda: K.rasgado(K.emoji(it.get("emoji", "⭐"), tam), 16, 4))
    cola_mundo(c.frente_img, c.cam, im, it.get("x", 0.78) * W, it.get("y", 0.62) * H, k, it.get("giro", -12), a)


def fx_prompt(c, it):
    t = c.t; a = alfa_item(it, t, 0.01, 0.15); frase = "> " + it.get("texto", "")
    n = int(len(frase) * cl((t - it["_em"]) / it.get("digita", 1.0)))
    f = fonte("mono", 30); w = int(max(560, f.getlength(frase) + 70))
    im = Image.new("RGBA", (w, 96), (252, 250, 245, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, 95], outline=ACENTO + (255,), width=3)
    d.text((22, 48), frase[:n] + ("▌" if int(t * 4) % 2 else ""), font=f, fill=TINTA_C, anchor="lm")
    cola(c.frente_img, K.sombra(im, 12, (0, 8), 0.25), it.get("x", 0.5) * W, it.get("y", 0.765) * H, 1.0, -2, a)


def carimbo(txt, cor_):
    f = fonte("cond", 92); w = int(f.getlength(txt)) + 70; h = 150
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([5, 5, w - 6, h - 6], 18, outline=cor_ + (235,), width=8)
    d.text((w / 2, h / 2 + 4), txt, font=f, fill=cor_ + (235,), anchor="mm")
    a = np.asarray(im.split()[3]).astype(np.float32) * (np.random.default_rng(5).uniform(0, 1, (h, w)) > 0.18)
    im.putalpha(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
    return im


def fx_carimbo(c, it):
    t = c.t; k = mola((t - it["_em"]) / 0.3); a = alfa_item(it, t, 0.01, 0.2)
    im = cache(("car", it.get("texto", "APROVADO")), lambda: carimbo(it.get("texto", "APROVADO"), hexrgb(it.get("cor", "#E25C2C"))))
    cola_mundo(c.frente_img, c.cam, im, it.get("x", 0.78) * W, it.get("y", 0.62) * H, 1.6 - 0.6 * k, it.get("giro", -14), a * cl(k * 2))


def fx_lista(c, it):
    t = c.t; t0 = it["_em"]; sai_k = cl((t - (it["_ate"] - 0.6)) / 0.6)
    if t < t0: return
    k = sai((t - t0) / 0.4)
    cw, chh = 700, 150 + 62 * max(len(it.get("itens", [])), 4)
    im = Image.new("RGBA", (cw, chh), (253, 252, 247, 255)); d = ImageDraw.Draw(im)
    for yy in range(118, chh, 62): d.line([(30, yy), (cw - 30, yy)], fill=(150, 175, 230, 255), width=2)
    d.line([(80, 0), (80, chh)], fill=(230, 120, 120, 255), width=2)
    d.text((100, 56), it.get("titulo", ""), font=fonte("serif_i", 50), fill=TINTA_C, anchor="lm")
    marcas = [tempo(m, t0) for m in it["marcas"]] if "marcas" in it else [t0 + 0.4 + j * it.get("intervalo", 0.42) for j in range(len(it.get("itens", [])))]
    for j, (s, tj) in enumerate(zip(it.get("itens", []), marcas)):
        if t < tj: continue
        n = int(len(s) * cl((t - tj) / 0.35))
        d.text((100, 150 + j * 62), f"{j + 1:02d}  " + s[:n], font=fonte("mono", 27), fill=ACENTO + (255,), anchor="lm")
    card = K.sombra(im, 16, (0, 12), 0.3)
    X = 540 + 1300 * sai_k; Y = it.get("y", 0.75) * H + (1 - k) * 700
    cola(c.frente_img, card, X, Y, 1.0, 3 - 6 * sai_k)
    cola(c.frente_img, cache("fita2", lambda: K.fita(180, 52, "#F49CBB", 5)), X - 10, Y - chh / 2 - 6, 1.0, -4)


def fx_comentario(c, it):
    t = c.t; k = mola((t - it["_em"]) / 0.35); a = alfa_item(it, t, 0.01, 0.15)
    im = cache(("com", it.get("usuario"), it.get("texto")), lambda: K.comentario(it.get("usuario", "@voce"), it.get("texto", ""), 560))
    cola(c.frente_img, im, it.get("x", 0.5) * W, it.get("y", 0.77) * H, k, -3, a)
    if it.get("seta", True): cola(c.frente_txt, cache(("rotc", it.get("seta_texto", "AQUI EMBAIXO ↓")),
                                  lambda: txt_img(it.get("seta_texto", "AQUI EMBAIXO ↓"), "mono", 32, TINTA_C + (255,), track=3)),
                                  it.get("x", 0.5) * W, it.get("y", 0.77) * H + 160, 1.0, 0, a * sai((t - it["_em"] - 0.3) / 0.2))


def fx_curtidas(c, it):
    t = c.t; k = mola((t - it["_em"]) / 0.35); a = alfa_item(it, t, 0.01, 0.2)
    im = cache(("cu", it.get("n", "9.999")), lambda: K.curtidas(it.get("n", "9.999"), 230))
    cola_mundo(c.frente_img, c.cam, im, it.get("x", 0.2) * W, it.get("y", 0.64) * H, k, 8, a)


FX = {"rotulo": fx_rotulo, "italico": fx_italico, "gigante": fx_gigante, "fileiras": fx_fileiras, "contorno": fx_contorno,
      "parede": fx_parede, "foto": fx_foto, "adesivos": fx_adesivos, "adesivo": fx_adesivo, "prompt": fx_prompt,
      "carimbo": fx_carimbo, "lista": fx_lista, "comentario": fx_comentario, "curtidas": fx_curtidas}
SEM_DESENHO = {"lentes", "tratamento", "soco", "flash"}
for it in ITENS:
    if it["tipo"] not in FX and it["tipo"] not in SEM_DESENHO: sys.exit(f"tipo desconhecido no roteiro: {it['tipo']}")


def cresce(t):
    c = sai(t / ROT.get("tinta_inicio", 3.2)) if ROT.get("tinta_inicio", 3.2) > 0 else 1.0
    if ROT.get("tinta_fim", True): c += 0.75 * suave((t - (DUR - 1.8)) / 1.8)
    return c


# ================================================================== quadro
class Ctx: pass


def quadro(i):
    t = i / FPS; cam = Cam(t)
    c = Ctx(); c.t, c.i, c.cam, c.cabeca, c.esconde_pessoa = t, i, cam, None, False
    novo = lambda: Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.tras_img, c.tras_txt, c.frente_img, c.frente_txt = novo(), novo(), novo(), novo()
    ativos = [it for it in ITENS if it["_de"] <= t < it["_ate"]]
    # --- pessoa
    rgb = np.asarray(quadro_rgb(i)).astype(np.float32) / 255
    al = mascara(i)
    if i in VERDE: rgb = despill(rgb)
    ol = OLHOS.em(i)
    al = corta_busto(al, ol, BUSTO)
    modo = next((it.get("modo", "meio") for it in ativos if it["tipo"] == "tratamento"), "cor")
    rgb = trata(rgb, modo)
    for it in ativos:
        if it["tipo"] == "lentes" and (OCULOS or ROT.get("forcar_lentes")): rgb = lentes(rgb, ol, it, t, min(1, (t - it["_de"]) / 0.08)); break
    r2, a2, _ = TINTA.aplica(rgb, al, t, cresce(t), H_OUT)
    src = Image.fromarray((np.clip(np.dstack([r2, a2]), 0, 1) * 255).astype(np.uint8), "RGBA")
    z = cam.z * ESC
    ox = (540 - FCX * ESC - cam.fx) * cam.z + W / 2 + cam.dx
    oy = (TOPO - FTOP * ESC - cam.fy) * cam.z + H / 2 + cam.dy
    pessoa = src.transform((W, H), Image.AFFINE, (1 / z, 0, -ox / z, 0, 1 / z, -oy / z), Image.BILINEAR)
    al_tela = np.asarray(pessoa.split()[3]).astype(np.float32) / 255
    if any(it["tipo"] == "contorno" for it in ativos):
        fx_, fy_, fw_, fh_ = ol[:4]
        c.cabeca = cam.p(*fonte_mundo(fx_ + fw_ / 2, fy_ + fh_ * 0.42))
        _, yq = cam.p(*fonte_mundo(0, fy_ + fh_ * 1.05))
        c.al_cabeca = al_tela.copy(); c.al_cabeca[int(min(max(0, yq), H)):] = 0
    # --- efeitos
    for it in ativos:
        if it["tipo"] in FX: FX[it["tipo"]](c, it)
    # --- montar
    out = fundo(cam)
    out.alpha_composite(c.tras_img); out.alpha_composite(c.tras_txt)
    if not c.esconde_pessoa:
        sh = pessoa.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.22))
        sombra = Image.new("RGBA", (W, H), (60, 45, 30, 0)); sombra.putalpha(sh)
        out.alpha_composite(sombra, (int(8 * cam.z), int(16 * cam.z)))
        out.alpha_composite(pessoa)
    else: al_tela = al_tela * 0
    out.alpha_composite(c.frente_img); out.alpha_composite(c.frente_txt)
    for tf in FLASHES:
        if tf <= t < tf + 0.12:
            out = Image.blend(out, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.55 * (1 - (t - tf) / 0.12))
    txt = c.tras_txt.copy()
    txt.putalpha(Image.fromarray((np.asarray(txt.split()[3]).astype(np.float32) * (1 - al_tela)).astype(np.uint8)))
    txt.alpha_composite(c.frente_txt)
    return out.convert("RGB"), txt


FLASHES = sorted({it["_em"] for it in ITENS if it["tipo"] == "flash"} |
                 {it["_de"] for it in ITENS if it["tipo"] in ("tratamento", "foto")} |
                 {it["_ate"] for it in ITENS if it["tipo"] in ("tratamento", "foto") and it["_ate"] < DUR - 0.2})


# ================================================================== som
class Som(K.Som):
    def gota(self, t, f0=520, g=0.4):
        n, tt = self._t(0.12); f = f0 * (1 + 2.2 * (tt / 0.12))
        self.poe(np.sin(2 * np.pi * np.cumsum(f) / K.SR) * np.exp(-tt * 38) * 0.8, t, g)

    def slam(self, t, g=0.6): self.baque(t, g); self.clique(t, g * 0.8); self.whoosh(t, 0.25, g * 0.5)


def sons(saida):
    S = Som(DUR, seed=9); v = ROT.get("sfx_volume", 1.0)
    if ROT.get("tinta_inicio", 3.2) > 0:
        for tt, f in [(0.25, 380), (0.9, 470), (1.6, 340), (2.4, 520)]: S.gota(tt, f, 0.35 * v)
    for g in TINTA.gotas[::3]:
        t = 3.5 + g["ph"]
        while t < DUR: S.gota(t, 600 + g["w"] * 4, 0.12 * v); t += g["pinga"] * 2.3
    if ROT.get("tinta_fim", True):
        S.sobe(DUR - 0.3, 1.6, 0.3 * v)
        for tt in (DUR - 1.4, DUR - 0.9, DUR - 0.5): S.gota(tt, 300, 0.35 * v)
    for tf in FLASHES: S.flash(tf, 0.35 * v)
    for it in ITENS:
        tp, a, b, e = it["tipo"], it["_de"], it["_ate"], it["_em"]
        if tp == "rotulo":
            for w, s in palavras_entre(a, b): S.tique(s, 2400, 0.12 * v)
        elif tp in ("gigante", "fileiras"): S.slam(e, 0.42 * v)
        elif tp == "parede": S.whoosh(a + 1.0, 0.9, 0.4 * v); S.whoosh(b, 0.85, 0.4 * v)
        elif tp == "soco": S.whoosh(e + 0.06, 0.22, 0.45 * v)
        elif tp == "lentes" and (OCULOS or ROT.get("forcar_lentes")): S.tique(a, 3200, 0.18 * v)
        elif tp == "adesivos":
            for n in range(len(it.get("itens", [0] * 13))): S.pop(a + 0.12 + n * it.get("intervalo", 0.14), 480 + (n % 5) * 90, 0.3 * v)
            S.whoosh(b, 0.4, 0.5 * v)
        elif tp == "adesivo": S.pop(e, 600, 0.45 * v); S.papel(e, 0.3 * v)
        elif tp == "foto": S.papel(a, 0.5 * v); S.whoosh(a + 0.2, 0.35, 0.5 * v); S.baque(a + 0.3, 0.3 * v)
        elif tp == "prompt": S.digita(e, e + it.get("digita", 1.0), 0.15 * v)
        elif tp == "carimbo": S.ding(e, 1318, 0.4 * v); S.baque(e + 0.05, 0.4 * v)
        elif tp == "lista":
            S.papel(e, 0.5 * v); S.whoosh(e + 0.2, 0.35, 0.4 * v)
            marcas = [tempo(m, e) for m in it["marcas"]] if "marcas" in it else [e + 0.4 + j * it.get("intervalo", 0.42) for j in range(len(it.get("itens", [])))]
            for m in marcas: S.digita(m, m + 0.35, 0.12 * v)
            S.whoosh(b, 0.4, 0.4 * v)
        elif tp == "comentario": S.pop(e, 650, 0.45 * v)
        elif tp == "curtidas": S.pop(e, 720, 0.45 * v); S.ding(e + 0.1, 1568, 0.3 * v)
    S.salva(saida)


# ================================================================== saída
def trecho(a, b, saida, saida_txt=None, meia=False):
    w, h = (W // 2, H // 2) if meia else (W, H)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", saida], stdin=subprocess.PIPE)
    q = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", saida_txt], stdin=subprocess.PIPE) if saida_txt else None
    for i in range(a, b):
        im, txt = quadro(i)
        p.stdin.write((im.resize((w, h), Image.BILINEAR) if meia else im).tobytes())
        if q: q.stdin.write(txt.tobytes())
        if (i - a) % 90 == 0: print(f"  quadro {i} de {b}", flush=True)
    p.stdin.close(); p.wait()
    if q: q.stdin.close(); q.wait()


if __name__ == "__main__":
    if "--ver" in args:
        os.makedirs(P("ver"), exist_ok=True)
        for v in args[args.index("--ver") + 1:]:
            im, _ = quadro(min(int(float(v) * FPS), N - 1)); im.save(P("ver", f"q_{float(v):05.2f}.jpg"), quality=88)
            print("ver/" + f"q_{float(v):05.2f}.jpg")
        sys.exit()
    if "--trecho" in args:
        k = args.index("--trecho")
        trecho(int(args[k + 1]), int(args[k + 2]), args[k + 3], None if args[k + 4] == "-" else args[k + 4], "--meia" in args); sys.exit()
    meia = "--rascunho" in args
    nome = "rascunho" if meia else ROT.get("saida", "final.mp4").replace(".mp4", "")
    nproc = int(ROT.get("processos", max(2, min(6, (os.cpu_count() or 4) // 2))))
    cortes = np.linspace(0, N, nproc + 1).astype(int)
    os.makedirs(P("partes"), exist_ok=True)
    procs = []
    for k in range(nproc):
        cmd = [sys.executable, "-I", __file__, args[0], "--trecho", str(cortes[k]), str(cortes[k + 1]), P("partes", f"p{k}.mp4"),
               "-" if meia else P("partes", f"t{k}.mov")] + (["--meia"] if meia else [])
        procs.append(subprocess.Popen(cmd))
    sons(P(f"{nome}-sfx.wav"))
    if any(pr.wait() for pr in procs): sys.exit("um dos processos falhou")
    junta = lambda lista, saida: subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", saida], check=True)
    with open(P("partes", "lista.txt"), "w") as f: f.writelines(f"file 'p{k}.mp4'\n" for k in range(nproc))
    junta(P("partes", "lista.txt"), P("partes", "video.mp4"))
    trilha = ROT.get("trilha")
    entradas = ["-i", P("partes", "video.mp4"), "-i", P("base.mp4"), "-i", P(f"{nome}-sfx.wav")]
    filtro = "[1:a]aresample=48000[v];[2:a]volume=0.9[s];[v][s]amix=inputs=2:normalize=0[m]"
    if trilha:
        entradas += ["-i", P(trilha)]
        filtro = ("[1:a]aresample=48000,asplit[v][vk];[2:a]volume=0.9[s];"
                  f"[3:a]volume={ROT.get('trilha_volume', 0.18)}[tr];[tr][vk]sidechaincompress=threshold=0.03:ratio=6:release=400[td];"
                  "[v][s][td]amix=inputs=3:normalize=0[m]")
    filtro += ";[m]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", filtro, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", P(f"{nome}.mp4")], check=True)
    if not meia:
        with open(P("partes", "lista_t.txt"), "w") as f: f.writelines(f"file 't{k}.mov'\n" for k in range(nproc))
        junta(P("partes", "lista_t.txt"), P(f"{nome}-camada-textos.mov"))
    print("pronto:", f"{nome}.mp4")
