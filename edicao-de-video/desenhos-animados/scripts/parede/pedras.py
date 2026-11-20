# Junta máscaras SAM de vários quadros num mapa de "peças" (pedras/azulejos/tijolos) no espaço do quadro 1.
# uso: python pedras.py <limite_y_ref> <quadro_a> [quadro_b ...]   (o primeiro tem prioridade)
# limite_y_ref: descarta peças com centro abaixo dessa linha (ex.: a calçada). Use 99999 pra não cortar.
# Saída: pedras_lab.npy (int32, 0 = nada) e olhar/pedras.jpg pra conferir.
import sys,os,cv2,numpy as np
ylim=float(sys.argv[1]); qs=[int(a) for a in sys.argv[2:]]
Hs=np.load('homog.npy') if os.path.exists('homog.npy') else None
a0=cv2.imread('quadros/00001.jpg'); H_,W_=a0.shape[:2]
def labs(n):
    ms=np.unpackbits(np.load(f'sam_{n}.npy'),axis=-1)[:,:,:W_].astype(bool)
    pm=cv2.imread(f'mask/{n:05d}.png',0)>60
    pmd=cv2.dilate(pm.astype(np.uint8),np.ones((15,15),np.uint8))>0
    ar=ms.sum((1,2)); res=[]
    for i in np.argsort(-ar):
        A=ar[i]
        if A<1500 or A>0.08*W_*H_ or (ms[i]&pmd).sum()>0.15*A: continue
        m=(ms[i]&~pmd).astype(np.uint8)
        if n!=1 and Hs is not None: m=cv2.warpPerspective(m,np.linalg.inv(Hs[n-1]),(W_,H_),flags=cv2.INTER_NEAREST)
        res.append(m)
    return res
camadas=[]
for n in reversed(qs): camadas+=labs(n)          # o primeiro da lista fica por cima
lab=np.zeros((H_,W_),np.int32)
for k,m in enumerate(camadas,1): lab[m>0]=k
out=np.zeros_like(lab); n=0
for v in range(1,len(camadas)+1):
    m=(lab==v).astype(np.uint8)
    if m.sum()<1500: continue
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    nn,l2,st,cen=cv2.connectedComponentsWithStats(m,4)
    if nn<2: continue
    b=1+np.argmax(st[1:,4])
    if st[b,4]<1500 or cen[b,1]>ylim: continue
    n+=1; out[l2==b]=n
np.save('pedras_lab.npy',out); print(n,'peças')
os.makedirs('olhar',exist_ok=True)
r=np.random.RandomState(1); cols=r.randint(60,255,(n+1,3)).astype(np.uint8)
v=a0.copy(); s=out>0; v[s]=(0.35*a0[s]+0.65*cols[out][s]).astype(np.uint8)
cv2.imwrite('olhar/pedras.jpg',cv2.resize(v,(W_//2,H_//2)))
