# Gera efeitos sonoros sintetizados (livres) em <skill>/sfx/: clique, hit, pop, boom, whoosh, whoosh_curto, papel.
#   python3 -I gerar_sfx.py [pasta]     (só precisa de numpy)
import numpy as np, wave, os, sys
SR = 48000
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sfx')
os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(7)
def t(d): return np.arange(int(d * SR)) / SR
def passa_baixa(x, a):            # filtro de 1 polo (a perto de 1 = mais grave)
    y = np.zeros_like(x); acc = 0.0
    for i, v in enumerate(x): acc = a * acc + (1 - a) * v; y[i] = acc
    return y
def salvar(nome, x):
    x = x / (np.abs(x).max() + 1e-9) * 0.85
    f = int(0.004 * SR); x[-f:] *= np.linspace(1, 0, f)
    with wave.open(os.path.join(out, nome + '.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
# clique de interruptor
tt = t(0.09); clique = rng.standard_normal(len(tt)) * np.exp(-tt * 400) * 0.6 + np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 90) * 0.5
salvar('clique', clique)
# pancada
tt = t(1.2); hit = np.sin(2 * np.pi * (95 - 40 * tt) * tt) * np.exp(-tt * 6) + passa_baixa(rng.standard_normal(len(tt)), 0.85) * np.exp(-tt * 18) * 2
salvar('hit', hit)
# pop de bolha
tt = t(0.16); f = 420 * np.exp(-tt * 18) + 110; pop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 28) + rng.standard_normal(len(tt)) * np.exp(-tt * 300) * 0.4
salvar('pop', pop)
# boom grave
tt = t(1.6); boom = np.sin(2 * np.pi * (58 - 18 * tt) * tt) * np.exp(-tt * 2.6) + passa_baixa(rng.standard_normal(len(tt)), 0.97) * np.exp(-tt * 3) * 6
salvar('boom', boom)
# whoosh (ruído com envelope que sobe e desce e "brilho" que varre)
def whoosh(d):
    tt = t(d); env = np.sin(np.pi * tt / d) ** 2
    r = rng.standard_normal(len(tt)); a = 0.75 + 0.2 * np.cos(np.pi * tt / d)
    y = np.zeros_like(r); acc = 0.0
    for i, v in enumerate(r): acc = a[i] * acc + (1 - a[i]) * v; y[i] = acc
    return (r - y * 0.5) * 0.15 * env + y * env
salvar('whoosh', whoosh(0.55)); salvar('whoosh_curto', whoosh(0.25))
# rasgo de papel: ruído com estalinhos irregulares
tt = t(0.55); env = np.clip(tt / 0.03, 0, 1) * np.exp(-tt * 4)
crep = (rng.random(len(tt)) < 0.02).astype(float); crep = np.convolve(crep, np.exp(-np.arange(200) / 30), 'same')
papel = rng.standard_normal(len(tt)) * (0.3 + crep) * env
papel = papel - passa_baixa(papel, 0.9)
salvar('papel', papel)
print('sfx em', os.path.abspath(out))
