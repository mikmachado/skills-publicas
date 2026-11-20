"""máscara de quem PASSA ao fundo (pernas sem cabeça que o recorte automático não pega): diferença de cor
contra uma placa limpa (mediana dos quadros alinhados). Usa homografias.json. Junta com mask_topo/ se existir
(seg_crop.swift num recorte da área onde as pessoas passam).  -> mask_gente/
uso (na pasta da cena): python3 pessoas_passando.py x0 y0 x1 y1   (área onde as pessoas passam)"""
import cv2, numpy as np, json, os, sys
X0, Y0, X1, Y1 = [int(v) for v in sys.argv[1:5]]
H, W = 1920, 1080
HS = [np.array(h) for h in json.load(open("homografias.json"))]
n = len(HS)
fr = []
for i in range(1, n + 1, 3):
    q = cv2.imread(f"quadros/{i:05d}.jpg")
    fr.append(cv2.warpPerspective(q, np.linalg.inv(HS[i - 1]), (W, H), flags=cv2.INTER_LINEAR))
placa = cv2.imread('placa.jpg') if os.path.exists('placa.jpg') else np.median(np.stack(fr), 0).astype(np.uint8); del fr
cv2.imwrite("placa.jpg", placa)
os.makedirs("mask_gente", exist_ok=True)
lab = lambda im: cv2.cvtColor(cv2.GaussianBlur(im, (0, 0), 2), cv2.COLOR_BGR2LAB).astype(np.float32)
zona = np.zeros((H, W), np.float32); zona[Y0:Y1, X0:X1] = 1
for i in range(1, n + 1):
    q = cv2.imread(f"quadros/{i:05d}.jpg")
    pl = cv2.warpPerspective(placa, HS[i - 1], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    dd = lab(q) - lab(pl); dd[..., 0] *= 0.6; d = np.linalg.norm(dd, axis=2)
    m = (d > 42).astype(np.uint8) * (zona > 0)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    k, lb, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    for j in range(1, k):
        if st[j, 4] > 1500: keep[lb == j] = 1
    keep = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 1.5)
    pt = f"mask_topo/{i:05d}.png"
    old = cv2.imread(pt, 0).astype(np.float32) / 255 * zona if os.path.exists(pt) else np.zeros((H, W), np.float32)
    cv2.imwrite(f"mask_gente/{i:05d}.png", (np.maximum(old, keep) * 255).astype(np.uint8))
print("ok", n)
