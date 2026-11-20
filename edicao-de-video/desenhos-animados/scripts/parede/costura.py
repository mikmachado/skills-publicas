# Acha a linha onde a parede encontra o chão (no quadro 1): y = a + b*x. Imprime a e b.
# uso: python costura.py <y_min> <y_max>   (faixa onde procurar, em px do quadro)
import sys,cv2,numpy as np
y0,y1=int(sys.argv[1]),int(sys.argv[2])
g=cv2.imread('quadros/00001.jpg',0).astype(np.float32); pm=cv2.imread('mask/00001.png',0)>40
W_=g.shape[1]; P=[]
for x0 in range(0,W_-40,40):
    if pm[y0:y1,x0:x0+40].mean()>0.05: continue
    col=g[y0:y1,x0:x0+40].mean(1)
    v=np.convolve(np.abs(np.diff(col)),np.ones(5)/5,'same')
    P.append((x0+20,y0+int(np.argmax(v))))
P=np.array(P,float); best=None
for _ in range(400):   # RANSAC simples
    i,k=np.random.choice(len(P),2,replace=False)
    if P[i,0]==P[k,0]: continue
    b=(P[k,1]-P[i,1])/(P[k,0]-P[i,0]); a=P[i,1]-b*P[i,0]
    inl=np.abs(P[:,1]-(a+b*P[:,0]))<8
    if best is None or inl.sum()>best[2].sum(): best=(a,b,inl)
b,a=np.polyfit(P[best[2],0],P[best[2],1],1)
print(f'costura: a={a:.1f} b={b:.4f}  ({best[2].sum()}/{len(P)} colunas)')
