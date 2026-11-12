#!/usr/bin/env python3
"""Prepara um vídeo para o cenário desenhado: base 9:16, quadros, recorte da pessoa, recorte firme das pernas,
transcrição e medidas do corpo (linha do assento, centro, topo da cabeça).

  python3 -I preparar.py bruto.MOV              → base.mp4, quadros/, mask/, pernas/, transcricao.json, info.json
  python3 -I preparar.py bruto.MOV --lingua en
  python3 -I preparar.py bruto.MOV --sem-transcricao

Rode na pasta do projeto. Recorte: fundo verde chapado pela cor; o resto pelo recorte de pessoa do macOS (Vision).
"""
import json, os, shutil, subprocess, sys, tempfile
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from chave import alfa_verde, fracao_verde

W, H = 1080, 1920


def roda(cmd, **kw):
    print("→", " ".join(cmd[:4]), "…", flush=True)
    subprocess.run(cmd, check=True, **kw)


# ------------------------------------------------------------------ pernas: presença no tempo
JANELA = 15  # ±quadros


def _pernas(args):
    i, f, Y0, Y1, pres = args
    full = np.asarray(Image.open(os.path.join("mask", f)).convert("L"), np.float32) / 255
    p = Image.fromarray(pres).resize((W, H - (Y0 - 100)), Image.BILINEAR)
    p = np.clip((np.asarray(p, np.float32) / 255 - 0.22) / 0.33, 0, 1)
    p = Image.fromarray((p * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.MinFilter(17)) \
        .filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.5))
    p = np.asarray(p, np.float32) / 255
    w = np.clip((np.arange(H - (Y0 - 100)) + (Y0 - 100) - Y0) / (Y1 - Y0), 0, 1)[:, None]
    low = full[Y0 - 100:]
    full[Y0 - 100:] = low * (1 - w) + np.maximum(low, p) * w
    Image.fromarray((full * 255).astype(np.uint8)).save(os.path.join("pernas", f))


def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    bruto = args[0]
    lingua = args[args.index("--lingua") + 1] if "--lingua" in args else "pt"

    if not os.path.exists("base.mp4"):
        roda(["ffmpeg", "-v", "error", "-y", "-i", bruto, "-map", "0:v:0", "-map", "0:a:0?", "-vf",
              "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
              "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "base.mp4"])
    if not os.path.isdir("quadros") or not os.listdir("quadros"):
        os.makedirs("quadros", exist_ok=True)
        roda(["ffmpeg", "-v", "error", "-y", "-i", "base.mp4", "-q:v", "2", "quadros/%05d.jpg"])
    qs = sorted(f for f in os.listdir("quadros") if f.endswith(".jpg"))
    N = len(qs); print(f"{N} quadros")

    # 1. recorte
    os.makedirs("mask", exist_ok=True)
    verde = []
    for f in qs:
        im = Image.open(os.path.join("quadros", f)); im.draft("RGB", (270, 480))
        verde.append(fracao_verde(np.asarray(im.convert("RGB").resize((108, 192)))) > 0.2)
    nv = [f for f, v in zip(qs, verde) if not v]
    if nv and not all(os.path.exists(os.path.join("mask", f.replace(".jpg", ".png"))) for f in nv):
        tmp = tempfile.mkdtemp(); tmpm = tempfile.mkdtemp()
        for f in nv: os.symlink(os.path.abspath(os.path.join("quadros", f)), os.path.join(tmp, f))
        roda(["swift", os.path.join(AQUI, "seg.swift"), tmp, tmpm])
        nomes = [f.replace(".jpg", ".png") for f in nv]
        carrega = lambda n: np.asarray(Image.open(os.path.join(tmpm, n)).convert("L"), np.float32)
        ant = None; atual = carrega(nomes[0])
        for k, n in enumerate(nomes):
            prox = carrega(nomes[k + 1]) if k + 1 < len(nomes) else atual
            viz = [x for x in (ant, prox) if x is not None]
            m = atual * 0.5 + sum(viz) / len(viz) * 0.5
            m = np.clip((m - 70) * 255 / 130, 0, 255).astype(np.uint8)
            Image.fromarray(m).filter(ImageFilter.GaussianBlur(1.2)).save(os.path.join("mask", n))
            ant, atual = atual, prox
        shutil.rmtree(tmp); shutil.rmtree(tmpm)
    for f, v in zip(qs, verde):
        if v:
            a = np.asarray(Image.open(os.path.join("quadros", f)).convert("RGB"))
            al, _ = alfa_verde(a)
            Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0)).save(
                os.path.join("mask", f.replace(".jpg", ".png")))
    ms = sorted(os.listdir("mask"))

    # 2. medidas do corpo (em meia resolução)
    peq = np.stack([np.asarray(Image.open(os.path.join("mask", f)).convert("L").resize((W // 2, H // 2)), np.uint8) for f in ms])
    cob = (peq > 128).reshape(N, -1).mean(1)
    tem = cob > max(0.02, np.median(cob) * 0.5)
    entra = int(np.argmax(tem)) if tem.any() else 0
    med = (np.median(peq[tem] if tem.any() else peq, axis=0) > 128)
    larg_l = med.sum(1)
    linhas = np.where(larg_l > 20)[0]
    topo, fundo = int(linhas[0]), int(linhas[-1])
    # faixa das pernas: último terço do corpo; assento = onde a largura cai para menos da metade da largura dos joelhos
    a = topo + int(0.6 * (fundo - topo))
    maxw = larg_l[a:fundo + 1].max()
    y = int(np.argmax(larg_l[a:fundo + 1])) + a
    while y < fundo and larg_l[y] > 0.5 * maxw: y += 1
    perfil = med[a:y].sum(0).astype(np.float64); acc = np.cumsum(perfil) / max(1, perfil.sum())
    x5, x95 = int(np.searchsorted(acc, 0.03)), int(np.searchsorted(acc, 0.97))
    cx = int(x5 + x95); larg = int((x95 - x5) * 2)
    topo *= 2; sy = int(y * 2) + 12
    print(f"pessoa entra no quadro {entra}; cabeça y={topo}, assento y={sy}, centro x={cx}, largura das pernas {larg}px")

    # 3. pernas: máximo da máscara numa janela de ±0,5 s (pernas quase não mexem; tênis e mangas ficam sólidos)
    Y0 = int(sy - 0.21 * (sy - topo)); Y1 = Y0 + 80
    os.makedirs("pernas", exist_ok=True)
    if len(os.listdir("pernas")) < N:
        baixo = peq[:, (Y0 - 100) // 2:]
        trabalhos = []
        for i, f in enumerate(ms):
            a, b = max(0, i - JANELA), min(N, i + JANELA + 1)
            trabalhos.append((i, f, Y0, Y1, baixo[a:b].max(0)))
        with ProcessPoolExecutor(6) as ex: list(ex.map(_pernas, trabalhos, chunksize=16))
    print("pernas/ pronto")

    # 4. transcrição
    if "--sem-transcricao" not in args and not os.path.exists("transcricao.json"):
        roda([sys.executable, "-I", os.path.join(AQUI, "transcrever.py"), "base.mp4", "--lingua", lingua])

    json.dump({"quadros": N, "entra": entra, "cabeca_y": topo, "assento_y": sy, "centro_x": cx, "largura_pernas": larg},
              open("info.json", "w"), indent=1)
    print("pronto: base.mp4, quadros/, mask/, pernas/, transcricao.json, info.json")


if __name__ == "__main__":
    main()
