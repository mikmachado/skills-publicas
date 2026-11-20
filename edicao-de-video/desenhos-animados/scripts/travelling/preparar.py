# prepara: probabilidades limpas (sem a pessoa), curva do topo do muro estabilizada, deslocamento do chão
import cv2,numpy as np
P=np.load('probs.npy').astype(np.float32)   # N,5,480,270 : muro predio ceu arvore chao
U=np.load('fluxo_u.npy').astype(np.float32) # N,960,540
N=len(P)
def pess(j,w,h,d):
    m=cv2.resize(cv2.imread(f'mask/{j+1:05d}.png',0),(w,h))>90
    return cv2.dilate(m.astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(d,d)))
Q=np.zeros_like(P)
for j in range(N):
    pm=pess(j,270,480,9)
    for k in range(5):
        Q[j,k]=cv2.inpaint((P[j,k]*255).astype(np.uint8),pm,5,cv2.INPAINT_TELEA)/255.
# média ±1 quadro
Qs=np.stack([Q[max(0,j-1):j+2].mean(0) for j in range(N)])
np.save('probs_limpo.npy',Qs.astype(np.float16))
# velocidade do muro / chão (px meia-res por quadro) e do fundo
sw=np.zeros(N); sf=np.zeros(N)
for j in range(N):
    pm=pess(j,540,960,25)>0
    z=U[j][700:950]; sw[j]=np.median(z[~pm[700:950]])
    sf[j]=np.median(U[j][150:400][~pm[150:400]])
np.save('vel.npy',np.stack([sw,sf]))
# topo do muro
T=np.zeros((N,540),np.float32)
for j in range(N):
    M=cv2.resize(Qs[j,0]+Qs[j,4],(540,960))
    g=cv2.GaussianBlur(cv2.cvtColor(cv2.resize(cv2.imread(f'quadros/{j+1:05d}.jpg'),(540,960)),cv2.COLOR_BGR2GRAY).astype(np.float32),(0,0),1.2)
    gy=np.abs(cv2.Sobel(g,cv2.CV_32F,0,1,ksize=3))
    for x in range(540):
        col=M[:,x]>0.5; y0=330
        ys=np.where(col[y0:])[0]+y0
        t=np.nan
        for y in ys:
            if col[y:y+30].mean()>0.9: t=y; break
        if not np.isnan(t):
            a=int(max(0,t-10)); b=int(min(959,t+10)); t=a+np.argmax(gy[a:b,x])
        T[j,x]=t
    ok=~np.isnan(T[j]); T[j]=np.interp(np.arange(540),np.where(ok)[0],T[j][ok])
    from scipy.ndimage import median_filter
    T[j]=cv2.GaussianBlur(median_filter(T[j],11).reshape(1,-1),(0,0),3)[0]
def shift(c,s):  # desloca curva s px pra direita
    x=np.arange(540); return np.interp(x-s,x,c)
Ts=T.copy()
for j in range(N):
    acc=[T[j]]; w=[1.0]
    c=T[j]; 
    for d in (1,2):
        if j-d>=0: acc.append(shift(T[j-d],sum(sw[j-d+1:j+1]))); w.append(0.6/d)
        if j+d<N: acc.append(shift(T[j+d],-sum(sw[j+1:j+d+1]))); w.append(0.6/d)
    Ts[j]=np.average(np.stack(acc),0,np.array(w))
np.save('topo.npy',Ts*2); print('ok')
