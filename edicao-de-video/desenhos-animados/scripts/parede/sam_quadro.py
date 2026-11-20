# SAM (segment anything) automático num quadro -> sam_<n>.npy (máscaras empacotadas)
# uso (no .venv com torch+torchvision+transformers): python sam_quadro.py <n_do_quadro>
import sys,numpy as np
from transformers import pipeline
from PIL import Image
n=int(sys.argv[1])
gen=pipeline('mask-generation',model='facebook/sam-vit-large',device='cpu')   # MPS falha (float64)
out=gen(Image.open(f'quadros/{n:05d}.jpg').convert('RGB'),points_per_batch=64,points_per_crop=48,pred_iou_thresh=0.86,stability_score_thresh=0.9)
ms=np.array([np.array(m) for m in out['masks']]).astype(bool)
np.save(f'sam_{n}.npy',np.packbits(ms,axis=-1)); print(n,ms.shape[0],'máscaras')
