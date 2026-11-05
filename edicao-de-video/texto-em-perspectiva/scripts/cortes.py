#!/usr/bin/env python3
"""Cortes, zooms, cor e som em cima do vídeo já composto (parede colada, linha do tempo sem cortes).
Corte SEMPRE depois de colar a parede: assim o zoom move tudo junto e o texto não escorrega.

- um corte por frase da transcrição, tirando as pausas; frases longas ganham um corte no meio;
- planos alternados: aberto com push lento, aproximado (1,12) e close no rosto nas frases curtas;
- cor "rica e clara" (pretos firmes, saturação 1,4, branco neutro) — desligue com --sem-cor;
- música opcional que abaixa sob a voz, e efeitos sintetizados: "pop" nas palavras grandes
  (estilos H e M do projeto.json), whoosh e rolagem no feed, papel + pop nos prints.

  python3 cortes.py projeto.json comp.mp4 final.mp4
  python3 cortes.py projeto.json comp.mp4 final.mp4 --camada camada.mov --musica trilha.mp3 --musica-ini 30

Saídas extras: <final>-camada-cortada.mov (se --camada), trilha-camada.wav e sfx-camada.wav.
No projeto.json: "rosto": [x, y] (centro do rosto no 1080x1920) para o close.
"""
import json, os, subprocess, sys
import numpy as np, wave

args = sys.argv[1:]
cfg_path, entrada, saida = args[0], args[1], args[2]
op = lambda k, d=None: args[args.index(k) + 1] if k in args else d
cfg = json.load(open(cfg_path)); D = os.path.dirname(os.path.abspath(cfg_path))
rel = lambda p: p if os.path.isabs(p) else os.path.join(D, p)
T = json.load(open(rel(cfg.get("transcricao", "transcricao.json"))))
pal = [w for s in T for w in s["w"]]
dur_in = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", entrada],
                              capture_output=True, text=True).stdout)

# ---------- segmentos ----------
seg, nome = [], []
for x in T:
    a, b = x["s"] - 0.10, x["e"] + 0.16
    if seg and a - seg[-1][1] < 0.3:
        m = (seg[-1][1] + a) / 2; seg[-1][1] = m; a = m
    seg.append([max(a, 0), b]); nome.append(x["t"])
seg[0][0] = max(0, T[0]["s"] - 0.2)
seg[-1][1] = min(dur_in, seg[-1][1] + 0.6)

# telas largas: feed e prints ficam abertos (parede inteira à mostra)
largas, k = [], 0
for t in cfg.get("telas", []):
    if "pular" in t: k += t["pular"]; continue
    if "linhas" in t: k += sum(n for li in t["linhas"] for _, _, n in li); continue
    n = t.get("feed", t.get("prints", {})).get("palavras", 0)
    if n: largas.append((pal[k]["s"] - 0.3, pal[k + n - 1]["e"] + 0.3))
    k += n
larga = lambda a: any(s <= a <= e for s, e in largas)

s2, n2 = [], []
for (a, b), t in zip(seg, nome):
    ws = [w["s"] for w in pal if a + 1.4 < w["s"] < b - 1.4]
    if b - a > 3.4 and ws and not larga(a):
        m = min(ws, key=lambda s: abs(s - (a + b) / 2)) - 0.04
        s2 += [[a, m], [m, b]]; n2 += [t, t + "#2"]
    else:
        s2.append([a, b]); n2.append(t)
seg, nome = s2, n2

rx, ry = cfg.get("rosto", [540, 600])
esq = cfg.get("parede", {}).get("lado", "esquerda") == "esquerda"
LARGO = (1.0, 1.05, 540, 900)
PUNCH = (1.12, 1.15, rx, ry + 250)
ROSTO = (1.20, 1.24, 0 if esq else 1080, ry)   # borda da parede presa: o texto não sai do quadro
plano, alt = [], 0
for (a, b), t in zip(seg, nome):
    if len(t.split()) <= 3 and not t.endswith("#2"): plano.append(ROSTO)
    elif larga(a): plano.append(LARGO)
    else: plano.append([LARGO, PUNCH][alt % 2]); alt += 1

COR = ("colorchannelmixer=rr=1.0:gg=0.985:bb=1.025,"
       "curves=all='0/0 0.12/0.06 0.5/0.47 0.85/0.88 1/1',eq=saturation=1.4,unsharp=5:5:0.35")

def zoom(zi, zf, ax, ay, d, alpha=False):
    z = f"({zi}+({zf}-{zi})*t/{d:.3f})"
    fmt = ",format=yuva444p10le" if alpha else ""
    return (f"scale=w='ceil(1080*{z}/2)*2':h='ceil(1920*{z}/2)*2':eval=frame:flags=lanczos{fmt},"
            f"crop=1080:1920:x='min(max({ax}*(iw/1080)-{ax},0),iw-1080)':y='min(max({ay}*(ih/1920)-{ay},0),ih-1920)'")

def monta(ent, sai, alpha=False):
    fc, cat = [], ""
    for i, ((a, b), (zi, zf, ax, ay)) in enumerate(zip(seg, plano)):
        d = b - a
        fc.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,{zoom(zi, zf, ax, ay, d, alpha)}[v{i}]")
        if alpha:
            cat += f"[v{i}]"
        else:
            fc.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d - 0.012:.3f}:d=0.012[a{i}]")
            cat += f"[v{i}][a{i}]"
    n = len(seg)
    if alpha:
        fc.append(f"{cat}concat=n={n}:v=1:a=0[out]")
        cmd = ["-map", "[out]", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
    else:
        cor = "" if "--sem-cor" in args else f",{COR}"
        fc.append(f"{cat}concat=n={n}:v=1:a=1[vc][ac];[vc]format=yuv420p{cor},format=yuv420p[out];[ac]anull[aout]")
        cmd = ["-map", "[out]", "-map", "[aout]", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "pcm_s16le"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-filter_complex", ";".join(fc)] + cmd + [sai], check=True)

tmp = rel("_cortado.mov")
monta(entrada, tmp)
if op("--camada"):
    monta(op("--camada"), os.path.splitext(saida)[0] + "-camada-cortada.mov", alpha=True)

# ---------- som ----------
SR = 48000; rng = np.random.default_rng(11); DUR = sum(b - a for a, b in seg)
def env(n, at, q):
    t = np.arange(n) / SR; return np.minimum(t / at, 1) * np.exp(-t * q)
def pop(f0):
    n = int(.16 * SR); t = np.arange(n) / SR; f = f0 * (1 + 1.8 * (1 - np.exp(-t * 40)))
    return .7 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, 28) + rng.normal(0, 1, n) * env(n, .0003, 400) * .3
def whoosh(d=.55):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.normal(0, 1, n); y = np.zeros(n); a = 0.0
    kk = .015 + .3 * np.sin(np.pi * t / d) ** 2
    for i in range(n): a += kk[i] * (x[i] - a); y[i] = a
    return 1.4 * y * np.sin(np.pi * t / d) ** 1.5
def flick():
    n = int(.12 * SR); x = rng.normal(0, 1, n); x = x - np.convolve(x, np.ones(8) / 8, "same")
    return .35 * x * np.sin(np.pi * np.arange(n) / n) ** 2
def papel():
    n = int(.22 * SR); return .5 * np.convolve(rng.normal(0, 1, n), np.ones(14) / 14, "same") * env(n, .006, 20)
P1, P2, WH, FL, PA = pop(520), pop(380), whoosh(), flick(), papel()

ev, k, alt = [], 0, 0
for t in cfg.get("telas", []):
    if "pular" in t: k += t["pular"]; continue
    if "linhas" in t:
        for li in t["linhas"]:
            for txt, est, n in li:
                if est[0] in "HM": ev.append((pal[k]["s"] - .03, [P1, P2][alt % 2], .55)); alt += 1
                k += n
        continue
    if "feed" in t:
        s0 = pal[k]["s"]; ev.append((s0 - .1, WH, .8)); ev += [(s0 + .62 * j, FL, .9) for j in range(1, 6)]
        k += t["feed"]["palavras"]
    if "prints" in t:
        for it in t["prints"]["itens"]:
            s0 = pal[k + it["palavra"]]["s"]; ev += [(s0 - .02, PA, .9), (s0, P2, .45)]
        k += t["prints"]["palavras"]
for (a, b), p in zip(seg, plano):
    if p == ROSTO: ev.append((a - .08, WH, .35))

def no_corte(t):
    acc = 0.0
    for a, b in seg:
        if a <= t < b: return acc + t - a
        acc += b - a
    return None
fx = np.zeros(int((DUR + 1) * SR))
for t, s, g in ev:
    tf = no_corte(t)
    if tf is None: tf = no_corte(t + .1)
    if tf is None: continue
    i = int(tf * SR); fx[i:i + len(s)] += (s * g)[:len(fx) - i]
fx = fx[:int(DUR * SR)]; fx = fx / max(np.abs(fx).max(), 1e-6) * .6
w = wave.open(rel("sfx-camada.wav"), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((fx * 32767).astype(np.int16).tobytes()); w.close()

entradas = ["-i", tmp, "-i", rel("sfx-camada.wav")]
fc = f"[0:a]aresample={SR},asplit[voz][chave];[1:a]volume=0.75,aformat=channel_layouts=stereo[fx];"
if op("--musica"):
    mi = float(op("--musica-ini", 0))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", op("--musica"), "-vn", "-af",
                    f"aresample={SR},atrim={mi}:{mi + DUR:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.15,"
                    f"afade=t=out:st={DUR - 1.2:.3f}:d=1.2,volume=0.30", rel("trilha-camada.wav")], check=True)
    entradas += ["-i", rel("trilha-camada.wav")]
    fc += ("[2:a][chave]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=300[m];"
           "[voz][m][fx]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9[a]")
else:
    fc += "[voz][fx]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9[a]"
subprocess.run(["ffmpeg", "-v", "error", "-y"] + entradas + ["-filter_complex", fc, "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", saida], check=True)
os.remove(tmp)
print(f"{saida}: {len(seg)} cortes, {DUR:.1f} s, {len(ev)} efeitos")
for (a, b), p, t in zip(seg, plano, nome):
    print(f"  {a:6.2f}-{b:6.2f}  {['aberto', 'aproximado', 'rosto'][[LARGO, PUNCH, ROSTO].index(p)]:10s} {t[:50]}")
