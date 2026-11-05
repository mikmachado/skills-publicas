#!/usr/bin/env python3
"""Gera o "cartão" de texto que depois vai para a parede em perspectiva.

É o passo do CapCut no tutorial: linhas empilhadas, cada uma esticada até a
mesma largura (palavra curta fica gigante), letra condensada amarela com
contorno preto, sobre fundo branco (some no modo "multiplicar") ou transparente.

  python3 cartao.py --linhas "EU AMO USAR|TEXTOS|DESSE JEITINHO" -o cartao.png
  python3 cartao.py --linhas "TEXTO EM|PERSPECTIVA" --cor "#111" --contorno-px 0 --fundo transparente -o t.png
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont

FONTES = [
    os.path.expanduser("~/Library/Fonts/Anton-Regular.ttf"),
    os.path.expanduser("~/Library/Fonts/BebasNeue-Regular.ttf"),
    "/System/Library/Fonts/Avenir Next Condensed.ttc",
]


def cor(s):
    if s in ("transparente", "none"):
        return (0, 0, 0, 0)
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


INDICE = 0


def linha_img(txt, fonte, tam, fill, stroke, spx, condensar):
    f = ImageFont.truetype(fonte, tam, index=INDICE)
    x0, y0, x1, y1 = f.getbbox(txt, stroke_width=spx)
    im = Image.new("RGBA", (x1 - x0 + 4, y1 - y0 + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - x0, 2 - y0), txt, font=f, fill=fill, stroke_width=spx, stroke_fill=stroke)
    if condensar != 1:
        im = im.resize((max(1, round(im.width * condensar)), im.height), Image.LANCZOS)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--linhas", required=True, help="linhas separadas por |")
    ap.add_argument("-o", "--saida", required=True)
    ap.add_argument("--largura", type=int, default=1080)
    ap.add_argument("--altura", type=int, default=1920, help="altura do cartão (0 = só o texto + margem)")
    ap.add_argument("--fundo", default="#FFFFFF", help="#hex ou transparente")
    ap.add_argument("--cor", default="#FFE600")
    ap.add_argument("--contorno", default="#000000")
    ap.add_argument("--contorno-px", type=int, default=14)
    ap.add_argument("--fonte", default=next((f for f in FONTES if os.path.exists(f)), FONTES[-1]))
    ap.add_argument("--indice", type=int, default=-1, help="face dentro de um .ttc (padrão: Heavy da Avenir Next Condensed)")
    ap.add_argument("--condensar", type=float, default=0.78, help="aperta na horizontal (fonte larga → cara de Anton)")
    ap.add_argument("--margem", type=float, default=0.08, help="margem lateral, fração da largura")
    ap.add_argument("--entrelinha", type=float, default=0.06, help="espaço entre linhas, fração da altura da linha")
    ap.add_argument("--topo", type=float, default=0.12, help="onde o bloco começa (fração da altura); -1 = centraliza")
    a = ap.parse_args()
    global INDICE
    INDICE = a.indice if a.indice >= 0 else (8 if a.fonte.endswith(".ttc") else 0)
    if a.fonte.endswith("Avenir Next Condensed.ttc"):
        a.condensar = 1.0 if a.condensar == 0.78 else a.condensar

    alvo = round(a.largura * (1 - 2 * a.margem))
    linhas = []
    for t in a.linhas.split("|"):
        t = t.strip()
        base = linha_img(t, a.fonte, 200, cor(a.cor), cor(a.contorno), round(a.contorno_px * 200 / 160), a.condensar)
        tam = max(8, round(200 * alvo / base.width))
        im = linha_img(t, a.fonte, tam, cor(a.cor), cor(a.contorno), round(a.contorno_px * tam / 160), a.condensar)
        linhas.append(im.resize((alvo, round(im.height * alvo / im.width)), Image.LANCZOS))

    gap = [round(l.height * a.entrelinha) for l in linhas]
    bloco = sum(l.height for l in linhas) + sum(gap[:-1])
    alt = a.altura or round(bloco + 2 * a.margem * a.largura)
    card = Image.new("RGBA", (a.largura, alt), cor(a.fundo))
    y = (alt - bloco) // 2 if (a.topo < 0 or not a.altura) else round(alt * a.topo)
    for l, g in zip(linhas, gap):
        card.alpha_composite(l, ((a.largura - l.width) // 2, y))
        y += l.height + g
    card.save(a.saida)
    print(a.saida, card.size)


if __name__ == "__main__":
    main()
