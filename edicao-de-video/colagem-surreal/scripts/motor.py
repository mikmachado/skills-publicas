#!/usr/bin/env python3
"""Colagem surreal — monta o vídeo a partir do roteiro.json (rode na pasta do projeto, depois do preparar.py).

  python3 -I motor.py roteiro.json --palavras        → palavras da fala com tempo (para escrever o roteiro)
  python3 -I motor.py roteiro.json --plano           → cenas, cortes secos e duração final
  python3 -I motor.py roteiro.json --recorte         → ver/recorte_<take>.jpg (recorte sobre magenta, o vídeo todo)
  python3 -I motor.py roteiro.json --ver 3.2 12 40   → ver/q_003.20.jpg … (tempos do vídeo FINAL)
  python3 -I motor.py roteiro.json                   → render/ + final.mp4, final-camada-textos.mov, final-sfx.wav, final.srt
  python3 -I motor.py roteiro.json --trecho 10 20    → refaz só esses segundos do vídeo final (depois: --monta)
  python3 -I motor.py roteiro.json --monta           → só junta render/ + áudio de novo
"""
import sys, os, json, math, re, unicodedata, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
ATIVOS = os.path.join(AQUI, "..", "ativos")
W, H, FPS = 1080, 1920, 30

_arg = next((a for a in sys.argv[1:] if a.endswith(".json")), None) or os.environ.get("COLAGEM_ROTEIRO")
if not _arg: sys.exit(__doc__)
ROTEIRO = os.path.abspath(_arg)
os.environ["COLAGEM_ROTEIRO"] = ROTEIRO
PROJ = os.path.dirname(ROTEIRO)
R = json.load(open(ROTEIRO))
OUT = os.path.join(PROJ, "render/quadros"); OUTT = os.path.join(PROJ, "render/texto")

# ================================================================== utilidades
def clamp(p): return min(max(p, 0.0), 1.0)
def sai(p): p = clamp(p); return 1 - (1 - p) ** 3
def entra(p): p = clamp(p); return p ** 3
def suave(p): p = clamp(p); return 3 * p * p - 2 * p ** 3
def mola(p, c=1.9):
    p = clamp(p); p -= 1
    return 1 + (c + 1) * p ** 3 + c * p ** 2


_cache = {}
def C(chave, fn):
    if chave not in _cache: _cache[chave] = fn()
    return _cache[chave]


CORES = {"cinza": (52, 50, 48), "vermelho": (193, 18, 31), "preto": (20, 20, 20), "branco": (250, 248, 244)}
DUO = {"verde": ((0x0b, 0x3d, 0x22), (0x9b, 0xf0, 0x8c)), "amarelo": ((0x5a, 0x33, 0x05), (0xff, 0xe0, 0x5a)),
       "azul": ((0x0c, 0x1c, 0x5e), (0x8f, 0xc8, 0xff)), "magenta": ((0x4a, 0x06, 0x38), (0xff, 0x8f, 0xc8))}
PAPEIS = {"amarelo": (242, 196, 64), "vermelho": (226, 86, 92), "azul": (143, 200, 255), "verde": (155, 220, 140), "rosa": (244, 166, 184)}
FONTE = R.get("fonte", "/System/Library/Fonts/Supplemental/MarkerFelt.ttc")
PAPEL = np.array(R.get("papel", [239, 236, 230]), np.float32)


def norm(s):
    s = unicodedata.normalize("NFC", s.lower())
    return re.sub(r"[^\w]", "", s)


# ================================================================== fala e tempos
def _palavras():
    t = json.load(open(os.path.join(PROJ, "transcricao.json")))
    out = []
    for s in t:
        for w in s.get("w", s.get("words", [])):
            out.append((w.get("w", w.get("word", "")).strip(), w["s"], w["e"]))
    return out


PALAVRAS = _palavras()


def acha(ref, desde=0.0):
    """número → segundos da fala; "@palavra", "@palavra#2", "@palavra+0.3", "@palavra:fim" → procura a partir de `desde`."""
    if isinstance(ref, (int, float)): return float(ref)
    m = re.match(r"@([^#+:\-]+)(?:#(\d+))?(:fim)?([+-][\d.]+)?$", ref.strip())
    if not m: raise ValueError(f"tempo inválido: {ref}")
    alvo, n, fim, d = norm(m.group(1)), int(m.group(2) or 1), m.group(3), float(m.group(4) or 0)
    k = 0
    for w, s, e in PALAVRAS:
        if s < desde - 0.05: continue
        nw = norm(w)
        if nw == alvo or (len(alvo) > 3 and nw.startswith(alvo)):
            k += 1
            if k == n: return (e if fim else s) + d
    perto = [w for w, s, e in PALAVRAS if s >= desde - 0.05][:12]
    raise ValueError(f"palavra não encontrada: {ref} (a partir de {desde:.2f}s; próximas: {' '.join(perto)})")


def _cortes(a, b, fixos=(), pad0=0.05, pad1=0.09, junta=0.18):
    iv = [(max(s - pad0, a), min(e + pad1, b)) for w, s, e in PALAVRAS if s < b and e > a] + [tuple(x) for x in fixos]
    iv.sort()
    out = []
    for x, y in iv:
        if out and x - out[-1][1] < junta: out[-1] = (out[-1][0], max(out[-1][1], y))
        else: out.append((x, y))
    if not out: out = [(a, b)]
    if out[0][0] - a < 0.4: out[0] = (a, out[0][1])
    if b - out[-1][1] < 0.6: out[-1] = (out[-1][0], b)
    return out


CENAS = []
_t = 0.0
for k, c in enumerate(R["cenas"]):
    c = dict(c); c["_k"] = k
    c["_de"] = acha(c["de"], _t if isinstance(c["de"], str) else 0)
    c["_ate"] = acha(c["ate"], c["_de"])
    c["_tr"] = _cortes(c["_de"], c["_ate"], c.get("fixos", [])) if c.get("cortes_secos", True) else [(c["_de"], c["_ate"])]
    c["_dur"] = sum(y - x for x, y in c["_tr"])
    CENAS.append(c); _t = c["_ate"]
_o = 0.0
for c in CENAS: c["_off"] = _o; _o += c["_dur"]
DUR = _o
N = int(round(DUR * FPS))


def cena_em(t):
    for c in CENAS:
        if t < c["_off"] + c["_dur"]: return c
    return CENAS[-1]


def fonte_de(c, tl):
    acc = 0.0
    for x, y in c["_tr"]:
        if tl < acc + (y - x): return x + (tl - acc)
        acc += y - x
    return c["_tr"][-1][1] + (tl - acc)


def L(c, ts):
    acc, tr = 0.0, c["_tr"]
    if ts < tr[0][0]: return ts - tr[0][0]
    for x, y in tr:
        if ts < x: return acc
        if ts <= y: return acc + (ts - x)
        acc += y - x
    return acc + (ts - tr[-1][1])


def S(c, ref, padrao=None):
    """referência da cena → tempo da FONTE (procura palavras a partir do início da cena)."""
    if ref is None: return padrao
    return C(("S", c["_k"], str(ref)), lambda: acha(ref, c["_de"]))


def T(c, ref, padrao=None):
    """referência → tempo LOCAL da cena."""
    s = S(c, ref)
    return padrao if s is None else L(c, s)


def g(c, chave, padrao=None): return c.get(chave, padrao)


# ================================================================== takes (quadros recortados + rostos)
class Take:
    def __init__(self, nome):
        self.nome = nome
        self.dir = os.path.join(PROJ, "recorte", nome)
        self.n = len([f for f in os.listdir(self.dir) if f.endswith(".png")])
        raw = json.load(open(os.path.join(PROJ, "rostos", f"{nome}.json")))
        v = np.full((len(raw), 4), np.nan)
        for i, x in enumerate(raw):
            if x: v[i] = x[:4]
        # corta onde o rosto pula (troca de take dentro do arquivo) e suaviza dentro de cada pedaço
        cx = v[:, 0] + v[:, 2] / 2
        cortes = [0] + [i for i in range(1, len(v)) if np.isfinite(cx[i]) and np.isfinite(cx[i - 1]) and abs(cx[i] - cx[i - 1]) > 70] + [len(v)]
        for a, b in zip(cortes[:-1], cortes[1:]):
            bl = v[a:b]
            for k in range(4):
                col = bl[:, k]; ok = ~np.isnan(col)
                if ok.sum() == 0: continue
                col[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), col[ok])
                if len(col) > 9: bl[:, k] = np.convolve(np.pad(col, 4, mode="edge"), np.ones(9) / 9, "valid")
        ok = np.isfinite(v[:, 0])
        if ok.any():
            for k in range(4): v[~ok, k] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), v[ok, k])
        self.rostos = v

    def fq(self, ts): return int(min(max(round(ts * FPS) + 1, 1), self.n))
    def rgba(self, f): return Image.open(os.path.join(self.dir, f"{int(min(max(f, 1), self.n)):05d}.png"))
    def rosto(self, f): return self.rostos[int(min(max(f, 1), self.n)) - 1]


def TK(nome="fala"): return C(("take", nome), lambda: Take(nome))


# ================================================================== desenho
def fazer_papel():
    rng = np.random.default_rng(3)
    n = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 20) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) - 128
    base = PAPEL[None, None] + (n * 0.25 + rng.normal(0, 5, (H, W)).astype(np.float32))[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.46) / (H * 0.6)) ** 2)
    return np.clip(base * (1 - 0.13 * np.clip(r - 0.45, 0, 1) ** 1.4)[..., None], 0, 255) / 255


def fazer_raios(n=16):
    S_ = 2800
    im = Image.new("L", (S_, S_), 0); d = ImageDraw.Draw(im); c = S_ / 2
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = a0 + 2 * math.pi / n * 0.42
        d.polygon([(c, c), (c + S_ * math.cos(a0), c + S_ * math.sin(a0)), (c + S_ * math.cos(a1), c + S_ * math.sin(a1))], fill=255)
    yy, xx = np.mgrid[0:S_, 0:S_].astype(np.float32)
    rr = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    return Image.fromarray((np.asarray(im, np.float32) / 255 * np.clip((rr - 380) / 700, 0, 1) * 0.16 * 255).astype(np.uint8))


def fundo(t, raios=True, cy=1000):
    base = C("papel", fazer_papel).copy()
    if raios:
        Rr = C("raios", fazer_raios); S_ = Rr.width
        im = Rr.rotate(t * 2.2, resample=Image.BILINEAR)
        x0, y0 = int(S_ / 2 - 540), int(S_ / 2 - cy)
        base *= (1 - np.asarray(im.crop((x0, y0, x0 + W, y0 + H)), np.float32)[..., None] / 255 * 0.55)
    return base


def cola(base, cam, alfa=1.0):
    al = cam[..., 3:4] * alfa
    base[...] = base * (1 - al) + cam[..., :3] * al


PB = [False]


def realca(cam, sat=1.22, con=1.06, pb=None):
    if PB[0] if pb is None else pb:
        l = cam[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32)
        cam[..., :3] = np.clip((l - 0.5) * 1.28 + 0.5, 0, 1)[..., None] * np.array([1.0, 0.99, 0.97], np.float32)
        return cam
    rgb = cam[..., :3]; l = rgb.mean(-1, keepdims=True)
    cam[..., :3] = np.clip(((l + (rgb - l) * sat) - 0.5) * con + 0.51, 0, 1)
    return cam


def cola_img(base, im, cx, cy, esc=1.0, giro=0.0, alfa=1.0, sombra=True, sombra_op=0.35):
    if esc <= 0.01 or alfa <= 0.01: return
    im2 = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))), Image.BICUBIC)
    if giro: im2 = im2.rotate(giro, expand=True, resample=Image.BICUBIC)
    cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x, y = int(cx - im2.width / 2), int(cy - im2.height / 2)
    if sombra:
        s = Image.new("RGBA", im2.size, (40, 30, 30, 0)); s.putalpha(im2.getchannel("A").point(lambda v: v * sombra_op))
        s = s.filter(ImageFilter.GaussianBlur(10)); cam.paste(s, (x + 8, y + 16), s)
    cam.paste(im2, (x, y), im2)
    cola(base, np.asarray(cam, np.float32) / 255, alfa)


def aplica_sombra(base, cam, raio=18, desloc=(10, 22), opac=0.28):
    al = Image.fromarray((cam[..., 3] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(raio))
    sh = np.roll(np.roll(np.asarray(al, np.float32) / 255, desloc[1], 0), desloc[0], 1) * opac
    base *= (1 - sh[..., None] * np.array([1, 1.05, 1.1]))


def elipse(base, cx, cy, rx, ry, cor, alfa=1.0, blur=1.2, multiplica=False):
    im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    m = np.asarray(im.filter(ImageFilter.GaussianBlur(blur)), np.float32)[..., None] / 255 * alfa
    if multiplica: base *= (1 - m)
    else: base[...] = base * (1 - m) + np.array(cor, np.float32)[None, None] / 255 * m


def carrega(n, larg=None, alt=None):
    arq = n if n.endswith(".png") else n + ".png"
    for p in ([n] if os.path.isabs(n) else []) + [os.path.join(PROJ, n), os.path.join(PROJ, "ativos", arq), os.path.join(ATIVOS, arq)]:
        if os.path.isfile(p): break
    else: raise FileNotFoundError(f"ativo não encontrado: {n} (procurei no projeto, em ativos/ do projeto e nos ativos da skill)")
    a = Image.open(p).convert("RGBA")
    if larg: a = a.resize((int(larg), int(a.height * larg / a.width)), Image.LANCZOS)
    elif alt: a = a.resize((int(a.width * alt / a.height), int(alt)), Image.LANCZOS)
    return a


def A(n, **kw): return C(("a", n, tuple(sorted(kw.items()))), lambda: carrega(n, **kw))


def transforma(a, esc, src, scr, giro=0.0):
    inv = (1 / esc, 0, src[0] - scr[0] / esc, 0, 1 / esc, src[1] - scr[1] / esc)
    t = a.transform((W, H), Image.AFFINE, inv, resample=Image.BICUBIC)
    if giro: t = t.rotate(giro, center=scr, resample=Image.BICUBIC)
    return np.asarray(t, np.float32) / 255


def corta_abaixo(a, y, suave_px=3.0, onda=True, incl=0.0, x0=540.0):
    arr = np.asarray(a, np.float32).copy()
    yy = np.arange(arr.shape[0], dtype=np.float32)[:, None]; xs = np.arange(arr.shape[1], dtype=np.float32)[None, :]
    yc = y + incl * (xs - x0) if incl else y + ((10 * np.sin(xs / 40 + 1) + 6 * np.sin(xs / 17)) if onda else 0 * xs)
    arr[..., 3] *= np.clip((yc - yy) / suave_px + 0.5, 0, 1)
    return Image.fromarray(arr.astype(np.uint8))


def cabeca(tk, f, larg_rosto, scr, pescoco=1.1, giro=0.0, incl=0.0):
    fx, fy, fw, fh = tk.rosto(f)
    a = corta_abaixo(tk.rgba(f), fy + fh * pescoco, incl=incl, x0=fx + fw / 2)
    return transforma(a, larg_rosto / fw, (fx + fw / 2, fy + fh / 2), scr, giro)


def caixa(tk, f):
    def fn():
        al = np.asarray(tk.rgba(f))[..., 3] > 128
        ys, xs = np.nonzero(al)
        return (int(np.percentile(xs, 1)), int(ys.min()), int(np.percentile(xs, 99)), int(ys.max()))
    return C(("cx", tk.nome, f), fn)


def duotone(a, esc, cla, borda=14):
    arr = np.asarray(a, np.float32)
    lum = np.clip(((arr[..., :3] @ np.array([0.3, 0.59, 0.11])) / 255 - 0.22) / 0.62, 0, 1) ** 1.25
    e, c = np.array(esc, np.float32), np.array(cla, np.float32)
    out = Image.fromarray(np.dstack([e + (c - e) * lum[..., None], arr[..., 3]]).astype(np.uint8))
    if borda:
        pad = borda + 4
        big = Image.new("RGBA", (out.width + 2 * pad, out.height + 2 * pad), (0, 0, 0, 0))
        ab = Image.new("L", big.size, 0); ab.paste(out.getchannel("A"), (pad, pad))
        ab = ab.point(lambda v: 255 if v > 100 else 0).filter(ImageFilter.MaxFilter(2 * borda + 1)).filter(ImageFilter.GaussianBlur(1))
        branco = Image.new("RGBA", big.size, (255, 255, 255, 255)); branco.putalpha(ab)
        big.alpha_composite(branco); big.alpha_composite(out, (pad, pad)); out = big
    return out


def figurinha(take, ts, cor, larg=280, borda=12):
    def fn():
        tk = TK(take); f = tk.fq(ts)
        fx, fy, fw, fh = tk.rosto(f)
        a = corta_abaixo(tk.rgba(f), fy + fh * 1.1)
        a = a.crop((int(max(fx - fw * 0.5, 0)), int(max(fy - fh * 0.8, 0)), int(fx + fw * 1.5), int(fy + fh * 1.25)))
        a = a.resize((larg, int(a.height * larg / a.width)), Image.LANCZOS)
        return duotone(a, *DUO[cor], borda=borda)
    return C(("fig", take, ts, cor, larg, borda), fn)


def disco(r, cor, seed=1):
    def fn():
        rng = np.random.default_rng(seed)
        S_ = int(2 * r + 60); c = S_ / 2; n = 360
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        ruido = np.convolve(rng.normal(0, 1, n * 3), np.ones(9) / 9, "same")[n:2 * n]
        rr = r * (1 + 0.018 * ruido) + rng.normal(0, 1.2, n)
        m_b = Image.new("L", (S_, S_), 0); ImageDraw.Draw(m_b).polygon([(c + rr[k] * math.cos(ang[k]), c + rr[k] * math.sin(ang[k])) for k in range(n)], fill=255)
        ri = rr - 5 - 2 * np.abs(ruido)
        m_i = Image.new("L", (S_, S_), 0); ImageDraw.Draw(m_i).polygon([(c + ri[k] * math.cos(ang[k]), c + ri[k] * math.sin(ang[k])) for k in range(n)], fill=255)
        grao = rng.normal(0, 7, (S_, S_)).astype(np.float32)
        fib = np.asarray(Image.fromarray(rng.normal(128, 30, (S_ // 4, S_ // 4)).clip(0, 255).astype(np.uint8)).resize((S_, S_), Image.BICUBIC), np.float32) - 128
        mi = (np.asarray(m_i, np.float32) / 255)[..., None]
        rgb = (np.array(cor, np.float32)[None, None] + (grao + fib * 0.12)[..., None]) * mi + (np.array([246, 243, 236], np.float32)[None, None] + grao[..., None] * 0.5) * (1 - mi)
        return Image.fromarray(np.dstack([rgb.clip(0, 255), np.asarray(m_b.filter(ImageFilter.GaussianBlur(0.7)), np.float32)]).astype(np.uint8))
    return C(("disco", r, tuple(cor), seed), fn)


def pontilhado(base, c, R_, t, n=96, cor=(110, 106, 100), alfa=1.0):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(n):
        a = 2 * math.pi * k / n + t * 0.12
        x, y = c[0] + R_ * math.cos(a), c[1] + R_ * math.sin(a)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), outline=cor + (255,), width=2)
    cola(base, np.asarray(im, np.float32) / 255, alfa)


def silhueta(base, cam, desloc=(26, 20), cor=(34, 32, 30), alfa=0.92):
    al = np.roll(np.roll(cam[..., 3], desloc[1], 0), desloc[0], 1) * alfa
    base[...] = base * (1 - al[..., None]) + np.array(cor, np.float32)[None, None] / 255 * al[..., None]


def vivo(t, fase=0.0, forca=1.0):
    return 0.8 * forca * math.sin(t * 1.15 + fase), 5 * forca * math.sin(t * 1.6 + fase * 2)


def x_vermelho(larg=480):
    def fn():
        arr = np.asarray(carrega("x.png", larg=larg), np.float32).copy()
        v = arr[..., 1] > arr[..., 0] * 0.8
        arr[..., 0] = np.where(v, 196, arr[..., 0]); arr[..., 1] = np.where(v, 30, arr[..., 1]); arr[..., 2] = np.where(v, 36, arr[..., 2])
        return Image.fromarray(arr.astype(np.uint8))
    return C(("x", larg), fn)


def carimbo(base, t, t0, cx, cy, larg=480, giro=-8):
    if t0 is None or t < t0: return
    p = sai((t - t0) / 0.13)
    cola_img(base, x_vermelho(larg), cx, cy, esc=2.3 - 1.3 * p, giro=giro, alfa=min(1, p * 1.6), sombra=False)


# ================================================================== tipografia
_fontes = {}
def fonte(tam):
    if tam not in _fontes: _fontes[tam] = ImageFont.truetype(FONTE, tam, index=1 if FONTE.endswith(".ttc") else 0)
    return _fontes[tam]


def etiqueta(txt, tam=118, fundo_=(200, 22, 32), tinta=(255, 255, 255)):
    f = fonte(tam); bb = f.getbbox(txt); w, h = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = int(tam * 0.32), int(tam * 0.26)
    im = Image.new("RGBA", (w + 2 * pw, h + 2 * ph), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=int(tam * 0.12), fill=fundo_ + (255,))
    d.text((pw - bb[0], ph - bb[1]), txt, font=f, fill=tinta + (255,))
    return im


def blocos(c):
    """textos da cena → [(ini_local, fim_local, atras, [(txt, t_local, tam, cor, x, y)])], com layout automático."""
    def fn():
        out = []
        lista = c.get("textos", [])
        desde = c["_de"]
        for bi, b in enumerate(lista):
            x0 = b.get("x", 70); y = b.get("y", 150); max_x = b.get("max_x", W - 40)
            itens = []
            for ln in b["linhas"]:
                if isinstance(ln, str): ln = [ln, "cinza"]
                if isinstance(ln, list): ln = {"texto": ln[0], "cor": ln[1] if len(ln) > 1 else "cinza", **({"tam": ln[2]} if len(ln) > 2 else {})}
                txt, cor = ln["texto"], ln.get("cor", "cinza")
                tam = ln.get("tam", 120 if cor != "cinza" else 60)
                if "em" in ln: ts = acha(ln["em"], desde)
                else:
                    try: ts = acha("@" + norm(txt.split()[0]), desde)
                    except ValueError: ts = desde
                desde = ts
                while True:
                    bb = fonte(tam).getbbox(txt)
                    if ln.get("x", x0) + bb[2] - bb[0] <= max_x or tam <= 30: break
                    tam -= 4
                xx = ln.get("x", x0); yy = ln.get("y", y)
                itens.append((txt, L(c, ts), tam, CORES.get(cor, CORES["cinza"]) if isinstance(cor, str) else tuple(cor), xx, yy))
                y = yy + int(tam * (1.12 if cor == "cinza" else 1.02)) + 6
            ini = itens[0][1]
            if "ate" in b: fim = L(c, acha(b["ate"], acha(b["linhas"][-1]["em"], 0) if isinstance(b["linhas"][-1], dict) and "em" in b["linhas"][-1] else desde))
            elif bi + 1 < len(lista): fim = None
            else: fim = c["_dur"] + 1
            out.append([ini, fim, b.get("atras", False), itens])
        for k in range(len(out)):
            if out[k][1] is None: out[k][1] = out[k + 1][0] - 0.04
        return out
    return C(("blocos", c["_k"]), fn)


def desenha_textos(cam, c, t, atras):
    for ini, fim, a, itens in blocos(c):
        if a != atras or t < ini or t > fim + 0.12: continue
        sp = clamp((t - fim) / 0.12)
        for txt, t0, tam, cor, x, y in itens:
            if t < t0: continue
            p = mola((t - t0) / 0.22, 2.2)
            esc = max(0.05, 0.55 + 0.45 * p) * (1 - 0.4 * sp)
            f = fonte(tam); bb = f.getbbox(txt); w, h = bb[2] - bb[0], bb[3] - bb[1]
            im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), txt, font=f, fill=cor + (255,))
            im = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))), Image.BICUBIC)
            im.putalpha(im.getchannel("A").point(lambda v: int(v * (1 - sp))))
            cam.paste(im, (int(x + w / 2 - im.width / 2), int(y + h / 2 - im.height / 2)), im)


# ================================================================== CENAS
# Cada cena desenha em `base` (float RGB 0..1, 1080×1920). t = tempo local da cena, ts = tempo da fonte.

# ---------- em_pe: corpo inteiro, cenário de colagem, objetos gigantes com X, cópias coloridas
def cena_em_pe(base, c, t, ts):
    tk = TK(g(c, "take", "fala")); f = tk.fq(ts)
    b = caixa(tk, tk.fq(c["_de"] + 0.2))
    esc = g(c, "altura", 1150) / (b[3] - b[1])
    pe = ((b[0] + b[2]) / 2, b[3])
    pos = (g(c, "x", 640), 1770)
    giro, dy = vivo(t, 0.3, 0.8)
    cen = g(c, "cenario", ["estante", "planta"])
    if "estante" in cen:
        est = A("estante_vinho.png", alt=1180)
        cola_img(base, est, W - est.width * 0.32, 1650 - est.height / 2, sombra_op=0.3)
    elipse(base, pos[0], pos[1] + 4, 250, 52, (242, 210, 70))
    if "planta" in cen:
        pl = A("planta.png", alt=960)
        cola_img(base, pl, 175, 1772 - pl.height / 2, giro=0.8 * math.sin(t * 0.9), sombra_op=0.3)
    cam = realca(transforma(tk.rgba(f), esc, pe, (pos[0], pos[1] + dy * 0.3), giro))
    for o in g(c, "objetos", []):
        t1, t2 = T(c, o["em"]), T(c, o.get("ate"), 1e9)
        if t1 <= t < t2:
            im = A(o["ativo"], alt=o.get("alt", 540))
            cola_img(base, im, o.get("x", 310), o.get("y", 900) + 10 * math.sin(t * 2), esc=mola((t - t1) / 0.3, 1.8), giro=6 * math.sin(t * 1.5))
            carimbo(base, t, T(c, o.get("carimbo")), o.get("x", 310) + 10, o.get("y", 900) + 20, int(im.width * 0.9))
    cp = g(c, "copias")
    if cp:
        t3, t4 = T(c, cp["de"]), T(c, cp["ate"])
        if t3 <= t < t4:
            for cor, atraso, x, e2, espelha, t_in in sorted([("verde", 0.30, 330, 1.00, True, 0.00), ("azul", 0.55, 890, 0.86, False, 0.07),
                                                             ("amarelo", 0.75, 160, 0.78, False, 0.14), ("magenta", 0.95, 770, 0.72, True, 0.21)], key=lambda k: k[3]):
                if t < t3 + t_in: continue
                a = tk.rgba(tk.fq(max(ts - atraso, c["_de"])))
                if espelha: a = a.transpose(Image.FLIP_LEFT_RIGHT)
                p = mola((t - t3 - t_in) / 0.18, 2.2)
                pe2 = ((W - pe[0]) if espelha else pe[0], pe[1])
                clone = transforma(duotone(a, *DUO[cor], borda=0), esc * e2 * max(p, 0.05), pe2, (x, 1772 - (1 - e2) * 420), -giro if espelha else giro)
                aplica_sombra(base, clone, raio=16, desloc=(14, 10), opac=0.18); cola(base, clone)
    aplica_sombra(base, cam, raio=16, desloc=(14, 10), opac=0.25)
    cola(base, cam)
    if cp and T(c, cp["de"]) <= t < T(c, cp["ate"]):
        carimbo(base, t, T(c, cp.get("carimbo")), 340, 1250, 460, giro=7)


def sons_em_pe(c, som, Tt):
    for o in g(c, "objetos", []):
        som.pop(Tt(o["em"]), 560, 0.4)
        if o.get("carimbo"): som.baque(Tt(o["carimbo"]), 0.55); som.papel(Tt(o["carimbo"]) + 0.02, 0.3)
    cp = g(c, "copias")
    if cp:
        for k in range(4): som.pop(Tt(cp["de"]) + 0.07 * k, 560 + 90 * k, 0.3)
        if cp.get("carimbo"): som.baque(Tt(cp["carimbo"]), 0.55); som.papel(Tt(cp["carimbo"]) + 0.02, 0.3)


# ---------- cerebro: cabeça gigante, a tampa do crânio sai, cérebro sobe, Mica mini cai dentro
CAB = (540, 1235, 640)
COR_ANEL = np.array([205, 45, 52], np.float32) / 255


def geo_cranio(tk, f_ref):
    def fn():
        cx, cy, larg = CAB
        fx, fy, fw, fh = tk.rosto(f_ref)
        y_corte = cy + (0.06 - 0.5) * fh * larg / fw
        cb = cabeca(tk, f_ref, larg, (cx, cy))
        lin = np.flatnonzero(cb[int(y_corte), :, 3] > 0.5)
        a = (lin.max() - lin.min()) / 2 + 10; b = a * 0.17
        xs = np.arange(W, dtype=np.float32); dx = np.clip((xs - cx) / a, -1, 1)
        yfr = y_corte + b * np.sqrt(1 - dx ** 2)
        yy = np.arange(H, dtype=np.float32)[:, None]
        abaixo = np.clip((yy - yfr[None, :]) / 2 + 0.5, 0, 1)
        abaixo = np.where((np.abs(xs - cx) < a)[None, :], abaixo, np.clip((yy - y_corte) / 2 + 0.5, 0, 1))
        Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
        e = ((X - cx) / a) ** 2 + ((Y - y_corte) / b) ** 2
        def anel(esp, frente):
            e2 = ((X - cx) / (a - esp)) ** 2 + ((Y - y_corte) / (b - esp * 0.55)) ** 2
            return np.clip((1 - e) * 40, 0, 1) * np.clip((e2 - 1) * 12, 0, 1) * ((Y >= y_corte) if frente else (Y < y_corte))
        miolo = np.clip((1 - e) * 40, 0, 1)
        miolo_cor = np.dstack([110 + 40 * np.clip((y_corte - Y) / b, 0, 1), 20 + 0 * Y, 28 + 0 * Y]) / 255
        return dict(y=y_corte, a=a, b=b, abaixo=abaixo, miolo=np.dstack([miolo_cor, miolo]), miolo_m=miolo, yy=yy,
                    anel_f=anel(22, True), anel_t=anel(22, False), luz=anel(8, True) * (Y > y_corte + b * 0.4),
                    cer=carrega("cerebro.png", larg=a * 2 * 0.97))
    return C(("geo", tk.nome, f_ref), fn)


def cena_cerebro(base, c, t, ts):
    tk = TK("fala")
    gig = g(c, "gigante")
    if gig:   # a gigante calada vem de outro trecho (vai e volta em câmera lenta)
        a0, a1 = tk.fq(S(c, gig["de"])), tk.fq(S(c, gig["ate"]))
        n = max(a1 - a0, 1); dur0 = (a1 - a0) / FPS
        if t < dur0: f = a0 + int(t * FPS)
        else:
            k = int((t - dur0) * FPS * 0.5) % (2 * n)
            f = a1 - k if k <= n else a0 + (k - n)
    else: f = tk.fq(ts)
    f_ref = tk.fq(S(c, gig["de"]) + 0.5) if gig else tk.fq(c["_de"] + 0.5)
    G = geo_cranio(tk, f_ref)
    cx, cy, larg = CAB
    cab = realca(cabeca(tk, f, larg, (cx, cy)))
    t_tampa = T(c, g(c, "abre_em"), 0.12)
    if t < t_tampa:
        aplica_sombra(base, cab); cola(base, cab)
    else:
        corpo = cab.copy(); corpo[..., 3] *= G["abaixo"]
        aplica_sombra(base, corpo)
        cola(base, G["miolo"])
        cola(base, np.dstack([np.broadcast_to(COR_ANEL * 0.82, (H, W, 3)), G["anel_t"]]))
        mini_x, mini_y = cx + G["a"] * 0.40, G["y"] - G["cer"].height * 0.60
        mn = g(c, "mini")
        if mn:
            t_mini = T(c, mn.get("cai_em"), t_tampa + 0.6) - 0.3
            if t >= t_mini:
                if mn.get("take", "fala") == "fala":
                    fm = tk.fq(max(ts, S(c, mn.get("de"), ts))); src = tk.rgba(fm)
                else:
                    tm = TK(mn["take"]); src = tm.rgba(int((t - t_mini) * FPS * mn.get("velocidade", 0.82)) + 1)
                arr = np.asarray(src, np.float32).copy()
                arr[..., 3] *= np.clip((1250 - np.arange(arr.shape[0], dtype=np.float32)) / 8, 0, 1)[:, None]
                dy = -900 * (1 - mola((t - t_mini) / 0.42, 1.3))
                cola(base, realca(transforma(Image.fromarray(arr.astype(np.uint8)), 0.47, (540, 1150), (mini_x, mini_y + dy))))
        p = mola((t - t_tampa - 0.08) / 0.45, 1.6)
        cer = G["cer"]
        cy_c = G["y"] - cer.height * 0.30 + (1 - p) * cer.height * 0.7
        cam = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cam.paste(cer, (int(cx - cer.width / 2), int(cy_c - cer.height / 2)), cer)
        cam = np.asarray(cam, np.float32) / 255
        cam[..., 3] *= (1 - G["abaixo"]) * np.where(G["yy"] < G["y"], 1.0, G["miolo_m"])
        cola(base, cam)
        cola(base, corpo)
        cola(base, np.dstack([np.broadcast_to(COR_ANEL, (H, W, 3)), G["anel_f"]]))
        cola(base, np.dstack([np.broadcast_to(np.array([1.0, 0.55, 0.55]), (H, W, 3)), G["luz"] * 0.6]))
        pt = sai((t - t_tampa) / 0.55)
        if pt < 1:
            tampa = cab.copy(); tampa[..., 3] *= (1 - G["abaixo"])
            im = Image.fromarray((tampa * 255).astype(np.uint8)).rotate(-28 * pt, center=(cx + G["a"], G["y"]), resample=Image.BICUBIC, translate=(140 * pt, -820 * pt))
            cola(base, np.asarray(im, np.float32) / 255)
    # objetos em volta do cérebro e na frente da mini
    lugares = {"mini": (cx + G["a"] * 0.40 + 105, G["y"] - G["cer"].height * 0.60 + 60, -24),
               "esquerda": (cx - G["a"] * 0.62, G["y"] - 40, 12), "topo": (cx - G["a"] * 0.30, G["y"] - G["cer"].height * 0.42, -10),
               "direita": (cx + G["a"] * 0.75, G["y"] - 60, 8)}
    for o in g(c, "objetos", []):
        t0 = T(c, o["em"])
        if t < t0: continue
        x, y, gr = lugares.get(o.get("onde", "mini"), lugares["mini"])
        im = A(o["ativo"], alt=o.get("alt", 300))
        cola_img(base, im, o.get("x", x), o.get("y", y), esc=mola((t - t0) / 0.3, 2.0), giro=gr + 4 * math.sin((t - t0) * 3.2))
    canto = g(c, "canto")   # outro take (ex.: Mica com lupa) subindo pelo canto de baixo
    if canto and t >= T(c, canto["em"]):
        tl = T(c, canto["em"]); tc = TK(canto["take"])
        a = tc.rgba(min(int((t - tl) * FPS) + canto.get("quadro", 10), tc.n))
        p = mola((t - tl) / 0.4, 1.3)
        lay = realca(transforma(a, canto.get("escala", 0.44), (540, 1920), (canto.get("x", 215), 1920 + 600 * (1 - p))))
        aplica_sombra(base, lay, raio=12, desloc=(10, 10), opac=0.25); cola(base, lay)
    cc = g(c, "cabeca_canto")   # cabeça em duotone (de outro take) entrando pelo canto
    if cc and t >= T(c, cc["em"]):
        tt = T(c, cc["em"]); tc = TK(cc["take"])
        fr = min(int((t - tt) * FPS) + 1, tc.n)
        fx, fy, fw, fh = tc.rosto(fr)
        a = corta_abaixo(tc.rgba(fr), fy + fh * 1.12, onda=False)
        a = a.crop((int(max(fx - fw * 0.45, 0)), int(max(fy - fh * 0.75, 0)), int(fx + fw * 1.45), int(fy + fh * 1.25)))
        im = duotone(a, *DUO[cc.get("cor", "magenta")], borda=0)
        im = im.resize((int(im.width * 560 / im.height), 560), Image.LANCZOS)
        cola_img(base, im, W - 190 + (1 - sai((t - tt) / 0.35)) * 420, H - 250, giro=8)
    for k, fg in enumerate(g(c, "figurinhas", [])):
        t0 = T(c, fg["em"])
        if t < t0 or t > T(c, fg.get("ate"), 1e9): continue
        st = figurinha(fg.get("take", "fala"), fg["quadro"], fg.get("cor", "verde"), larg=fg.get("larg", 250))
        cola_img(base, st, fg.get("x", 190), fg.get("y", 1060), esc=mola((t - t0) / 0.3, 2.0), giro=fg.get("giro", -8) + 3 * math.sin(t * 3 + k))


def sons_cerebro(c, som, Tt):
    ta = Tt(g(c, "abre_em")) if g(c, "abre_em") else c["_off"] + 0.12
    som.whoosh(ta + 0.25, 0.45, 0.4); som.pop(ta + 0.2, 380, 0.4)
    mn = g(c, "mini")
    if mn:
        tm = (Tt(mn["cai_em"]) if mn.get("cai_em") else ta + 0.6) - 0.3
        som.whoosh(tm + 0.3, 0.35, 0.3); som.baque(tm + 0.42, 0.4)
    for o in g(c, "objetos", []): som.pop(Tt(o["em"]), 620, 0.35)
    for fg in g(c, "figurinhas", []): som.pop(Tt(fg["em"]), 640, 0.33)
    if g(c, "canto"): som.whoosh(Tt(c["canto"]["em"]) + 0.25, 0.4, 0.3)
    if g(c, "cabeca_canto"): som.pop(Tt(c["cabeca_canto"]["em"]), 480, 0.4); som.whoosh(Tt(c["cabeca_canto"]["em"]) + 0.2, 0.35, 0.25)


# ---------- tv: sentada de perfil vendo uma TV antiga em glitch, feixe vermelho chegando nela
def tv_cinza(alt=560):
    def fn():
        a = carrega("tv.png"); arr = np.asarray(a, np.float32).copy()
        l = np.clip((arr[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32) - 128) * 1.2 + 128, 0, 255)
        arr[..., :3] = l[..., None] * np.array([1.0, 0.99, 0.97])
        mk = Image.new("L", a.size, 0); ImageDraw.Draw(mk).rounded_rectangle((80, 70, 316, 303), radius=48, fill=255)
        e = alt / a.height
        gi = Image.fromarray(arr.astype(np.uint8)).resize((int(a.width * e), alt), Image.LANCZOS)
        return gi, mk.resize(gi.size, Image.LANCZOS)
    return C(("tvc", alt), fn)


def tela_glitch(t, w, h):
    rng = np.random.default_rng(int(t * 12))
    cores = np.array([[235, 60, 50], [250, 140, 40], [220, 40, 140], [60, 90, 230], [245, 245, 240], [130, 40, 200], [250, 210, 60]], np.float32)
    larg = rng.uniform(0.5, 1.5, 14); larg = larg / larg.sum() * w
    img = np.zeros((h, w, 3), np.float32); x = 0.0
    for k in range(14):
        img[:, int(x):int(x + larg[k]) + 1] = cores[rng.integers(len(cores))]; x += larg[k]
    img = np.roll(img, int(rng.integers(-18, 18)), axis=1)
    fx = int(rng.integers(0, h)); img[fx:fx + 30] = np.roll(img[fx:fx + 30], int(rng.integers(-40, 40)), axis=1)
    img *= (0.85 + 0.15 * (np.arange(h) % 4 < 2))[:, None, None]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img *= np.clip(1 - 0.45 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2), 0.35, 1)[..., None]
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def cena_tv(base, c, t, ts):
    tk = TK(g(c, "take", "fala")); f = tk.fq(ts)
    b = caixa(tk, tk.fq(c["_de"] + 1.0))
    alt = b[3] - b[1]; esc = g(c, "altura", 640) / alt
    pe = ((b[0] + b[2]) / 2, b[3]); chao = 1400; pos = (300, chao)
    larg_tela = (b[2] - b[0]) * esc
    tv, mk = tv_cinza(560)
    tvx, tvy = 790, chao - 280
    elipse(base, tvx + 10, chao + 10, 230, 64, (240, 222, 40))
    giro, dy = vivo(t, 0.5, 0.5)
    cam = realca(transforma(tk.rgba(f), esc, pe, pos, giro * 0.3))
    esq = pos[0] - larg_tela / 2
    elipse(base, esq + larg_tela * 0.3, chao, larg_tela * 0.42, 15, None, alfa=0.30, blur=9, multiplica=True)
    elipse(base, esq + larg_tela * 0.8, chao - alt * esc * 0.075, larg_tela * 0.24, 12, None, alfa=0.32, blur=9, multiplica=True)
    cola(base, cam)
    if g(c, "pipoca", True): cola_img(base, A("pipoca.png", alt=130), max(70, esq - 50), chao - 66)
    sx0 = tvx - tv.width / 2 + tv.width * 0.17
    sy0, sy1 = tvy - tv.height / 2 + tv.height * 0.15, tvy - tv.height / 2 + tv.height * 0.50
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon([(sx0, sy0), (sx0, sy1), (-20, chao - 90), (-20, chao - 640)], fill=255)
    luz = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255 * (0.80 + 0.04 * math.sin(t * 11))
    base[...] = base * (1 - luz[..., None]) + base * np.array([0.95, 0.42, 0.42], np.float32)[None, None] * luz[..., None]
    tvi = tv.copy(); tvi.paste(tela_glitch(t, tv.width, tv.height), (0, 0), mk)
    cola_img(base, tvi, tvx, tvy, sombra_op=0.3)
    o = g(c, "objeto_sai")
    if o and t >= T(c, o["em"]):
        q = sai((t - T(c, o["em"])) / 0.45)
        cola_img(base, A(o.get("ativo", "rolo"), alt=200), sx0 + 40 - 260 * q, (sy0 + sy1) / 2 + 20 * q, esc=0.25 + 0.75 * q, giro=-20 * q)


def sons_tv(c, som, Tt):
    o = g(c, "objeto_sai")
    if o: som.pop(Tt(o["em"]), 560, 0.35); som.whoosh(Tt(o["em"]) + 0.3, 0.35, 0.2)


# ---------- mala: tudo o que ela cita cai dentro da mala até encher; passagem de carro opcional
MALA_LARG, MALA_POS, MALA_BORDA = 860, (540, 1560), [(0, 352), (515, 400), (719, 340)]


def mala_camadas():
    def fn():
        m = carrega("mala.png", larg=MALA_LARG); s_ = MALA_LARG / 719
        mk = Image.new("L", m.size, 0)
        ImageDraw.Draw(mk).polygon([(x * s_, y * s_ - 6) for x, y in MALA_BORDA] + [(m.width, m.height), (0, m.height)], fill=255)
        frente = m.copy()
        frente.putalpha(Image.fromarray((np.asarray(m.getchannel("A"), np.float32) * np.asarray(mk.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255).astype(np.uint8)))
        return m, frente
    return C("malas", fn)


def borda_y(x):
    s_ = MALA_LARG / 719; x0 = MALA_POS[0] - MALA_LARG / 2; y0 = MALA_POS[1] - 624 * s_ / 2
    return float(np.interp(x, [x0 + a * s_ for a, b in MALA_BORDA], [y0 + b * s_ for a, b in MALA_BORDA]))


TAM_OBJ = {"aviao": 300, "livro": 210, "carro": 160, "xicara1": 170}


def itens_mala(c):
    def fn():
        rng = np.random.default_rng(11)
        lst = []
        lados = [(860, 680), (215, 720), (880, 860), (205, 900)]
        for k, it in enumerate(g(c, "itens", [])):
            t0 = S(c, it["em"])
            lst.append((it["ativo"], t0, it.get("de_onde", lados[k % 4]), 0.55))
            for q in range(it.get("copias", 2)): lst.append((it["ativo"], t0 + 0.18 + 0.16 * q, (rng.uniform(250, 830), -150), 0.0))
        en = g(c, "enche")
        if en:
            nomes = [it["ativo"] for it in g(c, "itens", [])] or ["livro"]
            for k in range(en.get("n", 12)): lst.append((nomes[k % len(nomes)], S(c, en["em"]) + k * 0.09, (rng.uniform(220, 860), -150), 0.0))
        out = []
        for k, (nome, t0, ini, espera) in enumerate(lst):
            x = rng.uniform(240, 840)
            y = borda_y(x) + 30 - 150 * (k / max(len(lst), 1)) ** 0.8 + rng.uniform(-12, 12)
            out.append(dict(nome=nome, larg=TAM_OBJ.get(nome.replace(".png", ""), 200), t0=t0, ini=ini, fim=(x, y), espera=espera,
                            giro=rng.uniform(-35, 35), gira=rng.uniform(-200, 200)))
        return out
    return C(("itens", c["_k"]), fn)


def cena_carro(base, c, t, ts, cr):
    s_ = 1.15
    carro = C("carro_lado", lambda: carrega("carro_lado_full.png", larg=int(1024 * s_)))
    a, b = S(c, cr["de"]), S(c, cr["ate"])
    q = clamp((ts - a) / max(b - a, 0.1))
    cx, cy = 420 + 220 * q, 1000 + 2 * math.sin(t * 33)
    estrada = 1000 + (401 - 286) * s_
    im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).rectangle((110, estrada, 970, estrada + 26), fill=255)
    m = np.asarray(im, np.float32)[..., None] / 255
    base[...] = base * (1 - m) + np.array([0.94, 0.88, 0.16])[None, None] * m
    jx, jy = cx + (500 - 512) * s_, cy + (222 - 286) * s_
    tk = TK(cr.get("take", "fala"))
    f = tk.fq(cr.get("rosto", ts) + (ts - a)) if "rosto" in cr else tk.fq(ts)
    cola(base, realca(cabeca(tk, f, 50, (jx + 30, jy + 12), pescoco=2.4), pb=True))
    cola_img(base, carro, cx, cy, sombra_op=0.2)


def cena_mala(base, c, t, ts):
    cr = g(c, "carro")
    if cr and S(c, cr["de"]) <= ts < S(c, cr["ate"]):
        cena_carro(base, c, t, ts, cr); return
    tk = TK("fala"); f = tk.fq(ts)
    fx, fy, fw, fh = tk.rosto(f)
    giro, dy = vivo(t, 1.1, 0.7)
    cam = realca(transforma(tk.rgba(f), 460 / fw, (fx + fw / 2, fy + fh / 2), (540, 880 + dy), giro))
    aplica_sombra(base, cam); cola(base, cam)
    tb = T(c, g(c, "pula_em"), 1e9)
    pul = 1 + (0.05 * math.sin((t - tb) * 22) * math.exp(-(t - tb) * 5) if t >= tb else 0)
    tm = T(c, g(c, "mala_em"), 0.3)
    if t < tm: return
    pm = mola((t - tm) / 0.35, 1.6)
    yoff = 500 * (1 - pm) + MALA_POS[1] * (pul - 1)
    mala, frente = mala_camadas()
    cola_img(base, mala, MALA_POS[0], MALA_POS[1] + yoff, esc=pul)
    voando = []
    for it in itens_mala(c):
        t0 = L(c, it["t0"])
        if t < t0: continue
        im = A(it["nome"], larg=it["larg"])
        if it["espera"] > 0 and t < t0 + it["espera"]:
            voando.append((im, it["ini"][0], it["ini"][1], mola((t - t0) / 0.28, 2.0), 10 * math.sin(t * 3))); continue
        q = clamp((t - t0 - it["espera"]) / 0.42)
        x = it["ini"][0] + (it["fim"][0] - it["ini"][0]) * q; y = it["ini"][1] + (it["fim"][1] - it["ini"][1]) * q * q
        gg = it["giro"] * q + it["gira"] * (1 - q) * 0.2
        if q < 1: voando.append((im, x, y + yoff, 1.0 - 0.38 * q, gg))
        else: cola_img(base, im, x, y + yoff, esc=0.62 * pul, giro=gg, sombra_op=0.25)
    cola_img(base, frente, MALA_POS[0], MALA_POS[1] + yoff, esc=pul, sombra=False)
    for im, x, y, e, gg in voando: cola_img(base, im, x, y, esc=e, giro=gg)


def sons_mala(c, som, Tt):
    if g(c, "mala_em"): som.whoosh(Tt(c["mala_em"]) + 0.3, 0.4, 0.3)
    for it in g(c, "itens", []): som.pop(Tt(it["em"]), 600, 0.38)
    for it in itens_mala(c):
        tq = c["_off"] + L(c, it["t0"]) + it["espera"] + 0.42
        som.papel(tq, 0.28); som.baque(tq, 0.12)
    if g(c, "pula_em"): som.baque(Tt(c["pula_em"]), 0.45)
    cr = g(c, "carro")
    if cr: som.whoosh(Tt(cr["de"]) + 0.2, 0.6, 0.3); som.tique(Tt(cr["de"]) + 0.45, 520, 0.2); som.tique(Tt(cr["de"]) + 0.55, 520, 0.2)


# ---------- celular: cabeça de perfil em disco de papel, as coisas entram no celular até ele explodir
def celular_colagem():
    def fn():
        from nucleo import rasgado, fita
        cel = carrega("celular.png", alt=860)
        arr = np.asarray(cel, np.float32)
        ys, xs = np.nonzero((arr[..., :3].min(-1) > 232) & (arr[..., 3] > 200))
        rect = (int(xs.min()) + 4, int(ys.min()) + 4, int(xs.max()) - 4, int(ys.max()) - 4)
        pad = 26
        big = Image.new("RGBA", (cel.width + 2 * pad, cel.height + 2 * pad), (0, 0, 0, 0)); big.paste(cel, (pad, pad), cel)
        try: r = rasgado(big, borda=16, seed=4)
        except Exception: r = big
        dx, dy = (r.width - big.width) // 2, (r.height - big.height) // 2
        f1 = fita(170, 48, "#F2B134", 1).rotate(28, expand=True); r.paste(f1, (r.width - f1.width + 10, -6), f1)
        return r, (rect[0] + pad + dx, rect[1] + pad + dy, rect[2] + pad + dx, rect[3] + pad + dy)
    return C("celcol", fn)


def feed(c, sw):
    def fn():
        from nucleo import coracao_img
        itens = g(c, "itens", ["livro", "aviao", "carro", "xicara1"])
        fr = g(c, "feed_quadros") or [CENAS[0]["_de"] + 1 + k * (DUR / 5) for k in range(4)]
        fotos = []
        for k in range(max(len(itens), len(fr))):
            if k < len(fr): fotos.append(("fig", fr[k]))
            if k < len(itens): fotos.append((itens[k], None))
        posts, alt_total = [], 0
        cores = list(DUO)
        for k, (nome, q_) in enumerate(fotos):
            card = Image.new("RGBA", (sw, int(sw * 1.28)), (255, 255, 255, 255)); d = ImageDraw.Draw(card)
            d.ellipse((14, 14, 54, 54), fill=(225, 90, 110, 255)); d.rounded_rectangle((66, 24, 66 + sw * 0.4, 40), 8, fill=(205, 200, 195, 255))
            q = sw - 20
            foto = Image.new("RGBA", (q, q), list(PAPEIS.values())[k % 4] + (255,))
            st = figurinha("fala", q_, cores[k % 4], larg=int(q * 0.8), borda=0) if nome == "fig" else carrega(nome, larg=int(q * 0.7))
            foto.paste(st, ((q - st.width) // 2, (q - st.height) // 2 + 10), st); card.paste(foto, (10, 66))
            hz = coracao_img(34, (225, 40, 60)); card.paste(hz, (14, 76 + q), hz)
            d.rounded_rectangle((60, 84 + q, 60 + sw * 0.3, 98 + q), 7, fill=(205, 200, 195, 255))
            posts.append(card); alt_total += card.height + 12
        strip = Image.new("RGBA", (sw, alt_total * 2), (246, 243, 236, 255)); y = 0
        for _ in range(2):
            for p in posts: strip.paste(p, (0, y)); y += p.height + 12
        return strip, alt_total
    return C(("feed", c["_k"], sw), fn)


def itens_cel(c):
    def fn():
        rng = np.random.default_rng(21)
        nomes = g(c, "itens", ["livro", "carro", "aviao", "xicara1"])
        t0 = S(c, g(c, "enche_em"), c["_de"] + 1.5); t1 = S(c, g(c, "explode_em"), t0 + 3)
        n = max(int((t1 - t0 - 0.4) / 0.11), 6)
        return [dict(nome=nomes[k % len(nomes)], t0=t0 + k * 0.11, larg=rng.uniform(90, 150), dx=rng.uniform(0.15, 0.85),
                     dy=rng.uniform(0, 1), giro=rng.uniform(-40, 40)) for k in range(n)]
    return C(("itcel", c["_k"]), fn)


def estilhacos(c):
    def fn():
        rng = np.random.default_rng(33)
        nomes = g(c, "itens", ["livro", "carro", "aviao", "xicara1"]) + ["brilho"]
        return [dict(tipo=["obj", "obj", "cor", "like", "papel"][k % 5], nome=nomes[k % len(nomes)], ang=rng.uniform(0, 2 * math.pi),
                     v=rng.uniform(900, 1900), giro=rng.uniform(-400, 400), tam=rng.uniform(90, 170),
                     cor=list(PAPEIS.values())[k % 4], n=int(rng.uniform(300, 9900))) for k in range(26)]
    return C(("estil", c["_k"]), fn)


def cabeca_disco(base, c, t, ts, padrao_olha="direita"):
    tk = TK(g(c, "take", "fala")); f = tk.fq(ts)
    olha = g(c, "olha", padrao_olha); s = 1 if olha == "direita" else -1
    giro, dy = vivo(t, 2.0 if s > 0 else 0.7)
    dc = g(c, "disco_centro", (490, 800) if s > 0 else (640, 900))
    centro = (dc[0] - 40 * s, dc[1] + 20 + dy) if s > 0 else (dc[0] + 20, dc[1] + dy)
    r = g(c, "disco_raio", 370 if s > 0 else 395)
    cola_img(base, disco(r, PAPEIS.get(g(c, "disco_cor", "amarelo" if s > 0 else "vermelho"), (242, 196, 64)), 3 + c["_k"]), dc[0], dc[1], sombra_op=0.25)
    return tk, f, s, giro, dc, centro, r


def cena_celular(base, c, t, ts):
    tk, f, s, giro, dc, centro, r = cabeca_disco(base, c, t, ts, "direita")
    pontilhado(base, dc, r + 70, t)
    cab = realca(cabeca(tk, f, 400, centro, pescoco=1.15, giro=giro, incl=0.5 * s))
    silhueta(base, cab, (30 * s, 22)); aplica_sombra(base, cab, raio=14, desloc=(8 * s, 14), opac=0.25); cola(base, cab)
    cel0, (x0, y0, x1, y1) = celular_colagem()
    sw, sh = x1 - x0, y1 - y0
    tp = T(c, g(c, "celular_em"), 0.6); tx = T(c, g(c, "explode_em"), c["_dur"] - 0.6)
    CX_, CY_ = (790, 1330) if s > 0 else (290, 1330)
    itens = itens_cel(c)
    dentro = [it for it in itens if t >= L(c, it["t0"]) + 0.5]
    cheio = len(dentro) / len(itens)
    from nucleo import curtidas, coracao_img
    if tp <= t < tx:
        cel = cel0.copy()
        strip, per = feed(c, sw)
        rol = int(((t - tp) * 260 + (t - tp) ** 2 * 260) % per)
        tela = strip.crop((0, rol, sw, rol + sh)).copy()
        for k, it in enumerate(dentro):
            im = A(it["nome"], larg=it["larg"]).rotate(it["giro"], expand=True, resample=Image.BICUBIC)
            yy = sh - 40 - (k / len(itens)) * sh * 0.95 - it["dy"] * 80
            tela.paste(im, (int(it["dx"] * sw - im.width / 2), int(yy - im.height / 2)), im)
        cel.paste(tela, (x0, y0))
        tremor = (3 + 22 * cheio ** 2) * math.sin(t * 47)
        cola_img(base, cel, CX_ + tremor, CY_ + 600 * (1 - mola((t - tp) / 0.35, 1.6)) + 8 * math.sin(t * 1.4),
                 esc=1 + 0.07 * cheio ** 2 + 0.02 * cheio * math.sin(t * 30), giro=6 * s + tremor * 0.15)
        ta = L(c, itens[0]["t0"])
        for k in range(int(cheio * 8)):
            tk_ = ta + 0.3 + k * 0.32
            if t < tk_: continue
            q = clamp((t - tk_) / 0.9); lado = -1 if k % 2 else 1
            im = C(("lk", k), lambda k=k: curtidas(120 + k * 377, tam=150)) if k % 2 else C(("hz", k), lambda: coracao_img(70, (225, 40, 60)))
            cola_img(base, im, CX_ + lado * (230 + 140 * q), CY_ - 200 + k * 50 - 260 * q, esc=mola(q / 0.3), alfa=1 - clamp((q - 0.7) / 0.3), giro=lado * 10)
    hx, hy = centro[0], centro[1] - 260
    for it in itens:
        t0 = L(c, it["t0"])
        if not (t0 <= t < t0 + 0.5) or t >= tx: continue
        q = suave((t - t0) / 0.5)
        cola_img(base, A(it["nome"], larg=it["larg"] * 1.5), hx + (CX_ - hx) * q, hy + (CY_ - hy) * q - 300 * math.sin(math.pi * q), esc=1 - 0.5 * q, giro=it["giro"] + 300 * q)
    if t >= tx:
        u = t - tx
        if u < 0.12: cola_img(base, cel0, CX_, CY_, esc=1.1 + u * 2, alfa=1 - u / 0.12)
        for k, p in enumerate(estilhacos(c)):
            x = CX_ + math.cos(p["ang"]) * p["v"] * u; y = CY_ + math.sin(p["ang"]) * p["v"] * u + 900 * u * u
            if p["tipo"] == "obj": im = A(p["nome"], larg=p["tam"])
            elif p["tipo"] == "cor": im = C(("hz2", k), lambda: coracao_img(90, (225, 40, 60)))
            elif p["tipo"] == "like": im = C(("lk2", k), lambda p=p: curtidas(p["n"], tam=170))
            else: im = disco(int(p["tam"] * 0.35), p["cor"], k)
            cola_img(base, im, x, y, esc=min(1, u / 0.08), giro=p["giro"] * u)
        if u >= 0.12 and g(c, "resultado", "zine"):
            cola_img(base, A(g(c, "resultado", "zine"), larg=460), CX_, CY_ - 40, esc=mola((u - 0.12) / 0.3, 2.0), giro=8 + 2 * math.sin(t * 2))


def sons_celular(c, som, Tt):
    som.whoosh((Tt(c["celular_em"]) if g(c, "celular_em") else c["_off"] + 0.6) + 0.25, 0.4, 0.3)
    for k, it in enumerate(itens_cel(c)): som.pop(c["_off"] + L(c, it["t0"]) + 0.45, 500 + (k % 5) * 60, 0.22)
    tx = Tt(c["explode_em"]) if g(c, "explode_em") else c["_off"] + c["_dur"] - 0.6
    som.sobe(tx, 1.4, 0.3); som.vidro(tx, 0.5); som.baque(tx, 0.6); som.papel(tx + 0.07, 0.4); som.ding(tx + 0.17, 1318, 0.25)


# ---------- perfil: só a cabeça (perfil ou 3/4) num disco de papel, tesoura, figurinhas, surrealismo
def cena_perfil(base, c, t, ts):
    tn = T(c, g(c, "nuvem_em"))
    if tn is not None and t >= tn:
        p = sai((t - tn) / 0.8)
        cola_img(base, A("nuvem.png", larg=420), 260 + 60 * math.sin(t * 0.7) - 500 * (1 - p), 640, alfa=p, sombra=False)
    tk, f, s, giro, dc, centro, r = cabeca_disco(base, c, t, ts, "esquerda")
    tes = g(c, "tesoura")
    t1, t2 = (T(c, tes["de"]), T(c, tes["ate"])) if tes else (1e9, 1e9)
    if not (t1 <= t < t2 + 0.3): pontilhado(base, dc, r + 70, t)
    cab = realca(cabeca(tk, f, 430, (centro[0], centro[1]), pescoco=1.18, giro=giro, incl=0.45 * s))
    silhueta(base, cab, (30 * s, 22)); aplica_sombra(base, cab, raio=14, desloc=(8 * s, 14), opac=0.25); cola(base, cab)
    if t1 <= t < t2 + 0.3:
        prog = sai((t - t1) / max(min(t2 - t1, 2.2), 0.5)); alfa = 1 - clamp((t - t2) / 0.3)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        R_ = r + 35; a0 = math.radians(200)
        for k in range(int(72 * prog)):
            if k % 2: continue
            aa = a0 + 2 * math.pi * k / 72; ab = a0 + 2 * math.pi * (k + 0.6) / 72
            d.line([(dc[0] + R_ * math.cos(aa), dc[1] + R_ * math.sin(aa)), (dc[0] + R_ * math.cos(ab), dc[1] + R_ * math.sin(ab))], fill=(40, 38, 36, 255), width=7)
        cola(base, np.asarray(im, np.float32) / 255, alfa)
        ang = a0 + 2 * math.pi * prog
        cola_img(base, A("tesoura.png", alt=230), dc[0] + R_ * math.cos(ang), dc[1] + R_ * math.sin(ang), giro=-math.degrees(ang) - 90 + 8 * math.sin(t * 30), alfa=alfa)
    for o in g(c, "objetos", []):
        t0, tf = T(c, o["em"]), T(c, o.get("ate"), 1e9)
        if t0 <= t < tf + 0.3:
            ex = entra((t - tf) / 0.3) if t >= tf else 0
            cola_img(base, A(o["ativo"], larg=o.get("larg", 230)), o.get("x", 170) - 500 * ex, o.get("y", 1300) + 10 * math.sin(t * 2), esc=mola((t - t0) / 0.3, 2.0), giro=o.get("giro", -10))
    for k, fg in enumerate(g(c, "figurinhas", [])):
        t0, tf = T(c, fg["em"]), T(c, fg.get("ate"), 1e9)
        if t < t0 or t > tf + 0.35: continue
        st = figurinha(fg.get("take", "fala"), fg["quadro"], fg.get("cor", "verde"), larg=fg.get("larg", 280))
        ex = entra((t - tf) / 0.35) if t >= tf else 0
        cola_img(base, st, fg.get("x", 195) - 600 * ex, fg.get("y", 780 + 390 * k), esc=mola((t - t0) / 0.3, 2.0), giro=fg.get("giro", -8 + 8 * (k % 2)) + 3 * math.sin(t * 3 + k))
    tp = T(c, g(c, "peixe_em"))
    if tp is not None and t >= tp and (t - tp) < 2.6:
        q = (t - tp) / 2.6
        cola_img(base, A("peixe.png", larg=260), 1250 - 1500 * q, 1050 - 120 * math.sin(math.pi * q) + 25 * math.sin(t * 8), giro=6 * math.sin(t * 10))
    th = T(c, g(c, "coracao_em"))
    if th is not None and t >= th:
        from nucleo import coracao_img
        p = mola((t - th) / 0.3, 2.2) * (1 + 0.06 * math.sin((t - th) * 12))
        cola_img(base, C("cor", lambda: coracao_img(150, (200, 22, 32))), 380, 860, esc=p, giro=-12)


def sons_perfil(c, som, Tt):
    tes = g(c, "tesoura")
    if tes: som.digita(Tt(tes["de"]), Tt(tes["de"]) + min(2.2, Tt(tes["ate"]) - Tt(tes["de"])), 0.22)
    for o in g(c, "objetos", []): som.pop(Tt(o["em"]), 520, 0.35)
    for fg in g(c, "figurinhas", []): som.pop(Tt(fg["em"]), 640, 0.38)
    if g(c, "nuvem_em"): som.whoosh(Tt(c["nuvem_em"]) + 0.5, 0.6, 0.18)
    if g(c, "peixe_em"): som.sobe(Tt(c["peixe_em"]), 0.7, 0.18)
    if g(c, "coracao_em"): som.pop(Tt(c["coracao_em"]), 760, 0.4); som.ding(Tt(c["coracao_em"]) + 0.04, 1760, 0.15)


# ---------- cta: cabeça num círculo pontilhado, etiqueta com a palavra para comentar, objeto (o guia)
def cena_cta(base, c, t, ts):
    tk = TK("fala"); f = tk.fq(ts)
    ce = (540, 1080)
    pontilhado(base, (ce[0], ce[1] - 20), 430, t, n=90, alfa=clamp(t / 0.3))
    cab = realca(cabeca(tk, f, 470, ce)); aplica_sombra(base, cab); cola(base, cab)
    et = g(c, "etiqueta")
    if et and t >= T(c, et["em"]):
        cola_img(base, C(("etq", et["texto"]), lambda: etiqueta(et["texto"], 120)), 540, 430,
                 esc=mola((t - T(c, et["em"])) / 0.32, 2.2), giro=-3 + 1.5 * math.sin(t * 3))
    o = g(c, "objeto")
    if o and t >= T(c, o["em"]):
        cola_img(base, A(o.get("ativo", "zine"), larg=o.get("larg", 360)), o.get("x", 850), o.get("y", 1560), esc=mola((t - T(c, o["em"])) / 0.32, 2.0), giro=10 + 2 * math.sin(t * 2))


def sons_cta(c, som, Tt):
    if g(c, "etiqueta"): som.pop(Tt(c["etiqueta"]["em"]), 520, 0.45); som.ding(Tt(c["etiqueta"]["em"]) + 0.04, 1318, 0.25)
    if g(c, "objeto"): som.pop(Tt(c["objeto"]["em"]), 600, 0.4)


TIPOS = {"em_pe": (cena_em_pe, sons_em_pe, False), "cerebro": (cena_cerebro, sons_cerebro, True), "tv": (cena_tv, sons_tv, False),
         "mala": (cena_mala, sons_mala, True), "celular": (cena_celular, sons_celular, True), "perfil": (cena_perfil, sons_perfil, True),
         "cta": (cena_cta, sons_cta, True)}

# câmera padrão por tipo: [ref, zoom, foco|null, duração]
CAM_PADRAO = {"em_pe": [[0, 1.3, [640, 880], 0], ["+0", 2.0, [640, 860], 1.5], ["+2.4", 1.0, None, 0.4]],
              "cerebro": [[0, 1.0, None, 0], ["+0", 1.08, [560, 950], 3.0]], "tv": [[0, 1.0, None, 0], ["+0", 1.05, [540, 1000], 5.5]],
              "mala": [[0, 1.3, [540, 880], 0], ["+0", 1.15, [540, 900], 1.6], ["+1.8", 1.0, None, 0.35]],
              "celular": [[0, 1.0, None, 0], ["+0", 1.22, [500, 820], 2.0], ["+2.0", 1.0, None, 0.45]],
              "perfil": [[0, 1.0, None, 0], ["+0", 1.2, [640, 900], 2.2], ["+2.2", 1.0, None, 0.4]],
              "cta": [[0, 1.0, None, 0], ["+0", 1.12, [540, 1060], 0.9], ["+1.4", 1.0, None, 0.3]]}


def camera(c):
    def fn():
        lst = []
        for ref, z, foco, d in g(c, "camera", CAM_PADRAO.get(c["tipo"], [[0, 1.0, None, 0]])):
            if ref == 0: ts = -1e9
            elif isinstance(ref, str) and ref.startswith("+"): ts = c["_de"] + float(ref[1:])
            else: ts = S(c, ref)
            lst.append((ts, z, tuple(foco) if foco else None, d))
        return lst
    return C(("cam", c["_k"]), fn)


def cam_em(lista, ts):
    z, f = 1.0, (W / 2, H * 0.47)
    for k, (t0, zz, ff, d) in enumerate(lista):
        if ts < t0: break
        alvo = ff if ff else (W / 2, H * 0.47)
        if d <= 0: z, f = zz, alvo
        else:
            z0, f0 = cam_em(lista[:k], t0); p = suave((ts - t0) / d)
            z = z0 + (zz - z0) * p; f = (f0[0] + (alvo[0] - f0[0]) * p, f0[1] + (alvo[1] - f0[1]) * p)
    return z, f


def pb_em(c, ts):
    p = g(c, "pb", c["tipo"] in ("em_pe", "tv", "celular", "perfil"))
    if isinstance(p, bool): return p
    if "ate" in p: return ts < S(c, p["ate"])
    if "de" in p: return ts >= S(c, p["de"])
    return False


def texto_atras(c, ts):
    cp = g(c, "copias")
    return bool(cp and S(c, cp["de"]) - 0.1 <= ts < S(c, cp["ate"]))


# ================================================================== quadro
def quadro(i):
    t = i / FPS
    c = cena_em(t); tl = t - c["_off"]; ts = fonte_de(c, tl)
    PB[0] = pb_em(c, ts)
    raios = g(c, "raios", TIPOS[c["tipo"]][2]); cy = 1200 if c["tipo"] == "tv" else 1000
    base = fundo(t, raios, cy)
    TIPOS[c["tipo"]][0](base, c, tl, ts)
    rgb = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))
    z, (fx, fy) = cam_em(camera(c), ts)
    z *= 1.035 + 0.012 * math.sin(t * 0.8)
    fx += 10 * math.sin(t * 0.5); fy += 8 * math.sin(t * 0.63)
    w2, h2 = int(W / z), int(H / z)
    x0 = int(min(max(fx - w2 / 2, 0), W - w2)); y0 = int(min(max(fy - h2 / 2, 0), H - h2))
    gc = 0.5 * math.sin(t * 0.4)
    def cam(img, fill):
        return img.rotate(gc, resample=Image.BICUBIC, center=(fx, fy), fillcolor=fill).crop((x0, y0, x0 + w2, y0 + h2)).resize((W, H), Image.BICUBIC)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    atras = texto_atras(c, ts)
    for flag in (False, True): desenha_textos(txt, c, tl, flag)
    if atras:   # texto atrás de tudo o que está na cena
        bg = fundo(t, raios, cy)
        m = np.clip((np.abs(base - bg).max(-1) - 0.012) / 0.05, 0, 1)
        mi = cam(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), 0)
        im = cam(Image.fromarray((np.clip(bg, 0, 1) * 255).astype(np.uint8)), (236, 233, 227))
        im.paste(txt, (0, 0), txt)
        im = Image.composite(cam(rgb, (236, 233, 227)), im, mi)
    else:
        im = cam(rgb, (236, 233, 227)); im.paste(txt, (0, 0), txt)
    im.save(os.path.join(OUT, f"{i + 1:05d}.png"), compress_level=1)
    txt.save(os.path.join(OUTT, f"{i + 1:05d}.png"), compress_level=1)
    return i


# ================================================================== áudio
SR = 48000


def le_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def salva_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def audio(saida):
    from nucleo import Som
    fala = le_audio(os.path.join(PROJ, "fala.wav"))
    voz = np.zeros(int(DUR * SR) + SR, np.float32); fade = int(0.012 * SR)
    for c in CENAS:
        for a, b in c["_tr"]:
            s = fala[int(a * SR):int(b * SR)].copy()
            if len(s) > 2 * fade: s[:fade] *= np.linspace(0, 1, fade); s[-fade:] *= np.linspace(1, 0, fade)
            o = int((c["_off"] + L(c, a)) * SR); voz[o:o + len(s)] += s
    voz = voz[:int(DUR * SR)]
    som = Som(DUR, seed=7)
    for c in CENAS:
        TIPOS[c["tipo"]][1](c, som, lambda ref, c=c: c["_off"] + T(c, ref))
    som.salva(saida + "-sfx.wav")
    sfx = le_audio(saida + "-sfx.wav")[:len(voz)]; sfx = np.pad(sfx, (0, len(voz) - len(sfx)))
    mix = voz + sfx * R.get("sfx_volume", 0.85)
    if R.get("trilha"):
        tr = le_audio(os.path.join(PROJ, R["trilha"]))[:len(voz)]; tr = np.pad(tr, (0, len(voz) - len(tr)))
        k = int(0.15 * SR); env = np.convolve(np.abs(voz), np.ones(k) / k, "same")
        duck = np.convolve(1 - 0.55 * np.clip(env / 0.03, 0, 1), np.ones(k) / k, "same")
        mix += tr * (R.get("trilha_volume", 0.08) / (np.sqrt(np.mean(tr ** 2)) + 1e-6)) * duck
    salva_wav(os.path.join(PROJ, "render/mix.wav"), mix / max(np.abs(mix).max() / 0.95, 1))
    # volume de Reels: mede e corrige para ~ -14 LUFS
    med = subprocess.run(["ffmpeg", "-nostats", "-i", os.path.join(PROJ, "render/mix.wav"), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", med)[-1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(PROJ, "render/mix.wav"), "-af", f"volume={-14 - I:.2f}dB,alimiter=limit=0.89:level=false",
                    "-ar", str(SR), os.path.join(PROJ, "render/mix_final.wav")], check=True)


def srt(saida):
    def fmt(x):
        ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); mi, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"
    linhas, k = [], 1
    for c in CENAS:
        ws = [(w, s, e) for w, s, e in PALAVRAS if any(a - 0.02 <= s <= b + 0.02 for a, b in c["_tr"])]
        for i in range(0, len(ws), 5):
            gr = ws[i:i + 5]
            linhas.append(f"{k}\n{fmt(c['_off'] + L(c, gr[0][1]))} --> {fmt(c['_off'] + L(c, gr[-1][2]))}\n{' '.join(w for w, _, _ in gr)}\n"); k += 1
    open(saida + ".srt", "w").write("\n".join(linhas))


def monta():
    saida = os.path.join(PROJ, os.path.splitext(R.get("saida", "final.mp4"))[0])
    audio(saida); srt(saida)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(OUT, "%05d.png"), "-i", os.path.join(PROJ, "render/mix_final.wav"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", saida + ".mp4"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(OUTT, "%05d.png"), "-c:v", "prores_ks", "-profile:v", "4444",
                    "-pix_fmt", "yuva444p10le", saida + "-camada-textos.mov"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", saida + ".mp4", "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "26", "-preset", "slow",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", saida + "-celular.mp4"], check=True)
    print("pronto:", saida + ".mp4", "| camada de textos, sfx, srt e cópia leve ao lado")


# ================================================================== comandos
def ver(tempos):
    os.makedirs(os.path.join(PROJ, "ver"), exist_ok=True)
    ids = [int(round(float(x) * FPS)) for x in tempos]
    with Pool(min(8, len(ids))) as p: p.map(quadro, ids)
    for x, i in zip(tempos, ids):
        Image.open(os.path.join(OUT, f"{i + 1:05d}.png")).convert("RGB").save(os.path.join(PROJ, "ver", f"q_{float(x):06.2f}.jpg"), quality=88)
    print("→ ver/q_*.jpg")


def audita_recorte():
    os.makedirs(os.path.join(PROJ, "ver"), exist_ok=True)
    for nome in sorted(os.listdir(os.path.join(PROJ, "recorte"))):
        tk = TK(nome); ids = list(range(1, tk.n + 1, 60))[:40] or [1]
        cols = 10; out = Image.new("RGB", (cols * 162, ((len(ids) + cols - 1) // cols) * 288))
        for k, i in enumerate(ids):
            a = tk.rgba(i); bg = Image.new("RGBA", a.size, (255, 0, 255, 255)); bg.alpha_composite(a)
            out.paste(bg.convert("RGB").resize((162, 288)), ((k % cols) * 162, (k // cols) * 288))
        out.save(os.path.join(PROJ, "ver", f"recorte_{nome}.jpg"))
    print("→ ver/recorte_<take>.jpg (sobre magenta: sobras e buracos aparecem fácil)")


if __name__ == "__main__":
    a = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True); os.makedirs(OUTT, exist_ok=True)
    if "--palavras" in a:
        for w, s, e in PALAVRAS: print(f"{s:7.2f}  {w}")
    elif "--plano" in a:
        for c in CENAS:
            print(f"{c['_off']:6.2f}s  {c['tipo']:8s} fonte {c['_de']:.2f}–{c['_ate']:.2f}  → {c['_dur']:.2f}s  trechos: " +
                  ", ".join(f"{x:.2f}–{y:.2f}" for x, y in c["_tr"]))
        print(f"duração final {DUR:.2f}s, {N} quadros")
    elif "--recorte" in a: audita_recorte()
    elif "--ver" in a: ver([x for x in a[a.index("--ver") + 1:] if not x.startswith("--")])
    elif "--monta" in a: monta()
    else:
        ini, fim = 0, N
        if "--trecho" in a:
            k = a.index("--trecho"); ini, fim = int(float(a[k + 1]) * FPS), min(int(float(a[k + 2]) * FPS) + 1, N)
        print(f"duração {DUR:.2f}s, {N} quadros; renderizando {ini}–{fim}")
        with Pool(R.get("processos", 8)) as p:
            for k, _ in enumerate(p.imap_unordered(quadro, range(ini, fim), chunksize=4)):
                if k % 150 == 0: print(f"  {k}/{fim - ini}", flush=True)
        if "--trecho" not in a: monta()
        else: print("trecho pronto; para juntar: --monta")
