# Homografia quadro 1 -> quadro j usando só o cenário (sem a pessoa). Câmera parada ou na mão,
# fundo mais ou menos plano (parede/fachada/chão). Saída: homog.npy (N,3,3). Rode na pasta do projeto.
import cv2,numpy as np,os
N=len([f for f in os.listdir('quadros') if f.endswith('.jpg')]); sift=cv2.SIFT_create(4000)
def load(j):
    g=cv2.imread(f'quadros/{j+1:05d}.jpg',0); m=cv2.imread(f'mask/{j+1:05d}.png',0)
    keep=(cv2.dilate((m>40).astype(np.uint8),np.ones((61,61),np.uint8))==0).astype(np.uint8)*255
    return g,keep
g0,k0=load(0); kp0,d0=sift.detectAndCompute(g0,k0)
bf=cv2.FlannBasedMatcher({'algorithm':1,'trees':5},{'checks':64})
Hs=[];inl=[]
for j in range(N):
    g,k=load(j); kp,d=sift.detectAndCompute(g,k)
    mm=bf.knnMatch(d0,d,k=2); good=[a for a,b in mm if a.distance<0.7*b.distance]
    p0=np.float32([kp0[a.queryIdx].pt for a in good]); p1=np.float32([kp[a.trainIdx].pt for a in good])
    H,ms=cv2.findHomography(p0,p1,cv2.RANSAC,2.0)
    Hs.append(H if H is not None else Hs[-1]); inl.append(int(ms.sum()) if ms is not None else 0)
    if j%50==0: print(j,'pontos',inl[-1],'desloc',round(H[0,2],1),round(H[1,2],1),flush=True)
np.save('homog.npy',np.array(Hs)); print('menor nº de pontos:',min(inl),'(abaixo de ~150 = desconfie)')
