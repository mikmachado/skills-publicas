# Fluxo óptico horizontal (DIS, meia resolução) -> fluxo_u.npy. Câmera acompanhando (travelling).
import cv2,numpy as np
dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
N=len([f for f in __import__('os').listdir('quadros') if f.endswith('.jpg')]); U=np.zeros((N,960,540),np.float16)
g=lambda i: cv2.resize(cv2.cvtColor(cv2.imread(f'quadros/{i:05d}.jpg'),cv2.COLOR_BGR2GRAY),(540,960))
p=g(1)
for i in range(2,N+1):
    c=g(i); f=dis.calc(p,c,None); U[i-1]=f[...,0]; p=c
U[0]=U[1]; np.save('fluxo_u.npy',U); print('ok')
