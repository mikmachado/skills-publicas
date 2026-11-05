#!/usr/bin/env python3
"""Desenha a "parede plana" animada: tudo que vai aparecer na parede, reto, sobre branco,
no tempo da fala. Depois o perspectiva.py cola essa textura na parede (modo multiplicar).

Tudo vem de um arquivo de configuração (veja exemplos/projeto.json):
  - parede: ponto de fuga, focal e o retângulo útil da parede em (Z profundidade, Y altura);
  - telas: a legenda frase a frase (fontes e tamanhos misturados), um feed de posts subindo,
    prints que aparecem quando uma palavra é dita.

  python3 parede.py projeto.json               → parede.mp4 + imprime os 4 cantos para o perspectiva.py
  python3 parede.py projeto.json --cantos      → só imprime os cantos (para conferir com grade.py)
  python3 parede.py projeto.json --ver 9.7 22  → só salva quadros de teste (parede_09.70.jpg …)

Geometria da parede lateral (câmera nivelada): um ponto (Z, Y) da parede vai para
  x = vpx ∓ focal/Z   (− parede à esquerda, + à direita)     y = vpy + focal·Y/Z
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageOps, ImageFont

FPS = 30
AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------- fontes (macOS; troque em "fontes" no projeto.json) ----------
SYS = "/System/Library/Fonts"
FONTES = {
    "l": [f"{SYS}/Avenir Next.ttc", 5, 112],      # texto corrido
    "L": [f"{SYS}/Avenir Next.ttc", 5, 150],      # texto corrido maior
    "h": [f"{SYS}/Avenir Next Condensed.ttc", 8, 200],   # palavra-chave
    "H": [f"{SYS}/Avenir Next Condensed.ttc", 8, 330],   # palavra-chave gigante (use caixa alta)
    "s": [f"{SYS}/Supplemental/Didot.ttc", 1, 190],      # itálico serifado (palavra emotiva)
    "S": [f"{SYS}/Supplemental/Didot.ttc", 1, 280],
    "m": [f"{SYS}/Supplemental/Bradley Hand Bold.ttf", 0, 160],  # letra de mão (fechos)
    "M": [f"{SYS}/Supplemental/Bradley Hand Bold.ttf", 0, 260],
}
CORES = {"": "#1E1B19", "t": "#C4543A", "p": "#186872", "m": "#DEA026"}


def hexcor(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def carrega(path):
    cfg = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    cfg["_dir"] = base
    FONTES.update(cfg.get("fontes", {}))
    CORES.update(cfg.get("cores", {}))
    return cfg


def rel(cfg, p):
    return p if os.path.isabs(p) else os.path.join(cfg["_dir"], p)


def cantos(cfg):
    pa = cfg["parede"]
    vpx, vpy = pa["vp"]; f = pa["focal"]; z0, z1 = pa["z"]; y0, y1 = pa["y"]
    sx = -1 if pa.get("lado", "esquerda") == "esquerda" else 1
    P = lambda Z, Y: (round(vpx + sx * f / Z, 1), round(vpy + f * Y / Z, 1))
    if sx < 0:   # perto da câmera à esquerda da tela
        return [P(z0, y0), P(z1, y0), P(z1, y1), P(z0, y1)]
    return [P(z1, y0), P(z0, y0), P(z0, y1), P(z1, y1)]


def main():
    args = sys.argv[1:]
    cfg = carrega(args[0])
    cs = cantos(cfg)
    txt_cantos = " ".join(f"{x},{y}" for x, y in cs)
    if "--cantos" in args:
        print(txt_cantos); return
    prev = [float(a) for a in args[args.index("--ver") + 1:]] if "--ver" in args else []

    pa = cfg["parede"]; ppu = pa.get("px_por_unidade", 800)
    CW = int(round((pa["z"][1] - pa["z"][0]) * ppu)) // 2 * 2
    CH = int(round((pa["y"][1] - pa["y"][0]) * ppu)) // 2 * 2
    MX, MY = int(CW * 0.07), int(CH * 0.06)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                rel(cfg, cfg.get("base", "base.mp4"))], capture_output=True, text=True).stdout)

    pal = [w for s in json.load(open(rel(cfg, cfg.get("transcricao", "transcricao.json")))) for w in s["w"]]
    _fc = {}

    def fonte(est, esc=1.0):
        f, i, t = FONTES[est]; k = (est, round(t * esc))
        if k not in _fc: _fc[k] = ImageFont.truetype(f, k[1], index=i)
        return _fc[k]

    _sp = {}

    def sprite(txt, est, esc=1.0):
        k = (txt, est, esc)
        if k in _sp: return _sp[k]
        e, c = (est.split(":") + [""])[:2]
        f = fonte(e, esc); asc, desc = f.getmetrics()
        im = Image.new("RGBA", (int(f.getlength(txt)) + 40, asc + desc + 20), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((20, 10), txt, font=f, fill=hexcor(CORES[c]) + (255,))
        _sp[k] = (im, asc + 10)
        return _sp[k]

    # ---------- telas: cada item consome palavras da transcrição, em ordem ----------
    telas, k = [], 0

    def linhas_de(spec):
        nonlocal k
        out = []
        for lin in spec:
            li = []
            for txt, est, n in lin:
                li.append({"txt": txt, "est": est, "s": pal[k]["s"], "e": pal[k + n - 1]["e"]}); k += n
            out.append(li)
        return out

    for t in cfg["telas"]:
        if "pular" in t:
            k += t["pular"]; continue
        if "linhas" in t:
            telas.append({"tipo": "texto", "linhas": linhas_de(t["linhas"])})
        elif "feed" in t:
            fd = t["feed"]; ini = k
            rot = [linhas_de(r) for r in fd.get("rotulos", [])]
            k = ini + fd["palavras"]
            telas.append({"tipo": "feed", "w": pal[ini:k], "rot": rot, "cfg": fd})
        elif "prints" in t:
            pr = t["prints"]; ini = k
            tit = linhas_de([pr["titulo"]]) if pr.get("titulo") else []
            k = ini + pr["palavras"]
            telas.append({"tipo": "prints", "w": pal[ini:k], "tit": tit, "cfg": pr})
    if k != len(pal):
        print(f"aviso: as telas consumiram {k} de {len(pal)} palavras da transcrição", file=sys.stderr)
    for t in telas:
        t["s"] = (t["linhas"][0][0]["s"] if t["tipo"] == "texto" else t["w"][0]["s"]) - 0.08
    for i, t in enumerate(telas):
        fim = t["linhas"][-1][-1]["e"] if t["tipo"] == "texto" else t["w"][-1]["e"]
        prox = telas[i + 1]["s"] if i + 1 < len(telas) else dur
        t["f"] = min(prox - 0.02, fim + 0.9)

    def layout(linhas):
        res, y = [], 0
        for li in linhas:
            larg = sum(fonte(w["est"].split(":")[0]).getlength(w["txt"]) for w in li)
            esp = 0.32 * min(FONTES[w["est"].split(":")[0]][2] for w in li)
            esc = min(1.0, (CW - 2 * MX) / (larg + esp * (len(li) - 1)))
            asc = max(fonte(w["est"].split(":")[0], esc).getmetrics()[0] for w in li)
            desc = max(fonte(w["est"].split(":")[0], esc).getmetrics()[1] for w in li)
            x = MX
            for w in li:
                im, a = sprite(w["txt"], w["est"], esc)
                res.append((w, im, x - 20, y + asc - a))
                x += im.width - 40 + esp * esc
            y += asc + desc * 0.55
        oy = MY + (CH - 2 * MY - y) / 2
        return [(w, im, x, yy + oy) for w, im, x, yy in res]

    def mola(u):
        if u <= 0: return 0.0
        if u >= 1: return 1.0
        return 1 + 2.6 * (u - 1) ** 3 + 1.6 * (u - 1) ** 2

    def cola(q, im, x, y, u, alfa=1.0, de_baixo=40):
        if u <= 0 or alfa <= 0: return
        s = 0.85 + 0.15 * mola(u); a = min(1, u * 2.2) * alfa
        if s != 1:
            im2 = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
            x += (im.width - im2.width) / 2; y += (im.height - im2.height) / 2; im = im2
        if a < 1:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        q.alpha_composite(im, (int(x), int(y + (1 - mola(u)) * de_baixo)))

    # ---------- feed ----------
    class Midia:
        def __init__(self, path, w, h):
            self.w, self.h = w, h
            self.video = os.path.splitext(path)[1].lower() in (".mp4", ".mov", ".m4v", ".webm")
            if self.video:
                self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", path, "-vf",
                                           f"fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            else:
                self.cur = ImageOps.fit(Image.open(path).convert("RGB"), (w, h), Image.LANCZOS)

        def quadro(self):
            if self.video:
                self.cur = Image.frombuffer("RGB", (self.w, self.h), self.p.stdout.read(self.w * self.h * 3))
            return self.cur

        def fecha(self):
            if self.video: self.p.kill()

    def moldura(fd, fw, mh):
        hd, ac = int(fw * 0.12), int(fw * 0.15)
        im = Image.new("RGBA", (fw, hd + mh + ac), (255, 255, 255, 255)); d = ImageDraw.Draw(im)
        r = int(hd * 0.66)
        if fd.get("avatar"):
            av = ImageOps.fit(Image.open(rel(cfg, fd["avatar"])).convert("RGB"), (r, r))
            m = Image.new("L", (r, r), 0); ImageDraw.Draw(m).ellipse([0, 0, r - 1, r - 1], fill=255)
            im.paste(av, (24, (hd - r) // 2), m)
        else:
            d.ellipse([24, (hd - r) // 2, 24 + r, (hd + r) // 2], fill=(220, 214, 205))
        ink = hexcor(CORES[""])
        d.text((40 + r, hd // 2 - 22), fd.get("perfil", "seu_perfil"), font=ImageFont.truetype(FONTES["l"][0], 40, index=2), fill=ink)
        y = hd + mh + 26; acc = hexcor(CORES["t"])
        d.polygon([(60, y + 52), (34, y + 24), (34, y + 12), (46, y + 2), (60, y + 12), (74, y + 2), (86, y + 12), (86, y + 24)], fill=acc)
        d.ellipse([110, y + 2, 160, y + 50], outline=ink, width=5)
        d.polygon([(200, y + 4), (250, y + 4), (222, y + 50)], outline=ink, width=5)
        d.text((30, y + 70), fd.get("curtidas", "12,4 mil curtidas"), font=ImageFont.truetype(FONTES["l"][0], 34, index=2), fill=ink)
        return im, hd

    feed_estado = {}

    def feed(q, t, tela):
        fd = tela["cfg"]
        if "m" not in feed_estado:
            fw = int(CW * 0.7); mh = int(fw * 1.25)
            feed_estado["m"] = [Midia(rel(cfg, p), fw, mh) for p in fd["posts"]]
            feed_estado["mold"] = moldura(fd, fw, mh)
            feed_estado["fw"] = fw
        mid = feed_estado["m"]; (mold, hd), fw = feed_estado["mold"], feed_estado["fw"]
        ph = mold.height + 40; jtop = int(CH * 0.25)
        u = t - tela["s"]; passo = 0.62; n = int(u // passo); r = (u % passo) / passo
        off = (n + (1 - (1 - min(r / 0.55, 1)) ** 3)) * ph * 0.82
        sai = max(0, (t - (tela["f"] - 0.25)) / 0.25)
        y0 = CH - off - (sai ** 2) * CH
        jan = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        for i, m in enumerate(mid):
            y = int(y0 + i * ph); fr = m.quadro()
            if y > CH or y + ph < jtop: continue
            card = mold.copy(); card.paste(fr, (0, hd)); jan.alpha_composite(card, ((CW - fw) // 2, y))
        jan = jan.crop((0, jtop, CW, CH)); q.alpha_composite(jan, (0, jtop))
        rots = tela["rot"]
        if rots:
            atual = max([r for r in rots if r[0][0]["s"] - 0.05 <= t] or [rots[0]], key=lambda r: r[0][0]["s"])
            y = int(CH * 0.04)
            for li in atual:
                x = MX
                for w in li:
                    im, a = sprite(w["txt"], w["est"], 0.6)
                    cola(q, im, x, y, (t - w["s"] + 0.05) / 0.22, 1 - sai); x += im.width - 10
                y += int(CH * 0.1)

    _shot = {}

    def prints(q, t, tela):
        pr = tela["cfg"]; w = tela["w"]; sai = max(0, (t - (tela["f"] - 0.2)) / 0.2)
        for li in tela["tit"]:
            x = MX
            for ww in li:
                im, a = sprite(ww["txt"], ww["est"], 0.8)
                cola(q, im, x, int(CH * 0.05), (t - ww["s"] + 0.05) / 0.22, 1 - sai); x += im.width - 10
        n = len(pr["itens"]); larg = (CW - 2 * MX) / n
        for j, it in enumerate(pr["itens"]):
            ww = w[it["palavra"]]; u = (t - ww["s"] + 0.05) / 0.25; oy = (j % 2) * int(CH * 0.04)
            if it["imagem"] not in _shot:
                im = Image.open(rel(cfg, it["imagem"])).convert("RGB"); sw = int(larg * 0.9)
                im = im.resize((sw, int(im.height * sw / im.width)), Image.LANCZOS)
                m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=44, fill=255)
                out = Image.new("RGBA", (im.width + 24, im.height + 24), (0, 0, 0, 0))
                ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius=56, fill=hexcor(CORES[""]) + (255,))
                out.paste(im, (12, 12), m); _shot[it["imagem"]] = out
            cx = MX + j * larg
            nome, a = sprite(it["nome"], "m:" + it.get("cor", "t"), 0.5)
            cola(q, nome, cx + larg / 2 - nome.width / 2, int(CH * 0.14) + oy, u, 1 - sai)
            cola(q, _shot[it["imagem"]], cx, int(CH * 0.23) + oy, u, 1 - sai, de_baixo=120)

    saida = rel(cfg, cfg.get("saida", "parede.mp4"))
    enc = None
    if not prev:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "medium",
                                "-pix_fmt", "yuv444p", saida], stdin=subprocess.PIPE)
    N = int(round(dur * FPS)); cache = {}
    branco = Image.new("RGBA", (CW, CH), (255, 255, 255, 255))
    for i in range(N):
        t = i / FPS
        if prev and not any(abs(t - p) < 0.5 / FPS for p in prev):
            if t > max(prev): break
            continue
        q = branco.copy()
        for ti, tela in enumerate(telas):
            if not (tela["s"] <= t < tela["f"]): continue
            if tela["tipo"] == "feed": feed(q, t, tela)
            elif tela["tipo"] == "prints": prints(q, t, tela)
            else:
                if ti not in cache: cache[ti] = layout(tela["linhas"])
                sai = max(0, (t - (tela["f"] - 0.12)) / 0.12)
                for w, im, x, y in cache[ti]:
                    cola(q, im, x, y, (t - w["s"] + 0.04) / 0.22, 1 - sai)
        if prev:
            q.convert("RGB").save(rel(cfg, f"parede_{t:05.2f}.jpg"), quality=85)
        else:
            enc.stdin.write(q.convert("RGB").tobytes())
            if i % 150 == 0: print(f"\r{i}/{N}", end="", file=sys.stderr, flush=True)
    for m in feed_estado.get("m", []): m.fecha()
    if enc:
        enc.stdin.close(); enc.wait()
        print(f"\n{saida}  ({CW}x{CH})")
    print("cantos:", txt_cantos)


if __name__ == "__main__":
    main()
