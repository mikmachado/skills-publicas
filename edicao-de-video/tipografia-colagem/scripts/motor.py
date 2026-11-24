#!/usr/bin/env python3
"""Motor da skill tipografia-colagem.

Gera os quadros (PNG 1080x1920) de um Reels de texto animado estilo colagem,
com cada cena presa a uma palavra da fala. Tudo vem do projeto.json.

Uso:
  python3 motor.py projeto.json                  # todos os quadros em <saida>/quadros
  python3 motor.py projeto.json --ver 0.5,3.2,9  # prévia (folha) nesses segundos
"""
import json, math, os, sys, random
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, "..", "fontes")
ANTON = os.path.join(FONTES, "Anton-Regular.ttf")
QUICK = os.path.join(FONTES, "Quicksand.ttf")
W, H, FPS = 1080, 1920, 30

CORES = {
    "roxo": (108, 76, 204), "roxo_escuro": (58, 36, 120), "amarelo": (242, 192, 46),
    "amarelo_escuro": (214, 160, 20), "amarelo_padrao": (230, 176, 30), "vermelho": (214, 50, 30),
    "vermelho_escuro": (150, 30, 20), "preto": (20, 18, 20), "bege": (171, 165, 154),
    "creme": (237, 230, 216), "laranja": (217, 119, 87),
}
def C(x):
    if isinstance(x, (list, tuple)): return tuple(x)
    return CORES[x]
PURPLE, PURPLE_D, YELLOW, RED, BLACK, BEIGE, CREAM = (C(k) for k in ["roxo", "roxo_escuro", "amarelo", "vermelho", "preto", "bege", "creme"])

# ---------------- projeto ----------------
PROJ = None; PDIR = "."; WORDS = []; SCENES = []; DUR = 0.0; OUT = ""
def carregar(caminho):
    global PROJ, PDIR, WORDS, SCENES, DUR, OUT
    PDIR = os.path.dirname(os.path.abspath(caminho))
    PROJ = json.load(open(caminho))
    WORDS = json.load(open(os.path.join(PDIR, PROJ.get("palavras", "palavras.json"))))
    SCENES = []
    for i, c in enumerate(PROJ["cenas"]):
        S = 0.0 if i == 0 else wt(c["inicio"]) - c.get("antes", 0.06)
        SCENES.append((S, c))
    fim = WORDS[-1]["e"] + PROJ.get("final_extra", 1.6)
    DUR = PROJ.get("duracao", round(fim, 2))
    OUT = os.path.join(PDIR, PROJ.get("saida", "saida"))
    os.makedirs(os.path.join(OUT, "quadros"), exist_ok=True)

def _norm(s):
    return s.strip().strip(".,!?;:…\"'").lower()

def wt(ref):
    """'palavra' = 1ª ocorrência; 'palavra#2' = 2ª. Retorna o início (s)."""
    if isinstance(ref, (int, float)): return float(ref)
    nome, _, n = ref.partition("#")
    n = int(n) if n else 1
    k = 0
    for w in WORDS:
        if _norm(w["w"]) == _norm(nome):
            k += 1
            if k == n: return w["s"]
    raise KeyError(f"palavra não encontrada na fala: {ref}")

def foto_path(nome): return os.path.join(PDIR, PROJ.get("fotos", "fotos"), nome + "_cut.png")

# ---------------- base ----------------
_fc = {}
def font(path, size, weight=None):
    k = (path, size, weight)
    if k not in _fc:
        f = ImageFont.truetype(path, size)
        if path == QUICK:
            try: f.set_variation_by_name(weight or "Bold")
            except Exception: pass
        _fc[k] = f
    return _fc[k]
def qfont(size, weight="Bold"): return font(QUICK, size, weight)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def back_out(x, s=2.2):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def bounce_drop(x):
    x = clamp(x)
    if x < 0.6: return (x / 0.6) ** 2
    y = (x - 0.6) / 0.4
    return 1 - 0.12 * math.sin(y * math.pi) * (1 - y)

def letter_img(ch, fpath, size, fill, outline=None, ow=0, shadow=None, sh=(0, 0)):
    f = font(fpath, size)
    bb = f.getbbox(ch)
    pad = ow + max(abs(sh[0]), abs(sh[1])) + 10
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = (pad - bb[0], pad - bb[1])
    if shadow: d.text((o[0] + sh[0], o[1] + sh[1]), ch, font=f, fill=shadow, stroke_width=ow, stroke_fill=shadow)
    d.text(o, ch, font=f, fill=fill, stroke_width=ow, stroke_fill=outline or fill)
    return im

def paste_rot(base, im, cx, cy, ang=0, scale=1.0):
    if scale <= 0.01: return
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if ang: im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def word_layout(word, fpath, size, tracking=0):
    f = font(fpath, size); xs, x = [], 0
    for ch in word:
        xs.append(x); x += f.getlength(ch) + tracking
    return xs, x - tracking

def zebra(w, h, t, c1=None, c2=None, period=46):
    c1 = c1 or PURPLE; c2 = c2 or PURPLE_D
    s = 3
    yy, xx = np.mgrid[0:h // s, 0:w // s].astype(np.float32) * s
    warp = 70 * np.sin(yy / 140 + t * 2.0) + 40 * np.sin(xx / 210 - t * 1.3 + yy / 90)
    m = (np.sin((xx * 0.8 + yy * 0.6 + warp) / period * math.pi) > 0)[..., None]
    a = np.where(m, np.array(c1, np.uint8), np.array(c2, np.uint8)).astype(np.uint8)
    return Image.fromarray(a, "RGB").resize((w, h), Image.NEAREST).convert("RGBA")

ZEBRAS = {"roxa": ("roxo", "roxo_escuro"), "vermelha": ("vermelho", "vermelho_escuro"), "amarela": ("amarelo", "amarelo_escuro")}
def fundo(spec, t):
    """'preto' | 'bege' | 'amarelo' | 'zebra_roxa' | 'zebra_vermelha' | 'zebra_amarela'"""
    if spec.startswith("zebra_"):
        a, b = ZEBRAS[spec[6:]]
        im = Image.new("RGBA", (W, H)); im.paste(zebra(W, H, t, C(a), C(b), 50), (0, 0)); return im
    return Image.new("RGBA", (W, H), C(spec) + (255,))

_rng = np.random.default_rng(3)
GRAIN = [_rng.normal(0, 13, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
def add_grain(img, fi):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    a = a + np.kron(GRAIN[fi % 6], np.ones((2, 2), np.float32))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")

# ---------------- rabiscos ----------------
def jitter(pts, seed, amt=6):
    r = random.Random(seed); ph = [r.uniform(0, 6.28) for _ in range(4)]
    n = max(1, len(pts) - 1); out = []
    for i, (x, y) in enumerate(pts):
        u = i / n * 6.28
        out.append((x + amt * (math.sin(u * 1.3 + ph[0]) + 0.5 * math.sin(u * 3.1 + ph[1])),
                    y + amt * (math.sin(u * 1.7 + ph[2]) + 0.5 * math.sin(u * 2.7 + ph[3]))))
    return out

def draw_stroke(d, pts, prog, color, width):
    if prog <= 0 or len(pts) < 2: return
    p = pts[:max(2, int(len(pts) * clamp(prog)))]
    d.line(p, fill=color, width=width, joint="curve")
    rr = width / 2
    for x, y in (p[0], p[-1]): d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color)

def arrow_path(x0, y0, x1, y1, bend=180, n=60):
    pts = []; dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
    for i in range(n + 1):
        t = i / n
        b = math.sin(t * math.pi) * bend
        loop = 60 * math.sin(t * math.pi * 2) * math.exp(-((t - 0.5) ** 2) / 0.01)
        pts.append((x0 + dx * t + nx * (b + loop), y0 + dy * t + ny * (b + loop)))
    return pts

def seta(d, x0, y0, x1, y1, bend, prog, cor, w, seed):
    path = jitter(arrow_path(x0, y0, x1, y1, bend), seed, 7)
    draw_stroke(d, path, prog, cor, w)
    if prog >= 0.98:
        a = math.atan2(path[-1][1] - path[-6][1], path[-1][0] - path[-6][0])
        for s in (-1, 1):
            draw_stroke(d, [(path[-1][0] + 75 * math.cos(a + s * 2.5), path[-1][1] + 75 * math.sin(a + s * 2.5)), path[-1]], 1, cor, w)

def ellipse_path(cx, cy, rx, ry, turns=1.15, n=80, start=-2.0):
    return [(cx + rx * math.cos(start + 2 * math.pi * turns * i / n) * (1 + 0.04 * i / n),
             cy + ry * math.sin(start + 2 * math.pi * turns * i / n)) for i in range(n + 1)]

def sparks(d, cx, cy, p, col=None, r0=40, r1=120, n=3, a0=0.0, spread=0.45, w=12):
    if p <= 0: return
    col = col or CREAM
    for j in range(n):
        a = a0 + (j - (n - 1) / 2) * spread; rr = r0 + (r1 - r0) * p
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + rr * math.cos(a), cy + rr * math.sin(a))], fill=col, width=w)

def star(d, sx, sy, r, seed, col=None, w=10):
    if r <= 1: return
    pts = []
    for j in range(11):
        a = -math.pi / 2 + j * math.pi / 5; rr = r if j % 2 == 0 else r * 0.45
        pts.append((sx + rr * math.cos(a), sy + rr * math.sin(a)))
    d.line(jitter(pts, seed, 3), fill=col or CREAM, width=w, joint="curve")

def cobra(d, pts, prog, cor, w):
    draw_stroke(d, pts, prog, cor, w)
    if prog > 0:
        n = max(2, int(len(pts) * prog)); hx, hy = pts[n - 1]
        r = w * 0.85
        d.ellipse((hx - r, hy - r * 0.8, hx + r, hy + r * 0.8), fill=cor)
        d.ellipse((hx + r * 0.12, hy - r * 0.45, hx + r * 0.45, hy - r * 0.08), fill=BLACK)

def seed_of(t): return int(t * FPS / 3)

def card(w, h, fill, r=80, border=None, bw=0):
    im = Image.new("RGBA", (w + 2 * bw, h + 2 * bw), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if border: d.rounded_rectangle((0, 0, w + 2 * bw - 1, h + 2 * bw - 1), r + bw, fill=border)
    d.rounded_rectangle((bw, bw, bw + w - 1, bw + h - 1), r, fill=fill)
    return im

def pill(img, text, cx, cy, size, fg, bgc, p=1.0, ang=0):
    if p <= 0 or not text: return
    f = qfont(size); tw = f.getlength(text)
    c = card(int(tw + size * 1.0), int(size * 1.5), bgc, r=int(size * 0.75))
    ImageDraw.Draw(c).text((c.width / 2, c.height / 2 - size * 0.08), text, font=f, fill=fg, anchor="mm")
    paste_rot(img, c, cx, cy, ang, scale=back_out(p))

def pattern_rows(d, text, fnt, color, t, speed=220, step=170, y0=-60, rows=13):
    tw = fnt.getlength(text + " ")
    for r in range(rows):
        off = (t * speed) % tw
        d.text((-off if r % 2 else off - tw, y0 + r * step), (text + " ") * 8, font=fnt, fill=color)

def letters(img, word, size, cy, lt, t0, stagger=0.045, dur=0.26, cols=None, angs=None, mode="drop",
            outline=None, ow=0, shadow=None, sh=(0, 0), tracking=-6, maxw=960, cx=W / 2, t=0.0,
            breathe=0, fpath=ANTON, skip=()):
    xs, tw = word_layout(word, fpath, size, tracking)
    if tw > maxw:
        size = int(size * maxw / tw); xs, tw = word_layout(word, fpath, size, tracking)
    f = font(fpath, size); x0 = cx - tw / 2
    cols = cols or [CREAM]; angs = angs or [0]
    for i, ch in enumerate(word):
        if i in skip or ch == " ": continue
        st = t0 + i * stagger
        if lt < st: continue
        q = (lt - st) / dur
        im = letter_img(ch, fpath, size, cols[i % len(cols)], outline=outline, ow=ow, shadow=shadow, sh=sh)
        lx = x0 + xs[i] + f.getlength(ch) / 2
        a = angs[i % len(angs)]
        br = breathe * math.sin(t * 6 + i * 1.3) * clamp((lt - st - dur) / 0.2)
        if mode == "drop":
            p = bounce_drop(q); paste_rot(img, im, lx, -350 + (cy + 350) * p + br, a * p)
        else:
            p = back_out(q); paste_rot(img, im, lx, cy + br, a * p, scale=0.15 + 0.85 * p)
    return size, x0, xs

def letter_times(word, t0, stagger):
    return [t0 + i * stagger for i, ch in enumerate(word) if ch != " "]

# ---------------- recortes (fotos) com movimento de gif ----------------
_ph = {}
def sticker(name, h, border=16):
    k = (name, h)
    if k not in _ph:
        im = Image.open(foto_path(name)).convert("RGBA")
        im = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
        pad = border * 3
        cv = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0)); cv.alpha_composite(im, (pad, pad))
        a = cv.getchannel("A").point(lambda v: 255 if v > 90 else 0)
        rim = a.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(1))
        sh = Image.new("RGBA", cv.size, (0, 0, 0, 0)); sh.putalpha(rim.point(lambda v: v * 0.45).filter(ImageFilter.GaussianBlur(10)))
        out = Image.new("RGBA", (cv.width + 24, cv.height + 24), (0, 0, 0, 0))
        out.alpha_composite(sh, (20, 22))
        cr = Image.new("RGBA", cv.size, CREAM + (255,)); cr.putalpha(rim)
        out.alpha_composite(cr, (0, 0)); out.alpha_composite(cv, (0, 0))
        _ph[k] = out
    return _ph[k]

GIF_FPS = 8
def gif_motion(t, style, seed=0):
    """balanço 'travado' (stop-motion): pulo | danca | tremor | respira"""
    ts = math.floor(t * GIF_FPS) / GIF_FPS; k = math.floor(t * GIF_FPS)
    r = random.Random(k * 31 + seed)
    jx, jy, ja = r.uniform(-4, 4), r.uniform(-4, 4), r.uniform(-1.2, 1.2)
    if style == "pulo":
        ph = (ts * 2.0) % 1.0
        return jx, -110 * math.sin(ph * math.pi) + jy, 6 * math.sin(ts * 2 * math.pi) + ja, 1 + (0.06 if ph < 0.13 else 0)
    if style == "danca":
        s = 1 if k % 4 < 2 else -1
        return 12 * s + jx, jy, 7 * s + ja, 1.0
    if style == "tremor":
        return jx * 2, jy * 2, (5 if k % 2 else -5) + ja, 1 + 0.03 * (k % 2)
    if style == "respira":
        return jx * 0.5, jy * 0.5, 3 * math.sin(ts * 3) + ja * 0.5, 1 + 0.035 * math.sin(ts * 4)
    return 0, 0, 0, 1.0

def place(img, foto, cx, cy, p, t):
    """foto = {"nome":..., "altura":..., "x":..., "y":..., "giro":..., "movimento":...}"""
    if p <= 0 or not foto: return
    dx = dy = da = 0; ds = 1.0
    if p >= 1 and foto.get("movimento"): dx, dy, da, ds = gif_motion(t, foto["movimento"], len(foto["nome"]))
    paste_rot(img, sticker(foto["nome"], foto.get("altura", 800)), foto.get("x", cx) + dx, foto.get("y", cy) + dy,
              foto.get("giro", 0) * clamp(p) + da, scale=(0.2 + 0.8 * back_out(p, 1.6)) * ds)

def lt_of(c, S, key, default=None):
    v = c.get(key, default)
    return None if v is None else wt(v) - S

# =====================================================================
# MODELOS DE CENA.  Cada um: (lt, t, S, c) -> imagem, e sons(S, c) -> eventos
# =====================================================================
PALETA = [YELLOW, PURPLE, RED, YELLOW, PURPLE, RED, YELLOW, PURPLE, RED, YELLOW]
ANGS = [-7, 4, -3, 8, -5, 6, -4, 3, -8, 5]

def cores_de(c, default):
    return [C(x) for x in c["cores"]] if "cores" in c else default

# 1) queda: palavra(s) gigantes caindo letra por letra
def m_queda(lt, t, S, c):
    img = fundo(c.get("fundo", "preto"), t)
    linhas = c["linhas"]; t0 = lt_of(c, S, "em", c["inicio"]) - 0.1 if S else lt_of(c, S, "em", c["inicio"]) - 0.1
    cols = cores_de(c, [PURPLE, RED, YELLOW] if len(linhas) == 1 else PALETA)
    k = 0
    ys = [H / 2 + 40] if len(linhas) == 1 else [720, 1230]
    size = 560 if len(linhas) == 1 else 470
    for li, word in enumerate(linhas):
        n = len(word)
        letters(img, word, size, ys[li], lt, t0 + k * 0.035, 0.035 if len(linhas) > 1 else 0.05, 0.24,
                cols[k % len(cols):] + cols[:k % len(cols)], ANGS[k % 10:] + ANGS[:k % 10], t=t, breathe=6, maxw=980)
        k += n
    d = ImageDraw.Draw(img); s = seed_of(t); enf = c.get("enfeite", "faiscas")
    tf = t0 + k * 0.04 + 0.15
    if enf == "faiscas":
        p = ease_out((lt - tf) / 0.15)
        for sx, sy, a in [(130, 560, -2.4), (950, 600, -0.7), (900, 1380, 0.8)]: sparks(d, sx, sy, p, a0=a)
    elif enf == "cobra":
        sp = ease_in_out((lt - tf + 0.1) / 0.4)
        cobra(d, jitter([(-80 + 1240 * i / 120, 980 + 150 * math.sin(i / 120 * 1.6 * 2 * math.pi)) for i in range(121)], s, 3), sp, YELLOW, 58)
        st = ease_out((lt - tf - 0.1) / 0.2)
        for sx, sy, kk in [(180, 380, 1.0), (920, 1530, 0.8), (880, 330, 0.6)]: star(d, sx, sy, 70 * kk * st, s + sx)
    return img
def s_queda(S, c):
    t0 = wt(c.get("em", c["inicio"])) - 0.1; ev = []; k = 0
    stg = 0.035 if len(c["linhas"]) > 1 else 0.05
    for w in c["linhas"]:
        ev += [("pop", x + 0.15, 0.3) for x in letter_times(w, t0 + k * 0.035, stg)]; k += len(w)
    return ev

# 2) zebra_card: card de zebra inclinado + palavra em 2 linhas pipocando + tira lateral + seta
def m_zebra_card(lt, t, S, c):
    img = fundo(c.get("fundo", "bege"), t)
    p = ease_out(lt / 0.2); cw, chh = 1500, 1250
    z = zebra(cw, chh, t)
    m = Image.new("L", (cw, chh), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, chh - 1), 70, fill=255); z.putalpha(m)
    bd = Image.new("RGBA", (cw + 40, chh + 40), (0, 0, 0, 0))
    ImageDraw.Draw(bd).rounded_rectangle((0, 0, cw + 39, chh + 39), 85, fill=BLACK); bd.alpha_composite(z, (20, 20))
    paste_rot(img, bd, W / 2 + 30, H / 2 + 80 + 1400 * (1 - p), -8 + 3 * (1 - p))
    if c.get("tira"):
        sp = ease_out((lt - 0.08) / 0.2)
        strip = Image.new("RGBA", (300, 140 + 120 * len(c["tira"])), CREAM + (255,)); sd = ImageDraw.Draw(strip)
        for r, txt in enumerate(c["tira"]): sd.text((30, 40 + r * 120), txt, font=font(ANTON, 96), fill=PURPLE_D)
        paste_rot(img, strip, W - 120 + 400 * (1 - sp), 380, 6)
    cols = [YELLOW, PURPLE, CREAM, RED, YELLOW, CREAM]
    ys = [720, 1080] if len(c["linhas"]) > 1 else [900]
    for li, word in enumerate(c["linhas"]):
        letters(img, word, 330, ys[li], lt, 0.03 + li * 0.15, 0.025, 0.16, cols[li * 3:] + cols[:li * 3], [-6, -2, 2], "pop",
                BLACK, 10, BLACK, (14, 16), -4, t=t)
    if c.get("seta", True):
        seta(ImageDraw.Draw(img), 160, 1680, 600, 1340, -140, ease_in_out((lt - 0.2) / 0.25), YELLOW, 26, seed_of(t))
    return img
def s_zebra_card(S, c):
    ev = []
    for li, w in enumerate(c["linhas"]):
        ev += [("pop_curto", S + x + 0.08, 0.15) for x in letter_times(w, 0.03 + li * 0.15, 0.025)]
    return ev

# 3) card_fino: card preto com fonte fina, linhas aparecendo na fala, fundo com palavra repetida
def m_card_fino(lt, t, S, c):
    img = fundo(c.get("fundo", "amarelo"), t); d = ImageDraw.Draw(img)
    if c.get("padrao"): pattern_rows(d, c["padrao"], font(ANTON, 170), C("amarelo_padrao"), t, step=175)
    p = back_out(lt / 0.18, 1.6)
    n = len(c["linhas"]); ch = 260 + 240 * n
    cc = card(900, ch, BLACK, 90); cd = ImageDraw.Draw(cc)
    cols = [YELLOW, CREAM, YELLOW]
    for i, ln in enumerate(c["linhas"]):
        if ln.get("em") is None or lt > wt(ln["em"]) - S - 0.05:
            fnt = font(ANTON, 200) if ln.get("grossa") else qfont(200 if n > 2 else 230)
            cd.text((450, 150 + 240 * i + (240 * (2 - n) / 2 if n < 2 else 0)), ln["texto"], font=fnt, fill=C(ln["cor"]) if "cor" in ln else cols[i % 3], anchor="mm")
    paste_rot(img, cc, W / 2, H / 2, -6 + 10 * (1 - p), scale=0.5 + 0.5 * p)
    if c.get("circulo", True):
        li = c.get("circulo_linha", n - 1)
        cy = H / 2 - ch / 2 + 150 + 240 * li
        draw_stroke(ImageDraw.Draw(img), jitter(ellipse_path(W / 2, cy, 290, 140), seed_of(t), 5),
                    ease_in_out((lt - (wt(c["linhas"][li]["em"]) - S if c["linhas"][li].get("em") else 0.25)) / 0.25), PURPLE, 18)
    return img
def s_card_fino(S, c):
    return [("pop", wt(ln["em"]), 0.25) for ln in c["linhas"] if ln.get("em")]

# 4) palavra: etiqueta + palavra grande pipocando (1 ou 2 linhas) + foto opcional + extras
def m_palavra(lt, t, S, c):
    img = fundo(c.get("fundo", "preto"), t); s = seed_of(t)
    d = ImageDraw.Draw(img)
    te = lt_of(c, S, "em", c["inicio"])
    foto = c.get("foto")
    if c.get("pincelada"):
        swipe = [(60 + 960 * i / 40, 1000 + 60 * math.sin(i / 40 * 6)) for i in range(41)]
        draw_stroke(d, jitter(swipe, s, 6), ease_in_out(lt / 0.22), YELLOW, 260)
    if foto and foto.get("atras", True): place(img, foto, W / 2, 1500, (lt - 0.05) / 0.22, t)
    lado = c.get("etiqueta_cor", ["preto", "creme"])
    pill(img, c.get("etiqueta"), W / 2, c.get("etiqueta_y", 300), 88, C(lado[1]), C(lado[0]), lt / 0.2, -3)
    linhas = c["linhas"]
    ys = c.get("ys", [620, 1000] if len(linhas) > 1 else [800])
    cols = cores_de(c, [YELLOW, PURPLE, RED])
    contorno = c.get("contorno", True)
    fall = c.get("letra_cai")
    fall_t = te + 0.55
    k = 0
    for li, word in enumerate(linhas):
        skip = (len(word) - 1,) if (fall and li == len(linhas) - 1 and lt > fall_t) else ()
        letters(img, word, c.get("tamanho", 400), ys[li], lt, te - 0.05 + li * 0.17, 0.035, 0.2,
                cols[k % len(cols):] + cols[:k % len(cols)], [-8, 6, -4, 7, -6, 5], "pop",
                BLACK if contorno else None, 10 if contorno else 0, C(c.get("sombra", "preto")) if contorno else None, (16, 18) if contorno else (0, 0),
                t=t, breathe=c.get("balanco", 5), skip=skip)
        k += len(word)
    if fall and lt > fall_t:
        word = linhas[-1]; size = c.get("tamanho", 400)
        xs, tw = word_layout(word, ANTON, size, -6)
        if tw > 960: size = int(size * 960 / tw); xs, tw = word_layout(word, ANTON, size, -6)
        f = font(ANTON, size); q = lt - fall_t
        lx = W / 2 - tw / 2 + xs[-1] + f.getlength(word[-1]) / 2
        paste_rot(img, letter_img(word[-1], ANTON, size, cols[(k - 1) % len(cols)]), lx + 120 * q, ys[-1] + 2600 * q * q, -4 - 220 * q)
    if foto and not foto.get("atras", True): place(img, foto, W / 2, 1500, (lt - 0.05) / 0.25, t)
    d = ImageDraw.Draw(img)
    if c.get("seta"):
        seta(d, 110, 1780, 470, 1560, 120, ease_in_out((lt - (fall_t - 0.25 if fall else te + 0.3)) / 0.25), CREAM, 22, s)
    if c.get("faiscas"):
        p = ease_out((lt - te - 0.3) / 0.2)
        for sx, sy, a in [(120, 450, -2.6), (960, 450, -0.5), (130, 1250, 2.4), (950, 1250, 0.6)]: sparks(d, sx, sy, p, YELLOW, a0=a, w=14)
        star(d, 180, 1650, 90 * p, s, YELLOW, 12)
    if c.get("estrelas"):
        st = ease_out((lt - te - 0.3) / 0.2)
        star(d, 170, 420, 80 * st, s + 1, BLACK, 12); star(d, 900, 1550, 60 * st, s + 2, CREAM, 10)
    return img
def s_palavra(S, c):
    te = wt(c.get("em", c["inicio"])); ev = [("pop", te, 0.3)]
    if c.get("letra_cai"): ev.append(("whoosh_longo", te + 0.5, 0.35))
    return ev

# 5) cadeado: etiqueta + palavra num card vermelho + legenda + cadeado rabiscado
def m_cadeado(lt, t, S, c):
    img = fundo(c.get("fundo", "bege"), t)
    pill(img, c.get("etiqueta"), 300, 330, 90, CREAM, BLACK, lt / 0.2, -4)
    tc = lt_of(c, S, "em")
    p = ease_out((lt - tc + 0.12) / 0.22)
    paste_rot(img, card(940, 620, RED, 60, BLACK, 14), W / 2 + 1200 * (1 - p), 900, 4)
    if p > 0.9:
        letters(img, c["palavra"], 400, 900, lt, tc, 0.04, 0.18, [CREAM], [4, 2, 6, 3, 5], "pop", BLACK, 8, BLACK, (16, 18), t=t, maxw=820)
    tp = lt_of(c, S, "legenda_em")
    if lt > tp:
        q = back_out((lt - tp) / 0.2)
        f = qfont(110); tw = f.getlength(c["legenda"])
        c2 = card(int(tw + 120), 220, BLACK, 110)
        ImageDraw.Draw(c2).text((c2.width / 2, 100), c["legenda"], font=f, fill=YELLOW, anchor="mm")
        paste_rot(img, c2, W / 2 - 60, 1360, -5, scale=0.2 + 0.8 * q)
    lp = ease_in_out((lt - lt_of(c, S, "cadeado_em", c["legenda_em"])) / 0.3)
    if lp > 0:
        s = seed_of(t); d = ImageDraw.Draw(img); cx, cy = 840, 1500
        shk = [(cx - 55 + 110 * i / 30, cy - 60 - 90 * math.sin(math.pi * i / 30)) for i in range(31)]
        draw_stroke(d, jitter(shk, s, 3), lp, YELLOW, 20)
        if lp > 0.5:
            body = [(cx - 90, cy - 60), (cx + 90, cy - 60), (cx + 90, cy + 80), (cx - 90, cy + 80), (cx - 90, cy - 60)]
            d.polygon(jitter(body, s + 1, 3), fill=YELLOW); d.ellipse((cx - 16, cy - 10, cx + 16, cy + 22), fill=BLACK)
    return img
def s_cadeado(S, c):
    return [("pop", wt(c["em"]), 0.3), ("pop", wt(c["legenda_em"]), 0.25), ("risco", wt(c.get("cadeado_em", c["legenda_em"])) + 0.05, 0.25)]

# 6) linhas: título que sobe + linhas de uma palavra repetida enchendo a tela + card final
def m_linhas(lt, t, S, c):
    img = fundo(c.get("fundo", "amarelo"), t); d = ImageDraw.Draw(img)
    t_de = lt_of(c, S, "de"); t_ate = lt_of(c, S, "ate")
    up = ease_in_out((lt - t_de + 0.05) / 0.3)
    letters(img, c["titulo"], int(430 - 230 * up), H / 2 - (H / 2 - 230) * up, lt, 0.0, 0.04, 0.22,
            [BLACK, PURPLE, RED, BLACK, PURPLE], [-3, 4, -2, 3, -4], t=t)
    rep = c["repetir"]
    for r in range(7):
        rt = t_de + r * (t_ate - t_de) / 7
        if lt < rt: continue
        p = ease_out((lt - rt) / 0.25)
        txt = ((rep.lower() if r % 2 == 0 else rep.upper()) + " ") * 5
        fnt = qfont(150) if r % 2 == 0 else font(ANTON, 160)
        drift = (t * 90) % 400
        x = (-1600 * (1 - p) if r % 2 == 0 else 1600 * (1 - p)) - 200 - (drift if r % 2 == 0 else -drift + 400)
        d.text((x, 470 + r * 190), txt, font=fnt, fill=PURPLE if r % 2 == 0 else RED)
    if lt > t_ate - 0.05:
        q = back_out((lt - t_ate + 0.05) / 0.22)
        cc = card(880, 560, BLACK, 80); cd = ImageDraw.Draw(cc)
        cd.text((440, 130), c.get("card_pequeno", ""), font=qfont(80), fill=CREAM, anchor="mm")
        g = c.get("card_grande", rep.upper()); fg = font(ANTON, 230)
        if fg.getlength(g) > 800: fg = font(ANTON, int(230 * 800 / fg.getlength(g)))
        cd.text((440, 340), g, font=fg, fill=YELLOW, anchor="mm")
        paste_rot(img, cc, W / 2, 1150, -4, scale=0.2 + 0.8 * q)
        d = ImageDraw.Draw(img); sp = ease_out((lt - t_ate - 0.15) / 0.15)
        sparks(d, 150, 830, sp, BLACK, a0=-2.4); sparks(d, 930, 1470, sp, BLACK, a0=0.8)
    return img
def s_linhas(S, c):
    return [("pop", S + 0.15, 0.3), ("pop", wt(c["ate"]), 0.35)]

# 7) camera: etiqueta + câmera rabiscada + card com 2 linhas + X vermelho
def m_camera(lt, t, S, c):
    img = fundo(c.get("fundo", "preto"), t); d = ImageDraw.Draw(img); s = seed_of(t)
    pill(img, c.get("etiqueta"), W / 2, 330, 110, BLACK, YELLOW, lt / 0.2, -3)
    cp = ease_in_out((lt - lt_of(c, S, "camera_em", c["inicio"]) + 0.05) / 0.35)
    cx, cy = W / 2, 900
    body = [(cx - 330, cy - 190), (cx - 120, cy - 190), (cx - 80, cy - 260), (cx + 80, cy - 260), (cx + 120, cy - 190),
            (cx + 330, cy - 190), (cx + 330, cy + 220), (cx - 330, cy + 220), (cx - 330, cy - 190)]
    bp = []
    for a, b in zip(body, body[1:]):
        for i in range(10): bp.append((a[0] + (b[0] - a[0]) * i / 10, a[1] + (b[1] - a[1]) * i / 10))
    bp.append(body[-1])
    draw_stroke(d, jitter(bp, s, 5), cp, CREAM, 20)
    draw_stroke(d, jitter(ellipse_path(cx, cy + 15, 150, 150, 1.05), s + 2, 4), (cp - 0.4) / 0.6, CREAM, 20)
    if cp > 0.9: d.ellipse((cx + 220, cy - 140, cx + 270, cy - 90), fill=RED)
    lns = c["linhas"]
    t1 = wt(lns[0]["em"]) - S
    if lt > t1 - 0.1:
        q = back_out((lt - t1 + 0.1) / 0.2)
        cc = card(860, 300, PURPLE, 60); cd = ImageDraw.Draw(cc)
        for i, ln in enumerate(lns[:2]):
            if lt > wt(ln["em"]) - S - 0.05:
                cd.text((430, 90 + 125 * i), ln["texto"], font=qfont(96), fill=CREAM if i == 0 else YELLOW, anchor="mm")
        paste_rot(img, cc, W / 2, 1470, 3, scale=0.2 + 0.8 * q)
    if c.get("x_em"):
        xp = ease_in_out((lt - lt_of(c, S, "x_em") + 0.02) / 0.14)
        d = ImageDraw.Draw(img)
        draw_stroke(d, [(cx - 380 + 760 * i / 20, cy - 330 + 630 * i / 20) for i in range(21)], xp, RED, 40)
        draw_stroke(d, [(cx + 380 - 760 * i / 20, cy - 330 + 630 * i / 20) for i in range(21)], (xp - 0.5) * 2, RED, 40)
    return img
def s_camera(S, c):
    ev = [("pop", wt(c["linhas"][0]["em"]), 0.25)]
    if c.get("x_em"): ev.append(("risco", wt(c["x_em"]) - 0.02, 0.4))
    return ev

# 8) olho_foto: foto num card com zebra + olho piscando + etiqueta + palavra circulada
def m_olho_foto(lt, t, S, c):
    img = fundo(c.get("fundo", "bege"), t); s = seed_of(t)
    pc = back_out(lt / 0.22, 1.5)
    foto = c.get("foto")
    if foto and pc > 0:
        ph = Image.open(foto_path(foto["nome"])).convert("RGBA")
        cw_, chh_ = 760, 860
        sc_ = max(cw_ / ph.width, chh_ / ph.height); ph = ph.resize((int(ph.width * sc_), int(ph.height * sc_)), Image.LANCZOS)
        z = zebra(cw_, chh_, t, YELLOW, C("amarelo_escuro"), 40)
        z.alpha_composite(ph, ((cw_ - ph.width) // 2, chh_ - ph.height))
        m = Image.new("L", (cw_, chh_), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, cw_ - 1, chh_ - 1), 50, fill=255); z.putalpha(m)
        frame = card(cw_, chh_, BLACK, 50, CREAM, 16); frame.alpha_composite(z, (16, 16))
        gdx, gdy, gda, gds = gif_motion(t, foto.get("movimento", "respira"), 5) if lt > 0.22 else (0, 0, 0, 1)
        paste_rot(img, frame, W / 2 - 40 + gdx, 640 + gdy, -5 + 8 * (1 - pc) + gda, scale=(0.3 + 0.7 * pc) * gds)
    d = ImageDraw.Draw(img)
    K = 0.42 if foto else 1.0
    cx, cy = (880, 230) if foto else (W / 2, 780)
    op = back_out((lt - (0.12 if foto else 0)) / 0.2)
    blink = 1.0; bl = lt - 0.5
    if 0 < bl < 0.14: blink = abs(math.cos(bl / 0.14 * math.pi))
    ew, eh = 400 * K * op, 230 * K * op * max(0.05, blink)
    pts = [(cx + ew * math.cos(a), cy + eh * math.sin(a) * abs(math.sin(a)) ** 0.3) for a in np.linspace(0, 2 * math.pi, 60)]
    if op > 0.05:
        d.polygon(pts, fill=YELLOW); d.line(pts + [pts[0]], fill=BLACK, width=int(16 * max(K, 0.55)), joint="curve")
        if blink > 0.4:
            px = cx + 90 * K * math.sin(t * 3.0); py = cy + 20 * K * math.cos(t * 2.3); r = 120 * K * op * min(1, blink)
            d.ellipse((px - r, py - r, px + r, py + r), fill=BLACK)
            d.ellipse((px - r * 0.2 + 30 * K, py - r * 0.6, px + r * 0.25 + 30 * K, py - r * 0.15), fill=CREAM)
        for k in range(5):
            a = math.pi + 0.35 + k * 0.6
            x1, y1 = cx + ew * 0.95 * math.cos(a), cy + eh * 0.95 * math.sin(a) * blink
            d.line([(x1, y1), (x1 + 60 * K * math.cos(a), y1 + 60 * K * math.sin(a))], fill=BLACK, width=int(14 * max(K, 0.55)))
    pill(img, c.get("etiqueta"), W / 2, 1200, 72, CREAM, BLACK, lt / 0.2, -2)
    tv = lt_of(c, S, "em")
    letters(img, c["palavra"], 400, 1500, lt, tv - 0.03, 0.035, 0.2, [PURPLE], [-4, 3, -3, 4, -2], "pop", BLACK, 10, BLACK, (16, 18), t=t, breathe=4)
    draw_stroke(ImageDraw.Draw(img), jitter(ellipse_path(W / 2, 1500, 470, 240, 1.12), s, 6), ease_in_out((lt - tv - 0.2) / 0.3), RED, 20)
    return img
def s_olho_foto(S, c): return [("pop", wt(c["em"]), 0.35)]

# 9) muro: palavra em tijolos 3x3 (castelo) que desaba numa palavra
def m_muro(lt, t, S, c):
    img = fundo(c.get("fundo", "preto"), t)
    tc = lt_of(c, S, "cai_em")
    word = c["palavra"].replace(" ", "")
    nc = c.get("colunas", 3)
    rows = [word[i:i + nc] for i in range(0, len(word), nc)]
    nr = len(rows)
    cols = [PURPLE, YELLOW, RED]
    bw = bh = min(300, int(960 / nc) - 10)
    rnd = random.Random(4)
    base = 1350
    for r, row in enumerate(rows):
        for i, ch in enumerate(row):
            idx = r * nc + i
            st = (nr - 1 - r) * 0.06 + i * 0.03
            p = ease_out((lt - st) / 0.16)
            fr, fx, fa = rnd.random(), rnd.random(), rnd.random()
            if p <= 0: continue
            x = W / 2 + (i - (nc - 1) / 2) * (bw + 10)
            y = base - (nr - 1 - r) * (bh + 10) - 900 * (1 - p)
            ang = 0
            if lt > tc:
                q = lt - tc - fr * 0.08
                if q > 0: y += 3200 * q * q; x += (fx - 0.5) * 900 * q; ang = (fa - 0.5) * 300 * q
            col = cols[idx % 3]
            b = card(bw, bh, col, 26, BLACK, 8)
            ImageDraw.Draw(b).text((b.width / 2, b.height / 2), ch, font=font(ANTON, int(bh * 0.8)), fill=BLACK if col == YELLOW else CREAM, anchor="mm")
            paste_rot(img, b, x, y, ang)
    if lt < tc + 0.05:
        p = ease_out((lt - 0.2) / 0.15); d = ImageDraw.Draw(img)
        yt = base - (nr - 1) * (bh + 10) - bh / 2 - 10
        for k in range(nc):
            x = W / 2 + (k - (nc - 1) / 2) * (bw + 10)
            if p > 0: d.rectangle((x - bw * 0.23, yt - 130 * p, x + bw * 0.23, yt), fill=YELLOW)
    pill(img, c.get("etiqueta"), W / 2, 260, 90, BLACK, CREAM, lt / 0.2, 3)
    return img
def s_muro(S, c): return [("estrondo", wt(c["cai_em"]) + 0.05, 0.5)]

# 10) papel: palavra numa folha pautada que sai do papel + lâmpada
def m_papel(lt, t, S, c):
    img = fundo(c.get("fundo", "bege"), t); d = ImageDraw.Draw(img); s = seed_of(t)
    pill(img, c.get("etiqueta"), W / 2, 300, 88, CREAM, BLACK, lt / 0.2, -3)
    pw, ph = 880, 900
    paper = Image.new("RGBA", (pw, ph), CREAM + (255,)); pd = ImageDraw.Draw(paper)
    for y in range(120, ph, 70): pd.line([(40, y), (pw - 40, y)], fill=(170, 190, 220), width=4)
    pd.line([(130, 0), (130, ph)], fill=(230, 120, 110), width=5)
    pp = ease_out((lt - 0.05) / 0.25)
    paste_rot(img, paper, W / 2, 1100 + 1200 * (1 - pp), -4)
    ti = lt_of(c, S, "em"); tpap = lt_of(c, S, "sai_em", c["em"])
    lift = ease_in_out((lt - tpap) / 0.35)
    if lt > ti - 0.05:
        if lift > 0:
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            letters(sh, c["palavra"], 300, 1080 + 40 * lift, lt, ti - 0.05, 0.03, 0.16, [(0, 0, 0, 90)], [0], "pop", t=t, cx=W / 2 + 30 * lift)
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        letters(img, c["palavra"], int(300 * (1 + 0.25 * lift)), 1080 - 380 * lift, lt, ti - 0.05, 0.03, 0.16, [PURPLE, RED, YELLOW, PURPLE, RED],
                [-3 - 6 * lift, 2 + 5 * lift, -4, 3 + 6 * lift, -2 - 5 * lift], "pop", BLACK, int(6 + 4 * lift), BLACK, (10, 12), t=t, breathe=8 * lift)
    if c.get("lampada_em"):
        bp = ease_in_out((lt - lt_of(c, S, "lampada_em")) / 0.35); d = ImageDraw.Draw(img); bx, by = 870, 560
        draw_stroke(d, jitter(ellipse_path(bx, by, 90, 100, 0.85, start=2.3), s, 3), bp, YELLOW, 16)
        if bp > 0.8:
            d.line([(bx - 40, by + 110), (bx + 40, by + 110)], fill=YELLOW, width=14)
            d.line([(bx - 30, by + 140), (bx + 30, by + 140)], fill=YELLOW, width=14)
            sparks(d, bx, by, ease_out((bp - 0.8) * 5), YELLOW, 115, 170, n=5, a0=-math.pi / 2, spread=0.6, w=10)
    return img
def s_papel(S, c):
    ev = [("pop", wt(c["em"]), 0.3)]
    if c.get("lampada_em"): ev.append(("ding", wt(c["lampada_em"]) + 0.25, 0.25))
    return ev

# 11) fina_onda: palavra fina enorme com cobra + palavra grossa em onda
def m_fina_onda(lt, t, S, c):
    img = fundo(c.get("fundo", "roxo"), t); d = ImageDraw.Draw(img); s = seed_of(t)
    ta = lt_of(c, S, "fina_em"); tm = lt_of(c, S, "onda_em")
    p = ease_out((lt - ta + 0.08) / 0.25)
    fa = qfont(380, "Light")
    if fa.getlength(c["fina"]) > 1000: fa = qfont(int(380 * 1000 / fa.getlength(c["fina"])), "Light")
    d.text((W / 2 + 600 * (1 - p), 700), c["fina"], font=fa, fill=CREAM, anchor="mm")
    pill(img, c.get("etiqueta"), 270, 330, 70, PURPLE, YELLOW, lt / 0.2, -4)
    sp = ease_in_out((lt - ta) / 0.5)
    sn = jitter([(-60 + 1200 * i / 120, 700 + 200 * math.sin(i / 120 * 2.6 * math.pi + 0.6) * (0.6 + 0.4 * math.sin(t * 2))) for i in range(121)], s, 3)
    d = ImageDraw.Draw(img); cobra(d, sn, sp, YELLOW, 70)
    if c.get("meio"): d.text((W / 2, 1060), c["meio"], font=qfont(110, "Light"), fill=CREAM, anchor="mm")
    if lt > tm - 0.05:
        word = c["onda"]; xs, tw = word_layout(word, ANTON, 230, -4); f = font(ANTON, 230)
        sc = min(1, 980 / tw); cols = [YELLOW, RED, CREAM]
        for i, ch in enumerate(word):
            st = tm - 0.05 + i * 0.03
            if lt < st: continue
            q = back_out((lt - st) / 0.18)
            im = letter_img(ch, ANTON, int(230 * sc), cols[i % 3], BLACK, 6, BLACK, (8, 10))
            paste_rot(img, im, W / 2 + (xs[i] + f.getlength(ch) / 2 - tw / 2) * sc, 1420 + 90 * math.sin(t * 7 - i * 0.7),
                      14 * math.cos(t * 7 - i * 0.7), scale=q)
    return img
def s_fina_onda(S, c): return [("pop", wt(c["fina_em"]), 0.3), ("pop", wt(c["onda_em"]), 0.3)]

# 12) video: título + card de vídeo com play + foto apontando
def m_video(lt, t, S, c):
    img = fundo(c.get("fundo", "amarelo"), t); d = ImageDraw.Draw(img)
    if c.get("padrao"): pattern_rows(d, c["padrao"], qfont(130), C("amarelo_padrao"), t, step=160)
    letters(img, c["titulo"], 330, 380, lt, 0.0, 0.04, 0.2, [RED, PURPLE, BLACK, RED], [-5, 4, -3, 5], t=t)
    tv = lt_of(c, S, "em")
    foto = c.get("foto")
    cxv = 700 if foto else W / 2
    if lt > tv - 0.08:
        q = back_out((lt - tv + 0.08) / 0.22)
        cc = card(560, 900, BLACK, 70, CREAM, 12); cd = ImageDraw.Draw(cc)
        cd.polygon([(230, 330), (230, 530), (390, 430)], fill=YELLOW)
        cd.text((292, 720), c.get("card_texto", ""), font=qfont(84), fill=CREAM, anchor="mm")
        prog = clamp((lt - tv) / 0.9)
        cd.rounded_rectangle((60, 820, 520, 836), 8, fill=(70, 70, 70)); cd.rounded_rectangle((60, 820, 60 + 460 * prog, 836), 8, fill=RED)
        paste_rot(img, cc, cxv, 1080 if foto else 1140, 5 - 9 * (1 - q), scale=0.2 + 0.8 * q)
    if foto: place(img, dict({"altura": 1150, "x": 270, "y": 1330, "giro": -3, "movimento": "danca"}, **foto), 270, 1330, (lt - 0.02) / 0.22, t)
    return img
def s_video(S, c): return [("pop", S + 0.15, 0.3), ("pop", wt(c["em"]), 0.3)]

# 13) dupla: card A + card B (ex.: VOCÊ + CLAUDE)
def m_dupla(lt, t, S, c):
    img = fundo(c.get("fundo", "preto"), t); s = seed_of(t)
    pill(img, c.get("etiqueta"), W / 2, 360, 70, BLACK, CREAM, lt / 0.2, -2)
    def bloco(txt, cor, tcor, cx, cy, ang, p):
        f = font(ANTON, 220)
        if f.getlength(txt) > 820: f = font(ANTON, int(220 * 820 / f.getlength(txt)))
        cc = card(int(f.getlength(txt) + 140), 300, C(cor), 60, CREAM, 10)
        ImageDraw.Draw(cc).text((cc.width / 2, 160), txt, font=f, fill=C(tcor), anchor="mm")
        paste_rot(img, cc, cx, cy, ang, scale=p)
    bloco(c["a"], c.get("a_cor", "roxo"), "creme", W / 2 - 60, 760, -6, back_out((lt - 0.08) / 0.22))
    pp = ease_in_out((lt - 0.25) / 0.2); d = ImageDraw.Draw(img)
    draw_stroke(d, jitter([(W / 2, 960 + 200 * i / 10) for i in range(11)], s, 4), pp, YELLOW, 34)
    draw_stroke(d, jitter([(W / 2 - 100 + 200 * i / 10, 1060) for i in range(11)], s + 1, 4), pp, YELLOW, 34)
    tc = lt_of(c, S, "b_em")
    if lt > tc - 0.06:
        bloco(c["b"], c.get("b_cor", "laranja"), "preto", W / 2 + 50, 1370, 5, back_out((lt - tc + 0.06) / 0.22))
        d = ImageDraw.Draw(img); st = ease_out((lt - tc - 0.1) / 0.2)
        star(d, 930, 1170, 70 * st, s, YELLOW, 12); star(d, 150, 1560, 50 * st, s + 3, CREAM, 10)
    return img
def s_dupla(S, c): return [("pop", S + 0.1, 0.3), ("pop", wt(c["b_em"]), 0.35)]

# 14) pergunta: card preto com pergunta em 3 partes (fina, grossa, fina circulada)
def m_pergunta(lt, t, S, c):
    img = fundo(c.get("fundo", "bege"), t); s = seed_of(t)
    p = back_out(lt / 0.2, 1.6)
    cc = card(940, 1000, BLACK, 90); ImageDraw.Draw(cc).text((470, 200), c.get("topo", ""), font=qfont(170), fill=YELLOW, anchor="mm")
    paste_rot(img, cc, W / 2, H / 2, -4 + 8 * (1 - p), scale=0.5 + 0.5 * p)
    tc = lt_of(c, S, "grande_em")
    letters(img, c["grande"], 330, H / 2 - 20, lt, tc - 0.05, 0.035, 0.18, [CREAM, PURPLE, RED, YELLOW, CREAM], [-4, 3, -2, 4, -3], "pop", t=t, breathe=4, maxw=780)
    if c.get("baixo"):
        ts = lt_of(c, S, "baixo_em")
        if lt > ts - 0.12:
            q = back_out((lt - ts + 0.12) / 0.2)
            im = Image.new("RGBA", (800, 240), (0, 0, 0, 0)); ImageDraw.Draw(im).text((400, 120), c["baixo"], font=qfont(170), fill=CREAM, anchor="mm")
            paste_rot(img, im, W / 2, H / 2 + 300, -4, scale=q)
            draw_stroke(ImageDraw.Draw(img), jitter(ellipse_path(W / 2, H / 2 + 300, 330, 130, 1.12), s, 5), ease_in_out((lt - ts) / 0.3), PURPLE, 16)
    return img
def s_pergunta(S, c):
    ev = [("pop", wt(c["grande_em"]), 0.3)]
    if c.get("baixo_em"): ev.append(("pop", wt(c["baixo_em"]), 0.25))
    return ev

# 15) cta: balão de comentário + palavra gigante caindo
def m_cta(lt, t, S, c):
    img = fundo(c.get("fundo", "amarelo"), t); s = seed_of(t)
    p = back_out(lt / 0.22)
    f = qfont(150); tw = f.getlength(c.get("balao", "comenta"))
    bw_ = int(max(560, tw + 160))
    bub = Image.new("RGBA", (bw_, 380), (0, 0, 0, 0)); bd = ImageDraw.Draw(bub)
    bd.rounded_rectangle((10, 10, bw_ - 10, 290), 140, fill=CREAM, outline=BLACK, width=12)
    bd.polygon([(170, 280), (130, 370), (290, 285)], fill=CREAM)
    bd.line([(170, 288), (130, 370), (290, 287)], fill=BLACK, width=12)
    bd.text((bw_ / 2, 150), c.get("balao", "comenta"), font=f, fill=BLACK, anchor="mm")
    paste_rot(img, bub, W / 2, 470, -5, scale=0.2 + 0.8 * p)
    tb = lt_of(c, S, "em")
    letters(img, c["palavra"], 470, 1180, lt, tb - 0.08, 0.06, 0.28, [PURPLE, RED, BLACK, PURPLE, RED], [-8, 6, -5, 7, 10], t=t, breathe=10, maxw=1000)
    d = ImageDraw.Draw(img); st = ease_out((lt - tb - 0.4) / 0.25)
    for sx, sy, a in [(110, 900, -2.5), (980, 870, -0.6), (130, 1520, 2.3), (960, 1520, 0.7)]: sparks(d, sx, sy, st, BLACK, a0=a, w=14)
    star(d, 540, 1680, 80 * st, s, BLACK, 12)
    zz = [(120 + i * 42, 1480 + (24 if i % 2 else -24)) for i in range(21)]
    draw_stroke(d, jitter(zz, s + 3, 5), ease_in_out((lt - tb - 0.5) / 0.3), PURPLE, 18)
    return img
def s_cta(S, c):
    return [("pop", S + 0.1, 0.3)] + [("pop", x + 0.17, 0.4) for x in letter_times(c["palavra"], wt(c["em"]) - 0.08, 0.06)]

MODELOS = {
    "queda": (m_queda, s_queda), "zebra_card": (m_zebra_card, s_zebra_card), "card_fino": (m_card_fino, s_card_fino),
    "palavra": (m_palavra, s_palavra), "cadeado": (m_cadeado, s_cadeado), "linhas": (m_linhas, s_linhas),
    "camera": (m_camera, s_camera), "olho_foto": (m_olho_foto, s_olho_foto), "muro": (m_muro, s_muro),
    "papel": (m_papel, s_papel), "fina_onda": (m_fina_onda, s_fina_onda), "video": (m_video, s_video),
    "dupla": (m_dupla, s_dupla), "pergunta": (m_pergunta, s_pergunta), "cta": (m_cta, s_cta),
}

def eventos():
    ev = []
    for i, (S, c) in enumerate(SCENES):
        if i: ev.append(("whoosh", S - 0.11, 0.32))
        ev += MODELOS[c["tipo"]][1](S, c)
    return ev

def quadro(t, fi):
    idx = max(i for i, (st, _) in enumerate(SCENES) if st <= t)
    S, c = SCENES[idx]; lt = t - S
    img = MODELOS[c["tipo"]][0](lt, t, S, c)
    k = max(0.0, 1 - lt / 0.18) if idx else 0
    dx = 4 * math.sin(t * 13) + 40 * k * math.sin(t * 90)
    dy = 3 * math.cos(t * 11) + 30 * k * math.cos(t * 77)
    sc = 1.02 + 0.05 * k
    zw, zh = int(W * sc), int(H * sc)
    z = img.resize((zw, zh), Image.BICUBIC)
    ox, oy = (zw - W) / 2 + dx, (zh - H) / 2 + dy
    return add_grain(z.crop((int(ox), int(oy), int(ox) + W, int(oy) + H)), fi // 2)

_PROJ_PATH = None
def _init(p): carregar(p)
def _render(fi):
    quadro(fi / FPS, fi).save(os.path.join(OUT, "quadros", f"f{fi:04d}.png")); return fi

if __name__ == "__main__":
    caminho = sys.argv[1]; carregar(caminho)
    if "--ver" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--ver") + 1].split(",")]
        th = [quadro(t, int(t * FPS)).resize((270, 480)) for t in ts]
        cols = min(6, len(th)); rows = math.ceil(len(th) / cols)
        sheet = Image.new("RGB", (270 * cols, 480 * rows), (255, 255, 255))
        for i, im in enumerate(th): sheet.paste(im, ((i % cols) * 270, (i // cols) * 480))
        out = os.path.join(OUT, "previa.jpg"); sheet.save(out, quality=88); print(out)
        sys.exit()
    n = int(DUR * FPS)
    with Pool(os.cpu_count() or 4, initializer=_init, initargs=(caminho,)) as p:
        for _ in p.imap_unordered(_render, range(n), chunksize=4): pass
    json.dump({"duracao": DUR, "quadros": n, "cenas": [[round(S, 3), c["tipo"]] for S, c in SCENES]},
              open(os.path.join(OUT, "cenas.json"), "w"), ensure_ascii=False, indent=1)
    print("ok", n, "quadros em", os.path.join(OUT, "quadros"))
