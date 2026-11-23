# Ponta do indicador da mão que escreve, um ponto por quadro do CTA -> dedo.json (+ f/dedo_ok.jpg e f/trajeto.jpg para conferir)
# Precisa de maos_cta.json (maos.sh) e projeto.json (início do CTA e se é espelhado). Rode: python3 -I <skill>/scripts/dedo.py
import json, cv2, numpy as np
P = json.load(open('projeto.json')); A = P['trechos'][-1][0]; esp = P['escrita'].get('espelhar', False)
d = json.load(open('maos_cta.json'))
raw = {}
for i, maos in enumerate(d):
    melhor = None
    for m in maos:
        t = m.get('indexTip')
        if not t or t[2] < 0.3 or t[1] > 1250: continue       # a outra mão costuma estar abaixada
        if melhor is None or t[1] < melhor[1]: melhor = t
    if melhor: raw[A + i] = melhor[:2]
ns = np.arange(A, A + len(d)); ks = sorted(raw)
xs = np.interp(ns, ks, [raw[k][0] for k in ks]); ys = np.interp(ns, ks, [raw[k][1] for k in ks])
k = np.array([1, 2, 3, 2, 1], float); k /= k.sum()
xs = np.convolve(np.pad(xs, 2, mode='edge'), k, 'valid'); ys = np.convolve(np.pad(ys, 2, mode='edge'), k, 'valid')
json.dump({str(int(n)): [float(x), float(y)] for n, x, y in zip(ns, xs, ys)}, open('dedo.json', 'w'))
print('dedo encontrado em', len(raw), 'de', len(d), 'quadros -> dedo.json')
def quadro(n):
    im = cv2.imread(f'quadros/{n:04d}.jpg'); return im[:, ::-1].copy() if esp else im
tiles = []
for n in range(A, A + len(d), 4):
    fr = quadro(n); i = n - A; cv2.circle(fr, (int(xs[i]), int(ys[i])), 10, (0, 255, 255), 3)
    t = cv2.resize(fr[600:1300, 200:900], None, fx=0.3, fy=0.3); cv2.putText(t, str(n), (3, 18), 0, 0.55, (0, 0, 255), 2); tiles.append(t)
while len(tiles) % 10: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite('f/dedo_ok.jpg', np.vstack([np.hstack(tiles[i:i + 10]) for i in range(0, len(tiles), 10)]))
fr = quadro(A + len(d) // 2)
for i in range(1, len(d)):
    t = i / len(d); cv2.line(fr, (int(xs[i - 1]), int(ys[i - 1])), (int(xs[i]), int(ys[i])), (int(255 * t), 60, int(255 * (1 - t))), 3)
cv2.imwrite('f/trajeto.jpg', cv2.resize(fr[500:1300, 150:950], None, fx=0.6, fy=0.6))
# sugestão de janelas/faixas por linha: o dedo volta para a esquerda = começou outra linha
print('x do dedo a cada 4 quadros:', ' '.join(f'{int(n)}:{int(x)}' for n, x in zip(ns[::4], xs[::4])))
