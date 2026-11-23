# Sugere a trajetória do punho (mão levantada) para a cordinha do 1/3, a partir de um json do maos.sh.
#   python3 -I punho.py maos_13.json 8     (8 = primeiro quadro do json)
import json, sys, numpy as np
d = json.load(open(sys.argv[1])); A = int(sys.argv[2])
sug = {}
for i, maos in enumerate(d):
    alta = None
    for m in maos:
        pts = [v for v in m.values() if v[2] > 0.3]
        if len(pts) < 3: continue
        c = np.mean([p[:2] for p in pts], axis=0)
        if alta is None or c[1] < alta[1]: alta = c
    if alta is not None and i % 3 == 0: sug[str(A + i)] = [int(alta[0]), int(alta[1])]
print('"punho":', json.dumps(sug))
print('confira com grade.py: o ponto deve ficar no meio do punho fechado; pega = quando a mão chega perto da bolinha, solta = quando desce/abre')
