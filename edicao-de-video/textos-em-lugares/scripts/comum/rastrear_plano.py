"""câmera na mão: homografia quadro1 -> quadro i usando SÓ a superfície onde vai o texto (retângulo x0 y0 x1 y1,
sem as pessoas de mask/), SIFT + refino ECC, suavizada de leve.  -> homografias.json
uso (na pasta da cena): python3 rastrear_plano.py x0 y0 x1 y1
Dica: não inclua paredes perto da câmera junto com o chão/escada (paralaxe = texto tremendo)."""
import cv2, numpy as np, os, json, sys
X0, Y0, X1, Y1 = [int(v) for v in sys.argv[1:5]]
n = len(os.listdir("quadros"))
sift = cv2.SIFT_create(6000)
def zona(i):
    m = cv2.imread(f"mask/{i:05d}.png", 0)
    ok = np.zeros(m.shape, np.uint8); ok[Y0:Y1, X0:X1] = 255
    ok[cv2.dilate(m, np.ones((51, 51), np.uint8)) > 40] = 0
    return ok
def ler(i): return cv2.imread(f"quadros/{i:05d}.jpg", 0)
g0 = ler(1); z0 = zona(1)
k0, d0 = sift.detectAndCompute(g0, z0)
S = 0.5
g0s = cv2.resize(g0, None, fx=S, fy=S).astype(np.float32); z0s = cv2.resize(z0, None, fx=S, fy=S)
D = np.diag([S, S, 1.0]); Di = np.linalg.inv(D)
bf = cv2.BFMatcher(); Hs = []; Hprev = np.eye(3)
for i in range(1, n + 1):
    g = ler(i); z = zona(i)
    k, d = sift.detectAndCompute(g, z)
    ms = [a for a, b in bf.knnMatch(d, d0, k=2) if a.distance < 0.72 * b.distance]
    src = np.float32([k[m.queryIdx].pt for m in ms]); dst = np.float32([k0[m.trainIdx].pt for m in ms])
    H, inl = cv2.findHomography(dst, src, cv2.USAC_MAGSAC, 2.0) if len(ms) > 30 else (None, None)
    if H is None: H = Hprev
    # ECC: alinha quadro i ao quadro 1 na escada (subpixel). warp mapeia coords do template (quadro1) no quadro i
    Wm = (D @ H @ Di).astype(np.float32); Wm /= Wm[2, 2]
    gs = cv2.resize(g, None, fx=S, fy=S).astype(np.float32)
    try:
        _, Wm = cv2.findTransformECC(cv2.GaussianBlur(g0s, (0, 0), 1), cv2.GaussianBlur(gs, (0, 0), 1), Wm,
                                     cv2.MOTION_HOMOGRAPHY, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-6), z0s, 5)
        H = Di @ Wm.astype(np.float64) @ D
    except cv2.error: pass
    H /= H[2, 2]; Hs.append(H); Hprev = H
    if i % 40 == 0: print(i, len(ms), None if inl is None else int(inl.sum()), np.round(H[:2, 2], 1))
# suavização leve nas trajetórias de 4 cantos (tira o chiado sem deixar o texto escorregar)
C = np.float32([[450, 350], [1050, 350], [1050, 1850], [450, 1850]])
P = np.array([cv2.perspectiveTransform(C[None], H)[0] for H in Hs])
k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
Pp = np.pad(P, ((2, 2), (0, 0), (0, 0)), mode="edge")
Ps = sum(k[j] * Pp[j:j + len(P)] for j in range(5))
Hs = [cv2.getPerspectiveTransform(C, p.astype(np.float32)).tolist() for p in Ps]
json.dump(Hs, open("homografias.json", "w"))
print("ok", len(Hs))
