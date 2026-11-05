#!/usr/bin/env python3
"""Máscara da pessoa + o que está colado nela (cadeira, banco, mesa, violão).

O recorte de pessoa do Vision não pega móveis, e aí os posts passam entre a pessoa e a
cadeira. Aqui: (1) pinta a pessoa com a cor do fundo, para o móvel virar o objeto em
destaque; (2) recorta os objetos com o Vision; (3) fica só com o que encosta na pessoa
(descarta prateleira, estante, cabos); (4) junta com a máscara da pessoa.

  python3 -I mascara_objetos.py quadros/ mask/ mask_tudo/ [--cor 70,84,62] [--zona 380,870,955,1920]

--cor = cor do fundo atrás da pessoa (padrão: mediana da borda de cima do 1º quadro).
--zona = x0,y0,x1,y1: só aceita objeto dentro desse retângulo (corta estante, prateleira
         e cabos que encostam na pessoa). A pessoa em si nunca é cortada.
"""
import glob, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageFilter


def dilata(a):
    b = a.copy()
    b[1:] |= a[:-1]; b[:-1] |= a[1:]; b[:, 1:] |= a[:, :-1]; b[:, :-1] |= a[:, 1:]
    return b


def colados(obj, semente):
    """Reconstrução geodésica: cresce a semente só por dentro de obj."""
    r = semente & obj
    while True:
        n = dilata(r) & obj
        if (n == r).all():
            return r
        r = n


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    qdir, mdir, odir = sys.argv[1:4]
    os.makedirs(odir, exist_ok=True)
    qs = sorted(glob.glob(os.path.join(qdir, "*.jpg")))
    if "--cor" in sys.argv:
        cor = [int(v) for v in sys.argv[sys.argv.index("--cor") + 1].split(",")]
    else:
        q0 = np.asarray(Image.open(qs[0]).convert("RGB"))
        cor = np.median(q0[:40].reshape(-1, 3), 0).astype(int).tolist()
    zona = None
    if "--zona" in sys.argv:
        zona = [int(v) for v in sys.argv[sys.argv.index("--zona") + 1].split(",")]
    aqui = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory() as tmp:
        pq, pm = os.path.join(tmp, "q"), os.path.join(tmp, "m")
        os.makedirs(pq); os.makedirs(pm)
        for q in qs:
            nome = os.path.basename(q)
            im = np.asarray(Image.open(q).convert("RGB")).copy()
            pes = Image.open(os.path.join(mdir, nome.replace(".jpg", ".png"))).convert("L")
            im[np.asarray(pes.filter(ImageFilter.MaxFilter(9))) > 60] = cor
            Image.fromarray(im).save(os.path.join(pq, nome), quality=92)
        subprocess.run(["swift", os.path.join(aqui, "seg_objetos.swift"), pq, pm], check=True)
        for q in qs:
            nome = os.path.basename(q).replace(".jpg", ".png")
            pes = Image.open(os.path.join(mdir, nome)).convert("L")
            obj = Image.open(os.path.join(pm, nome)).convert("L")
            W, H = pes.size
            p4 = np.asarray(pes.resize((W // 4, H // 4))) > 100
            o4 = np.asarray(obj.resize((W // 4, H // 4))) > 100
            # semente = a pessoa engordada (o móvel encosta nela, não fica por baixo da máscara)
            sem = p4.copy()
            for _ in range(4):
                sem = dilata(sem)
            ok = colados(o4, sem)
            ok = Image.fromarray(ok.astype(np.uint8) * 255).resize((W, H), Image.NEAREST).filter(ImageFilter.MaxFilter(9))
            o = np.minimum(np.asarray(obj), np.asarray(ok))
            if zona:
                z = np.zeros_like(o); z[zona[1]:zona[3], zona[0]:zona[2]] = 255
                o = np.minimum(o, z)
            final = np.maximum(np.asarray(pes), o)
            Image.fromarray(final).save(os.path.join(odir, nome))
    print("pronto:", len(qs), "máscaras em", odir)


if __name__ == "__main__":
    main()
