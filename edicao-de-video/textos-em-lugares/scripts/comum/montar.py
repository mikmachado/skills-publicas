"""MONTAGEM FINAL: junta as cenas na ordem, corta presos à fala (tira as pausas), acelera (1.2x por padrão),
aplica cor (cor.txt) e trata o áudio: cada cena no mesmo volume, voz limpa/comprimida, efeitos (whoosh na troca
de cena, pop nas palavras-chave), volume final -16 LUFS sem estourar. Música opcional (com ducking).
uso (na pasta do projeto, com as pastas das cenas dentro): python3 <skill>/scripts/comum/montar.py montagem.json
montagem.json: {"cenas": [{"pasta": "cena1", "video": "comp.mp4", "pop": ["texto"], "segura_fim": false}, ...],
                "velocidade": 1.2, "musica": null, "saida": "final/video.mp4"}
Cada pasta precisa de transcricao.json (transcrever.py)."""
import json, os, sys, subprocess, wave, numpy as np

R = os.getcwd()
CFG = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "montagem.json"))
VEL, SR = float(CFG.get("velocidade", 1.2)), 48000
TRILHA = CFG.get("musica"); MUSICA = bool(TRILHA)
COR = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cor.txt")).read().strip()   # quente/ensolarado
CENAS = [(c["pasta"], c.get("video", "comp.mp4"), {w.lower() for w in c.get("pop", [])}, c.get("segura_fim", False))
         for c in CFG["cenas"]]
SAIDA = os.path.join(R, CFG.get("saida", "final/video.mp4"))
PAUSA, ANTES, DEPOIS = 0.35, 0.10, 0.16

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)

import re
def lufs(arq, filtro=""):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", arq, "-af", (filtro + "," if filtro else "") + "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1])
GANHO = {}
segs, pops, trocas = [], [], []      # segs: (entrada, ini, fim)
for k, (pasta, vid, chaves, segura) in enumerate(CENAS):
    d = json.load(open(f"{R}/{pasta}/transcricao.json"))
    ws = [w for s in d for w in s["w"]] if isinstance(d, list) and isinstance(d[0].get("w"), list) else d
    D = dur(f"{R}/{pasta}/{vid}")
    grupos = [[ws[0]]]
    for w in ws[1:]:
        (grupos[-1].append(w) if w["s"] - grupos[-1][-1]["e"] < PAUSA else grupos.append([w]))
    sc = []
    for g in grupos:
        a, b = max(0, g[0]["s"] - ANTES), min(D, g[-1]["e"] + DEPOIS)
        if sc and a - sc[-1][1] < 0.06: sc[-1][1] = b
        else: sc.append([a, b])
    if segura: sc[-1][1] = D - 0.05
    sel = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in sc)
    GANHO[k] = -20.0 - lufs(f"{R}/{pasta}/{vid}", f"aselect='{sel}'")     # todas as cenas no mesmo volume
    print(pasta, "ganho", round(GANHO[k], 1), "dB")
    trocas.append((k, sc[0][0]))
    for a, b in sc: segs.append((k, a, b))
    for w in ws:
        if w["w"].lower().strip(".,?!") in chaves: pops.append((k, w["s"]))

def no_final(k, t):
    acc = 0.0
    for kk, a, b in segs:
        if kk == k and a <= t < b: return (acc + t - a) / VEL
        acc += b - a
    return None
TOT = sum(b - a for _, a, b in segs) / VEL
print(f"{len(segs)} cortes, {TOT:.1f} s")

# ---------- vídeo + voz ----------
FD = os.path.dirname(SAIDA); os.makedirs(FD, exist_ok=True)
ent = []
for pasta, vid, _, _ in CENAS: ent += ["-i", f"{R}/{pasta}/{vid}"]
fc = ""
for j, (k, a, b) in enumerate(segs):
    fc += (f"[{k}:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,fps=30[v{j}];"
           f"[{k}:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aresample={SR},aformat=channel_layouts=stereo,volume={GANHO[k]:.2f}dB,"
           f"afade=t=in:d=0.012,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[a{j}];")
fc += "".join(f"[v{j}][a{j}]" for j in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[vc][ac];"
fc += f"[vc]setpts=PTS/{VEL},fps=30,{COR}[v];[ac]atempo={VEL}[voz]"
mudo = f"{FD}/_corte.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", fc, "-map", "[v]", "-map", "[voz]",
                "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", mudo.replace(".mp4", ".mov")], check=True)

# ---------- efeitos ----------
rng = np.random.default_rng(7)
def env(n, at, q): t = np.arange(n) / SR; return np.minimum(t / at, 1) * np.exp(-t * q)
def pop(f0):
    n = int(.16 * SR); t = np.arange(n) / SR; f = f0 * (1 + 1.8 * (1 - np.exp(-t * 40)))
    return .7 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, 28) + rng.normal(0, 1, n) * env(n, .0003, 400) * .3
def whoosh(d=.5):
    n = int(d * SR); t = np.arange(n) / SR; x = rng.normal(0, 1, n); y = np.zeros(n); a = 0.0
    kk = .015 + .3 * np.sin(np.pi * t / d) ** 2
    for i in range(n): a += kk[i] * (x[i] - a); y[i] = a
    return 1.4 * y * np.sin(np.pi * t / d) ** 1.5
P = [pop(520), pop(400)]; WH = whoosh()
fx = np.zeros(int((TOT + 1) * SR)); ev = []
for k, t0 in trocas[1:]:
    tf = no_final(k, t0 + 0.001)
    ev.append((tf - 0.22, WH, .9))
for j, (k, t) in enumerate(pops):
    tf = no_final(k, t)
    if tf is not None: ev.append((tf - 0.02, P[j % 2], .5))
for t, s, g in ev:
    i = max(0, int(t * SR)); fx[i:i + len(s)] += (s * g)[:len(fx) - i]
fx = fx[:int(TOT * SR)]; fx = fx / max(np.abs(fx).max(), 1e-6) * .6
w = wave.open(f"{FD}/sfx.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((fx * 32767).astype(np.int16).tobytes()); w.close()

# ---------- mix: voz tratada + efeitos, volume final em 2 passadas e limitador (sem estouro) ----------
saida = SAIDA
VOZ = ("highpass=f=85,lowpass=f=15000,adeclick,deesser=i=0.35,"
       "acompressor=threshold=-28dB:ratio=3.5:attack=6:release=140:knee=6:makeup=8dB,"
       "acompressor=threshold=-12dB:ratio=6:attack=1:release=60:makeup=0dB")
fc0 = f"[0:a]{VOZ},asplit[voz][key];[1:a]aresample={SR},pan=stereo|c0=c0|c1=c0,volume=0.30[sfx];"
ent0 = ["-i", mudo.replace(".mp4", ".mov"), "-i", f"{FD}/sfx.wav"]
if MUSICA:   # trilha baixa que abaixa sozinha quando a pessoa fala
    ent0 += ["-i", os.path.expanduser(TRILHA)]
    fc0 += (f"[2:a]atrim=0:{TOT:.3f},aresample={SR},aformat=channel_layouts=stereo,volume=0.35,afade=t=in:d=0.3,"
            f"afade=t=out:st={TOT - 1.2:.3f}:d=1.2[mus];[mus][key]sidechaincompress=threshold=0.04:ratio=6:attack=25:release=320[musd];"
            f"[voz][sfx][musd]amix=inputs=3:normalize=0:duration=first[m]")
else:
    fc0 += "[key]anullsink;[voz][sfx]amix=inputs=2:normalize=0:duration=first[m]"
mix = f"{FD}/_mix.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ent0 + ["-filter_complex", fc0, "-map", "[m]", "-c:a", "pcm_f32le", mix], check=True)
g = -16.0 - lufs(mix)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mudo.replace(".mp4", ".mov"), "-i", mix, "-map", "0:v", "-map", "1:a",
                "-af", f"volume={g:.2f}dB,aresample=192000,alimiter=limit=0.63:attack=3:release=80:level=false,aresample={SR}",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", saida], check=True)
os.remove(mudo.replace(".mp4", ".mov")); os.remove(mix)
print(saida, f"{len(ev)} efeitos, ganho final {g:.1f} dB")
