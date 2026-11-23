# Áudio: som original dos trechos + efeitos sonoros nos momentos do projeto.json -> audio.wav
#   python3 -I <skill>/scripts/audio.py base.mp4        ("volume_original" no projeto.json: 0 = só efeitos)
import numpy as np, subprocess, wave, sys, json, os
SR = 48000
SFX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sfx') + '/'
P = json.load(open('projeto.json'))
SEGS = [(a, b) for a, b, _ in P['trechos']]
def ler(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()
orig = ler(sys.argv[1] if len(sys.argv) > 1 else 'base.mp4')
if len(orig) == 0: orig = np.zeros(SR * 60, np.float32)
partes, off, t = [], {}, 0.0
for a, b in SEGS:
    s0, s1 = int((a - 1) / 30 * SR), int(b / 30 * SR)
    x = np.zeros(s1 - s0, np.float32); seg = orig[s0:s1]; x[:len(seg)] = seg
    f = int(0.01 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    off[a] = t; partes.append(x); t += (b - a + 1) / 30
mix = np.concatenate(partes) * P.get('volume_original', 1.0)
def quando(n):
    for a, b in SEGS:
        if a <= n <= b: return off[a] + (n - a) / 30
    return None
def por(x, n, g=1.0, adiant=0.0):
    q = quando(n)
    if q is None: return
    i = max(int((q - adiant) * SR), 0); j = min(len(mix), i + len(x)); mix[i:j] += x[:j - i] * g
rng = np.random.default_rng(1)
def vidro():
    d = int(0.9 * SR); tt = np.arange(d) / SR
    y = np.diff(np.concatenate([[0], rng.standard_normal(d) * np.exp(-tt * 9)])) * 0.5
    for k in range(26):
        t0 = rng.uniform(0, 0.6) ** 1.6; f = rng.uniform(2500, 7500); i0 = int(t0 * SR); tk = tt[: d - i0]
        y[i0:] += np.sin(2 * np.pi * f * tk) * np.exp(-tk * rng.uniform(25, 60)) * rng.uniform(0.15, 0.4)
    return y / np.abs(y).max() * 0.8
def toc():
    tt = np.arange(int(0.25 * SR)) / SR
    return (np.sin(2 * np.pi * 520 * tt) * 0.6 + np.sin(2 * np.pi * 1310 * tt) * 0.3) * np.exp(-tt * 28)
def tesourada():
    d = int(0.09 * SR); tt = np.arange(d) / SR
    y = np.diff(np.concatenate([[0], rng.standard_normal(d)])) * np.exp(-tt * 70) * 0.6
    for f in (3100, 4700, 6900): y += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 45) * 0.25
    y2 = np.zeros(int(0.16 * SR)); y2[:d] += y; i = int(0.06 * SR); y2[i:i + d] += y * 0.7
    return y2 / np.abs(y2).max() * 0.8
clique, hit, pop, boom, whoosh, wc, papel = (ler(SFX + f + '.wav') for f in ("clique", "hit", "pop", "boom", "whoosh", "whoosh_curto", "papel"))
c, s, t3, e = P['cordinha'], P['soco'], P['terceiro'], P['escrita']
# 1/3 — puxa a cordinha, acende piscando
por(wc, c['acende'] - 6, 0.5); por(clique, c['acende'], 1.0); por(clique, c['acende'] + 2, 0.6); por(clique, c['acende'] + 4, 0.9)
# 2/3 — soco, vidro, caco na cabeça
por(wc, s['impacto'] - 6, 0.6); por(hit, s['impacto'], 0.7); por(vidro(), s['impacto'], 0.9); por(toc(), s['na_cabeca'], 0.9)
# 3/3
por(pop, P['trechos'][2][0], 0.9)
if t3['modo'] == 'tesoura':
    for q in t3['tiques']: por(tesourada(), q, 0.9)
    por(papel, t3['estouro'], 1.0); por(wc, t3['estouro'] + 1, 0.4)
elif t3['modo'] == 'cutucao':
    por(wc, t3['contato'] - 5, 0.4); por(pop, t3['estouro'], 1.0); por(boom, t3['estouro'], 0.45)
else:
    por(whoosh, t3['contato'] - 2, 0.6, 0.15); por(hit, t3['contato'], 0.9); por(boom, t3['estouro'], 0.8)
# escrita
por(wc, e['linha1']['janela'][0], 0.35); por(wc, e['linha2']['janela'][0], 0.35)
por(whoosh, e.get('sublinhado', e['linha2']['janela'][1] + 1), 0.45, 0.1)
mix = np.clip(mix, -1, 1)
with wave.open('audio.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
print('audio.wav', round(len(mix) / SR, 2), 's')
