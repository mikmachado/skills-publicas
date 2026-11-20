# Desenhos animados — pessoa andando num parque (travelling, cena anda pra esquerda)
import sys, os, subprocess, cv2, numpy as np
sys.path.insert(0, os.path.expanduser('~/.claude/skills/desenhos-animados/scripts/comum'))
from desenho import *
P = np.load('probs.npy').astype(np.float32); N = len(P)   # muro(cerca) predio ceu veg chao
CR = np.load('desloc_linha.npy')                         # (N,960) desloc acumulado px cheios por linha meia-res
args = sys.argv[1:]; prev = 'prev' in args; nums = [int(a) for a in args if a.isdigit()]
ini, fim = (nums[0], nums[1]) if len(nums) >= 2 else (0, N)

def regiao(j, k, sig=4, lim=0.5):
    p = cv2.resize(P[j, k], (W, H), interpolation=cv2.INTER_LINEAR)
    return (cv2.GaussianBlur(p, (0, 0), sig) > lim).astype(np.uint8)
def contornos(m, minarea, maxn, suav=9, keep=None, minlen=20):
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cs = sorted([c for c in cs if cv2.contourArea(c) > minarea], key=cv2.contourArea, reverse=True)[:maxn]
    out = []
    for c in cs:
        c = c[:, 0, :].astype(np.float32)
        if len(c) < 4 * suav + 2: continue
        c = suav_fech(c, suav)
        ok = (c[:, 0] > 6) & (c[:, 0] < W - 7) & (c[:, 1] > 6) & (c[:, 1] < H - 7)
        if keep is not None:
            ci = np.clip(c.astype(int), 0, [W - 1, H - 1]); ok &= keep[ci[:, 1], ci[:, 0]] > 0
        cur = []
        for p, k in zip(c, ok):
            if k: cur.append(p)
            else:
                if len(cur) > minlen: out.append(np.array(cur))
                cur = []
        if len(cur) > minlen: out.append(np.array(cur))
    return out

# ---- sol (centro da área estourada no céu, suavizado) ----
SOL = np.full((N, 2), np.nan)
for j in range(N):
    g = cv2.GaussianBlur(cv2.imread(f'quadros/{j+1:05d}.jpg', 0)[:800], (0, 0), 9)
    ys, xs = np.nonzero(g > 250)
    if len(xs) > 300: SOL[j] = [xs.mean(), ys.mean()]
for d in range(2):
    ok = ~np.isnan(SOL[:, d]); SOL[:, d] = np.interp(np.arange(N), np.where(ok)[0], SOL[ok, d])
SOL = cv2.GaussianBlur(SOL.astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=3)

# ---- quando a palmeira entra ----
T_PALMA = 99
for j_ in range(N):
    v_ = (cv2.GaussianBlur(P[j_, 3], (0, 0), 2) > 0.5).astype(np.uint8)
    nl_, _, st_, _ = cv2.connectedComponentsWithStats(v_, 8)
    if any(st_[k, 1] < 8 and st_[k, 3] > 2.2 * st_[k, 2] and st_[k, 4] > 30000 / 16 for k in range(1, nl_)): T_PALMA = j_ / FPS; break
print('palmeira entra em', T_PALMA)
# ---- rabiscos do chão, presos ao mundo (x_mundo; tela = x_mundo + CR[j, y//2]) ----
r = np.random.RandomState(11)
CHAO = []; xw = -150; k = 0
nomes = ['estrela', 'coracao', 'espiral', 'zigue', 'estrela']
while xw < W + 6500:
    for y in (r.randint(1420, 1600), r.randint(1650, 1880)):
        fm_ = nomes[(k + r.randint(5)) % 5]
        CHAO.append((fm_, xw + r.randint(-60, 60), y, r.randint(48, 80) if fm_ != 'zigue' else 7, PAL[r.randint(6)], r.rand() * 6))
    xw += r.randint(110, 190); k += 1

# ---- textos ----
TIT = ("A ARTE DE", "EXPLORAR", "SEM PRESSA")
CEU = [("SAIA.", AMAR, 4.3, 250, 190), ("VIAJE.", CIANO, 4.85, 440, 190), ("CRIE.", ROSA, 5.4, 640, 205)]
SPC = [sprite(t_, sz, c, 0, 11) for t_, c, t0, y, sz in CEU]
# palavras soltas pintadas no chão, presas ao mundo (curtas!)
PAL_CHAO = [("ARTE", LIMA, 1.0), ("UAU!", ROSA, 2.0), ("BCN", CIANO, 3.0), ("CORES", AMAR, 4.0), ("GAUDÍ", LARANJA, 5.0), ("VIVA!", ROXO, 6.0), ("CRIAR", LIMA, 7.0), ("ARTE", ROSA, 8.0)]
SPCH = [sprite(t_, 104, c, r.randint(-6, 7)) for t_, c, _ in PAL_CHAO]
YCH = 1560
XW_CH = [W + 120 - CR[int(t0 * FPS), YCH // 2] for _, _, t0 in PAL_CHAO]   # entra pela direita no tempo t0

out = None if prev else subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-',
     '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', 'linhas_mudo.mp4'], stdin=subprocess.PIPE)
os.makedirs('olhar', exist_ok=True)
yy, xx = np.mgrid[0:H, 0:W]
for j in range(ini, fim):
    t = j / FPS
    fr = cv2.imread(f'quadros/{j+1:05d}.jpg').astype(np.float32) / 255
    pm = masc(j)
    dist = cv2.distanceTransform((pm < 0.3).astype(np.uint8), cv2.DIST_L2, 5)
    gray8 = cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray8, (0, 0), 2.2)
    PA = np.zeros((H, W), np.float32); PC = np.zeros((H, W, 3), np.float32)
    L = np.zeros((H, W, 3), np.uint8); A = np.zeros((H, W), np.uint8)
    longe = np.clip((dist - 85) / 90, 0, 1)          # protege os pés/sombra
    perto = np.clip((dist - 4) / 8, 0, 1)
    ceu = regiao(j, 2, 5); chao = regiao(j, 4, 5); veg = regiao(j, 3, 5); pr = regiao(j, 1, 4)
    # ---- cordinha da cerca: listras coloridas presas ao mundo ----
    cerca = cv2.dilate(regiao(j, 0, 2, 0.2), np.ones((15, 15), np.uint8))
    hsv = cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
    corda = ((hsv[..., 2] > 150) & (hsv[..., 1] < 60) & (cerca > 0)).astype(np.float32)
    corda = cv2.GaussianBlur(corda, (0, 0), 1.0)
    xwm = xx - CR[j][np.clip(yy // 2, 0, 959)]
    faixa = (np.floor(xwm / 46).astype(int) % 6)
    rev = np.clip(((t / 1.0) * (W + 400) - xx) / 200, 0, 1)
    ca = np.clip(corda * 1.6, 0, 1) * rev * perto * 0.95
    PC = np.where((ca > PA)[..., None], (np.array(PAL, np.float32) / 255)[faixa], PC); PA = np.maximum(PA, ca)
    # ---- prédios: rosa na borda com o céu + janelas amarelas ----
    ceud = cv2.dilate(ceu, np.ones((31, 31), np.uint8))
    for n, c in enumerate(contornos(pr, 4000, 6, 6, ceud)):
        traco(L, A, parcial(tremer(c, j, 1.8, 10 + n), ease((t - 0.5 - 0.1 * n) / 1.0)), ROSA, 7)
    if t > 1.0:
        inner = cv2.erode(pr, np.ones((15, 15), np.uint8))
        e2 = cv2.dilate(cv2.Canny(cv2.GaussianBlur(gray8, (0, 0), 1.4), 50, 120), np.ones((2, 2), np.uint8))
        pa = (e2 > 0) & (inner > 0)
        A = np.maximum(A, (pa * 255 * 0.85 * ease((t - 1.0) / 1.0)).astype(np.uint8)); L[pa] = AMAR
    # ---- vegetação: topo da cerca viva/árvores em lima + eco laranja tracejado ----
    vegd = cv2.dilate(cv2.bitwise_or(ceu, pr), np.ones((25, 25), np.uint8))
    for n, c in enumerate(contornos(veg, 20000, 3, 7, vegd, 30)):
        c = tremer(c, j, 2.0, 30 + n)
        traco(L, A, parcial(c, ease((t - 0.2) / 1.0)), LIMA, 9)
        for s in tracejar(parcial(c + [0, -26], ease((t - 0.45) / 1.0)), 36, 22, t * 130): traco(L, A, s, LARANJA, 6)
    # ---- tronco da palmeira (blob alto que toca o topo): contorno + hachura ----
    vo = cv2.morphologyEx(veg, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    cols_ = np.nonzero(vo[:500].sum(0) > 150)[0]
    if t >= T_PALMA and len(cols_) > 40:
        m = vo.copy(); m[:, :max(0, cols_.min() - 60)] = 0; m[:, cols_.max() + 60:] = 0
        y0, h0 = 0, H; tp = T_PALMA
        rv = ease((t - tp) / 0.9)
        hat = (((xx - CR[j, 200] + yy * 0.9) % 30) < 9) & (m > 0) & (yy < y0 + h0 * rv + 1)
        hv = (cv2.GaussianBlur(hat.astype(np.float32), (0, 0), 0.8) * 0.62 * 255).astype(np.uint8)
        sel = hv > 20; L[sel] = ROXO; A = np.maximum(A, hv)
        for c in contornos(m, 30000, 1, 9, None):
            traco(L, A, parcial(tremer(c, j, 2.5, 70), ease((t - tp) / 0.8)), LARANJA, 8)
    # ---- sol desenhado ----
    if t > 0.3:
        cx, cy = SOL[j]; fs = ease((t - 0.3) / 0.8)
        R0 = 70
        circ = np.stack([cx + np.cos(np.linspace(0, 2 * np.pi, 120)) * R0, cy + np.sin(np.linspace(0, 2 * np.pi, 120)) * R0], 1)
        traco(L, A, parcial(tremer(circ, j, 2.0, 80), fs), AMAR, 9)
        rot = t * 0.4
        for i in range(12):
            a_ = rot + i * np.pi / 6; r1 = R0 + 28; r2 = R0 + (70 if i % 2 == 0 else 48)
            ray = np.array([[cx + np.cos(a_) * r1, cy + np.sin(a_) * r1], [cx + np.cos(a_) * r2, cy + np.sin(a_) * r2]])
            ray = np.linspace(ray[0], ray[1], 8)
            if fs > (i + 1) / 13: traco(L, A, tremer(ray, j, 1.5, 81 + i), LARANJA if i % 2 else AMAR, 7)
    # ---- rabiscos no chão (presos ao mundo, longe dos pés) ----
    Lc = np.zeros((H, W, 3), np.uint8); Ac = np.zeros((H, W), np.uint8)
    for n, (fm, xw, y, a_, c, ph) in enumerate(CHAO):
        x = xw + CR[j, y // 2]
        if x < -120 or x > W + 120: continue
        if chao[min(y, H - 1), int(np.clip(x, 0, W - 1))] == 0: continue
        pts = FORMAS[fm](a_) * [1, 0.55]
        wob = np.sin(t * 4 + ph) * 0.07
        Rm = np.array([[np.cos(wob), -np.sin(wob)], [np.sin(wob), np.cos(wob)]])
        f_ = ease((t - 0.3 - max(0, x - 200) / 1400) / 0.5)
        traco(Lc, Ac, parcial(tremer(pts @ Rm.T + [x, y], j, 1.5, 100 + n), f_), c, 8)
    ac = Ac.astype(np.float32) / 255 * longe
    # palavras no chão
    Tch = np.zeros((H, W, 4), np.float32)
    for (txt, c, t0), sp, xw in zip(PAL_CHAO, SPCH, XW_CH):
        x = xw + CR[j, YCH // 2]
        if -400 < x < W + 400:
            sq = cv2.resize(sp, None, fx=1.0, fy=0.62)      # deitada no chão
            colar(Tch, sq, x, YCH, pop(t, t0, 0.3))
    Tch[..., 3] *= longe
    a = A.astype(np.float32) / 255 * perto; col = L.astype(np.float32) / 255
    a = np.maximum(a, ac); col = np.where((ac > 0)[..., None], Lc.astype(np.float32) / 255, col)
    bg = compor_tinta_linhas(fr, gray, PA, PC, a, col)
    bg = por_texto(bg, Tch, sombra=5)
    # ---- contorno da pessoa ----
    if t > 0.5:
        bm = (pm > 0.5).astype(np.uint8)
        dentro = lambda c: (c[:, 1] < H - 8) & (c[:, 0] > 4) & (c[:, 0] < W - 5)
        Lp = np.zeros((H, W, 3), np.uint8); Ap = np.zeros((H, W), np.uint8)
        for raio, esp, corx, tr_, d0 in [(37, 9, ROSA, False, 0.5), (75, 6, AMAR, True, 0.8)]:
            cs, _ = cv2.findContours(cv2.dilate(bm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (raio, raio))), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not cs: continue
            c = suav_fech(max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float32), 9 if not tr_ else 12)
            c = parcial(tremer(c, j, 2.4, 90 + raio), ease((t - d0) / 1.0))
            if tr_:
                for s in tracejar(c, 34, 24, t * 150):
                    if dentro(s).all(): traco(Lp, Ap, s, corx, esp)
            else:
                cur = []
                for p, k in zip(c, dentro(c)):
                    if k: cur.append(p)
                    else:
                        if len(cur) > 10: traco(Lp, Ap, np.array(cur), corx, esp)
                        cur = []
                if len(cur) > 10: traco(Lp, Ap, np.array(cur), corx, esp)
        ap = Ap.astype(np.float32) / 255 * np.clip((dist - 3) / 6, 0, 1)
        bg = bg * (1 - ap[..., None]) + Lp.astype(np.float32) / 255 * ap[..., None]
    tt = titulo(t, TIT, 0.4, 4.1, 300)
    if tt is not None: bg = por_texto(bg, tt, bgr=False)
    if t > CEU[0][2]:
        Tf = np.zeros((H, W, 4), np.float32)
        for (txt, c, t0, y, sz), sp in zip(CEU, SPC):
            sc = pop(t, t0)
            if sc > 0: colar(Tf, sp, W / 2 + np.sin(t * 5 + t0 * 3) * 3, y, sc)
        bg = por_texto(bg, Tf, sombra=9)
    o = bg * (1 - pm[..., None]) + fr * pm[..., None]
    o = (np.clip(o, 0, 1) * 255).astype(np.uint8)
    if prev: cv2.imwrite(f'olhar/prev_{j+1:05d}.jpg', o)
    else: out.stdin.write(o.tobytes())
    if j % 50 == 0: print(j, flush=True)
if out: out.stdin.close(); out.wait(); print('ok')
