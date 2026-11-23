# Quadros recortados com grade e COORDENADAS ESCRITAS (px do quadro 1080x1920) — para marcar punho, soco, tesoura, dedo.
#   python3 -I grade.py 14 50 3                      (de 14 a 50, de 3 em 3, recorte automático em volta da pessoa)
#   python3 -I grade.py 14 50 3 150 150 930 1350     (recorte x0 y0 x1 y1)    --espelhar = vira a imagem (CTA espelhado)
# Saída: f/grade_<a>_<b>.jpg. Leia a coordenada direto nos números da grade (não faça conta de escala).
import sys, cv2, numpy as np
arg = [a for a in sys.argv[1:] if not a.startswith('--')]
a, b, p = int(arg[0]), int(arg[1]), int(arg[2])
x0, y0, x1, y1 = (int(v) for v in arg[3:7]) if len(arg) >= 7 else (100, 100, 980, 1400)
esp = '--espelhar' in sys.argv
alvo = 300                                   # largura de cada quadrinho na folha
tiles = []
for n in range(a, b + 1, p):
    im = cv2.imread(f'quadros/{n:04d}.jpg')
    if esp: im = im[:, ::-1]
    im = im[y0:y1, x0:x1].copy(); s = alvo / (x1 - x0)
    im = cv2.resize(im, None, fx=s, fy=s)
    for x in range((x0 // 50 + 1) * 50, x1, 50):
        X = int((x - x0) * s); forte = x % 100 == 0
        cv2.line(im, (X, 0), (X, im.shape[0]), (0, 0, 255) if forte else (0, 200, 0), 1)
        if forte: cv2.putText(im, str(x), (X + 2, im.shape[0] - 4), 0, 0.33, (0, 0, 255), 1)
    for y in range((y0 // 50 + 1) * 50, y1, 50):
        Y = int((y - y0) * s); forte = y % 100 == 0
        cv2.line(im, (0, Y), (im.shape[1], Y), (0, 0, 255) if forte else (0, 200, 0), 1)
        if forte: cv2.putText(im, str(y), (2, Y - 2), 0, 0.33, (0, 0, 255), 1)
    cv2.putText(im, str(n), (4, 18), 0, 0.6, (255, 0, 255), 2); tiles.append(im)
por = 8
while len(tiles) % por: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(f'f/grade_{a}_{b}.jpg', np.vstack([np.hstack(tiles[i:i + por]) for i in range(0, len(tiles), por)]))
print(f'f/grade_{a}_{b}.jpg')
