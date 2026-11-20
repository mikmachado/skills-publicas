"""câmera na mão, movimento pequeno: fluxo óptico quadro a quadro em tudo menos a pessoa, modelo de
similaridade (desloca/gira/escala), encadeado e suavizado. uso: python3 rastrear_lk.py [saida.json] [y0 y1]   -> homografias.json
Prefira este quando a superfície tem pouca textura (piso liso) ou o rastreio por SIFT dá saltos."""
import cv2, numpy as np, os, json, sys
saida = sys.argv[1] if len(sys.argv) > 1 else "homografias.json"; y0, y1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1920)
n = len(os.listdir("quadros"))
def zona(i):
    m = cv2.imread(f"mask/{i:05d}.png", 0)
    ok = np.zeros(m.shape, np.uint8); ok[y0:y1] = 255
    ok[cv2.dilate(m, np.ones((61, 61), np.uint8)) > 30] = 0
    return ok
ler = lambda i: cv2.imread(f"quadros/{i:05d}.jpg", 0)
Hs = [np.eye(3)]; a = ler(1)
for i in range(2, n + 1):
    b = ler(i)
    p = cv2.goodFeaturesToTrack(a, 1500, 0.005, 12, mask=zona(i - 1))
    q, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p, None, winSize=(31, 31), maxLevel=4)
    r, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, q, None, winSize=(31, 31), maxLevel=4)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm((r - p).reshape(-1, 2), axis=1) < 0.5)
    M, inl = cv2.estimateAffinePartial2D(p[ok], q[ok], method=cv2.RANSAC, ransacReprojThreshold=1.0)
    Hs.append(np.vstack([M, [0, 0, 1]]) @ Hs[-1]); a = b
    if i % 25 == 0: print(i, int(ok.sum()), int(inl.sum()), np.round(Hs[-1][:2, 2], 1))
C = np.float32([[100, 800], [1000, 800], [1000, 1850], [100, 1850]])
P = np.array([cv2.perspectiveTransform(C[None], H)[0] for H in Hs])
k = np.array([1, 4, 6, 4, 1], float); k /= k.sum()
Pp = np.pad(P, ((2, 2), (0, 0), (0, 0)), mode="edge")
Ps = sum(k[j] * Pp[j:j + len(P)] for j in range(5))
json.dump([cv2.getPerspectiveTransform(C, p.astype(np.float32)).tolist() for p in Ps], open(saida, "w"))
print("ok", len(Hs))
