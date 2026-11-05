#!/usr/bin/env python3
"""Trilha de ansiedade/caos sintetizada, que acelera até cortar seco.

Pulso que acelera, tique-taque, baixo dissonante (lá contra si bemol), escala de Shepard
(parece subir para sempre), acordes em cluster e gaguejos no fim. Termina no segundo
do corte, sem cauda: o silêncio depois é parte do efeito.

  python3 -I trilha_caos.py --dur 13.3 -o trilha-caos.wav [--bpm 92 170]
"""
import argparse, wave
import numpy as np

SR = 48000


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dur", type=float, required=True, help="segundos até o corte")
    ap.add_argument("--bpm", type=float, nargs=2, default=[92, 170])
    ap.add_argument("-o", "--saida", default="trilha-caos.wav")
    a = ap.parse_args()
    D = a.dur; n = int(D * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(4)
    prog = t / D
    out = np.zeros(n)

    # tempo acelerando (curva exponencial): posição em batidas = integral do bpm
    b0, b1 = a.bpm
    bpm = b0 * (b1 / b0) ** prog
    batida = np.cumsum(bpm / 60 / SR)
    def tempos(sub):
        k = np.floor(batida * sub)
        return np.where(np.diff(k, prepend=-1) > 0)[0]

    def poe(som, i, g=1.0):
        m = min(len(som), n - i)
        if m > 0: out[i:i + m] += g * som[:m]

    # bumbo / coração
    m = int(0.25 * SR); tt = np.arange(m) / SR
    bumbo = np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 12)
    for i in tempos(1):
        poe(bumbo, i, 0.9)
        if prog[i] < 0.45:  # no começo, batida dupla de coração
            poe(bumbo, i + int(0.16 * SR), 0.45)

    # tique-taque: colcheias, semicolcheias no último terço
    m = int(0.03 * SR); tt = np.arange(m) / SR
    tique = rng.normal(0, 1, m); tique = (tique - np.convolve(tique, np.ones(4) / 4, "same")) * np.exp(-tt * 160)
    for j, i in enumerate(tempos(4)):
        if j % 2 == 0 or prog[i] > 0.66:
            poe(tique, i, 0.25 + 0.25 * prog[i])

    # baixo pulsante em colcheias, alternando lá e si bemol (segunda menor = tensão)
    m = int(0.18 * SR); tt = np.arange(m) / SR
    for j, i in enumerate(tempos(2)):
        f = 55 * (2 ** (1 / 12)) ** (1 if (j // 4) % 2 else 0)
        nota = sum(np.sin(2 * np.pi * f * h * tt) / h for h in (1, 2, 3, 4))
        poe(nota * np.exp(-tt * 14) * np.minimum(tt / 0.004, 1), i, 0.35)

    # escala de Shepard: parciais em oitavas subindo, envelope em log-frequência
    vel = 0.55  # oitavas por segundo
    ss = np.zeros(n)
    for k in range(8):
        oit = (k + vel * t) % 8
        f = 40 * 2 ** oit
        amp = np.exp(-((oit - 4) ** 2) / 3.2)
        ss += amp * np.sin(2 * np.pi * np.cumsum(f) / SR)
    out += ss * (0.05 + 0.20 * prog ** 1.5)

    # clusters a cada compasso
    m = int(0.35 * SR); tt = np.arange(m) / SR
    cl = sum(sum(np.sin(2 * np.pi * f * h * tt) / h ** 1.3 for h in (1, 2, 3, 5)) for f in (220, 233.08, 329.63, 349.23))
    cl = cl * np.exp(-tt * 7) * np.minimum(tt / 0.003, 1)
    for j, i in enumerate(tempos(1)):
        if j % 4 == 0:
            poe(cl, i, 0.10 + 0.12 * prog[i])

    # ruído subindo nos últimos 2,5 s
    r0 = max(0, n - int(2.5 * SR))
    rz = rng.normal(0, 1, n - r0)
    rz = rz - np.convolve(rz, np.ones(3) / 3, "same")
    out[r0:] += rz * np.linspace(0, 1, n - r0) ** 2 * 0.22

    # gaguejo: no último 1,2 s, repete pedacinhos cada vez menores
    g0 = n - int(1.2 * SR)
    i = g0; tam = int(0.12 * SR)
    while i < n - 64:
        pedaco = out[g0 - tam:g0].copy() if i == g0 else out[i - tam:i].copy()
        m = min(tam, n - i)
        out[i:i + m] = 0.6 * out[i:i + m] + 0.6 * pedaco[:m]
        i += m; tam = max(int(0.025 * SR), int(tam * 0.8))

    out = np.tanh(out * 1.3)
    out *= 0.89 / np.abs(out).max()
    out[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))  # corte seco sem estalo
    est = np.stack([out, np.roll(out, 23)], 1)  # um pouco de largura
    with wave.open(a.saida, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((est * 32767).astype(np.int16).tobytes())
    print(a.saida)


if __name__ == "__main__":
    main()
