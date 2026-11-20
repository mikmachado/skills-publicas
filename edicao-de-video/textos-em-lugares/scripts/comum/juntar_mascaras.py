"""mask_fina/ = recortes ampliados (mais precisos) onde cobrem; fora deles, a máscara cheia.
uso: python3 juntar_mascaras.py mask_fina mask dirA:x,y,w,h dirB:x,y,w,h ...
(cada dirX vem de: swift seg_crop.swift quadros dirX x y w h)"""
import cv2, numpy as np, os, sys
out, cheio = sys.argv[1], sys.argv[2]
cs = [(d, [int(v) for v in r.split(",")]) for d, r in (a.split(":") for a in sys.argv[3:])]
os.makedirs(out, exist_ok=True)
for fn in sorted(os.listdir(cheio)):
    m = cv2.imread(f"{cheio}/{fn}", 0)
    cov = np.zeros_like(m, bool); acc = np.zeros_like(m)
    for d, (x, y, w, h) in cs:
        c = cv2.imread(f"{d}/{fn}", 0)
        b = np.zeros_like(cov); b[y + 4:y + h - 4, x + 4:x + w - 4] = True    # borda do recorte não vale
        acc[b] = np.maximum(acc[b], c[b]); cov |= b
    m[cov] = acc[cov]
    cv2.imwrite(f"{out}/{fn}", m)
print("ok")
