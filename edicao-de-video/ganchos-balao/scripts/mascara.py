# recorte da pessoa (SegFormer ADE20K, classe person) -> mask/NNNN.png 1080x1920 — a mão passa na frente do balão
import torch, numpy as np, os, cv2
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
from PIL import Image
name = "nvidia/segformer-b5-finetuned-ade-640-640"
proc = SegformerImageProcessor.from_pretrained(name)
model = SegformerForSemanticSegmentation.from_pretrained(name).to('mps').eval()
pid = model.config.label2id['person']
import sys
# uso: <venv>/bin/python mascara.py 14-50,76-94,158-184   (só os quadros em que a mão encosta no balão; ~5 s por quadro)
fs = [f'{n:04d}.jpg' for t in sys.argv[1].split(',') for a, b in [map(int, t.split('-'))] for n in range(a, b + 1)]
os.makedirs('mask', exist_ok=True)
for i, f in enumerate(fs):
    im = Image.open('quadros/' + f).convert('RGB').resize((720, 1280))
    with torch.no_grad():
        lg = model(**proc(images=im, return_tensors='pt', do_resize=False).to('mps')).logits
        pr = torch.nn.functional.interpolate(lg, size=(960, 540), mode='bilinear').softmax(1)[0, pid]
    m = (pr.cpu().numpy() * 255).astype(np.uint8)
    m = cv2.resize(m, (1080, 1920), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite('mask/' + f.replace('.jpg', '.png'), m)
    if i % 50 == 0: print(i, flush=True)
print('ok')
