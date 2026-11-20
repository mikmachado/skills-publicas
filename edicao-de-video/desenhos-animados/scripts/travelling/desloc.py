# Deslocamento acumulado por linha da tela (meia-res, 960 linhas) -> desloc_linha.npy
# Serve pra "prender" tinta e palavras no chão/muro que passam na tela.
import numpy as np,cv2
U=np.load('fluxo_u.npy').astype(np.float32); N=len(U)
V=np.zeros((N,960),np.float32)
for j in range(N):
    m=cv2.resize(cv2.imread(f'mask/{j+1:05d}.png',0),(540,960))>60
    m=cv2.dilate(m.astype(np.uint8),np.ones((25,25)))>0
    V[j]=np.nanmedian(np.where(m,np.nan,U[j]),1)
V=cv2.GaussianBlur(np.nan_to_num(V),(0,0),sigmaX=8,sigmaY=1.5)
np.save('desloc_linha.npy',np.cumsum(V*2,0)); print('ok')
