#!/usr/bin/env python3
"""Prepara a gravação para a colagem surreal: quadros 9:16, recorte de cada quadro, rostos e transcrição.

  python3 -I preparar.py roteiro.json                → prepara a fala e todos os takes do roteiro
  python3 -I preparar.py roteiro.json --lingua en    → transcreve em inglês
  python3 -I preparar.py roteiro.json --refaz-recorte

Rode na pasta do projeto. Para cada take (a fala principal se chama "fala"):
  quadros/<take>/NNNNN.jpg   recorte/<take>/NNNNN.png (RGBA)   rostos/<take>.json
  transcricao.json (só da fala)   fala.wav (áudio da fala)

Recorte (fundo verde): pela cor + recorte de pessoa do Mac. Onde o chão aparece (corpo inteiro), abaixo
da linha do chão fica só a pessoa e a madeira (pés de cadeira); acima, tudo que não é verde perto da
pessoa (mantém cadeira e objetos que ela segura, tira sujeira do pano). Sem fundo verde: só o recorte
de pessoa do Mac.
"""
import json, os, subprocess, sys, tempfile, shutil
import numpy as np
from PIL import Image, ImageFilter
from multiprocessing import Pool

AQUI = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
if not args: sys.exit(__doc__)
R = json.load(open(args[0]))
lingua = args[args.index("--lingua") + 1] if "--lingua" in args else "pt"
REFAZ = "--refaz-recorte" in args


def roda(cmd, **kw):
    print("→", " ".join(str(c) for c in cmd[:5]), "…", flush=True)
    subprocess.run(cmd, check=True, **kw)


def takes():
    t = {"fala": {"arquivo": R["fala"]}}
    t.update(R.get("takes", {}))
    return t


# ------------------------------------------------------------------ recorte
def chave(a):
    f = a.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    d = g - np.maximum(r, b)
    al = np.clip((34 - d) / 20.0, 0, 1)
    g2 = np.minimum(g, np.maximum(r, b) + 4)
    rgb = np.stack([r, np.where(d > -2, g2, g), b], -1)
    return al, rgb


def verde_frac(a):
    f = a[::8, ::8].astype(np.float32)
    return float(((f[..., 1] - np.maximum(f[..., 0], f[..., 2])) > 25).mean())


def linha_chao(a):
    """y onde o pano verde acaba (menor dos dois lados), ou None se o chão não aparece."""
    ys_ = []
    for x0 in (20, a.shape[1] - 60):
        d = a[:, x0:x0 + 40, 1].astype(np.float32) - np.maximum(a[:, x0:x0 + 40, 0], a[:, x0:x0 + 40, 2]).astype(np.float32)
        ys = np.flatnonzero((d > 25).mean(1) > 0.5)
        if len(ys): ys_.append(int(ys.max()))
    if not ys_: return None
    y0 = min(ys_) - 10
    return y0 if y0 < a.shape[0] - 40 else None


def recorta(job):
    src, seg, dst = job
    if os.path.exists(dst) and not REFAZ: return
    im = np.asarray(Image.open(src).convert("RGB"))
    s = Image.open(seg).convert("L").point(lambda v: 255 if v > 90 else 0)
    if verde_frac(im) < 0.15:   # sem fundo verde: só o recorte de pessoa
        al = np.asarray(s.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
        rgb = im.astype(np.float32)
    else:
        al, rgb = chave(im)
        y0 = linha_chao(im)
        perto = s.resize((s.width // 4, s.height // 4)).filter(ImageFilter.MaxFilter(15)).resize(s.size)
        perto = np.asarray(perto.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
        if y0 is None:
            sp = np.asarray(s.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255
            al = al * sp
        else:
            o = im.astype(np.float32)
            sp = np.asarray(s.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
            r_, g_, b_ = o[..., 0], o[..., 1], o[..., 2]
            madeira = ((r_ - b_) > 45) & (r_ > g_) & (g_ > b_)
            madeira = np.asarray(Image.fromarray((madeira * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.GaussianBlur(1)), np.float32) / 255
            yy = np.arange(al.shape[0])[:, None]
            al = np.where(yy >= y0, al * np.maximum(sp, madeira * perto), al * perto)
    al = np.asarray(Image.fromarray((np.clip(al, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32)
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), "RGBA").save(dst, compress_level=1)


# ------------------------------------------------------------------ por take
os.makedirs("quadros", exist_ok=True); os.makedirs("recorte", exist_ok=True); os.makedirs("rostos", exist_ok=True)
for nome, tk in takes().items():
    qd, rd, sd = f"quadros/{nome}", f"recorte/{nome}", f"seg/{nome}"
    for d in (qd, rd, sd): os.makedirs(d, exist_ok=True)
    if not os.listdir(qd):
        corte = []
        if "de" in tk: corte += ["-ss", str(tk["de"])]
        if "ate" in tk: corte += ["-t", str(tk["ate"] - tk.get("de", 0))]
        roda(["ffmpeg", "-v", "error", "-y", *corte, "-i", tk["arquivo"], "-vf",
              "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30", "-q:v", "2", f"{qd}/%05d.jpg"])
    qs = sorted(f for f in os.listdir(qd) if f.endswith(".jpg"))
    print(f"[{nome}] {len(qs)} quadros")
    if len(os.listdir(sd)) < len(qs):
        roda(["swift", os.path.join(AQUI, "seg.swift"), qd, sd])
    with Pool(8) as p:
        p.map(recorta, [(f"{qd}/{q}", f"{sd}/{q[:-4]}.png", f"{rd}/{q[:-4]}.png") for q in qs], chunksize=8)
    if not os.path.exists(f"rostos/{nome}.json"):
        roda(["swift", os.path.join(AQUI, "olhos.swift"), qd, f"rostos/{nome}.json", "1"])

# ------------------------------------------------------------------ áudio e transcrição da fala
if not os.path.exists("fala.wav"):
    roda(["ffmpeg", "-v", "error", "-y", "-i", R["fala"], "-vn", "-ac", "2", "-ar", "48000", "fala.wav"])
if not os.path.exists("transcricao.json"):
    roda([sys.executable, "-I", os.path.join(AQUI, "transcrever.py"), "fala.wav", "--lingua", lingua])
print("pronto: quadros/, recorte/, rostos/, fala.wav, transcricao.json")
print("revise a transcrição (campo \"w\") e confira o recorte: python3 -I motor.py roteiro.json --recorte")
