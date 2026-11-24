#!/usr/bin/env python3
"""Mixa voz + batida sintetizada (abaixa sob a voz) + efeitos sonoros nos eventos das cenas.
Uso: python3 audio.py projeto.json   -> <saida>/mix.wav
Tudo é sintetizado aqui (livre para usar)."""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor as M
M.carregar(sys.argv[1])
SR = 48000; D = M.DUR; P = M.PROJ
rng = np.random.default_rng(1)
def novo(): return np.zeros(int(SR * D), np.float32)
def put(buf, a, t, g=1.0):
    i = int(t * SR)
    if i < 0: a = a[-i:]; i = 0
    if i >= len(buf): return
    a = a[:len(buf) - i]; buf[i:i + len(a)] += a * g
def env(n, dec): return np.exp(-np.arange(n) / SR * dec)
def pop(f=600, d=0.07):
    t = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * t * (1 - 2 * t)) * np.exp(-t * 60)
def whoosh(d=0.22):
    n = int(SR * d); x = np.convolve(rng.normal(0, 1, n), np.ones(25) / 25, "same")
    return x * np.sin(np.linspace(0, np.pi, n)) ** 2 * 3
def thump():
    t = np.arange(int(SR * 0.3)) / SR; return np.sin(2 * np.pi * (50 + 110 * np.exp(-t * 35)) * t) * np.exp(-t * 12)
def clap():
    n = int(SR * 0.12); return np.convolve(rng.normal(0, 1, n) * env(n, 35), [1, -0.6], "same") * 0.6
def hat():
    n = int(SR * 0.04); return np.diff(rng.normal(0, 1, n), prepend=0) * env(n, 110) * 0.5
def bass(f, d):
    t = np.arange(int(SR * d)) / SR; s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * t)
    return np.convolve(s, np.ones(40) / 40, "same") * np.minimum(1, t * 80) * np.exp(-t * 3)
def estrondo():
    n = int(SR * 0.6); t = np.arange(n) / SR
    return rng.normal(0, 1, n) * env(n, 6) * 0.6 + np.sin(2 * np.pi * (80 * np.exp(-t * 4)) * t) * env(n, 5)
def ding(f=1320):
    t = np.arange(int(SR * 0.5)) / SR; return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t)) * np.exp(-t * 7)
def risco():
    n = int(SR * 0.18); x = np.convolve(rng.normal(0, 1, n), np.ones(6) / 6, "same")
    return x * np.sin(np.linspace(0, np.pi, n)) * (0.6 + 0.4 * np.sin(np.linspace(0, 40, n))) * 1.5
SONS = {"pop": lambda k: pop(450 + (k % 8) * 60), "pop_curto": lambda k: pop(700 + (k % 12) * 40, 0.05),
        "whoosh": lambda k: whoosh(), "whoosh_longo": lambda k: whoosh(0.3), "estrondo": lambda k: estrondo(),
        "ding": lambda k: ding(), "risco": lambda k: risco()}

bed = novo()
if P.get("musica", True):
    bpm = P.get("bpm", 124); b = 60 / bpm; notas = [55, 55, 65.4, 49]
    for j in range(int(D / b) + 1):
        t = j * b
        put(bed, thump(), t, 0.55)
        if j % 2 == 1: put(bed, clap(), t, 0.22)
        put(bed, hat(), t + b / 2, 0.18); put(bed, hat(), t + b * 0.75, 0.08)
        put(bed, bass(notas[(j // 4) % 4], b * 0.9), t, 0.16)
    k0 = int((D - 0.6) * SR); bed[k0:] *= np.linspace(1, 0, len(bed) - k0)
sfx = novo()
for k, (tipo, t, g) in enumerate(M.eventos()): put(sfx, SONS[tipo](k), t, g)
w = wave.open(os.path.join(M.PDIR, P.get("voz", "voz.wav")))
v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
if w.getnchannels() == 2: v = v.reshape(-1, 2).mean(1)
voz = novo(); voz[:min(len(v), len(voz))] = v[:len(voz)]
e = np.convolve(np.abs(voz), np.ones(SR // 20) / (SR // 20), "same"); duck = 1 - 0.45 * np.clip(e / 0.05, 0, 1)
mix = voz + bed * duck * P.get("volume_musica", 1.0) + sfx * 0.8 * P.get("volume_efeitos", 1.0)
mix = mix / np.abs(mix).max() * 0.93
out = os.path.join(M.OUT, "mix.wav")
wo = wave.open(out, "wb"); wo.setnchannels(1); wo.setsampwidth(2); wo.setframerate(SR)
wo.writeframes((mix * 32767).astype(np.int16).tobytes()); wo.close(); print(out)
