"""Efeitos sonoros sintetizados (pop, whoosh, ding, riser…) — sem arquivos externos."""
import wave
import numpy as np

SR = 48000


class Som:
    def __init__(self, dur, seed=5):
        self.out = np.zeros(int(dur * SR) + SR); self.rng = np.random.default_rng(seed); self.dur = dur

    def poe(self, y, t, g=0.5):
        i = max(0, int(t * SR)); n = min(len(y), len(self.out) - i)
        if n > 0: self.out[i:i + n] += g * y[:n]

    def _t(self, d): n = int(d * SR); return n, np.arange(n) / SR

    def whoosh(self, t, d=0.4, g=0.5):
        n, tt = self._t(d); x = self.rng.normal(0, 1, n); y = np.zeros(n); a = 0.0
        k = 0.02 + 0.3 * np.sin(np.pi * tt / d) ** 2
        for i in range(n): a += k[i] * (x[i] - a); y[i] = a
        self.poe(1.2 * y * np.sin(np.pi * tt / d) ** 1.6, t - d * 0.6, g)

    def pop(self, t, f0=560, g=0.45):
        n, tt = self._t(0.14); f = f0 * (1 + 1.6 * (1 - np.exp(-tt * 40)))
        self.poe(0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(tt / 0.002, 1) * np.exp(-tt * 30), t, g)

    def tique(self, t, f0=1800, g=0.3):
        n, tt = self._t(0.05); self.poe(np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 90), t, g)

    def clique(self, t, g=0.35):
        n, tt = self._t(0.03); self.poe(self.rng.normal(0, 1, n) * np.exp(-tt * 220), t, g)

    def digita(self, t0, t1, g=0.18):
        t = t0
        while t < t1: self.clique(t, g * self.rng.uniform(0.6, 1)); t += self.rng.uniform(0.045, 0.09)

    def flash(self, t, g=0.5):  # obturador
        self.clique(t, g); self.clique(t + 0.07, g * 0.7)
        n, tt = self._t(0.25); self.poe(self.rng.normal(0, 1, n) * np.exp(-tt * 30) * 0.3, t, g)

    def baque(self, t, g=0.6):
        n, tt = self._t(0.35); f = 120 * np.exp(-tt * 8) + 45
        self.poe(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9), t, g)

    def ding(self, t, f0=1318, g=0.4):
        n, tt = self._t(0.6); y = np.zeros(n)
        for at, f in ((0, f0), (0.08, f0 * 1.335)):
            u = np.clip(tt - at, 0, None); y += (tt >= at) * np.exp(-u * 8) * (np.sin(2 * np.pi * f * u) + 0.3 * np.sin(2 * np.pi * 2.76 * f * u))
        self.poe(0.4 * y, t, g)

    def sobe(self, t, d=0.8, g=0.35):  # riser
        n, tt = self._t(d); f = 200 + 900 * (tt / d) ** 2
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * (tt / d) ** 2 + 0.3 * self.rng.normal(0, 1, n) * (tt / d) ** 3
        self.poe(y * 0.5, t - d, g)

    def vidro(self, t, g=0.55):  # estilhaço
        n, tt = self._t(0.9); y = self.rng.normal(0, 1, n) * np.exp(-tt * 14) * 0.6
        for k in range(14):
            at = self.rng.uniform(0, 0.6); f = self.rng.uniform(2500, 6500); u = np.clip(tt - at, 0, None)
            y += (tt >= at) * np.sin(2 * np.pi * f * u) * np.exp(-u * 40) * 0.25
        self.poe(y, t, g); self.baque(t, g * 0.6)

    def papel(self, t, g=0.4):
        n, tt = self._t(0.25); x = self.rng.normal(0, 1, n)
        y = np.diff(np.concatenate([[0], x])) * (self.rng.uniform(0, 1, n) > 0.6) * np.exp(-tt * 10)
        self.poe(y, t, g)

    def salva(self, path):
        o = self.out[:int(self.dur * SR)]
        pk = np.abs(o).max()
        o = o / pk * 0.6 if pk > 0.6 else o
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(o, -1, 1) * 32767).astype(np.int16).tobytes())
