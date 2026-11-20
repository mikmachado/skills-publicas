# Render "desenhos animados" para pessoa na frente de uma parede (câmera parada ou na mão).
# Precisa na pasta do projeto: quadros/, mask/, homog.npy, pedras_lab.npy (opcional), config JSON.
# uso: python render_parede.py config.json [ini fim] [prev]
#   prev = salva olhar/prev_XXXXX.jpg de cada quadro em vez de gerar vídeo (use ini fim curtos)
import sys, os, json, subprocess, cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'comum'))
from desenho import *

cfg = json.load(open(sys.argv[1])); args = sys.argv[2:]
prev = 'prev' in args; nums = [int(a) for a in args if a.isdigit()]
HS = np.load('homog.npy'); N = len(HS)
fr0 = cv2.imread('quadros/00001.jpg'); H_, W_ = fr0.shape[:2]
assert (W_, H_) == (W, H), 'esperado 1080x1920 (redimensione os quadros antes)'
cor = lambda nome: CORES[nome]
r = np.random.RandomState(cfg.get('semente', 7))

# ---------- peças (pedras/azulejos) ----------
pc = cfg.get('pedras', {})
LAB = np.load('pedras_lab.npy') if os.path.exists('pedras_lab.npy') and pc.get('ativo', True) else np.zeros((H, W), np.int32)
NP = int(LAB.max())
cen = np.zeros((NP + 1, 2)); cont = [None] * (NP + 1)
for v in range(1, NP + 1):
    m = (LAB == v).astype(np.uint8); ys, xs = np.nonzero(m); cen[v] = [xs.mean(), ys.mean()]
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float32)
    if len(c) > 40: c = suav_fech(c, 5)
    cont[v] = np.r_[c, c[:1]]
pinta = r.rand(NP + 1) < pc.get('fracao_pintada', 0.68)
cor_i = r.randint(len(PAL), size=NP + 1)
for v in range(1, NP + 1):            # evita vizinha com a mesma cor
    d = np.linalg.norm(cen[1:] - cen[v], axis=1); d[v - 1] = 1e9; nb = 1 + np.argmin(d)
    if cor_i[nb] == cor_i[v]: cor_i[v] = (cor_i[v] + 2) % len(PAL)
ORIG = np.array(pc.get('origem_onda', [540, 1000]), float)
t_pop = pc.get('t_inicio', 0.25) + np.linalg.norm(cen - ORIG, axis=1) / pc.get('velocidade_onda', 650) + r.rand(NP + 1) * 0.25
palf = np.array(PAL, np.float32) / 255
ALFA = pc.get('opacidade', 0.82)

# ---------- textos ----------
tit = cfg.get('titulo')
PAREDE = cfg.get('palavras_parede', [])
SPR = [sprite(p['texto'], p['tam'], cor(p['cor']), p.get('giro', 0)) for p in PAREDE]
FIM_WALL = cfg.get('palavras_parede_saem', 1e9)
FINAL = cfg.get('final', [])
SPF = [sprite(p['texto'], p['tam'], cor(p['cor']), 0, 11) for p in FINAL]
cos = cfg.get('costura')            # {"a":..., "b":...}  y = a + b*x no quadro 1
CHAO = cfg.get('rabiscos_chao', [])
contorno = cfg.get('contorno_pessoa', True)

ini, fim = (nums + [0, N])[:2] if len(nums) >= 2 else (0, N)
out = None if prev else subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
     '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', 'linhas_mudo.mp4'], stdin=subprocess.PIPE)
os.makedirs('olhar', exist_ok=True)
for j in range(ini, fim):
    t = j / FPS; Hj = HS[j]
    fr = cv2.imread(f'quadros/{j+1:05d}.jpg').astype(np.float32) / 255
    pm = masc(j)
    dist = cv2.distanceTransform((pm < 0.3).astype(np.uint8), cv2.DIST_L2, 5)
    gray = cv2.GaussianBlur(cv2.cvtColor((fr * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY), (0, 0), 2.2)
    # ---- tinta das peças (no quadro 1, depois entorta pro quadro j) ----
    if NP:
        pp = np.clip((t - t_pop) / 0.22, 0, 1); av = np.where(pinta, ALFA * pp, 0).astype(np.float32); av[0] = 0
        flash = np.where(pinta, np.clip(1 - (t - t_pop) / 0.25, 0, 1) * (t >= t_pop), 0) * 0.6; flash[0] = 0
        PCr = palf[cor_i][LAB]; PCr = PCr + (1 - PCr) * flash[LAB][..., None]
        PA = cv2.warpPerspective(av[LAB], Hj, (W, H), flags=cv2.INTER_LINEAR)
        PC = cv2.warpPerspective(PCr, Hj, (W, H), flags=cv2.INTER_LINEAR)
        PA *= np.clip((dist - 4) / 8, 0, 1)
    else:
        PA = np.zeros((H, W), np.float32); PC = np.zeros((H, W, 3), np.float32)
    # ---- linhas presas ao cenário ----
    Lr = np.zeros((H, W, 3), np.uint8); Ar = np.zeros((H, W), np.uint8)
    for v in range(1, NP + 1):
        if pinta[v]: continue          # peça sem tinta ganha contorno colorido
        f_ = ease((t - t_pop[v] - 0.1) / 0.7)
        if f_ > 0: traco(Lr, Ar, parcial(tremer(cont[v], j, 1.6, v), f_), PAL[(cor_i[v] + 1) % 6], 6)
    if cos:
        xs = np.arange(0, W + 1, 6.0); sm = np.stack([xs, cos['a'] + cos['b'] * xs], 1)
        traco(Lr, Ar, parcial(tremer(sm, j, 1.4, 3), ease((t - 0.15) / 0.9)), AMAR, 11)
        for s in tracejar(parcial(tremer(sm + [0, 30], j, 1.4, 4), ease((t - 0.35) / 0.9)), 40, 22, -t * 140):
            traco(Lr, Ar, s, CIANO, 7)
    for n, rb in enumerate(CHAO):
        f_ = ease((t - rb['t']) / 0.6)
        if f_ <= 0: continue
        pts = FORMAS[rb['forma']](rb['tam']) * [1, rb.get('achatar', 0.55)]
        wob = np.sin(t * 4 + n) * 0.06
        R = np.array([[np.cos(wob), -np.sin(wob)], [np.sin(wob), np.cos(wob)]])
        pts = pts @ R.T + [rb['x'], rb['y']]
        traco(Lr, Ar, parcial(tremer(pts, j, 1.5, 50 + n), f_), cor(rb['cor']), 8)
    L = cv2.warpPerspective(Lr, Hj, (W, H), flags=cv2.INTER_LINEAR)
    A = cv2.warpPerspective(Ar, Hj, (W, H), flags=cv2.INTER_LINEAR)
    # ---- contorno da pessoa (na tela) ----
    if contorno and t > 0.6:
        bm = (pm > 0.5).astype(np.uint8)
        dentro = lambda c: (c[:, 1] < H - 8) & (c[:, 0] > 4) & (c[:, 0] < W - 5)
        for raio, esp, corx, tr_, d0 in [(37, 9, ROSA, False, 0.6), (75, 6, AMAR, True, 0.9)]:
            dil = cv2.dilate(bm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (raio, raio)))
            cs, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if not cs: continue
            c = suav_fech(max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float32), 9 if not tr_ else 12)
            c = tremer(c, j, 2.4 if not tr_ else 2.0, 90 + raio)
            c = parcial(c, ease((t - d0) / 1.2))
            if tr_:
                for s in tracejar(c, 34, 24, t * 150):
                    if dentro(s).all(): traco(L, A, s, corx, esp)
            else:
                ok = dentro(c); cur = []
                for p, k in zip(c, ok):
                    if k: cur.append(p)
                    else:
                        if len(cur) > 10: traco(L, A, np.array(cur), corx, esp)
                        cur = []
                if len(cur) > 10: traco(L, A, np.array(cur), corx, esp)
    a = A.astype(np.float32) / 255 * np.clip((dist - 3) / 6, 0, 1); col = L.astype(np.float32) / 255
    bg = compor_tinta_linhas(fr, gray, PA, PC, a, col)
    # ---- palavras pintadas na parede (presas ao cenário) ----
    if PAREDE and min(p['t'] for p in PAREDE) - 0.1 < t < FIM_WALL + 0.5:
        Tr = np.zeros((H, W, 4), np.float32)
        sai = 1 - ease((t - FIM_WALL) / 0.4)
        for p, sp in zip(PAREDE, SPR):
            sc = pop(t, p['t'])
            if sc > 0: colar(Tr, sp, p['x'], p['y'] + np.sin(t * 4 + p['t'] * 3) * 3, sc * (1 + 0.25 * (1 - sai)), sai)
        bg = por_texto(bg, cv2.warpPerspective(Tr, Hj, (W, H), flags=cv2.INTER_LINEAR))
    if tit:
        tt = titulo(t, tit['linhas'], tit.get('t0', 0.45), tit.get('t1', 4.5), tit.get('y', 330))
        if tt is not None: bg = por_texto(bg, tt, bgr=False)
    if FINAL and t > FINAL[0]['t']:
        Tf = np.zeros((H, W, 4), np.float32)
        for p, sp in zip(FINAL, SPF):
            sc = pop(t, p['t'])
            if sc > 0: colar(Tf, sp, W / 2 + np.sin(t * 5 + p['t'] * 3) * 3, p['y'], sc)
        bg = por_texto(bg, Tf, sombra=9)
    o = bg * (1 - pm[..., None]) + fr * pm[..., None]       # pessoa sempre por cima
    o = (np.clip(o, 0, 1) * 255).astype(np.uint8)
    if prev: cv2.imwrite(f'olhar/prev_{j+1:05d}.jpg', o)
    else: out.stdin.write(o.tobytes())
    if j % 50 == 0: print(j, flush=True)
if out: out.stdin.close(); out.wait(); print('ok linhas_mudo.mp4')
