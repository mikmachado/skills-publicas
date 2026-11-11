"""Tinta preta brilhante escorrendo da borda de baixo do recorte (escorridos, bulbos, brilho e pingos caindo)."""
import numpy as np
from PIL import Image, ImageFilter

TINTA = np.array([0.045, 0.045, 0.05], np.float32)


def suaviza1d(v, k):
    ker = np.ones(k) / k
    return np.convolve(np.pad(v, k // 2, mode="edge"), ker, "valid")[: len(v)]


class Tinta:
    def __init__(self, escala=1.0, seed=7, n=13, comprimento=1.0):
        """escala: tamanho da pessoa na gravação (1 = rosto com ~590 px de largura num quadro 1080x1920)."""
        rng = np.random.default_rng(seed)
        us = np.linspace(0.04, 0.96, n) + rng.uniform(-0.015, 0.015, n)
        self.e = escala
        self.gotas = []
        for i, u in enumerate(us):
            w = rng.choice([rng.uniform(26, 40), rng.uniform(42, 70)], p=[0.55, 0.45]) * escala
            lmax = rng.choice([rng.uniform(90, 200), rng.uniform(220, 380), rng.uniform(400, 600)], p=[0.3, 0.4, 0.3]) * escala * comprimento
            self.gotas.append(dict(u=float(u), w=float(w), L=float(lmax), ph=rng.uniform(0, 6.28),
                                   vel=rng.uniform(0.25, 0.6), atraso=rng.uniform(0, 0.35),
                                   pinga=rng.uniform(1.6, 4.5), fase_p=rng.uniform(0, 4)))

    def perfil(self, al):
        """y da borda de baixo do recorte por coluna (nan sem recorte)"""
        H, W = al.shape
        m = al > 0.5
        tem = m.any(0)
        idx = H - 1 - np.argmax(m[::-1], axis=0)
        b = np.where(tem, idx, np.nan).astype(np.float64)
        ok = ~np.isnan(b)
        if ok.sum() < 10: return b
        bi = np.interp(np.arange(W), np.flatnonzero(ok), b[ok])
        bs = suaviza1d(bi, 31)
        return np.where(ok, bs, np.nan)

    def aplica(self, rgb, al, t, cresce=1.0, H_out=2700):
        """rgb HxWx3 float, al HxW -> (rgb2, al2) com altura H_out e a tinta."""
        H, W = al.shape
        b = self.perfil(al)
        out_rgb = np.zeros((H_out, W, 3), np.float32); out_al = np.zeros((H_out, W), np.float32)
        out_rgb[:H] = rgb; out_al[:H] = al
        ok = ~np.isnan(b)
        if ok.sum() < 10 or cresce <= 0.001: return out_rgb, out_al, np.zeros((H_out, W), np.float32)
        cols = np.flatnonzero(ok)
        xa, xb = cols.min(), cols.max()
        bb = np.where(ok, b, 0)
        # 1) escurece a parte de baixo do busto (vira tinta)
        D = 150 * self.e * min(1, cresce * 1.2)
        yy = np.arange(H, dtype=np.float32)[:, None]
        k = np.clip((yy - (bb[None, :] - D)) / max(D, 1), 0, 1) ** 1.4 * ok[None, :]
        k = k * 0.92
        out_rgb[:H] = rgb * (1 - k[..., None]) + TINTA * k[..., None]
        # 2) borda líquida + escorridos (forma)
        ink = np.zeros((H_out, W), np.float32)
        hl = np.zeros((H_out, W), np.float32)
        xs = np.arange(W, dtype=np.float32)
        lip = (10 + 9 * np.sin(xs / 41 + 1.3) + 6 * np.sin(xs / 17 + t * 0.8)) * min(1, cresce * 2) * self.e
        y_lip = (bb + lip).astype(np.float32)
        Y = np.arange(H_out, dtype=np.float32)[:, None]
        lipm = np.clip(y_lip[None, :] - Y + 0.5, 0, 1) * np.clip(Y - (bb[None, :] - 30), 0, 1) * ok[None, :]
        ink = np.maximum(ink, lipm)
        for g in self.gotas:
            x = xa + g["u"] * (xb - xa)
            if x < xa + 8 or x > xb - 8 or np.isnan(b[int(round(x))]): continue
            xi = int(round(x))
            y0 = float(b[xi]) - 6
            prog = np.clip((cresce - g["atraso"]) / (1 - g["atraso"] + 1e-6), 0, None)
            L = g["L"] * prog ** 0.8 * (0.9 + 0.1 * np.sin(t * g["vel"] + g["ph"]))
            if L < 4: continue
            w = g["w"]
            r = w * 0.66
            x0_, x1_ = int(x - w * 1.6), int(x + w * 1.6) + 1
            ya, yb = int(y0 - 10), int(min(H_out - 1, y0 + L + r * 1.2)) + 1
            if yb <= ya: continue
            YY = np.arange(ya, yb, dtype=np.float32)[:, None]
            XX = np.arange(x0_, x1_, dtype=np.float32)[None, :]
            dy = YY - y0
            # meia-largura: alarga no topo (junção), afina e fica constante
            hw = w / 2 * (1 + 1.1 * np.exp(-np.clip(dy, 0, None) / 34)) * (0.78 + 0.22 * np.clip(1 - dy / (L + 1), 0, 1)) * (1 + 0.14 * np.sin(dy / 47 + g['ph'] + t * 0.6))
            dx = np.abs(XX - x)
            corpo = np.clip(hw - dx + 0.5, 0, 1) * (dy <= L - r * 0.4) * (dy >= -10)
            cy = y0 + L - r * 0.2
            bulbo = np.clip(r - np.sqrt((XX - x) ** 2 + (YY - cy) ** 2) + 0.5, 0, 1)
            sh = np.maximum(corpo, bulbo)
            sl = (slice(ya, yb), slice(max(0, x0_), min(W, x1_)))
            cx0 = max(0, x0_) - x0_; cx1 = cx0 + (sl[1].stop - sl[1].start)
            ink[sl] = np.maximum(ink[sl], sh[:, cx0:cx1])
            # brilho: faixa à esquerda + ponto no bulbo
            fx = x - w * 0.22
            faixa = np.clip(w * 0.09 - np.abs(XX - fx), 0, 1) * np.clip((dy - 12) / 30, 0, 1) * (dy < L - r) * (0.55 + 0.35 * np.sin(dy / 23 + g['ph']) ** 2)
            faixa = np.maximum(faixa, np.clip(w * 0.05 - np.abs(XX - (x + w * 0.3)), 0, 1) * (dy > 20) * (dy < L - r) * 0.22)
            ponto = np.clip(r * 0.22 - np.sqrt((XX - (x - r * 0.3)) ** 2 + (YY - (cy - r * 0.35)) ** 2), 0, 1) * 0.9
            hl[sl] = np.maximum(hl[sl], np.maximum(faixa, ponto)[:, cx0:cx1])
            # pingo caindo
            per = g["pinga"]
            ph = ((t + g["fase_p"]) % per) / per
            if prog > 0.6 and ph < 0.45:
                q = ph / 0.45
                py = cy + r + 20 + 900 * self.e * q ** 2
                pr = r * 0.55
                if py < H_out - 5:
                    a0, a1 = int(py - pr - 2), int(py + pr * 1.4 + 2)
                    YY2 = np.arange(a0, a1, dtype=np.float32)[:, None]
                    XX2 = np.arange(int(x - pr - 2), int(x + pr + 3), dtype=np.float32)[None, :]
                    e = np.sqrt(((XX2 - x) / pr) ** 2 + ((YY2 - py) / (pr * (1.25 if True else 1))) ** 2)
                    d = np.clip((1 - e) * pr + 0.5, 0, 1) * (1 - max(0, q - 0.8) / 0.2)
                    s2 = (slice(max(0, a0), min(H_out, a1)), slice(int(x - pr - 2), int(x + pr + 3)))
                    d = d[s2[0].start - a0: s2[0].start - a0 + (s2[0].stop - s2[0].start)]
                    ink[s2] = np.maximum(ink[s2], d)
                    hp = np.clip(pr * 0.3 - np.sqrt((XX2 - (x - pr * 0.35)) ** 2 + (YY2 - (py - pr * 0.4)) ** 2), 0, 1)
                    hp = hp[s2[0].start - a0: s2[0].start - a0 + (s2[0].stop - s2[0].start)]
                    hl[s2] = np.maximum(hl[s2], hp * 0.9)
        # suaviza a forma (líquido)
        im = Image.fromarray((ink * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))
        ink = np.clip((np.asarray(im).astype(np.float32) / 255 - 0.5) * 3 + 0.5, 0, 1)
        hl = np.asarray(Image.fromarray((hl * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 255
        hl = hl * ink
        # borda clara à direita (reflexo do ambiente)
        cor = TINTA + hl[..., None] * (np.array([0.95, 0.95, 0.97]) - TINTA)
        nova = ink * (1 - out_al)
        out_rgb = out_rgb * out_al[..., None] + cor * nova[..., None]
        a2 = np.clip(out_al + nova, 0, 1)
        out_rgb = out_rgb / np.maximum(a2, 1e-4)[..., None]
        return out_rgb, a2, ink
