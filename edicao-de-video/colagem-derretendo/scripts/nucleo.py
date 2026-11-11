"""Peças comuns: vídeo, máscara, rosto, palavras, desenho, kit de elementos e som."""
import glob, json, math, os, re, subprocess, unicodedata, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- cores e fontes
PALETA = {
    "papel": "#F6F1E7", "tinta": "#1B1B1B", "terracota": "#E4572E", "petroleo": "#14606B",
    "mostarda": "#F2B134", "rosa": "#F49CBB", "ceu": "#7CC6E8", "verde": "#3BA55C", "branco": "#FFFFFF",
}
FONTES = {
    "bold": ("/System/Library/Fonts/Avenir Next.ttc", 0), "heavy": ("/System/Library/Fonts/Avenir Next.ttc", 8),
    "medium": ("/System/Library/Fonts/Avenir Next.ttc", 5), "regular": ("/System/Library/Fonts/Avenir Next.ttc", 7),
    "cond": ("/System/Library/Fonts/HelveticaNeue.ttc", 9), "mono": ("/System/Library/Fonts/Menlo.ttc", 1),
    "mono_r": ("/System/Library/Fonts/Menlo.ttc", 0), "didot": ("/System/Library/Fonts/Supplemental/Didot.ttc", 2),
    "didot_i": ("/System/Library/Fonts/Supplemental/Didot.ttc", 1), "mao": ("/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf", 0),
}
EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
_fc = {}


def fonte(nome, tam):
    k = (nome, int(tam))
    if k not in _fc:
        p, i = FONTES[nome]
        _fc[k] = ImageFont.truetype(p, max(6, int(tam)), index=i)
    return _fc[k]


def cor(c, a=255):
    if isinstance(c, (tuple, list)): return tuple(c[:3]) + (a,)
    c = PALETA.get(c, c).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


# ---------------------------------------------------------------- curvas de tempo
def clamp(p): return min(max(p, 0.0), 1.0)
def sai(p): p = clamp(p); return 1 - (1 - p) ** 3                      # desacelera
def entra(p): p = clamp(p); return p ** 3                              # acelera
def suave(p): p = clamp(p); return 3 * p * p - 2 * p ** 3
def mola(p, c=1.7):                                                     # passa do ponto e volta
    p = clamp(p); return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2
def lerp(a, b, p): return a + (b - a) * p


# ---------------------------------------------------------------- vídeo
def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "default=nw=1", path],
                         capture_output=True, text=True, check=True).stdout
    d = dict(l.split("=", 1) for l in out.strip().splitlines() if "=" in l)
    n, m = d["r_frame_rate"].split("/")
    return int(d["width"]), int(d["height"]), float(n) / float(m), float(d.get("duration", 0) or 0)


def tem_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return bool(out.strip())


def quadro_em(path, t, W, H):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.4f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255


def para_img(a):  # float HxWx3 0..1 → PIL
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def de_img(im):
    return np.asarray(im.convert("RGB"), np.float32) / 255


def sobre(base, camada, x=0, y=0, alfa=1.0):
    """Cola um RGBA (PIL) sobre um quadro float, em (x, y) = canto superior esquerdo."""
    if camada is None or alfa <= 0: return base
    H, W = base.shape[:2]
    x, y = int(round(x)), int(round(y)); w, h = camada.size
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0: return base
    c = np.asarray(camada.crop((x0 - x, y0 - y, x1 - x, y1 - y)), np.float32) / 255
    a = c[..., 3:4] * alfa
    base[y0:y1, x0:x1] = base[y0:y1, x0:x1] * (1 - a) + c[..., :3] * a
    return base


def sobre_centro(base, camada, cx, cy, escala=1.0, giro=0.0, alfa=1.0):
    if camada is None or escala <= 0.01: return base
    im = camada
    if abs(escala - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * escala)), max(1, int(im.height * escala))), Image.LANCZOS)
    if abs(giro) > 0.05:
        im = im.rotate(giro, Image.BICUBIC, expand=True)
    return sobre(base, im, cx - im.width / 2, cy - im.height / 2, alfa)


def transforma(fr, escala, cx, cy, para=None, giro=0.0, fundo=(0, 0, 0)):
    """Escala/gira o quadro inteiro em volta de (cx, cy); (cx, cy) vai parar em `para`."""
    H, W = fr.shape[:2]
    px, py = para if para else (cx, cy)
    a = math.radians(giro); ca, sa = math.cos(a) / escala, math.sin(a) / escala
    # ponto da saída (u, v) → origem
    coef = (ca, sa, cx - ca * px - sa * py, -sa, ca, cy + sa * px - ca * py)
    im = para_img(fr).transform((W, H), Image.AFFINE, coef, Image.BICUBIC, fillcolor=tuple(int(v * 255) for v in fundo))
    return de_img(im)


def zoom_borrado(fr, escala, cx, cy, forca, n=5, para=None):
    """Zoom com borrão de movimento radial (média de escalas vizinhas)."""
    if forca < 0.004: return transforma(fr, escala, cx, cy, para)
    acc = np.zeros_like(fr)
    for k in range(n):
        acc += transforma(fr, escala * (1 + forca * (k / (n - 1) - 0.5)), cx, cy, para)
    return acc / n


def desfoca(fr, r):
    if r <= 0.3: return fr
    if fr.shape[2] == 1:
        im = Image.fromarray((np.clip(fr[..., 0], 0, 1) * 255 + 0.5).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
        return np.asarray(im, np.float32)[..., None] / 255
    return de_img(para_img(fr).filter(ImageFilter.GaussianBlur(r)))


def vinheta(H, W, forca=0.5):
    y, x = np.ogrid[:H, :W]
    d = ((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2
    return (1 - forca * np.clip(d - 0.3, 0, 1.5) / 1.5)[..., None].astype(np.float32)


def solido(H, W, c):
    return np.broadcast_to(np.array(cor(c)[:3], np.float32) / 255, (H, W, 3)).copy()


# ---------------------------------------------------------------- máscara e rosto
class Mascaras:
    def __init__(self, pasta, W, H):
        self.arq = sorted(glob.glob(os.path.join(pasta, "*.png"))) if pasta else []
        self.W, self.H = W, H

    def __bool__(self): return bool(self.arq)

    def get(self, i):
        if not self.arq: return None
        m = Image.open(self.arq[min(i, len(self.arq) - 1)]).convert("L")
        if m.size != (self.W, self.H): m = m.resize((self.W, self.H), Image.BILINEAR)
        return np.asarray(m, np.float32)[..., None] / 255


def borda_adesivo(m, px, cor_borda=(1, 1, 1)):
    """Contorno de adesivo: máscara inchada `px` pixels."""
    im = Image.fromarray((m[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(px * 0.55))
    a = np.asarray(im, np.float32) / 255
    return np.clip((a - 0.04) * 6, 0, 1)[..., None]


class Rosto:
    """Centro e tamanho do rosto por quadro (rosto.json do rosto.swift), suavizado."""
    def __init__(self, arq, n, W, H, esc, fixo=None):
        self.fixo = fixo
        cx = np.full(n, np.nan); cy = np.full(n, np.nan); s = np.full(n, np.nan)
        if arq and os.path.exists(arq):
            dados = json.load(open(arq))
            for i, b in enumerate(dados[:n]):
                if b:
                    x, y, w, h = [v * esc for v in b]
                    cx[i], cy[i], s[i] = x + w / 2, y + h / 2, w
        ok = ~np.isnan(cx)
        if ok.sum() == 0:
            cx[:], cy[:], s[:] = W / 2, H * 0.36, W * 0.26
        else:
            idx = np.arange(n)
            for a in (cx, cy, s):
                a[:] = np.interp(idx, idx[ok], a[ok])
        k = np.ones(9) / 9
        pad = lambda a: np.convolve(np.pad(a, 4, mode="edge"), k, "valid")
        self.cx, self.cy, self.s = pad(cx), pad(cy), pad(s)

    def em(self, i):
        if self.fixo: return tuple(self.fixo)
        i = min(max(i, 0), len(self.cx) - 1)
        return float(self.cx[i]), float(self.cy[i]), float(self.s[i])


# ---------------------------------------------------------------- palavras
def _norm(s):
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFC", s.lower()))  # acento conta: "é" ≠ "e"


class Palavras:
    def __init__(self, arq):
        self.w = []
        if arq and os.path.exists(arq):
            for seg in json.load(open(arq)):
                self.w += [(p["s"], p["e"], p["w"]) for p in seg.get("w", [])]

    def tempo(self, v, depois=0.0):
        """Número → segundos. Texto "@palavra", "@palavra#2" (2ª vez), "@palavra+0.2", "@palavra:fim"."""
        if isinstance(v, (int, float)): return float(v)
        m = re.match(r"@([^#+\-:]+)(?:#(\d+))?(?::(fim))?([+-][\d.]+)?$", v.strip())
        if not m: return float(v)
        alvo, n, fim, d = _norm(m.group(1)), int(m.group(2) or 1), m.group(3), float(m.group(4) or 0)
        achou = 0
        for s, e, w in self.w:
            if s + 1e-3 < depois: continue
            if _norm(w) == alvo or (len(alvo) > 3 and _norm(w).startswith(alvo)):
                achou += 1
                if achou == n: return (e if fim else s) + d
        raise SystemExit(f"palavra não encontrada na transcrição: {v}")

    def lista(self):
        for s, e, w in self.w: print(f"{s:7.2f} {e:7.2f}  {w}")


# ---------------------------------------------------------------- desenho em 2x (borda lisa)
def desenho(w, h, fn, ss=2):
    im = Image.new("RGBA", (int(w * ss), int(h * ss)), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), ss, im)
    return im.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)


def sombra(im, raio=14, desloc=(0, 10), opac=0.35):
    """Devolve o RGBA com sombra macia embaixo (e margem)."""
    m = int(raio * 2.2) + max(abs(desloc[0]), abs(desloc[1]))
    out = Image.new("RGBA", (im.width + 2 * m, im.height + 2 * m), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: int(v * opac))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 255)); sh.putalpha(a)
    out.paste(sh, (m + desloc[0], m + desloc[1]), sh)
    out = out.filter(ImageFilter.GaussianBlur(raio))
    out.alpha_composite(im, (m, m))
    return out


def texto_tam(txt, f):
    b = f.getbbox(txt); return b[2] - b[0], b[3] - b[1]


def emoji(ch, tam):
    f = ImageFont.truetype(EMOJI, 160)
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((100, 100), ch, font=f, embedded_color=True, anchor="mm")
    bb = im.getbbox() or (0, 0, 200, 200)
    im = im.crop(bb)
    k = tam / max(im.size)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def imagem(path, tam):
    im = Image.open(path).convert("RGBA")
    k = tam / max(im.size)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


# ---------------------------------------------------------------- kit: universo social / digital / criativo / papel
APPS = {  # ícones genéricos de app (sem marca): gradiente + símbolo
    "camera": ("📸", "#F58529", "#DD2A7B"), "play": ("▶️", "#FF3B30", "#C00000"), "musica": ("🎵", "#1ED760", "#0B7A35"),
    "chat": ("💬", "#34C759", "#1E8E3E"), "email": ("✉️", "#4FA3FF", "#1460D6"), "foto": ("🖼️", "#FFD34E", "#F29A0A"),
    "video": ("🎬", "#8E5CF7", "#4B21C4"), "ia": ("✨", "#E4572E", "#B23A17"), "lapis": ("✏️", "#FFE08A", "#F2B134"),
    "paleta": ("🎨", "#F49CBB", "#D9487A"), "coracao": ("❤️", "#FF6B8B", "#E0284F"), "estrela": ("⭐", "#14606B", "#0A3D45"),
    "mic": ("🎙️", "#2B2B2B", "#000000"), "link": ("🔗", "#7CC6E8", "#2C8DBA"), "calendario": ("📅", "#FFFFFF", "#E9E9E9"),
    "mapa": ("📍", "#5AD07A", "#2E9C4C"), "tesoura": ("✂️", "#F6F1E7", "#E5DCC8"), "lampada": ("💡", "#FFF2B2", "#F2C94C"),
    "foguete": ("🚀", "#2C2C54", "#141432"), "grafico": ("📈", "#FFFFFF", "#EDEDED"),
}


def gradiente(w, h, c1, c2):
    a = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(cor(c1)[:3], np.float32) * (1 - a) + np.array(cor(c2)[:3], np.float32) * a
    return Image.fromarray(np.broadcast_to(g, (h, w, 3)).astype(np.uint8)).convert("RGBA")


def app_icone(nome, tam):
    """Ícone de app: chave de APPS, um emoji, ou caminho de PNG (logo da pessoa)."""
    if isinstance(nome, str) and os.path.exists(nome):
        logo = imagem(nome, tam * 0.62); fundo = ("#FFFFFF", "#F1F1F1")
    else:
        g, c1, c2 = APPS.get(nome, (nome, "#FFFFFF", "#EFEFEF"))
        logo = emoji(g, tam * 0.56); fundo = (c1, c2)
    s = 2; T = int(tam * s)
    base = gradiente(T, T, *fundo)
    m = Image.new("L", (T, T), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, T - 1, T - 1), radius=int(T * 0.23), fill=255)
    base.putalpha(m)
    brilho = Image.new("RGBA", (T, T), (255, 255, 255, 0))
    ImageDraw.Draw(brilho).ellipse((-T * 0.3, -T * 0.9, T * 1.3, T * 0.45), fill=(255, 255, 255, 38))
    brilho.putalpha(Image.fromarray(np.minimum(np.asarray(brilho.split()[3]), np.asarray(m))))
    base.alpha_composite(brilho)
    base = base.resize((int(tam), int(tam)), Image.LANCZOS)
    base.alpha_composite(logo, ((base.width - logo.width) // 2, (base.height - logo.height) // 2))
    return base


def comentario(usuario, texto, tam=480, curtidas=None, avatar=None, escuro=False):
    fb, fr = fonte("bold", tam * 0.058), fonte("medium", tam * 0.062)
    linhas, atual = [], ""
    for p in texto.split():
        t = (atual + " " + p).strip()
        if texto_tam(t, fr)[0] > tam * 0.66 and atual: linhas.append(atual); atual = p
        else: atual = t
    linhas.append(atual)
    lh = tam * 0.085; h = tam * 0.16 + lh * (len(linhas) + 0.6)
    fundo, tinta, cinza = ((28, 28, 30, 255), (245, 245, 245, 255), (150, 150, 155, 255)) if escuro else \
                          ((255, 255, 255, 255), (20, 20, 20, 255), (130, 130, 135, 255))

    def fn(d, s, im):
        d.rounded_rectangle((0, 0, tam * s - 1, h * s - 1), radius=tam * 0.06 * s, fill=fundo)
        r = tam * 0.06; ax, ay = tam * 0.05 + r, tam * 0.06 + r
        if avatar and os.path.exists(avatar):
            av = Image.open(avatar).convert("RGB").resize((int(2 * r * s),) * 2)
            mk = Image.new("L", av.size, 0); ImageDraw.Draw(mk).ellipse((0, 0, av.width - 1, av.height - 1), fill=255)
            im.paste(av, (int((ax - r) * s), int((ay - r) * s)), mk)
        else:
            c = list(APPS.values())[sum(map(ord, usuario)) % len(APPS)][1]
            d.ellipse(((ax - r) * s, (ay - r) * s, (ax + r) * s, (ay + r) * s), fill=cor(c))
            d.text((ax * s, ay * s), usuario[:1].upper(), font=fonte("heavy", r * 1.1 * s), fill=(255, 255, 255), anchor="mm")
        x0 = ax + r + tam * 0.035
        d.text((x0 * s, tam * 0.05 * s), usuario, font=fonte("bold", tam * 0.058 * s), fill=tinta)
        for k, l in enumerate(linhas):
            d.text((x0 * s, (tam * 0.05 + lh * (k + 1)) * s), l, font=fonte("medium", tam * 0.062 * s), fill=tinta)
        if curtidas is not None:
            hx = tam * 0.92
            co = coracao_img(tam * 0.055 * s, (255, 59, 92))
            im.alpha_composite(co, (int(hx * s - co.width / 2), int(tam * 0.045 * s)))
            d.text((hx * s, tam * 0.14 * s), str(curtidas), font=fonte("medium", tam * 0.04 * s), fill=cinza, anchor="mm")
    return sombra(desenho(tam, h, fn), raio=tam * 0.03, desloc=(0, int(tam * 0.02)), opac=0.25)


def notificacao(app, titulo, texto, tam=640):
    h = tam * 0.2
    ic = app_icone(app, h * 0.56)

    def fn(d, s, im):
        d.rounded_rectangle((0, 0, tam * s - 1, h * s - 1), radius=h * 0.3 * s, fill=(250, 250, 250, 240))
        im.alpha_composite(ic.resize((int(ic.width * s), int(ic.height * s))), (int(h * 0.22 * s), int(h * 0.22 * s)))
        x = h * 0.95
        d.text((x * s, h * 0.2 * s), titulo, font=fonte("bold", h * 0.2 * s), fill=(20, 20, 20))
        d.text((x * s, h * 0.5 * s), texto, font=fonte("medium", h * 0.19 * s), fill=(70, 70, 75))
        d.text(((tam - h * 0.25) * s, h * 0.2 * s), "agora", font=fonte("medium", h * 0.15 * s), fill=(140, 140, 145), anchor="ra")
    return sombra(desenho(tam, h, fn), raio=tam * 0.025, desloc=(0, int(tam * 0.015)), opac=0.25)


def coracao_img(tam, c=(255, 255, 255)):
    """Coração desenhado (as fontes do sistema não têm ♥)."""
    def fn(d, s, im):
        T = tam * s; r = T * 0.27
        d.ellipse((T * 0.02, T * 0.08, T * 0.02 + 2 * r, T * 0.08 + 2 * r), fill=c)
        d.ellipse((T * 0.98 - 2 * r, T * 0.08, T * 0.98, T * 0.08 + 2 * r), fill=c)
        d.polygon([(T * 0.04, T * 0.42), (T * 0.96, T * 0.42), (T * 0.5, T * 0.95)], fill=c)
    return desenho(max(2, tam), max(2, tam), fn)


def curtidas(n, tam=220):
    h = tam * 0.42
    f = fonte("heavy", h * 0.48)
    w = h * 1.05 + texto_tam(str(n), f)[0] + h * 0.45

    def fn(d, s, im):
        d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=h * 0.5 * s, fill=cor("#FF3B5C"))
        co = coracao_img(h * 0.5 * s)
        im.alpha_composite(co, (int(h * 0.32 * s), int(h * 0.27 * s)))
        d.text((h * 0.95 * s, h * 0.5 * s), str(n), font=fonte("heavy", h * 0.48 * s), fill=(255, 255, 255), anchor="lm")
    return sombra(desenho(w, h, fn), raio=8, desloc=(0, 5), opac=0.3)


def cursor(tam=90):
    def fn(d, s, im):
        p = [(0, 0), (0, 0.78), (0.2, 0.6), (0.34, 0.92), (0.47, 0.86), (0.33, 0.55), (0.6, 0.55)]
        pts = [(4 * s + x * (tam - 8) * s, 4 * s + y * (tam - 8) * s) for x, y in p]
        d.polygon(pts, fill=(15, 15, 15), outline=(255, 255, 255))
        d.line(pts + [pts[0]], fill=(255, 255, 255), width=int(3 * s))
    return sombra(desenho(tam * 0.65, tam, fn), raio=5, desloc=(2, 4), opac=0.3)


def rasgado(im, borda=14, seed=1, cor_borda=(255, 255, 255)):
    """Recorte de papel: borda branca irregular (rasgada) em volta de um RGBA."""
    rng = np.random.default_rng(seed)
    m = borda + 6
    big = Image.new("RGBA", (im.width + 2 * m, im.height + 2 * m), (0, 0, 0, 0))
    big.alpha_composite(im, (m, m))
    a = big.split()[3].filter(ImageFilter.GaussianBlur(borda * 0.5))
    a = np.asarray(a, np.float32) / 255
    ruido = rng.normal(0, 1, (a.shape[0] // 6 + 2, a.shape[1] // 6 + 2)).astype(np.float32)
    ruido = np.asarray(Image.fromarray(ruido).resize((a.shape[1], a.shape[0]), Image.BICUBIC))
    papel = ((a + 0.07 * ruido) > 0.12).astype(np.uint8) * 255
    out = Image.new("RGBA", big.size, cor_borda + (0,)); out.putalpha(Image.fromarray(papel))
    out.alpha_composite(big)
    return out


def fita(w=150, h=44, c="#F2B134", seed=0):
    rng = np.random.default_rng(seed)

    def fn(d, s, im):
        dente = lambda x0, lado: [(x0 + lado * rng.uniform(0, 6) * s, y * s) for y in np.linspace(0, h, 7)]
        pts = dente(0, 1) + dente(w * s, -1)[::-1]
        d.polygon(pts, fill=cor(c, 175))
    return desenho(w, h, fn)


def forma(tipo, tam, c, seed=0):
    rng = np.random.default_rng(seed)

    def fn(d, s, im):
        T = tam * s
        if tipo == "estrela":
            pts = [(T / 2 + T / 2 * (1 if k % 2 == 0 else 0.42) * math.sin(k * math.pi / 5),
                    T / 2 - T / 2 * (1 if k % 2 == 0 else 0.42) * math.cos(k * math.pi / 5)) for k in range(10)]
            d.polygon(pts, fill=cor(c))
        elif tipo == "circulo": d.ellipse((0, 0, T - 1, T - 1), fill=cor(c))
        elif tipo == "anel": d.ellipse((0, 0, T - 1, T - 1), outline=cor(c), width=int(T * 0.16))
        elif tipo == "pontos":
            for i in range(5):
                for j in range(5): d.ellipse((i * T / 5, j * T / 5, i * T / 5 + T / 11, j * T / 5 + T / 11), fill=cor(c))
        elif tipo == "listra":
            for k in range(-4, 8): d.polygon([(k * T / 5, T), (k * T / 5 + T / 10, T), (k * T / 5 + T / 10 + T, 0), (k * T / 5 + T, 0)], fill=cor(c))
        elif tipo == "rabisco":
            pts = [(x * s, T / 2 + math.sin(x / tam * 9) * T * 0.3) for x in np.linspace(0, tam, 40)]
            d.line(pts, fill=cor(c), width=int(T * 0.08), joint="curve")
        elif tipo == "seta":
            d.line([(T * 0.1, T * 0.85), (T * 0.5, T * 0.35), (T * 0.88, T * 0.15)], fill=cor(c), width=int(T * 0.07), joint="curve")
            d.polygon([(T * 0.95, T * 0.1), (T * 0.68, T * 0.12), (T * 0.86, T * 0.36)], fill=cor(c))
        elif tipo == "brilho":
            for a in range(4):
                ang = a * math.pi / 2
                d.polygon([(T / 2, T / 2), (T / 2 + math.cos(ang - 0.18) * T * 0.2, T / 2 + math.sin(ang - 0.18) * T * 0.2),
                           (T / 2 + math.cos(ang) * T / 2, T / 2 + math.sin(ang) * T / 2),
                           (T / 2 + math.cos(ang + 0.18) * T * 0.2, T / 2 + math.sin(ang + 0.18) * T * 0.2)], fill=cor(c))
        elif tipo == "coracao":
            im.alpha_composite(coracao_img(T, cor(c)), (0, 0))
    return desenho(tam, tam, fn)


def pilula(txt, tam_fonte, fundo="#FFFFFF", tinta="#1B1B1B", ponto=None, fonte_nome="bold", pad=0.55):
    f = fonte(fonte_nome, tam_fonte)
    tw, th = texto_tam(txt, f)
    h = tam_fonte * 1.75; extra = h * 0.9 if ponto else 0
    w = tw + h * pad * 2 + extra

    def fn(d, s, im):
        d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=h * 0.5 * s, fill=cor(fundo))
        x = h * pad
        if ponto:
            r = h * 0.26; d.ellipse(((x) * s, (h / 2 - r) * s, (x + 2 * r) * s, (h / 2 + r) * s), fill=cor(ponto))
            d.line([((x + r * 0.5) * s, (h / 2) * s), ((x + r * 0.9) * s, (h / 2 + r * 0.38) * s), ((x + r * 1.55) * s, (h / 2 - r * 0.4) * s)],
                   fill=(255, 255, 255), width=max(2, int(r * 0.28 * s)))
            x += extra
        d.text((x * s, h / 2 * s), txt, font=fonte(fonte_nome, tam_fonte * s), fill=cor(tinta), anchor="lm")
    return desenho(w, h, fn)


def elemento(spec, tam, seed=0):
    """Um item do kit a partir do JSON. str: chave de APPS/emoji/arquivo. dict: {"tipo": ...}."""
    if isinstance(spec, str): spec = {"tipo": "app", "nome": spec}
    t = spec.get("tipo", "app"); tam = spec.get("tam", tam)
    if t == "app": im = sombra(app_icone(spec["nome"], tam), raio=tam * 0.08, desloc=(0, int(tam * 0.06)), opac=0.3)
    elif t == "emoji": im = emoji(spec["nome"], tam)
    elif t == "comentario": im = comentario(spec.get("usuario", "@alguem"), spec.get("texto", ""), spec.get("tam", 470),
                                             spec.get("curtidas"), spec.get("avatar"), spec.get("escuro", False))
    elif t == "notificacao": im = notificacao(spec.get("app", "chat"), spec.get("titulo", ""), spec.get("texto", ""), spec.get("tam", 620))
    elif t == "curtidas": im = curtidas(spec.get("n", "1,2 mil"), tam)
    elif t == "cursor": im = cursor(tam)
    elif t == "forma": im = forma(spec.get("forma", "estrela"), tam, spec.get("cor", "terracota"), seed)
    elif t == "imagem": im = imagem(spec["arquivo"], tam)
    elif t == "fita": im = fita(tam, tam * 0.3, spec.get("cor", "mostarda"), seed)
    else: raise SystemExit(f"elemento desconhecido: {t}")
    if spec.get("papel"): im = rasgado(im, int(tam * 0.06) + 4, seed)
    return im


# ---------------------------------------------------------------- fundo limpo (sala vazia) por mediana
def placa_limpa(base, mascaras, W, H, n_total, fps, amostras=36):
    """Mediana dos quadros onde a pessoa não está: a sala vazia. Buracos preenchidos por difusão."""
    idx = np.linspace(0, n_total - 1, amostras).astype(int)
    fr = np.stack([quadro_em(base, i / fps, W, H) for i in idx])
    ms = np.stack([mascaras.get(i)[..., 0] for i in idx]) > 0.12
    fr[np.broadcast_to(ms[..., None], fr.shape)] = np.nan
    out = np.empty((H, W, 3), np.float32); buraco = np.zeros((H, W), bool)
    for y0 in range(0, H, 160):
        bloco = fr[:, y0:y0 + 160]
        with np.errstate(all="ignore"):
            med = np.nanmedian(bloco, axis=0)
        buraco[y0:y0 + 160] = np.isnan(med[..., 0]); out[y0:y0 + 160] = np.nan_to_num(med)
    if buraco.any():  # difusão: borra e copia só para dentro do buraco, de grosso para fino
        valido = (~buraco).astype(np.float32)[..., None]
        for r in (64, 32, 16, 8, 4):
            num = desfoca(out * valido, r); den = desfoca(np.repeat(valido, 3, 2), r)[..., :1]
            cheio = num / np.maximum(den, 1e-4)
            out = np.where(valido > 0, out, cheio)
            valido = np.maximum(valido, (den > 0.02).astype(np.float32))
    return out


# ---------------------------------------------------------------- som
SR = 48000


class Som:
    def __init__(self, dur, seed=5):
        self.out = np.zeros(int(dur * SR) + SR); self.rng = np.random.default_rng(seed); self.dur = dur

    def poe(self, y, t, g=0.5):
        i = max(0, int(t * SR)); n = min(len(y), len(self.out) - i)
        if n > 0: self.out[i:i + n] += g * y[:n]

    def _t(self, d): n = int(d * SR); return n, np.arange(n) / SR

    def whoosh(self, t, d=0.4, g=0.5):
        n, tt = self._t(d); x = self.rng.normal(0, 1, n); y = np.zeros(n); a = 0.0
        k = 0.02 + 0.3 * np.sin(np.pi * tt / d) ** 2
        for i in range(n): a += k[i] * (x[i] - a); y[i] = a
        self.poe(1.2 * y * np.sin(np.pi * tt / d) ** 1.6, t - d * 0.6, g)

    def pop(self, t, f0=560, g=0.45):
        n, tt = self._t(0.14); f = f0 * (1 + 1.6 * (1 - np.exp(-tt * 40)))
        self.poe(0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(tt / 0.002, 1) * np.exp(-tt * 30), t, g)

    def tique(self, t, f0=1800, g=0.3):
        n, tt = self._t(0.05); self.poe(np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 90), t, g)

    def clique(self, t, g=0.35):
        n, tt = self._t(0.03); self.poe(self.rng.normal(0, 1, n) * np.exp(-tt * 220), t, g)

    def digita(self, t0, t1, g=0.18):
        t = t0
        while t < t1: self.clique(t, g * self.rng.uniform(0.6, 1)); t += self.rng.uniform(0.045, 0.09)

    def flash(self, t, g=0.5):  # obturador
        self.clique(t, g); self.clique(t + 0.07, g * 0.7)
        n, tt = self._t(0.25); self.poe(self.rng.normal(0, 1, n) * np.exp(-tt * 30) * 0.3, t, g)

    def baque(self, t, g=0.6):
        n, tt = self._t(0.35); f = 120 * np.exp(-tt * 8) + 45
        self.poe(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9), t, g)

    def ding(self, t, f0=1318, g=0.4):
        n, tt = self._t(0.6); y = np.zeros(n)
        for at, f in ((0, f0), (0.08, f0 * 1.335)):
            u = np.clip(tt - at, 0, None); y += (tt >= at) * np.exp(-u * 8) * (np.sin(2 * np.pi * f * u) + 0.3 * np.sin(2 * np.pi * 2.76 * f * u))
        self.poe(0.4 * y, t, g)

    def sobe(self, t, d=0.8, g=0.35):  # riser
        n, tt = self._t(d); f = 200 + 900 * (tt / d) ** 2
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * (tt / d) ** 2 + 0.3 * self.rng.normal(0, 1, n) * (tt / d) ** 3
        self.poe(y * 0.5, t - d, g)

    def vidro(self, t, g=0.55):  # estilhaço
        n, tt = self._t(0.9); y = self.rng.normal(0, 1, n) * np.exp(-tt * 14) * 0.6
        for k in range(14):
            at = self.rng.uniform(0, 0.6); f = self.rng.uniform(2500, 6500); u = np.clip(tt - at, 0, None)
            y += (tt >= at) * np.sin(2 * np.pi * f * u) * np.exp(-u * 40) * 0.25
        self.poe(y, t, g); self.baque(t, g * 0.6)

    def papel(self, t, g=0.4):
        n, tt = self._t(0.25); x = self.rng.normal(0, 1, n)
        y = np.diff(np.concatenate([[0], x])) * (self.rng.uniform(0, 1, n) > 0.6) * np.exp(-tt * 10)
        self.poe(y, t, g)

    def salva(self, path):
        o = self.out[:int(self.dur * SR)]
        pk = np.abs(o).max()
        o = o / pk * 0.6 if pk > 0.6 else o
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(o, -1, 1) * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- papel de jornal (colagem)
def jornal(W, H, u, seed=1, palavras=None):
    """Página de jornal: papel amarelado, colunas de texto cinza, títulos e fios. RGB float."""
    rng = np.random.default_rng(seed)
    pal = palavras or ("edição efeito vídeo mundo novo ideia criar texto imagem tempo pacote máquina humana "
                       "ferramenta conteúdo aprender laboratório segredo truque minutos jornal notícia hoje").split()
    im = Image.new("RGB", (W, H), (233, 227, 211)); d = ImageDraw.Draw(im)
    fr, ft = fonte("didot", 21 * u), fonte("cond", 54 * u)
    col_w = 230 * u; gap = 22 * u; x = 18 * u
    while x < W:
        y = rng.uniform(-40, 0) * u
        while y < H:
            if rng.random() < 0.08:  # título
                txt = " ".join(rng.choice(pal, 2)).upper()
                d.text((x, y), txt, font=ft, fill=(40, 38, 36)); y += 64 * u
                d.line((x, y, x + col_w, y), fill=(90, 88, 84), width=max(1, int(2 * u))); y += 12 * u
            linha, lw = "", 0
            while True:
                w = str(rng.choice(pal))
                if texto_tam(linha + " " + w, fr)[0] > col_w: break
                linha = (linha + " " + w).strip()
            d.text((x, y), linha, font=fr, fill=(70, 68, 64)); y += 27 * u
        d.line((x + col_w + gap / 2, 0, x + col_w + gap / 2, H), fill=(150, 146, 136), width=max(1, int(u)))
        x += col_w + gap
    a = np.asarray(im, np.float32) / 255
    ruido = rng.normal(0, 0.025, (H // 4 + 1, W // 4 + 1)).astype(np.float32)
    ruido = np.asarray(Image.fromarray(ruido).resize((W, H), Image.BILINEAR))[..., None]
    return np.clip(a + ruido, 0, 1)


def borda_rasgada(m, px, u, seed=2):
    """Contorno irregular de papel rasgado em volta da máscara (H,W,1) → alfa (H,W,1)."""
    a = borda_adesivo(m, px * 1.15)
    H, W = a.shape[:2]
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (H // 18 + 2, W // 18 + 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(n).resize((W, H), Image.BICUBIC))[..., None]
    fino = rng.normal(0, 1, (H // 4 + 2, W // 4 + 2)).astype(np.float32)
    fino = np.asarray(Image.fromarray(fino).resize((W, H), Image.BILINEAR))[..., None]
    sopa = desfoca(m, px * 0.7)
    return np.clip(((sopa + 0.09 * n + 0.03 * fino) - 0.06) * 14, 0, 1) * a
