#!/usr/bin/env python3
"""Cenário desenhado: a pessoa real sentada num cenário em traço de caneta que se transforma.

  python3 -I motor.py roteiro.json --palavras        → lista as palavras com tempo (para escrever o roteiro)
  python3 -I motor.py roteiro.json --textos          → mostra os blocos de texto que vão entrar (automáticos ou do roteiro)
  python3 -I motor.py roteiro.json --ver 3.2 10.9    → quadros de teste em ver/
  python3 -I motor.py roteiro.json                   → final.mp4 + final-camada-textos.mov + final-sfx.wav

Rode na pasta do projeto (depois de preparar.py).
"""
import json, math, os, re, subprocess, sys, unicodedata
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from desenho import *
import desenho as D
from moveis import cadeira, sofa, banquinho, topo_predio
import cenarios as C
from cenarios import cam

W, H, FPS = 1080, 1920, 30
PASTA = os.getcwd()
CORES = {"verde": VERDE, "verde_escuro": VERDE_E, "verde_claro": VERDE_C, "laranja": LARANJA, "laranja_claro": LARANJA_C,
         "bege": BEGE, "bege_escuro": BEGE_E, "rosa": ROSA, "rosa_escuro": ROSA_E, "ceu": CEU, "ceu_claro": CEU_C, "branco": BRANCO}


def cor(c, padrao=None):
    if c is None: return padrao
    if isinstance(c, (list, tuple)): return tuple(c)
    if c.startswith("#"): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return CORES[c]


# ------------------------------------------------------------------ dados do projeto
R = None; INFO = None; PAL = []; SEGS = []; N = 0


def carrega(roteiro):
    global R, INFO, PAL, SEGS, N
    R = json.load(open(roteiro))
    INFO = json.load(open(os.path.join(PASTA, "info.json")))
    SEGS = json.load(open(os.path.join(PASTA, "transcricao.json")))
    PAL = [w for s in SEGS for w in s["w"]]
    N = INFO["quadros"]
    monta()


def norm(s):
    s = unicodedata.normalize("NFC", s.lower())
    return "".join(ch for ch in s if ch.isalnum())


def tempo(v, depois=0.0):
    """número, ou "@palavra", "@palavra#2", "@palavra+0.2", "@palavra:fim" (procura a partir de `depois`)"""
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    m = re.match(r"@([^#+\-:]+)(?:#(\d+))?(:fim)?([+\-][\d.]+)?$", v.strip())
    if not m: raise SystemExit(f"tempo inválido: {v}")
    p, n, fim, d = m.group(1), int(m.group(2) or 1), m.group(3), float(m.group(4) or 0)
    k = 0
    for w in PAL:
        if w["s"] < depois - 1e-6: continue
        a, b = norm(w["w"]), norm(p)
        if a == b or (len(b) > 3 and a.startswith(b)):
            k += 1
            if k == n: return (w["e"] if fim else w["s"]) + d
    raise SystemExit(f"palavra não encontrada: {v}  (use --palavras para ver a transcrição)")


# ------------------------------------------------------------------ montagem do roteiro
CX = SY = HT = 0; ESC = 1.0; ENTRA = INICIO = 0
CENAS = []; ASSENTOS = {}; CAM_AY = 1100; BLK = []
T_REAL_FIM = None; T_REAL_VOLTA = None; D_REAL = 0.6; D_WIPE = 0.45; D_MORF = 0.55


def monta():
    global CX, SY, HT, ESC, ENTRA, INICIO, CENAS, ASSENTOS, CAM_AY, T_REAL_FIM, T_REAL_VOLTA, BLK
    CX = int(R.get("centro_x", INFO["centro_x"])); SY = int(R.get("assento_y", INFO["assento_y"]))
    HT = int(R.get("cabeca_y", INFO["cabeca_y"]))
    ESC = float(R.get("tamanho_moveis", max(0.6, min(1.5, INFO["largura_pernas"] / 550))))
    ENTRA = INFO["entra"]
    INICIO = int(round(tempo(R["inicio"]) * FPS)) if "inicio" in R else ENTRA
    CAM_AY = (HT + SY) / 2 + 60
    esc = lambda partes: desloca(partes, s=ESC, cx=CX, cy=SY) if ESC != 1 else partes
    ASSENTOS = {"poltrona": lambda: esc(cadeira(CX, SY)), "cadeira": lambda: esc(cadeira(CX, SY)), "sofa": lambda: esc(sofa(CX, SY)),
                "banquinho": lambda: esc(banquinho(CX, SY)), "predio": lambda: esc(topo_predio(CX, SY, alto=2600)), "nenhum": lambda: []}
    CENAS = []
    for c in R["cenas"]:
        kw = {}
        if c.get("fundo", "parede") == "parede":
            kw = dict(cor=cor(c.get("cor"), ROSA), quadros=C.QUADROS_B if c.get("quadros", "A") == "B" else C.QUADROS_A,
                      extras=c.get("planta_e_luminaria", True))
        CENAS.append((tempo(c.get("em", 0)), c.get("fundo", "parede"), kw, c.get("assento", "poltrona")))
    CENAS.sort(key=lambda x: x[0])
    T_REAL_FIM = tempo(R.get("real_ate")) if R.get("real_ate") is not None else None
    T_REAL_VOLTA = tempo(R.get("real_volta")) if R.get("real_volta") is not None else None
    BLK = blocos()


def camera(t):
    """no fundo "terraco" a câmera se afasta (mostra o prédio alto) e volta de supetão na cena seguinte"""
    for k, c in enumerate(CENAS):
        if c[1] != "terraco": continue
        prox = CENAS[k + 1][0] if k + 1 < len(CENAS) else 1e9
        a, b = c[0] + 0.45, prox - 0.1
        if a <= t < b:
            u = (t - a) / max(0.3, b - a); e = 1 - (1 - u) ** 3
            return (1 - 0.5 * e, CX, CAM_AY)
        if b <= t < prox + 0.3:
            u = min(1, (t - b) / 0.4); e = u * u * (3 - 2 * u)
            return (0.5 + 0.5 * e, CX, CAM_AY)
    return (1, CX, CAM_AY)


def cena_em(t):
    k = 0
    for i, c in enumerate(CENAS):
        if t >= c[0]: k = i
    return k


# ------------------------------------------------------------------ textos
DIN = "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"
AVN = "/System/Library/Fonts/Avenir Next Condensed.ttc"
_f = {}
TAM = {"p": ("p", 70), "m": ("g", 160), "g": ("g", 240), "gg": ("g", 320)}


def fonte(tipo, tam):
    k = (tipo, int(tam))
    if k not in _f:
        _f[k] = ImageFont.truetype(DIN, int(tam)) if tipo == "g" else ImageFont.truetype(AVN, int(tam), index=0)
    return _f[k]


def auto_textos():
    """sem "textos" no roteiro: cada frase (partida nas vírgulas, até 6 palavras) vira um bloco —
    as palavras pequenas em volta e a palavra mais longa gigante"""
    pedacos = []
    for seg in SEGS:
        atual = []
        for w in seg["w"]:
            atual.append(w["w"].strip())
            if w["w"].rstrip().endswith((",", ";", ":")) and len(atual) >= 2: pedacos.append(atual); atual = []
        if atual:
            if pedacos and len(atual) == 1 and pedacos[-1] and len(pedacos[-1]) < 6: pedacos[-1] += atual
            else: pedacos.append(atual)
    final = []
    for p in pedacos:
        while len(p) > 6:
            k = len(p) // 2; final.append(p[:k]); p = p[k:]
        final.append(p)
    out = []
    for p in final:
        ws = [w.strip(".,!?;:") for w in p]
        k = max(range(len(ws)), key=lambda i: len(ws[i]))
        linhas = []
        if k > 0: linhas.append({"txt": " ".join(ws[:k]), "tam": "p"})
        linhas.append({"txt": ws[k], "tam": "gg" if len(ws[k]) <= 7 else "g"})
        if k + 1 < len(ws): linhas.append({"txt": " ".join(ws[k + 1:]), "tam": "p"})
        out.append({"linhas": linhas})
    return out


def blocos():
    lista = R.get("textos") or auto_textos()
    cursor = 0; out = []
    for b in lista:
        linhas = []
        for li in b["linhas"]:
            tipo, tam = TAM[li.get("tam", "p")]
            tam = int(li.get("px", tam))
            grande = tipo == "g"
            c = cor(li.get("cor"), LARANJA if li.get("tam") in ("g", "gg") else VERDE_E)
            sombra = cor(li.get("sombra"), VERDE_E if c != VERDE_E else BRANCO) if grande else None
            ps = li["txt"].split(); alvo = [norm(p) for p in ps]
            achou = None
            for i in range(cursor, len(PAL) - len(ps) + 1):   # a linha inteira em sequência na fala
                if [norm(PAL[i + j]["w"]) for j in range(len(ps))] == alvo: achou = i; break
            if achou is None:
                raise SystemExit(f"texto não encontrado na fala (na ordem e grafia da transcrição): '{li['txt']}'")
            ws = [(p, PAL[achou + j]["s"]) for j, p in enumerate(ps)]
            cursor = achou + len(ps)
            linhas.append(dict(tipo=tipo, tam=tam, cor=c, sombra=sombra, ws=ws, ef=li.get("efeito", "")))
        out.append(dict(ini=linhas[0]["ws"][0][1], linhas=linhas))
    for i, b in enumerate(out):
        b["fim"] = out[i + 1]["ini"] - 0.05 if i + 1 < len(out) else 999
    return out


def mola(u):
    if u <= 0: return 0.0
    return 1 - math.exp(-9 * u) * math.cos(16 * u)


_letra = {}


def letra_img(ch, tipo, tam, c, sombra, seed):
    k = (ch, tipo, tam, c, sombra, seed)
    if k in _letra: return _letra[k]
    r = np.random.default_rng(abs(hash((ch, seed))) % 2 ** 32)
    jt = 1 + r.uniform(-0.06, 0.06) if tipo == "g" else 1
    f = fonte(tipo, tam * jt)
    l, t_, rr, b = f.getbbox(ch)
    off = max(4, int(tam * 0.035)) if sombra else 0
    im = Image.new("RGBA", (rr - l + off + 20, b - t_ + off + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if sombra: d.text((10 - l + off, 10 - t_ + off), ch, font=f, fill=sombra + (255,))
    d.text((10 - l, 10 - t_), ch, font=f, fill=c + (255,))
    if tipo == "g": im = im.rotate(r.uniform(-4, 4), resample=Image.BICUBIC, expand=True)
    _letra[k] = im
    return im


def layout(bl, fator=1.0):
    y = 170; itens = []
    for li in bl["linhas"]:
        tam = li["tam"] * fator; g = li["tipo"] == "g"
        palavras = [(w.upper() if g else w, ts) for w, ts in li["ws"]]
        f = fonte(li["tipo"], tam); esp = f.getlength(" ")
        larg = sum(f.getlength(w) for w, _ in palavras) + esp * (len(palavras) - 1)
        if larg > 980:
            tam = tam * 980 / larg; f = fonte(li["tipo"], tam); esp = f.getlength(" ")
            larg = sum(f.getlength(w) for w, _ in palavras) + esp * (len(palavras) - 1)
        alt = tam * (0.78 if g else 0.95)
        x = (W - larg) / 2; cy = y + alt / 2
        for wi, (w, ts) in enumerate(palavras):
            for ch in w:
                adv = f.getlength(ch)
                itens.append(dict(ch=ch, x=x + adv / 2, y=cy, ts=ts, tam=int(tam), li=li, i=len(itens), wi=wi))
                x += adv
            x += esp
        y += alt + (24 if g else 18)
    return itens, y


def prepara_layout(bl):
    """encolhe o bloco se ele invadir a cabeça (considera a câmera afastada no terraço)"""
    limite = HT - 40
    s, _, ay = camera(bl["ini"] + 0.8)
    if s != 1: limite = ay + (HT - ay) * 0.5 - 40
    fator = 1.0
    for _ in range(12):
        it, y = layout(bl, fator)
        if y <= limite: break
        fator *= 0.9
    bl["it"], bl["y_fim"] = it, y


def textos(t, passo):
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for bl in BLK:
        if not (bl["ini"] - 0.1 <= t < bl["fim"] + 0.3): continue
        if "it" not in bl: prepara_layout(bl)
        saida = max(0.0, (t - bl["fim"]) / 0.25)
        for it in bl["it"]:
            li = it["li"]; ts = it["ts"] + (it["i"] % 50) * 0.012 * (li["tipo"] == "g")
            u = t - ts
            if u < 0: continue
            s = mola(u * 1.3)
            if saida > 0: s *= max(0, 1 - saida * (1 + (it["i"] % 7) * 0.15))
            if s <= 0.01: continue
            im = letra_img(it["ch"], li["tipo"], it["tam"], li["cor"], li["sombra"], passo % 3 + it["i"] * 7)
            dx = dy = 0; giro = 0
            if li["ef"] == "onda":
                dy = math.sin(t * 7 + it["i"] * 0.7) * it["tam"] * 0.07; giro = math.sin(t * 7 + it["i"] * 0.7 + 1) * 6
            elif li["ef"] == "pula":
                dy = -abs(math.sin(t * 6 + it["i"] * 0.9)) * it["tam"] * 0.08
            elif li["ef"] == "brilho":
                giro = math.sin(t * 5 + it["i"]) * 4
            q = im
            if s != 1 or giro:
                q = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
                if giro: q = q.rotate(giro, resample=Image.BICUBIC, expand=True)
            camada.alpha_composite(q, (int(it["x"] + dx - q.width / 2), int(it["y"] + dy - q.height / 2)))
        for li in bl["linhas"]:
            if li["ef"] == "placa" and t >= li["ws"][0][1] - 0.05: placa(camada, bl, li, t, passo)
            if li["ef"] == "brilho": brilhos(camada, t - li["ws"][0][1], passo, saida)
    return camada


def placa(camada, bl, li, t, passo):
    its = [i for i in bl["it"] if i["li"] is li]
    x0 = min(i["x"] for i in its) - 70; x1 = max(i["x"] for i in its) + 70
    y0 = its[0]["y"] - its[0]["tam"] * 0.5; y1 = its[0]["y"] + its[0]["tam"] * 0.42
    u = min(1, (t - its[0]["ts"]) / 0.3)
    xm = (x0 + x1) / 2; hw = (x1 - x0) / 2 * mola(u * 1.3)
    fundo = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    desenha(fundo, [parte(ret(xm - hw, y0, xm + hw, y1, 30), LARANJA, VERDE_E, 10)], passo)
    by = bl["y_fim"] + 10 + math.sin(t * 8) * 10
    if t > its[0]["ts"] + 0.5:
        for xs in (150, 930):
            desenha(fundo, [parte(poli(xs, by - 120, xs + 10, by), None, LARANJA, 11, aberta=True),
                            parte(poli(xs - 35, by - 40, xs + 10, by + 5, xs + 50, by - 45), None, LARANJA, 11, aberta=True)], passo)
    fundo = fundo.resize((W, H), Image.LANCZOS)
    fundo.alpha_composite(camada); camada.paste(fundo)


def estrela(cx, cy, r):
    return np.array([[cx + (r if k % 2 == 0 else r * 0.32) * math.cos(k * math.pi / 4 - math.pi / 2),
                      cy + (r if k % 2 == 0 else r * 0.32) * math.sin(k * math.pi / 4 - math.pi / 2)] for k in range(8)])


def brilhos(camada, u, passo, saida):
    if u < 0: return
    cam_ = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0)); ps = []
    for k, (x, y, r, d) in enumerate(((120, 300, 50, 0), (960, 260, 60, 0.1), (90, 720, 40, 0.2), (1000, 760, 46, 0.15), (300, 1050, 36, 0.3),
                                       (820, 1040, 42, 0.25), (180, 1350, 30, 0.35), (930, 1300, 34, 0.4))):
        s = mola((u - d) * 1.2) * (1 - saida) * (0.85 + 0.15 * math.sin(u * 9 + k))
        if s > 0.02:
            ps.append(parte(estrela(x, y, r * s * 1.4), (LARANJA, ROSA_E, VERDE_C, BRANCO)[k % 4], VERDE_E if k % 2 else LARANJA, 6))
    desenha(cam_, ps, passo)
    cam_ = cam_.resize((W, H), Image.LANCZOS); cam_.alpha_composite(camada); camada.paste(cam_)


# ------------------------------------------------------------------ composição
def fundo_img(k, t, passo, c):
    _, nome, kw, _ = CENAS[k]
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 255))
    C.FUNDOS[nome](im, t, passo, c, **kw)
    return im


def assento_partes(t):
    k = cena_em(t)
    novo = ASSENTOS[CENAS[k][3]]()
    if k == 0: return novo
    u = (t - CENAS[k][0]) / D_MORF
    if u >= 1: return novo
    return morfa(ASSENTOS[CENAS[k - 1][3]](), novo, u)


def iris(r, passo):
    th = np.linspace(0, 2 * math.pi, 140, endpoint=False)
    rr = r * (1 + 0.035 * np.sin(th * 7 + passo))
    return np.stack([CX + rr * np.cos(th), (HT + SY) / 2 + rr * np.sin(th)], 1)


def real_iris(t):
    if T_REAL_FIM is not None:
        if t < T_REAL_FIM: return (True, 0)
        if t < T_REAL_FIM + D_REAL: return (True, 2300 * ((t - T_REAL_FIM) / D_REAL) ** 1.6)
    if T_REAL_VOLTA is not None and t >= T_REAL_VOLTA:
        return (False, 2300 * min(1, (t - T_REAL_VOLTA) / D_REAL) ** 1.6)
    return None


def grade(q):
    lum = q.mean(2, keepdims=True)
    return np.clip((lum + (q - lum) * float(R.get("saturacao", 1.15)) - 0.03) / 0.95, 0, 1)


def escala(q, m, s, ax, ay):
    nw, nh = int(W * s), int(H * s)
    qi = Image.fromarray((q * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    mi = Image.fromarray((m * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    ox, oy = int(ax - ax * s), int(ay - ay * s)
    Q = Image.new("RGB", (W, H)); M = Image.new("L", (W, H), 0)
    Q.paste(qi, (ox, oy)); M.paste(mi, (ox, oy))
    return np.asarray(Q, np.float32) / 255, np.asarray(M, np.float32) / 255


def quadro(fi, so_texto=False):
    t = fi / FPS; passo = fi // 4; c = camera(t)
    if so_texto: return textos(t, passo)
    k = cena_em(t)
    bg = fundo_img(k, t, passo, c)
    u = (t - CENAS[k][0]) / D_WIPE if k > 0 else 9
    if u < 1:   # íris: o cenário novo abre de dentro da pessoa, com borda desenhada
        velho = fundo_img(k - 1, t, passo, c)
        r = 2300 * (u ** 1.6)
        m = Image.new("L", bg.size, 0)
        ImageDraw.Draw(m).polygon([tuple(v * SS) for v in iris(r, passo)], fill=255)
        velho.paste(bg, (0, 0), m)
        desenha(velho, [parte(iris(r, passo), None, LARANJA, 16)], passo)
        bg = velho
    assento = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    desenha(assento, cam(assento_partes(t), c), passo)
    bg.alpha_composite(assento)
    assento = assento.resize((W, H), Image.LANCZOS)
    bg = bg.resize((W, H), Image.LANCZOS).convert("RGB")
    tex = textura(W, H)[..., 0:1]
    arr = np.asarray(bg, np.float32) / 255 * tex
    real = grade(np.asarray(Image.open(os.path.join(PASTA, "quadros", f"{fi + 1:05d}.jpg")).convert("RGB"), np.float32) / 255)
    q = real
    m = np.asarray(Image.open(os.path.join(PASTA, "pernas", f"{fi + 1:05d}.png")).convert("L"), np.float32) / 255
    s, ax, ay = c
    if s != 1: q, m = escala(q, m, s, ax, ay)
    sm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)), np.float32) / 255
    sm = np.roll(np.roll(sm, int(18 * s), 1), int(12 * s), 0)[..., None]
    arr = arr * (1 - 0.28 * sm)
    m3 = m[..., None]
    arr = arr * (1 - m3) + q * m3
    # frente do assento por cima da base das pernas (esconde o banco real embaixo dos pés)
    if CENAS[k][3] != "nenhum":
        yl = ay + (SY + 2 - ay) * s
        rampa = np.clip((np.arange(H, dtype=np.float32)[:, None] - yl) / (10 * s), 0, 1)
        fr = np.asarray(assento, np.float32) / 255
        af = fr[..., 3:4] * rampa[..., None]
        arr = arr * (1 - af) + fr[..., :3] * tex * af
    ri = real_iris(t)
    if ri is not None:
        dentro, r = ri
        mk = Image.new("L", (W, H), 0)
        if r > 0: ImageDraw.Draw(mk).polygon([tuple(v) for v in iris(r, passo)], fill=255)
        mk = (np.asarray(mk.filter(ImageFilter.GaussianBlur(1)), np.float32) / 255)[..., None]
        if not dentro: mk = 1 - mk
        arr = real * (1 - mk) + arr * mk
        if 0 < r < 2300:
            anel = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
            desenha(anel, [parte(iris(r, passo), None, LARANJA, 16)], passo)
            an = np.asarray(anel.resize((W, H), Image.LANCZOS), np.float32) / 255
            arr = arr * (1 - an[..., 3:4]) + an[..., :3] * an[..., 3:4]
            arr = arr * (1 - m3) + q * m3   # o anel passa por trás da pessoa
    out = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    out.alpha_composite(textos(t, passo))
    return out.convert("RGB")


# ------------------------------------------------------------------ som
def som(saida):
    from som import Som
    t0 = INICIO / FPS
    S = Som(N / FPS - t0 + 0.5)
    for tt in (T_REAL_FIM, T_REAL_VOLTA):
        if tt is not None: S.whoosh(tt - t0 + 0.2, 0.5, 0.45); S.pop(tt - t0 + 0.05, 420, 0.33)
    for k, c in enumerate(CENAS[1:], 1):
        S.whoosh(c[0] - t0 + 0.15, 0.45, 0.45); S.pop(c[0] - t0 + 0.05, 420, 0.3)
        if c[1] == "terraco": S.sobe(c[0] + 1.1 - t0, 0.8, 0.25)
    for i, bl in enumerate(BLK):
        for li in bl["linhas"]:
            if li["tipo"] == "g":
                for j, (w, ts) in enumerate(li["ws"]): S.pop(ts - t0, 600 + 140 * ((i + j) % 3), 0.32)
            if li["ef"] in ("brilho", "placa"): S.ding(li["ws"][0][1] - t0, 1318 if li["ef"] == "brilho" else 1568, 0.35)
    S.salva(saida)


# ------------------------------------------------------------------ saídas
def _trecho(args):
    roteiro, a, b, saida, so_texto = args
    carrega(roteiro)
    if so_texto:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", saida]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p", saida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(a, b):
        p.stdin.write(quadro(fi, so_texto).tobytes())
        if fi % 90 == 0: print(os.path.basename(saida), f"{fi}/{b}", flush=True)
    p.stdin.close(); p.wait()


def final(roteiro):
    saida = R.get("saida", "final.mp4"); nome = os.path.splitext(saida)[0]
    os.makedirs("partes", exist_ok=True)
    np_ = int(R.get("processos", max(2, (os.cpu_count() or 4) // 2)))
    P = (N - INICIO + np_ - 1) // np_
    tarefas = [(roteiro, INICIO + k * P, min(N, INICIO + (k + 1) * P), f"partes/p{k}.mp4", False) for k in range(np_)]
    tarefas.append((roteiro, INICIO, N, "partes/textos.mov", True))
    with ProcessPoolExecutor(len(tarefas)) as ex: list(ex.map(_trecho, tarefas))
    open("partes/lista.txt", "w").write("".join(f"file 'p{k}.mp4'\n" for k in range(np_)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "partes/lista.txt", "-c", "copy", "partes/video.mp4"], check=True)
    som("partes/sfx.wav")
    t0 = INICIO / FPS
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", "base.mp4", "-vn", "-ac", "2", "-ar", "48000", "partes/voz.wav"], check=True)
    vol = float(R.get("sfx_volume", 1.0)) * 0.55
    entradas = ["-i", "partes/video.mp4", "-i", "partes/voz.wav", "-i", "partes/sfx.wav"]
    filtro = f"[1:a]loudnorm=I=-16:TP=-1.5[v];[2:a]volume={vol},aformat=channel_layouts=stereo[s];[v][s]amix=inputs=2:duration=first:normalize=0[a]"
    if R.get("trilha"):
        entradas += ["-i", R["trilha"]]
        tv = float(R.get("trilha_volume", 0.18))
        filtro = (f"[1:a]loudnorm=I=-16:TP=-1.5,asplit[v][vk];[3:a]volume={tv},aformat=channel_layouts=stereo[m];"
                  f"[m][vk]sidechaincompress=threshold=0.03:ratio=6:release=400[md];"
                  f"[2:a]volume={vol},aformat=channel_layouts=stereo[s];[v][s][md]amix=inputs=3:duration=first:normalize=0[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", filtro, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", saida], check=True)
    os.replace("partes/textos.mov", f"{nome}-camada-textos.mov")
    os.replace("partes/sfx.wav", f"{nome}-sfx.wav")
    print(f"pronto: {saida}, {nome}-camada-textos.mov, {nome}-sfx.wav")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    roteiro = a[0]
    if "--palavras" in a:
        PAL = [w for s in json.load(open("transcricao.json")) for w in s["w"]]
        for i in range(0, len(PAL), 8):
            print("  ".join(f"{w['w']}@{w['s']:.2f}" for w in PAL[i:i + 8]))
        sys.exit()
    carrega(roteiro)
    if "--textos" in a:
        for b in BLK:
            print(f"[{b['ini']:6.2f}] " + " / ".join(("" if l["tipo"] == "p" else "**") + " ".join(w for w, _ in l["ws"]) + ("" if l["tipo"] == "p" else "**") for l in b["linhas"]))
    elif "--ver" in a:
        os.makedirs("ver", exist_ok=True)
        for t in a[a.index("--ver") + 1:]:
            fi = int(round(float(t) * FPS))
            quadro(fi).save(f"ver/q_{float(t):05.2f}.jpg", quality=88); print(f"ver/q_{float(t):05.2f}.jpg")
    else:
        final(roteiro)
