#!/usr/bin/env python3
"""Posts em 3D flutuando atrás da pessoa, num estúdio branco infinito.

Faz em um passo o que o tutorial faz em três apps (Canva: vídeo dentro da moldura de post;
Alight Motion: 3D Flip + chroma key; CapCut: fundo branco, remover plano de fundo, keyframes,
"balanço de rebote", reflexo e luzes). Aqui cada post é um plano 3D de verdade: entra girando
(o Flip), assenta com mola, flutua de leve, faz sombra no fundo e recebe as luzes coloridas.

  python3 -I mural.py projeto.json                 # → saida do projeto (mp4) + camadas
  python3 -I mural.py projeto.json --ver 1.5 4 9   # → quadros soltos para conferir
  python3 -I mural.py projeto.json --gestos        # sugere tempos de entrada pelos gestos
  python3 -I mural.py projeto.json --rascunho      # metade da resolução, rápido

Configuração: ver exemplos/projeto.json e o SKILL.md.
"""
import glob, json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VIDEO = (".mp4", ".mov", ".m4v", ".webm", ".mkv")


# ---------------------------------------------------------------- utilidades
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


def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mola(p):  # easeOutBack: passa do ponto e volta, o "losango" com rebote
    p = min(max(p, 0.0), 1.0); c = 1.7
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def saida(p):
    p = min(max(p, 0.0), 1.0); return 1 - (1 - p) ** 3


def homografia(src, dst):
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(A, float), np.array(b, float))


# ---------------------------------------------------------------- a moldura de post
class Moldura:
    """Cartão branco no formato de post do Instagram: mídia 4:5 + barra com ♥ 💬 ✈ e salvar."""

    def __init__(self, larg, cfg):
        self.w = larg
        self.pad = max(6, round(larg * 0.045))
        self.mw = larg - 2 * self.pad
        self.mh = round(self.mw * cfg.get("proporcao", 1.25))
        self.barra = round(larg * 0.17)
        self.h = self.pad + self.mh + self.barra
        self.raio = round(larg * 0.018)
        self.cor = hexrgb(cfg.get("cor_moldura", "#FFFFFF"))
        self.cor_icone = hexrgb(cfg.get("cor_icone", "#262626"))
        self.cor_coracao = hexrgb(cfg.get("cor_coracao", "#FF3040"))
        self.base = self._desenha()

    def _desenha(self):
        s = 3  # desenha grande e reduz: ícones lisos
        W, H = self.w * s, self.h * s
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, W - 1, H - 1], self.raio * s, fill=self.cor + (255,))
        u = self.barra * s * 0.30  # tamanho do ícone
        cy = (self.pad + self.mh) * s + self.barra * s * 0.45
        x = self.pad * s + u * 0.55
        lw = max(2, round(u * 0.11))
        # coração cheio
        r = u * 0.27
        d.ellipse([x - u * 0.5, cy - u * 0.42, x - u * 0.5 + 2 * r, cy - u * 0.42 + 2 * r], fill=self.cor_coracao)
        d.ellipse([x + u * 0.5 - 2 * r, cy - u * 0.42, x + u * 0.5, cy - u * 0.42 + 2 * r], fill=self.cor_coracao)
        d.polygon([(x - u * 0.5 + r * 0.12, cy - u * 0.08), (x + u * 0.5 - r * 0.12, cy - u * 0.08),
                   (x, cy + u * 0.48)], fill=self.cor_coracao)
        d.rectangle([x - u * 0.2, cy - u * 0.3, x + u * 0.2, cy], fill=self.cor_coracao)
        # balão de comentário
        x += u * 1.45
        d.ellipse([x - u * 0.45, cy - u * 0.45, x + u * 0.45, cy + u * 0.45], outline=self.cor_icone, width=lw)
        d.polygon([(x - u * 0.40, cy + u * 0.18), (x - u * 0.52, cy + u * 0.52), (x - u * 0.12, cy + u * 0.42)],
                  fill=self.cor + (255,))
        d.line([(x - u * 0.40, cy + u * 0.20), (x - u * 0.52, cy + u * 0.52), (x - u * 0.14, cy + u * 0.42)],
               fill=self.cor_icone, width=lw, joint="curve")
        # avião de papel
        x += u * 1.4
        p = [(x - u * 0.48, cy - u * 0.40), (x + u * 0.50, cy - u * 0.40), (x - u * 0.05, cy + u * 0.50)]
        d.polygon(p, outline=self.cor_icone, width=lw)
        d.line([(x + u * 0.50, cy - u * 0.40), (x - u * 0.18, cy - u * 0.02)], fill=self.cor_icone, width=lw)
        # salvar
        x = W - self.pad * s - u * 0.45
        d.polygon([(x - u * 0.36, cy - u * 0.48), (x + u * 0.36, cy - u * 0.48), (x + u * 0.36, cy + u * 0.50),
                   (x, cy + u * 0.20), (x - u * 0.36, cy + u * 0.50)], outline=self.cor_icone, width=lw)
        return im.resize((self.w, self.h), Image.LANCZOS)

    def com(self, midia, t=0.0):
        im = self.base.copy()
        im.paste(midia, (self.pad, self.pad))
        return im


def fonte(tam, negrito=False):
    from PIL import ImageFont
    for path, idx in ((f"/System/Library/Fonts/Avenir Next.ttc", 2 if negrito else 5),
                      ("/System/Library/Fonts/Helvetica.ttc", 1 if negrito else 0)):
        try:
            return ImageFont.truetype(path, tam, index=idx)
        except Exception:
            pass
    return ImageFont.load_default()


class Player:
    """Tela de "tocando agora" de um app de música: capa, música, artista, barra andando, controles.
    Visual genérico (escuro com destaque verde), sem logo de marca."""

    def __init__(self, larg, p):
        self.w = larg
        self.pad = round(larg * 0.075)
        self.mw = self.mh = larg - 2 * self.pad
        self.topo = round(larg * 0.13)
        self.h = self.topo + self.mh + round(larg * 0.62)
        self.raio = round(larg * 0.05)
        self.musica, self.artista = p.get("musica", "Música"), p.get("artista", "Artista")
        self.total = p.get("duracao", 200); self.pos0 = p.get("pos", 35)
        self.fundo = hexrgb(p.get("cor_fundo", "#121212"))
        self.verde = hexrgb(p.get("cor_destaque", "#1ED760"))
        self.s = 3
        self.base = self._desenha()

    def _desenha(self):
        s, w = self.s, self.w
        W, H = w * s, self.h * s
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        topo_cor = tuple(min(255, c + 34) for c in self.fundo)
        d.rounded_rectangle([0, 0, W - 1, H - 1], self.raio * s, fill=self.fundo + (255,))
        # leve degradê no topo, como a cor da capa vazando
        for i in range(int(H * 0.45)):
            a = 1 - i / (H * 0.45)
            c = tuple(int(self.fundo[k] * (1 - a) + topo_cor[k] * a) for k in range(3))
            d.line([(self.raio * s * (1 if i < self.raio * s else 0), i), (W - 1 - self.raio * s * (1 if i < self.raio * s else 0), i)], fill=c)
        branco, cinza = (255, 255, 255), (179, 179, 179)
        u = w * s
        # topo: seta, "TOCANDO AGORA", três pontos
        y = self.topo * s * 0.5; lw = max(2, round(u * 0.008))
        x = self.pad * s
        d.line([(x, y - u * 0.012), (x + u * 0.02, y + u * 0.01), (x + u * 0.04, y - u * 0.012)], fill=branco, width=lw)
        f = fonte(round(u * 0.032), True)
        txt = "TOCANDO AGORA"; tw = d.textlength(txt, font=f)
        d.text(((W - tw) / 2, y - u * 0.02), txt, font=f, fill=branco)
        for k in range(3):
            cx = W - self.pad * s - u * 0.012 - k * u * 0.022
            d.ellipse([cx - u * 0.006, y - u * 0.006, cx + u * 0.006, y + u * 0.006], fill=branco)
        # textos
        y = (self.topo + self.mh) * s + u * 0.07
        ft = fonte(round(u * 0.068), True); fa = fonte(round(u * 0.048))
        titulo = self.musica
        while d.textlength(titulo, font=ft) > u * 0.70 and len(titulo) > 4:
            titulo = titulo[:-2].rstrip() + "…" if not titulo.endswith("…") else titulo[:-2] + "…"
        d.text((self.pad * s, y), titulo, font=ft, fill=branco)
        d.text((self.pad * s, y + u * 0.09), self.artista, font=fa, fill=cinza)
        # coração verde cheio à direita
        cx, cy, r = W - self.pad * s - u * 0.04, y + u * 0.065, u * 0.022
        d.ellipse([cx - 2 * r, cy - 1.6 * r, cx, cy + 0.4 * r], fill=self.verde)
        d.ellipse([cx, cy - 1.6 * r, cx + 2 * r, cy + 0.4 * r], fill=self.verde)
        d.polygon([(cx - 1.95 * r, cy - 0.3 * r), (cx + 1.95 * r, cy - 0.3 * r), (cx, cy + 1.9 * r)], fill=self.verde)
        self.y_barra = y + u * 0.21
        # controles
        cy = self.y_barra + u * 0.20; cx = W / 2; R = u * 0.085
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=branco)
        bw, bh = R * 0.18, R * 0.75
        d.rectangle([cx - R * 0.28 - bw / 2, cy - bh / 2, cx - R * 0.28 + bw / 2, cy + bh / 2], fill=self.fundo)
        d.rectangle([cx + R * 0.28 - bw / 2, cy - bh / 2, cx + R * 0.28 + bw / 2, cy + bh / 2], fill=self.fundo)
        for sg in (-1, 1):  # anterior / próxima
            x0 = cx + sg * u * 0.22; t = u * 0.035
            d.polygon([(x0 - sg * t, cy - t), (x0 - sg * t, cy + t), (x0 + sg * t * 0.6, cy)], fill=branco)
            d.rectangle([x0 + sg * t * 0.6 - (lw if sg > 0 else 0), cy - t, x0 + sg * t * 0.6 + (lw if sg < 0 else 0), cy + t], fill=branco)
        # aleatório (verde, com pontinho) e repetir
        x0 = self.pad * s + u * 0.02; t = u * 0.028
        d.line([(x0 - t, cy - t * 0.7), (x0 + t, cy + t * 0.7)], fill=self.verde, width=lw)
        d.line([(x0 - t, cy + t * 0.7), (x0 + t, cy - t * 0.7)], fill=self.verde, width=lw)
        d.ellipse([x0 - lw, cy + t * 1.4, x0 + lw, cy + t * 1.4 + 2 * lw], fill=self.verde)
        x0 = W - self.pad * s - u * 0.02
        d.rounded_rectangle([x0 - t, cy - t * 0.7, x0 + t, cy + t * 0.7], radius=t * 0.5, outline=branco, width=lw)
        self.cinza = cinza
        return im

    def com(self, midia, t=0.0):
        s, u = self.s, self.w * self.s
        im = self.base.copy(); d = ImageDraw.Draw(im)
        x0, x1, y = self.pad * s, im.width - self.pad * s, self.y_barra
        lw = max(3, round(u * 0.011))
        pos = (self.pos0 + t) % self.total
        xp = x0 + (x1 - x0) * pos / self.total
        d.line([(x0, y), (x1, y)], fill=(77, 77, 77), width=lw)
        d.line([(x0, y), (xp, y)], fill=(255, 255, 255), width=lw)
        d.ellipse([xp - lw * 1.6, y - lw * 1.6, xp + lw * 1.6, y + lw * 1.6], fill=(255, 255, 255))
        f = fonte(round(u * 0.03))
        mm = lambda v: f"{int(v) // 60}:{int(v) % 60:02d}"
        d.text((x0, y + u * 0.03), mm(pos), font=f, fill=self.cinza)
        rest = mm(self.total); d.text((x1 - d.textlength(rest, font=f), y + u * 0.03), rest, font=f, fill=self.cinza)
        im = im.resize((self.w, self.h), Image.LANCZOS)
        cap = midia.copy()
        mk = Image.new("L", cap.size, 0)
        ImageDraw.Draw(mk).rounded_rectangle([0, 0, cap.width - 1, cap.height - 1], round(self.w * 0.015), fill=255)
        im.paste(cap, (self.pad, self.topo), mk)
        return im


def cobre(im, w, h, foco=(0.5, 0.5)):
    sw, sh = im.size
    k = max(w / sw, h / sh)
    nw, nh = max(w, round(sw * k)), max(h, round(sh * k))
    im = im.resize((nw, nh), Image.BICUBIC)
    x0 = round((nw - w) * foco[0]); y0 = round((nh - h) * foco[1])
    return im.crop((x0, y0, x0 + w, y0 + h))


class Midia:
    """Foto ou vídeo para dentro do post. Vídeo pode começar em "de" e ter "velocidade"."""

    def __init__(self, path, w, h, fps, de=0.0, vel=1.0, foco=(0.5, 0.5)):
        self.w, self.h, self.fps = w, h, fps
        self.video = path.lower().endswith(VIDEO)
        if not self.video:
            self.img = cobre(Image.open(path).convert("RGB"), w, h, foco); return
        vw, vh, _, _ = probe(path)
        k = max(w / vw, h / vh)
        sw, sh = math.ceil(vw * k / 2) * 2, math.ceil(vh * k / 2) * 2
        x0, y0 = round((sw - w) * foco[0]), round((sh - h) * foco[1])
        vf = f"setpts=PTS/{vel},fps={fps},scale={sw}:{sh}:flags=bicubic,crop={w}:{h}:{x0}:{y0}"
        self.cmd = ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-ss", str(de), "-i", path, "-an", "-vf", vf,
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = None; self.last = None

    def quadro(self):
        if not self.video:
            return self.img
        if self.proc is None:
            self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
        buf = self.proc.stdout.read(self.w * self.h * 3)
        if len(buf) == self.w * self.h * 3:
            self.last = Image.frombuffer("RGB", (self.w, self.h), buf, "raw", "RGB", 0, 1)
        return self.last

    def fecha(self):
        if self.video and self.proc:
            self.proc.kill()


# ---------------------------------------------------------------- geometria 3D
def quad3d(w, h, cx, cy, rx, ry, rz, esc, f, W, H, dz=0.0):
    """Cantos (A B C D) de um cartão w×h girado em 3D e projetado; centro na tela em (cx, cy)."""
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    out = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x, y = x * esc, y * esc
        x, y = x * math.cos(c) - y * math.sin(c), x * math.sin(c) + y * math.cos(c)  # rz no plano
        x, z = x * math.cos(b), -x * math.sin(b)                                     # ry (Flip horizontal)
        y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)  # rx (Flip vertical)
        k = f / (f + z + dz)
        out.append((cx + x * k, cy + y * k))
    return np.array(out)


def gira(card, q, W, H):
    """Entorta o cartão (RGBA) para o quadrilátero q. Devolve (imagem do recorte, x0, y0)."""
    x0, y0 = np.floor(q.min(0)).astype(int) - 2
    x1, y1 = np.ceil(q.max(0)).astype(int) + 2
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None, 0, 0
    cw, ch = card.size
    src = np.array([[1, 1], [cw - 1, 1], [cw - 1, ch - 1], [1, ch - 1]], float)  # 1 px de borda vazia
    coef = homografia(q - [x0, y0], src)
    out = card.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)
    return out, x0, y0


# ---------------------------------------------------------------- cenário e luz
def estudio(W, H, chao, cfg):
    """Fundo infinito branco: parede, curva macia e chão levemente brilhante."""
    parede = np.array(hexrgb(cfg.get("cor_parede", "#E9E8E6")), float) / 255
    piso = np.array(hexrgb(cfg.get("cor_chao", "#F3F2F0")), float) / 255
    y = np.arange(H, dtype=float)[:, None] / H
    hz = chao / H
    curva = 0.05
    m = np.clip((y - (hz - curva)) / (2 * curva), 0, 1)
    m = m * m * (3 - 2 * m)
    topo = 1.0 + 0.035 * (1 - y / max(hz, 1e-3))  # mais claro em cima
    sombra_quina = 1 - 0.06 * np.exp(-((y - hz) / 0.025) ** 2)  # quina suave no encontro
    fundo = (parede * topo * (1 - m) + piso * (1 - 0.05 * np.clip((y - hz) / (1 - hz + 1e-6), 0, 1)) * m)
    fundo = fundo * sombra_quina
    x = np.arange(W, dtype=float)[None, :] / W
    lados = 1 - 0.05 * ((x - 0.5) * 2) ** 2  # só um respiro nas bordas, nada de vinheta escura
    fundo = fundo[:, None, :] if fundo.ndim == 2 else fundo
    img = np.clip(np.broadcast_to(fundo, (H, 1, 3)) * lados[..., None], 0, 1)
    return np.broadcast_to(img, (H, W, 3)).copy()


class Luzes:
    """Manchas de luz colorida que passeiam devagar (o efeito de luzes do vídeo de referência)."""

    def __init__(self, W, H, cfg, seed=7):
        self.W, self.H = W, H
        self.k = cfg.get("intensidade", 0.45)
        cores = cfg.get("cores", ["#FF7AD9", "#7AD7FF", "#FFE45C", "#B28CFF", "#7CFFB2"])
        rng = np.random.default_rng(seed)
        self.blobs = []
        for i, c in enumerate(cores):
            self.blobs.append(dict(c=np.array(hexrgb(c), float) / 255,
                                   x=rng.uniform(0.05, 0.95), y=rng.uniform(0.1, 0.95),
                                   r=rng.uniform(0.16, 0.26), fx=rng.uniform(0.03, 0.08), fy=rng.uniform(0.03, 0.07),
                                   px=rng.uniform(0, 6.28), py=rng.uniform(0, 6.28)))
        self.s = 8
        gy, gx = np.mgrid[0:H // self.s, 0:W // self.s]
        self.gx, self.gy = gx / (W / self.s), gy / (H / self.s) * (H / W)

    def mapa(self, t):
        acc = np.zeros(self.gx.shape + (3,)); a = np.zeros(self.gx.shape)
        for b in self.blobs:
            cx = b["x"] + 0.18 * math.sin(2 * math.pi * b["fx"] * t + b["px"])
            cy = (b["y"] + 0.12 * math.sin(2 * math.pi * b["fy"] * t + b["py"])) * self.H / self.W
            g = np.exp(-((self.gx - cx) ** 2 + (self.gy - cy) ** 2) / (2 * b["r"] ** 2 * 0.35))
            acc += g[..., None] * b["c"]; a += g
        cor = acc / np.maximum(a, 1e-6)[..., None]
        a = np.clip(a, 0, 1) * self.k
        im = Image.fromarray((np.dstack([cor, a[..., None]]) * 255).astype(np.uint8), "RGBA")
        im = im.resize((self.W, self.H), Image.BILINEAR)
        arr = np.asarray(im, float) / 255
        return arr[..., :3], arr[..., 3:4]


def tinge(img, cor, a):
    """Luz colorida sobre superfície clara: tinge sem escurecer (um pouco de soma, um pouco de multiplicação)."""
    tingido = np.clip(img * (0.55 + 0.55 * cor) + 0.10 * cor, 0, 1)
    return img * (1 - a) + tingido * a


# ---------------------------------------------------------------- layout automático
SLOTS = [  # x, y (fração da tela), largura (fração), rx, ry, rz — composição do vídeo de referência
    (0.24, 0.14, 0.36, 4, 24, -5),
    (0.80, 0.15, 0.40, 4, -24, 4),
    (0.17, 0.40, 0.30, 0, 30, 3),
    (0.85, 0.42, 0.36, 0, -28, -3),
    (0.20, 0.64, 0.34, -4, 28, -6),
    (0.82, 0.67, 0.30, -4, -26, 5),
    (0.52, 0.09, 0.30, 12, 0, 2),
    (0.68, 0.80, 0.22, -6, -20, -3),
    (0.33, 0.83, 0.22, -6, 20, 4),
]


def gestos(masks, fps, n):
    """Momentos em que a pessoa abre os braços/se mexe: picos de aumento da largura do recorte."""
    larg = []
    for p in masks:
        m = np.asarray(Image.open(p).convert("L").reduce(8)) > 128
        cols = np.where(m.any(0))[0]
        larg.append(cols[-1] - cols[0] if len(cols) else 0)
    larg = np.convolve(np.array(larg, float), np.ones(5) / 5, "same")
    d = np.gradient(larg)
    picos = [i for i in range(2, len(d) - 2) if d[i] > 0 and d[i] == d[max(0, i - 8):i + 9].max()]
    picos.sort(key=lambda i: -d[i])
    escolhidos = []
    for i in picos:
        if all(abs(i - j) > fps * 0.35 for j in escolhidos):
            escolhidos.append(i)
        if len(escolhidos) >= n:
            break
    return sorted(i / fps for i in escolhidos)


# ---------------------------------------------------------------- som
SR = 48000


def sfx(eventos, dur, seed=3):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(dur * SR) + SR)

    def whoosh(d=0.42):
        n = int(d * SR); t = np.arange(n) / SR; x = rng.normal(0, 1, n)
        y = np.zeros(n); a = 0.0; kk = 0.02 + 0.28 * np.sin(np.pi * t / d) ** 2
        for i in range(n):
            a += kk[i] * (x[i] - a); y[i] = a
        return 1.2 * y * np.sin(np.pi * t / d) ** 1.6

    def pop(f0):
        n = int(0.14 * SR); t = np.arange(n) / SR; f = f0 * (1 + 1.6 * (1 - np.exp(-t * 40)))
        e = np.minimum(t / 0.002, 1) * np.exp(-t * 30)
        return 0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * e

    for k, (t, chega) in enumerate(eventos):
        w = whoosh(); i = max(0, int((t - 0.05) * SR)); out[i:i + len(w)] += 0.5 * w[:len(out) - i]
        p = pop([560, 470, 640, 420][k % 4]); i = int(chega * SR); out[i:i + len(p)] += 0.45 * p[:len(out) - i]
    out = out[:int(dur * SR)]
    pk = np.abs(out).max()
    return out / pk * 0.6 if pk > 0 else out


# ---------------------------------------------------------------- principal
def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cfg_path = os.path.abspath(sys.argv[1])
    raiz = os.path.dirname(cfg_path)
    rel = lambda p: p if os.path.isabs(p) else os.path.join(raiz, p)
    cfg = json.load(open(cfg_path))
    args = sys.argv[2:]
    ver = [float(v) for v in args[args.index("--ver") + 1:]] if "--ver" in args else None
    rascunho = "--rascunho" in args

    base = rel(cfg["base"])
    W0, H0, fps, dur = probe(base)
    masks = sorted(glob.glob(os.path.join(rel(cfg.get("mascara", "mask")), "*.png")))
    if not masks:
        sys.exit("faltou a pasta de máscaras (rode o seg.swift)")
    posts = cfg["posts"]

    if "--gestos" in args:
        ts = gestos(masks, fps, len(posts))
        print("tempos sugeridos (s):", ", ".join(f"{t:.2f}" for t in ts))
        return

    esc = 0.5 if rascunho else 1.0
    W, H = int(W0 * esc) // 2 * 2, int(H0 * esc) // 2 * 2
    f = cfg.get("focal", 1.3) * H

    # pessoa: posição/escala no quadro novo
    pc = cfg.get("pessoa", {})
    p_esc = pc.get("escala", 1.0)
    p_dx, p_dy = pc.get("x", 0) * esc, pc.get("y", 0) * esc
    fundo_tipo = cfg.get("fundo", "estudio")
    original = fundo_tipo == "original"
    if original:
        p_esc, p_dx, p_dy = 1.0, 0, 0

    # pés: linha mais baixa do recorte (na amostra), já transformada
    amostra = masks[::max(1, len(masks) // 40)]
    fundos_pes = []
    for p in amostra:
        m = np.asarray(Image.open(p).convert("L").reduce(4)) > 128
        rows = np.where(m.any(1))[0]
        if len(rows): fundos_pes.append(rows[-1] * 4)
    pe0 = np.percentile(fundos_pes, 90) if fundos_pes else H0
    corta_embaixo = pe0 > H0 - 12
    pe = ((pe0 - H0 / 2) * p_esc + H0 / 2) * esc + p_dy
    chao = cfg.get("chao", (pe / H) if not corta_embaixo else 0.80) * H if isinstance(cfg.get("chao", None), (int, float)) else (pe if not corta_embaixo else 0.80 * H)
    reflexo = cfg.get("reflexo", True) and not original and not corta_embaixo

    if original:
        cenario = None
    elif fundo_tipo == "estudio":
        cenario = estudio(W, H, chao, cfg.get("estudio", {}))
    else:
        cenario = np.asarray(cobre(Image.open(rel(fundo_tipo)).convert("RGB"), W, H), float) / 255

    luz_cfg = cfg.get("luzes", {})
    luzes = Luzes(W, H, luz_cfg) if luz_cfg is not False and luz_cfg.get("ativo", True) else None

    # posts: tempos, lugares, mídias
    mold_cfg = cfg.get("moldura", {})
    sem_tempo = [i for i, p in enumerate(posts) if "entra" not in p]
    auto = []
    if sem_tempo:
        modo = cfg.get("tempos", "gestos")
        if modo == "gestos":
            auto = gestos(masks, fps, len(sem_tempo))
        if len(auto) < len(sem_tempo):
            ini, passo = cfg.get("primeiro", 0.6), cfg.get("intervalo", 0.45)
            auto = [ini + passo * k for k in range(len(sem_tempo))]
    cartoes = []
    for k, p in enumerate(posts):
        slot = SLOTS[k % len(SLOTS)]
        x = p.get("x", slot[0] * W0) * esc if "x" in p else slot[0] * W
        y = p.get("y", slot[1] * H0) * esc if "y" in p else slot[1] * H
        larg = round(p.get("largura", slot[2] * W0) * esc) if "largura" in p else round(slot[2] * W)
        rot = p.get("rot", list(slot[3:]))
        mold = Player(larg, p) if p.get("tipo") == "player" else Moldura(larg, mold_cfg)
        foco = tuple(p.get("foco", (0.5, 0.5)))
        media = Midia(rel(p["midia"]), mold.mw, mold.mh, fps, p.get("de", 0), p.get("velocidade", 1.0), foco)
        t0 = p["entra"] if "entra" in p else auto[sem_tempo.index(k)]
        lado = 1 if x < W / 2 else -1
        cartoes.append(dict(m=mold, media=media, x=x, y=y, rot=rot, t0=t0, lado=lado, sai=p.get("sai"),
                            anim=p.get("anim", cfg.get("anim", "flip")), fase=k * 1.37,
                            frente=p.get("frente", False)))
    cartoes.sort(key=lambda c: c["t0"])  # quem entra depois fica por cima
    anim_dur = cfg.get("duracao_entrada", 0.65)
    flutua = cfg.get("flutuar", 1.0)

    def pose(c, t):
        """Ângulos/escala/posição do cartão no tempo t; None se ainda não entrou."""
        dt = t - c["t0"]
        if dt < 0:
            return None
        rx, ry, rz = c["rot"]; x, y, s, op, dz = c["x"], c["y"], 1.0, 1.0, 0.0
        p = dt / anim_dur
        if c["anim"] == "flip":  # Alight Motion 3D Flip: começa de perfil e gira até o ângulo
            e = mola(p)
            ry = ry + (1 - e) * 88 * c["lado"]
            s = 0.75 + 0.25 * saida(p)
            op = min(1.0, p * 4)
        elif c["anim"] == "pop":
            e = mola(p); s = 0.2 + 0.8 * e; op = min(1.0, p * 5)
        elif c["anim"] == "cai":
            e = mola(p); y = y - (1 - e) * 0.5 * H; rz = rz + (1 - e) * 25 * c["lado"]; op = min(1.0, p * 5)
        elif c["anim"] == "vem":  # vem de trás (fundo) para a parede
            e = mola(p); dz = (1 - e) * 4 * f; op = min(1.0, p * 3)
        if flutua and dt > 0:  # "balanço de rebote" contínuo e suave
            w = 2 * math.pi * t / 4.5 + c["fase"]
            ry += 3.0 * flutua * math.sin(w); rx += 2.0 * flutua * math.sin(w * 0.8 + 1)
            rz += 0.8 * flutua * math.sin(w * 0.6 + 2); y += 6 * esc * flutua * math.sin(w * 0.9)
        if c["sai"] is not None and t > c["sai"]:
            q = (t - c["sai"]) / 0.35
            if q >= 1: return None
            s *= 1 - saida(q) * 0.8; op *= 1 - q
        return rx, ry, rz, x, y, s, op, dz

    def camada_posts(t, avanca=True, quais=None):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sombra = Image.new("L", (W, H), 0)
        for c in cartoes:
            fr = c["media"].quadro() if avanca and (t >= c["t0"] or c.get("ult") is None) else None
            if fr is not None: c["ult"] = fr
            if quais is not None and c["frente"] != quais:
                continue
            ps = pose(c, t)
            if ps is None or c.get("ult") is None:
                continue
            rx, ry, rz, x, y, s, op, dz = ps
            card = c["m"].com(c["ult"], t)
            q = quad3d(card.width, card.height, x, y, rx, ry, rz, s, f, W, H, dz)
            img, x0, y0 = gira(card, q, W, H)
            if img is None:
                continue
            if op < 1:
                a = img.getchannel("A").point(lambda v: int(v * op)); img.putalpha(a)
            sa = img.getchannel("A")
            off = round(22 * esc)
            sombra.paste(sa, (x0 + off, y0 + round(off * 1.4)), sa)
            lay.alpha_composite(img, (x0, y0))
        return lay, sombra

    # som
    eventos = [(c["t0"], c["t0"] + anim_dur * 0.55) for c in cartoes if c["t0"] < dur]
    pasta = os.path.splitext(rel(cfg.get("saida", "posts-3d.mp4")))[0]

    # ------------------------------------------------ quadro a quadro
    def compoe(fr_base, mask, t, avanca=True):
        """Devolve (quadro final RGB uint8, camada de posts RGBA)."""
        pessoa = Image.fromarray(fr_base).resize((W, H), Image.BICUBIC) if esc != 1 else Image.fromarray(fr_base)
        m = mask.resize((W, H), Image.BILINEAR) if mask.size != (W, H) else mask
        if not original and (p_esc != 1 or p_dx or p_dy):
            nw, nh = round(W * p_esc), round(H * p_esc)
            ox, oy = round((W - nw) / 2 + p_dx), round((H - nh) / 2 + p_dy)
            pc_img = Image.new("RGB", (W, H)); pc_img.paste(pessoa.resize((nw, nh), Image.BICUBIC), (ox, oy)); pessoa = pc_img
            pm = Image.new("L", (W, H), 0); pm.paste(m.resize((nw, nh), Image.BILINEAR), (ox, oy)); m = pm
        m = m.filter(ImageFilter.GaussianBlur(1.2 * esc + 0.4))
        ma = np.asarray(m, float)[..., None] / 255
        pa = np.asarray(pessoa, float) / 255

        fundo = (pa.copy() if original else cenario.copy())
        if reflexo:  # a pessoa espelhada no chão brilhante, sumindo para baixo
            linha = int(chao)
            alt = H - linha
            if alt > 4:
                ref = pa[linha - alt:linha][::-1] if linha - alt >= 0 else None
                rm = ma[linha - alt:linha][::-1] if linha - alt >= 0 else None
                if ref is not None:
                    g = np.linspace(0.32, 0, alt)[:, None, None] ** 1.2
                    a = rm * g
                    fundo[linha:] = fundo[linha:] * (1 - a) + ref * a
            # sombra de contato nos pés
            cols = np.where(ma[min(linha - 2, H - 1), :, 0] > 0.5)[0]
            if len(cols):
                yy, xx = np.mgrid[0:H, 0:W]
                cx = cols.mean(); rx_ = max(40 * esc, (cols[-1] - cols[0]) * 0.8)
                d = ((xx - cx) / rx_) ** 2 + ((yy - linha) / (14 * esc)) ** 2
                fundo *= 1 - 0.18 * np.exp(-d)[..., None]

        lay, sombra = camada_posts(t, avanca, quais=False)
        sb = sombra.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BILINEAR)
        sa = np.asarray(sb, float)[..., None] / 255 * cfg.get("sombra", 0.16)
        if not original:
            fundo = fundo * (1 - sa)
        la = np.asarray(lay, float) / 255
        fundo = fundo * (1 - la[..., 3:]) + la[..., :3] * la[..., 3:]

        if luzes is not None:
            cor, a = luzes.mapa(t)
            fundo = tinge(fundo, cor, a)
            pa_l = tinge(pa, cor, a * 0.25)  # um pouquinho na pessoa, para ela estar "no" lugar
        else:
            pa_l = pa
        out = fundo * (1 - ma) + pa_l * ma

        frente, _ = camada_posts(t, False, quais=True)  # posts marcados "frente": passam na frente dela
        fa = np.asarray(frente, float) / 255
        if fa[..., 3].any():
            out = out * (1 - fa[..., 3:]) + fa[..., :3] * fa[..., 3:]
            lay.alpha_composite(frente)
        return (np.clip(out, 0, 1) * 255).astype(np.uint8), lay

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", base, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    total = min(int(round(dur * fps)), len(masks))

    if ver:
        alvo = sorted(set(min(total - 1, int(round(v * fps))) for v in ver))
        i = 0
        while alvo:
            buf = dec.stdout.read(W0 * H0 * 3)
            if len(buf) < W0 * H0 * 3: break
            t = i / fps
            if i == alvo[0]:
                fr = np.frombuffer(buf, np.uint8).reshape(H0, W0, 3)
                img, _ = compoe(fr, Image.open(masks[i]).convert("L"), t)
                nome = f"{pasta}_{t:05.2f}.jpg"
                Image.fromarray(img).save(nome, quality=90); print(nome)
                alvo.pop(0)
            else:
                for c in cartoes:
                    if t >= c["t0"] or c.get("ult") is None:
                        c["ult"] = c["media"].quadro() or c.get("ult")
            i += 1
        dec.kill(); [c["media"].fecha() for c in cartoes]
        return

    tmp = pasta + "_video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                            "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    lay_enc = None
    if not rascunho:
        lay_enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                                    "-r", str(fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                                    "-pix_fmt", "yuva444p10le", pasta + "-camada-posts.mov"], stdin=subprocess.PIPE)
    for i in range(total):
        buf = dec.stdout.read(W0 * H0 * 3)
        if len(buf) < W0 * H0 * 3: break
        fr = np.frombuffer(buf, np.uint8).reshape(H0, W0, 3)
        img, lay = compoe(fr, Image.open(masks[i]).convert("L"), i / fps)
        enc.stdin.write(img.tobytes())
        if lay_enc: lay_enc.stdin.write(lay.tobytes())
        if i % int(fps * 5) == 0:
            print(f"  {i / fps:5.1f}s / {total / fps:.1f}s", flush=True)
    enc.stdin.close(); enc.wait()
    if lay_enc: lay_enc.stdin.close(); lay_enc.wait()
    dec.kill(); [c["media"].fecha() for c in cartoes]

    # som: voz original + whoosh/pop em cada entrada (+ trilha opcional)
    efeitos = sfx(eventos, total / fps)
    wav = pasta + "-sfx.wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((efeitos * 32767).astype(np.int16).tobytes())
    final = rel(cfg.get("saida", "posts-3d.mp4"))
    ent = ["-i", tmp, "-i", wav]; mix = []; n = 1
    if tem_audio(base):
        ent += ["-i", base]; n += 1; mix.append(f"[{n}:a]volume=1.0[v]")
    trilha = cfg.get("trilha")
    if trilha:
        ent += ["-ss", str(cfg.get("trilha_de", 0)), "-i", rel(trilha)]; n += 1
        vol = cfg.get("trilha_volume", 0.25)
        if tem_audio(base):  # trilha abaixa quando a pessoa fala
            mix = [f"[2:a]asplit=2[v][sc]", f"[{n}:a]volume={vol}[tr]",
                   "[tr][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[trd]"]
        else:
            mix.append(f"[{n}:a]volume={vol}[trd]")
    labels = ["[1:a]"] + (["[v]"] if tem_audio(base) else []) + (["[trd]"] if trilha else [])
    filtro = ";".join(mix + [f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[a]"])
    cor = cfg.get("cor")
    vf = []
    if cor == "rico":  # look "rico e claro": brancos neutros, pretos firmes, saturação alta
        vf = ["-vf", "curves=all='0/0 0.12/0.06 0.5/0.47 0.85/0.88 1/1',eq=saturation=1.25"]
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", filtro, "-map", "0:v", "-map", "[a]"]
                   + vf + (["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p"] if vf else ["-c:v", "copy"])
                   + ["-c:a", "aac", "-b:a", "192k", "-shortest", final], check=True)
    os.remove(tmp)
    print("pronto:", final)
    if lay_enc: print("camada dos posts (alpha, para o CapCut):", pasta + "-camada-posts.mov")
    print("efeitos sonoros:", wav)


if __name__ == "__main__":
    main()
