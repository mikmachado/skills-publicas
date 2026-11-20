# SegFormer ADE20K -> probs.npy (muro, predio, ceu, arvore, chao). Rode no .venv (torch+transformers).
import torch,numpy as np
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
from PIL import Image
name="nvidia/segformer-b5-finetuned-ade-640-640"
proc=SegformerImageProcessor.from_pretrained(name); model=SegformerForSemanticSegmentation.from_pretrained(name).to('mps').eval()
L=model.config.label2id
grp={'muro':['wall','fence','railing'],'predio':['building','house','skyscraper','tower'],'ceu':['sky'],'arvore':['tree','plant','palm','flower','grass'],'chao':['earth','sidewalk','floor','road','path','rock','field']}
N=len([f for f in __import__('os').listdir('quadros') if f.endswith('.jpg')]); P=np.zeros((N,5,480,270),np.float16)
for i in range(N):
    im=Image.open(f'quadros/{i+1:05d}.jpg').convert('RGB').resize((540,960))
    with torch.no_grad():
        lg=model(**proc(images=im,return_tensors='pt').to('mps')).logits
        pr=torch.nn.functional.interpolate(lg,size=(480,270),mode='bilinear').softmax(1)[0]
    for k,(g,ns) in enumerate(grp.items()):
        P[i,k]=sum(pr[L[n]] for n in ns if n in L).cpu().numpy()
    if i%50==0: print(i,flush=True)
np.save('probs.npy',P); print('ok')
