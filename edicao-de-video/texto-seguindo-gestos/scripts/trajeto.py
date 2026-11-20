"""corpo.json + maos.json -> maos2.npy [N, 2, xy]: ponta de cada mão por quadro.
Mão 0 = a que aparece à ESQUERDA da tela (mão direita da pessoa), mão 1 = à direita da tela.
O pulso vem da pose do corpo (estável com braço aberto); a ponta vem do dedo indicador da pose da mão
quando ela está perto do pulso, senão prolonga o antebraço 35%."""
import json, numpy as np
import os
C = json.load(open("corpo.json")); N = len(C)
M = json.load(open("maos.json")) if os.path.exists("maos.json") else [[] for _ in range(N)]
if len(M) < N: M += [[] for _ in range(N - len(M))]
out = np.full((N, 2, 2), np.nan)
for i in range(N):
    for k, (w, e) in enumerate((("rw", "re"), ("lw", "le"))):
        if w not in C[i] or C[i][w][2] < 0.25: continue
        wr = np.array(C[i][w][:2])
        best = None
        for h in M[i]:
            t = h.get("indexTip") or h.get("middleTip"); hw = h.get("wrist")
            if t and hw and np.hypot(*(np.array(hw[:2]) - wr)) < 70:
                if best is None or t[2] > best[2]: best = t
        if best is not None: out[i, k] = best[:2]
        elif e in C[i]:
            el = np.array(C[i][e][:2]); out[i, k] = wr + (wr - el) * 0.35
        else: out[i, k] = wr
np.save("maos2.npy", out)
print("quadros com mão (esq, dir):", np.isfinite(out[:, :, 0]).sum(0), "de", N)
