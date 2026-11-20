"""Leitura e limpeza das trilhas das mãos (usado por gestos.py e formas.py)."""
import numpy as np

def suav(a, s):
    r = int(3 * s); kk = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); kk /= kk.sum()
    return np.convolve(np.pad(a, r, mode="edge"), kk, "valid")

def limpar(P):
    """tira as piscadas do detector (pula entre a mão certa e o colo), preenche buracos e suaviza"""
    P = P.copy(); N = len(P); ok = np.isfinite(P[:, 0]); Q = P.copy()
    for i in range(N):
        j = [x for x in range(max(0, i - 4), min(N, i + 5)) if ok[x]]
        if len(j) >= 3 and ok[i]:
            med = np.median(P[j], axis=0)
            if np.hypot(*(P[i] - med)) > 110: Q[i] = med
    P = Q; idx = np.arange(N)
    if ok.sum() < 2: return np.full((N, 2), np.nan)
    for k in range(2): P[:, k] = np.interp(idx, idx[ok], P[ok, k])
    return np.stack([suav(P[:, 0], 1.8), suav(P[:, 1], 1.8)], 1)

def carregar(arq="maos2.npy"):
    M = np.load(arq)
    return [limpar(M[:, k]) for k in range(2)]
