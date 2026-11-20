#!/usr/bin/env python3
"""Acha os gestos (trechos em que as mãos desenham algo grande), adivinha a forma de cada um e
casa com as frases faladas. Escreve:
  gestos.jpg              -> uma imagem por gesto com o traço das mãos (olhe antes de confiar!)
  projeto_sugerido.json   -> ponto de partida do projeto.json (copie, revise e ajuste)
Rode de dentro da pasta do projeto, depois do preparar.sh:
  python3 -I <skill>/scripts/gestos.py [--altura 160]   (quanto a mão sobe acima do descanso p/ contar como gesto)
"""
import json, sys, os, math
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maos_util import carregar, suav

FPS, W, H = 30, 1080, 1920
PS = carregar("maos2.npy"); N = len(PS[0])
VEL = [suav(np.r_[0, np.hypot(*np.diff(p, axis=0).T)], 3) for p in PS]

# ---------- trechos com a mão levantada ----------
# cada gesto começa e termina com as mãos embaixo (colo, lados do corpo): o gesto é o trecho em que
# pelo menos uma mão está bem acima da posição de descanso dela
REPOUSO = [np.nanpercentile(p[:, 1], 80) for p in PS]
ALT = float(sys.argv[sys.argv.index("--altura") + 1]) if "--altura" in sys.argv else 160
alta = [PS[k][:, 1] < REPOUSO[k] - ALT for k in range(2)]
ativo = alta[0] | alta[1]
for i in range(1, N - 4):                      # fecha falhas de até 4 quadros
    if not ativo[i] and ativo[i - 1] and ativo[i + 1:i + 5].any(): ativo[i] = True
segs, i = [], 0
while i < N:
    if ativo[i]:
        j = i
        while j < N and ativo[j]: j += 1
        segs.append([max(0, i - 4), min(N, j + 4)]); i = j
    else: i += 1
gestos = []
for a, b in segs:
    curso = [VEL[k][a:b].sum() for k in range(2)]
    if (b - a) / FPS < 0.6 or max(curso) < 450: continue
    maos = [k for k in range(2) if alta[k][a:b].mean() > 0.35 and curso[k] > 0.3 * max(curso)] or [int(np.argmax(curso))]
    gestos.append({"a": a, "b": b, "maos": maos, "curso": curso})

# ---------- forma de cada gesto ----------
def reamostra(P, passo=30):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    u = np.arange(0, d[-1], passo)
    return np.stack([np.interp(u, d, P[:, 0]), np.interp(u, d, P[:, 1])], 1) if len(u) > 2 else P

def cobertura(P, c):
    ang = np.degrees(np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])) % 360
    h = np.zeros(36, bool); h[(ang // 10).astype(int)] = True
    return h.sum() * 10, h

def cantos(P):
    Q = reamostra(P, 40)
    if len(Q) < 5: return 0
    v = np.diff(Q, axis=0); a = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    da = np.abs((np.diff(a) + 180) % 360 - 180)
    da = np.convolve(da, [1, 1], "same")
    return int(((da[1:-1] > 55) & (da[1:-1] >= da[:-2]) & (da[1:-1] >= da[2:])).sum())

def classificar(g):
    a, b = g["a"], g["b"]
    P = np.vstack([PS[k][a:b] for k in g["maos"]])
    x0, y0 = np.percentile(P, 3, axis=0); x1, y1 = np.percentile(P, 97, axis=0)
    w, h = x1 - x0, y1 - y0
    c = ((x0 + x1) / 2, (y0 + y1) / 2)
    g["caixa"] = [int(x0), int(y0), int(x1), int(y1)]
    principal = PS[g["maos"][0]][a:b]
    if max(w, h) < 380 or w < 250:
        g["tipo"] = "pequeno"; return
    # uma mão: quadrado se passa perto dos dois cantos de cima da caixa; senão arco por cima
    diag = math.hypot(w, h)
    perto = lambda q: np.hypot(*(principal - q).T).min() < 0.2 * diag
    if perto((x0, y0)) and perto((x1, y0)):
        g["tipo"] = "retangulo"
        g["forma"] = {"tipo": "retangulo", "x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1) + 60, "r": 70}
        return
    # linha: o trecho mais longo em que a mão anda na horizontal (y numa faixa de ±50 px)
    if len(g["maos"]) == 1:
        melhor = (0, 0, 0)
        for i in range(len(principal)):
            j = i
            while j + 1 < len(principal) and abs(principal[j + 1, 1] - principal[i:j + 2, 1].mean()) < 50: j += 1
            xs = principal[i:j + 1, 0]
            if np.ptp(xs) > melhor[0]: melhor = (np.ptp(xs), i, j)
        largura, i, j = melhor
        if largura > 280 and (j - i + 1) > 0.3 * len(principal):
            g["tipo"] = "linha"; yl = int(np.median(principal[i:j + 1, 1]))
            g["forma"] = {"tipo": "linha", "x0": 110, "y0": yl, "x1": 970, "y1": yl}
            if principal[j, 0] < principal[i, 0]:
                g["obs"] = "(mão vai da direita pra esquerda: use espelhar ou esquerda_pra_direita)"
            return
    if len(g["maos"]) == 2:
        juntas = np.hypot(*(PS[0][a:a + 12] - PS[1][a:a + 12]).T).mean() < 400
        if juntas:      # sobem juntas pelo meio e abrem para os lados
            g["tipo"] = "arco"
            g["forma"] = {"tipo": "arco", "cx": int(c[0]), "base": int(y1), "rx": int(w / 2), "alt": int(h)}
        else:           # saem dos lados e dão a volta
            g["tipo"] = "elipse"
            g["forma"] = {"tipo": "elipse", "cx": int(c[0]), "cy": int(c[1]), "rx": int(w / 2), "ry": int(h / 2), "a0": 180, "a1": 540}
        return
    _, hist = cobertura(principal, c)
    if hist.sum() * 10 >= 300:
        g["tipo"] = "elipse"
        g["forma"] = {"tipo": "elipse", "cx": int(c[0]), "cy": int(c[1]), "rx": int(w / 2), "ry": int(h / 2), "a0": 180, "a1": 540}
        return
    g["tipo"] = "arco"
    g["forma"] = {"tipo": "elipse", "cx": int(c[0]), "cy": int(y1), "rx": int(w / 2), "ry": int(h), "a0": 180, "a1": 360}

for g in gestos: classificar(g)
gestos = [g for g in gestos if g["tipo"] != "pequeno"]

# ---------- frases (quebra em pontuação e pausas > 0,35 s) ----------
TROCAS = {"CLAUDIO": "CLAUDE", "CLOUD": "CLAUDE"}
ws = [w for s in json.load(open("transcricao.json")) for w in s["w"]]
frases, cur = [], []
for i, w in enumerate(ws):
    cur.append(w)
    pausa = i + 1 < len(ws) and ws[i + 1]["s"] - w["e"] > 0.35
    if w["w"].strip()[-1:] in ",.?!:;" or pausa or i == len(ws) - 1:
        t = " ".join(TROCAS.get(x["w"].upper().strip(",.?!:;"), x["w"].upper().strip(",.?!:;")) for x in cur)
        frases.append({"s": cur[0]["s"], "e": cur[-1]["e"], "t": t}); cur = []

def sobreposicao(a0, a1, b0, b1): return max(0, min(a1, b1) - max(a0, b0))
# cada frase vai para o gesto com que mais se sobrepõe (a fala costuma vir um pouco antes do gesto)
dono = {}
for i, f in enumerate(frases):
    ov = [sobreposicao(g["a"] / FPS - 0.6, g["b"] / FPS + 0.3, f["s"], f["e"]) for g in gestos]
    if ov and max(ov) > 0.5 * (f["e"] - f["s"]): dono[i] = int(np.argmax(ov))
for n, g in enumerate(gestos):
    g["frase"] = " ".join(frases[i]["t"] for i in sorted(dono) if dono[i] == n)
usados = set(dono)

def quebra(txt, n):
    ws = txt.split(); alvo = len(txt) / n; out, cur = [], ""
    for w in ws:
        if cur and len(cur) + len(w) + 1 > alvo * 1.15 and len(out) < n - 1: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return out + [cur]

proj = {"quadros": "quadros", "trocas": {"CLAUDIO": "CLAUDE"}, "espelhar": [], "formas": [], "blocos": []}
for g in gestos:
    t0, t1 = round(g["a"] / FPS, 2), round(g["b"] / FPS, 2)
    F = dict(g["forma"]); txt = g["frase"] or "???"
    if F["tipo"] == "retangulo": F["linhas"] = quebra(txt, 3)
    elif F["tipo"] == "linha" and len(txt) > 24: F["linhas"] = quebra(txt, 2)
    else: F["linhas"] = [txt]
    if F["tipo"] == "elipse" and F.get("a1") == 540 and len(txt) < 30: F["linhas"] = [f"{txt}  •  {txt}  •"]
    F.update({"maos": g["maos"], "g0": t0, "g1": t1, "fecha": round(t1 - 0.1, 2), "sai": round(t1 + 0.6, 2), "tam": 96})
    F["_detectado"] = f"{g['tipo']} {t0}-{t1}s mãos {g['maos']} " + g.get("obs", "")
    proj["formas"].append(F)
for i, f in enumerate(frases):
    if i in usados: continue
    lin = quebra(f["t"], max(1, min(3, round(len(f["t"]) / 16))))
    proj["blocos"].append({"linhas": [[l, 92] for l in lin], "y0": 250, "t0": round(f["s"] - 0.1, 2), "sai": round(f["e"] + 0.3, 2),
                           "_sobre": "frase sem gesto grande (ou troque por uma forma)"})
json.dump(proj, open("projeto_sugerido.json", "w"), ensure_ascii=False, indent=1)

# ---------- imagem de conferência ----------
ims = []
for n, g in enumerate(gestos):
    a, b = g["a"], g["b"]
    im = cv2.imread(f"quadros/{(a + b) // 2 + 1:04d}.jpg")
    for k, col in ((0, (0, 0, 255)), (1, (255, 120, 0))):
        for f in range(a, b, 1):
            c = (f - a) / max(1, b - a)
            cv2.circle(im, tuple(int(v) for v in PS[k][f]), 9 if k in g["maos"] else 4, tuple(int(x * (0.35 + 0.65 * c)) for x in col), -1)
        for f in range(a, b, 15):
            cv2.putText(im, f"{f / FPS:.1f}", (int(PS[k][f, 0]) + 12, int(PS[k][f, 1])), 0, 1.0, (255, 255, 255), 3)
    cv2.putText(im, f"{n + 1}. {g['tipo']} {a / FPS:.1f}-{b / FPS:.1f}s", (24, 80), 0, 2.0, (0, 0, 0), 9)
    cv2.putText(im, f"{n + 1}. {g['tipo']} {a / FPS:.1f}-{b / FPS:.1f}s", (24, 80), 0, 2.0, (255, 255, 255), 3)
    ims.append(cv2.resize(im, (360, 640)))
if ims: cv2.imwrite("gestos.jpg", np.hstack(ims))
for n, g in enumerate(gestos):
    print(f"{n + 1}. {g['a'] / FPS:5.2f}-{g['b'] / FPS:5.2f}s  {g['tipo']:9s} mãos {g['maos']}  «{g['frase']}» {g.get('obs', '')}")
print(f"\n{len(gestos)} gestos -> gestos.jpg, projeto_sugerido.json ({len(proj['blocos'])} frase(s) sem gesto viraram bloco)")
