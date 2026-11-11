#!/usr/bin/env python3
"""Prepara um vídeo para a colagem: base 9:16, quadros, recorte da pessoa, rosto/olhos e transcrição.

  python3 -I preparar.py bruto.MOV              → base.mp4, quadros/, mask/, olhos.json, transcricao.json, info.json
  python3 -I preparar.py bruto.MOV --lingua en  → transcreve em inglês
  python3 -I preparar.py bruto.MOV --sem-transcricao

Recorte: quadros com fundo verde chapado (chroma key) saem pela cor; o resto pelo recorte de pessoa do
macOS (Vision), suavizado no tempo. Rode na pasta do projeto.
"""
import json, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from chave import alfa_verde, fracao_verde

args = sys.argv[1:]
if not args: sys.exit(__doc__)
bruto = args[0]
lingua = args[args.index("--lingua") + 1] if "--lingua" in args else "pt"


def roda(cmd, **kw):
    print("→", " ".join(cmd[:4]), "…", flush=True)
    subprocess.run(cmd, check=True, **kw)


# 1. base 9:16, 30 fps
if not os.path.exists("base.mp4"):
    roda(["ffmpeg", "-v", "error", "-y", "-i", bruto, "-map", "0:v:0", "-map", "0:a:0?", "-vf",
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
          "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "base.mp4"])

# 2. quadros
if not os.path.isdir("quadros") or not os.listdir("quadros"):
    os.makedirs("quadros", exist_ok=True)
    roda(["ffmpeg", "-v", "error", "-y", "-i", "base.mp4", "-q:v", "2", "quadros/%05d.jpg"])
qs = sorted(f for f in os.listdir("quadros") if f.endswith(".jpg"))
N = len(qs)
print(f"{N} quadros")

# 3. recorte
os.makedirs("mask", exist_ok=True)
verde = []
for i, f in enumerate(qs):
    im = Image.open(os.path.join("quadros", f)); im.draft("RGB", (270, 480))
    verde.append(fracao_verde(np.asarray(im.convert("RGB").resize((108, 192)))) > 0.2)
nv = [f for f, v in zip(qs, verde) if not v]
print(f"fundo verde em {sum(verde)} quadros; recorte automático em {len(nv)}")
if nv and not all(os.path.exists(os.path.join("mask", f.replace(".jpg", ".png"))) for f in nv):
    tmp = tempfile.mkdtemp()
    for f in nv: os.symlink(os.path.abspath(os.path.join("quadros", f)), os.path.join(tmp, f))
    tmpm = tempfile.mkdtemp()
    roda(["swift", os.path.join(AQUI, "seg.swift"), tmp, tmpm])
    # suaviza no tempo (média com vizinhos) para não tremer
    nomes = [f.replace(".jpg", ".png") for f in nv]
    carrega = lambda n: np.asarray(Image.open(os.path.join(tmpm, n)).convert("L"), np.float32)
    ant = None; atual = carrega(nomes[0])
    for k, n in enumerate(nomes):
        prox = carrega(nomes[k + 1]) if k + 1 < len(nomes) else atual
        viz = [x for x in (ant, prox) if x is not None]
        m = atual * 0.5 + sum(viz) / len(viz) * 0.5
        m = np.clip((m - 70) * 255 / 130, 0, 255).astype(np.uint8)  # contraste: borda firme
        Image.fromarray(m).filter(ImageFilter.GaussianBlur(1.2)).save(os.path.join("mask", n))
        ant, atual = atual, prox
    shutil.rmtree(tmp); shutil.rmtree(tmpm)
for f, v in zip(qs, verde):
    if v:
        a = np.asarray(Image.open(os.path.join("quadros", f)).convert("RGB"))
        al, _ = alfa_verde(a)
        Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0)).save(
            os.path.join("mask", f.replace(".jpg", ".png")))

# 4. rosto e olhos
if not os.path.exists("olhos.json"):
    roda(["swift", os.path.join(AQUI, "olhos.swift"), "quadros", "olhos.json", "2"])

# 5. transcrição
if "--sem-transcricao" not in args and not os.path.exists("transcricao.json"):
    roda([sys.executable, "-I", os.path.join(AQUI, "transcrever.py"), "base.mp4", "--lingua", lingua])

# 6. info
caixas = [b for b in json.load(open("olhos.json")) if b]
fw = float(np.median([b[2] for b in caixas])) if caixas else 520
fx = float(np.median([b[0] + b[2] / 2 for b in caixas])) if caixas else 540
fy = float(np.median([b[1] for b in caixas])) if caixas else 600
json.dump({"quadros": N, "verde": [i for i, v in enumerate(verde) if v], "rosto_largura": fw, "rosto_centro_x": fx, "rosto_topo": fy},
          open("info.json", "w"), indent=1)
print("pronto: base.mp4, quadros/, mask/, olhos.json, transcricao.json, info.json")
print("rosto mediano:", int(fw), "px de largura")
