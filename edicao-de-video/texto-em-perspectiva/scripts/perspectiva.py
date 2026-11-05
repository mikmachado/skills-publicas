#!/usr/bin/env python3
"""Cola um cartão (texto, imagem ou vídeo) num plano do vídeo base, em perspectiva,
com a pessoa recortada passando na frente.

Reproduz o tutorial (CapCut + Alight Motion "Flip Layer" + chroma key + "Escurecer")
e a variante do Canva ("Transform Image"), sem sair do terminal.

Modos de animação (--anim):
  nenhuma   cartão parado nos --cantos (variante Canva)
  desdobra  cartão sai da quina do plano e se abre ao longo dele (cantos A-D = dobradiça)
  surge     aparece com fade + leve crescimento, já colado no plano
  porta     o Flip Layer do Alight Motion: o cartão começa de frente para a câmera em
            --rect e gira na dobradiça (--pivo) até --angulo. Com --cantos, a posição
            final encaixa exatamente nesses cantos.

Cantos sempre na ordem A=sup-esq, B=sup-dir, C=inf-dir, D=inf-esq do cartão,
em pixels do vídeo base (confira com grade.py).

  python3 perspectiva.py --base base.mp4 --camada cartao.png \
      --cantos "60,520 470,640 470,1250 60,1430" --anim porta --rect 60,520,700,910 \
      --mistura escurecer --luz 0.6 --mascara mask/ --ini 0.4 --dur 0.9 \
      --saida comp.mp4 --camada-saida camada.mov
"""
import argparse, glob, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of",
                          "default=nw=1", path], capture_output=True, text=True, check=True).stdout
    d = dict(l.split("=", 1) for l in out.strip().splitlines() if "=" in l)
    n, m = d["r_frame_rate"].split("/")
    return int(d["width"]), int(d["height"]), float(n) / float(m), float(d.get("duration", 0) or 0)


def pts(s):
    return np.array([[float(v) for v in p.split(",")] for p in s.split()], dtype=np.float64)


def homografia(src, dst):
    """3x3 que leva src (4x2) em dst (4x2)."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(A), np.array(b))
    return np.append(h, 1).reshape(3, 3)


def aplica(Hm, p):
    q = np.c_[p, np.ones(len(p))] @ Hm.T
    return q[:, :2] / q[:, 2:3]


def ease(p, tipo):
    p = min(max(p, 0.0), 1.0)
    if tipo == "linear":
        return p
    if tipo == "mola":  # easeOutBack: passa um pouco e volta, como no keyframe do Alight
        c = 1.4
        return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2
    return 1 - (1 - p) ** 3  # saida (easeOutCubic)


def quad_porta(rect, pivo, ang, f, W, H):
    x, y, w, h = rect
    th = math.radians(min(max(ang, -85), 85))
    cx, cy = W / 2, H / 2
    px = x if pivo == "esquerda" else x + w
    s = 1 if pivo == "esquerda" else -1
    out = []
    for X, Y in ((0, y), (w, y), (w, y + h), (0, y + h)):
        Xr, Z = X * math.cos(th), X * math.sin(th)
        k = f / (f + Z)
        out.append((cx + (px + s * Xr - cx) * k, cy + (Y - cy) * k))
    q = np.array(out)
    return q if pivo == "esquerda" else q[[1, 0, 3, 2]]  # direita: a lista começou pelo canto B


class Camada:
    """Imagem fixa ou vídeo, entregue como PIL RGBa (pré-multiplicado)."""

    def __init__(self, path, fps):
        self.video = os.path.splitext(path)[1].lower() in (".mp4", ".mov", ".m4v", ".webm", ".mkv")
        if not self.video:
            self.img = Image.open(path).convert("RGBA").convert("RGBa")
            self.size = self.img.size
            return
        self.w, self.h, _, _ = probe(path)
        self.size = (self.w, self.h)
        dec = ["ffmpeg", "-v", "error"] + (["-c:v", "libvpx-vp9"] if path.endswith(".webm") else [])
        self.proc = subprocess.Popen(dec + ["-i", path, "-vf", f"fps={fps}", "-f", "rawvideo",
                                            "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
        self.n, self.last = -1, None

    def quadro(self, i):
        if not self.video:
            return self.img
        while self.n < i:
            buf = self.proc.stdout.read(self.w * self.h * 4)
            if len(buf) < self.w * self.h * 4:
                break  # acabou: segura o último quadro
            self.n += 1
            self.last = Image.frombuffer("RGBA", self.size, buf, "raw", "RGBA", 0, 1).convert("RGBa")
        return self.last


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--camada", required=True, help="png/jpg (cartao.py, Canva) ou vídeo (mp4/mov/webm)")
    ap.add_argument("--saida", required=True, help="vídeo composto (mp4)")
    ap.add_argument("--camada-saida", help="só o cartão em perspectiva, ProRes 4444 com alpha, para o CapCut")
    ap.add_argument("--cantos", help='"x,y x,y x,y x,y" A B C D no vídeo base')
    ap.add_argument("--anim", default="nenhuma", choices=["nenhuma", "desdobra", "surge", "porta"])
    ap.add_argument("--rect", help="porta: x,y,w,h do cartão de frente para a câmera")
    ap.add_argument("--pivo", default="esquerda", choices=["esquerda", "direita"])
    ap.add_argument("--angulo", type=float, default=55, help="porta: ângulo final (positivo = borda livre vai para o fundo)")
    ap.add_argument("--angulo-ini", type=float, default=0)
    ap.add_argument("--focal", type=float, default=0, help="porta: distância focal em px (0 = altura do vídeo)")
    ap.add_argument("--ini", type=float, default=0, help="segundo em que o cartão entra")
    ap.add_argument("--fim", type=float, default=1e9, help="segundo em que o cartão sai")
    ap.add_argument("--dur", type=float, default=0.8, help="duração da animação de entrada")
    ap.add_argument("--sai", action="store_true", help="repete a animação ao contrário no --fim")
    ap.add_argument("--ease", default="saida", choices=["saida", "mola", "linear"])
    ap.add_argument("--mistura", default="normal", choices=["normal", "multiplicar", "escurecer"])
    ap.add_argument("--opacidade", type=float, default=1.0)
    ap.add_argument("--luz", type=float, default=0.0, help="0..1: herda sombra/luz da parede")
    ap.add_argument("--mascara", help="pasta de PNGs da pessoa (branco = pessoa, fica na frente)")
    ap.add_argument("--mascara-offset", type=int, default=0, help="quadro do base que corresponde ao 1º PNG")
    ap.add_argument("--crf", type=int, default=16)
    a = ap.parse_args()

    W, H, fps, dur = probe(a.base)
    total = int(round(dur * fps))
    f = a.focal or H
    if a.anim == "porta":
        if not a.rect:
            sys.exit("--anim porta precisa de --rect")
        rect = [float(v) for v in a.rect.split(",")]
        fix = np.eye(3)
        if a.cantos:  # encaixe fino: a posição final do giro vai exatamente para os cantos
            fix = homografia(quad_porta(rect, a.pivo, a.angulo, f, W, H), pts(a.cantos))
    elif not a.cantos:
        sys.exit("--cantos é obrigatório fora do modo porta")
    else:
        Hplano = homografia(np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float), pts(a.cantos))

    cam = Camada(a.camada, fps)
    masks = sorted(glob.glob(os.path.join(a.mascara, "*.png"))) if a.mascara else []

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-i", a.base, "-map", "0:v", "-map", "1:a?", "-c:a", "aac",
                            "-b:a", "192k", "-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium",
                            "-pix_fmt", "yuv420p", "-shortest", a.saida], stdin=subprocess.PIPE)
    lay = None
    if a.camada_saida:
        lay = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                                "-r", str(fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                                "-pix_fmt", "yuva444p10le", a.camada_saida], stdin=subprocess.PIPE)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.base, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    vazio = np.zeros((H, W, 4), np.uint8)
    unit = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)

    i = 0
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        base = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        t = i / fps
        if not (a.ini <= t < a.fim):
            enc.stdin.write(buf)
            if lay: lay.stdin.write(vazio.tobytes())
            i += 1; continue

        p = ease((t - a.ini) / a.dur if a.dur > 0 else 1, a.ease)
        if a.sai and a.dur > 0:
            p = min(p, ease((a.fim - t) / a.dur, a.ease))
        op = a.opacidade
        if a.anim == "porta":
            q = aplica(fix, quad_porta(rect, a.pivo, a.angulo_ini + (a.angulo - a.angulo_ini) * p, f, W, H))
        elif a.anim == "desdobra":
            q = aplica(Hplano, unit * [max(p, 1e-3), 1])
        elif a.anim == "surge":
            s = 0.92 + 0.08 * p
            q = aplica(Hplano, (unit - 0.5) * s + 0.5); op *= min(1, max(p, 0) * 1.5)
        else:
            q = pts(a.cantos)

        x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        if x1 - x0 < 2 or y1 - y0 < 2 or op <= 0:
            enc.stdin.write(buf)
            if lay: lay.stdin.write(vazio.tobytes())
            i += 1; continue

        src = cam.quadro(i - int(round(a.ini * fps)))
        # reduz antes de deformar para não serrilhar
        ew = max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3]))
        eh = max(np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1]))
        tw, th_ = max(2, min(src.width, int(ew * 1.5))), max(2, min(src.height, int(eh * 1.5)))
        if (tw, th_) != src.size:
            src = src.resize((tw, th_), Image.LANCZOS)
        rectc = np.array([[0, 0], [tw, 0], [tw, th_], [0, th_]], float)
        Hi = homografia(q - [x0, y0], rectc)  # saída → cartão (o PIL pede o inverso)
        warped = src.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple((Hi / Hi[2, 2]).flatten()[:8]),
                               Image.BICUBIC)
        Pm = np.asarray(warped.convert("RGBA"), np.float32) / 255  # straight
        A = Pm[..., 3:4] * op
        C = Pm[..., :3]
        B = base[y0:y1, x0:x1].astype(np.float32) / 255

        if a.luz > 0:
            L = B @ np.array([0.299, 0.587, 0.114], np.float32)
            r = max(4, int(min(x1 - x0, y1 - y0) / 10))
            Lb = np.asarray(Image.fromarray((L * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)),
                            np.float32) / 255
            dentro = Lb[A[..., 0] > 0.5]
            ref = float(np.median(dentro)) if dentro.size else 0.5
            sh = np.clip(Lb / max(ref, 1e-3), 0.45, 1.35)[..., None]
            C = np.clip(C * (1 + (sh - 1) * a.luz), 0, 1)

        if a.mistura == "multiplicar":
            Cm = B * C
        elif a.mistura == "escurecer":
            Cm = np.minimum(B, C)
        else:
            Cm = C
        if masks:
            k = i - a.mascara_offset
            mp = masks[min(max(k, 0), len(masks) - 1)]
            m = np.asarray(Image.open(mp).convert("L").resize((W, H), Image.BILINEAR), np.float32)[y0:y1, x0:x1, None] / 255
            A = A * (1 - m)
        out = base.copy()
        out[y0:y1, x0:x1] = np.clip((Cm * A + B * (1 - A)) * 255 + 0.5, 0, 255).astype(np.uint8)
        enc.stdin.write(out.tobytes())
        if lay:
            fr = vazio.copy()
            fr[y0:y1, x0:x1, :3] = (C * 255 + 0.5).astype(np.uint8)
            fr[y0:y1, x0:x1, 3] = (A[..., 0] * 255 + 0.5).astype(np.uint8)
            lay.stdin.write(fr.tobytes())
        i += 1
        if i % 30 == 0:
            print(f"\r{i}/{total}", end="", file=sys.stderr, flush=True)

    for pr in (enc, lay):
        if pr:
            pr.stdin.close(); pr.wait()
    print(f"\n{a.saida}" + (f" + {a.camada_saida}" if lay else ""))


if __name__ == "__main__":
    main()
