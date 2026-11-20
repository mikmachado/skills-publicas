import cv2,numpy as np,sys,subprocess
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1080,1920,30
Q=np.load('probs_limpo.npy').astype(np.float32); T=np.load('topo.npy'); SW,SF=np.load('vel.npy')
N=len(Q)
AMAR=(110,226,255)   # BGR #FFE26E
BR=(255,255,255)
ROSA=(163,79,255); LARANJA=(46,122,255); CIANO=(255,211,62); LIMA=(60,255,184); ROXO=(255,107,155)
PAL=[AMAR,ROSA,LARANJA,CIANO,LIMA,ROXO]
ESC=(25,18,20)
CX=np.cumsum(SW*2)   # deslocamento acumulado do chão/muro (px)
CB=np.cumsum(SF*2)   # deslocamento acumulado do fundo
def ease(x): x=np.clip(x,0,1); return 1-(1-x)**3
def masc(j):
    m=cv2.imread(f'mask/{j+1:05d}.png',0).astype(np.float32)/255
    b=(m>0.08).astype(np.uint8)
    b=cv2.morphologyEx(b,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(21,21)))
    fl=b.copy(); cv2.floodFill(fl,np.zeros((H+2,W+2),np.uint8),(0,0),1); b=b|(1-fl)
    b=cv2.erode(b,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
    return np.maximum(np.clip(m/0.45,0,1),cv2.GaussianBlur(b.astype(np.float32),(0,0),1.5))
def regiao(j,k,sig=4):
    p=cv2.resize(Q[j,k],(W,H),interpolation=cv2.INTER_LINEAR)
    return (cv2.GaussianBlur(p,(0,0),sig)>0.5).astype(np.uint8)
def contornos(m,minarea,maxn,suav=9,keep=None):
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    cs=sorted([c for c in cs if cv2.contourArea(c)>minarea],key=cv2.contourArea,reverse=True)[:maxn]
    out=[]
    for c in cs:
        c=c[:,0,:].astype(np.float32)
        k=cv2.getGaussianKernel(4*suav+1,suav)[:,0]; n=len(c)
        if n<4*suav+2: continue
        c=np.stack([np.convolve(np.r_[c[-2*suav:,d],c[:,d],c[:2*suav,d]],k,'same')[2*suav:-2*suav] for d in range(2)],1)
        # corta trechos na borda do quadro -> vira lista de trechos abertos
        dentro=(c[:,0]>6)&(c[:,0]<W-7)&(c[:,1]>6)&(c[:,1]<H-7)
        if keep is not None:
            ci=np.clip(c.astype(int),0,[W-1,H-1]); dentro&=keep[ci[:,1],ci[:,0]]>0
        seg=[];cur=[]
        for p,ok in zip(c,dentro):
            if ok: cur.append(p)
            elif len(cur)>20: seg.append(np.array(cur));cur=[]
            else: cur=[]
        if len(cur)>20: seg.append(np.array(cur))
        out+=seg
    return out
def tremer(pts,j,amp=2.2,seed=0):
    r=np.random.RandomState(seed+j//3)   # "boil" de desenho animado, troca a cada 3 quadros
    n=len(pts); k=max(2,n//40)
    no=r.randn(k+1,2)*amp
    idx=np.linspace(0,k,n); f=idx-np.floor(idx); i0=np.floor(idx).astype(int); i1=np.minimum(i0+1,k)
    return pts+no[i0]*(1-f[:,None])+no[i1]*f[:,None]
def parcial(pts,frac):
    n=int(len(pts)*np.clip(frac,0,1)); return pts[:n]
def tracejar(pts,dash,gap,off):
    d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    ph=((d+off)%(dash+gap))<dash
    segs=[];cur=[]
    for p,ok in zip(pts,ph):
        if ok: cur.append(p)
        elif cur:
            if len(cur)>1: segs.append(np.array(cur))
            cur=[]
    if len(cur)>1: segs.append(np.array(cur))
    return segs
S=2  # supersample das linhas? (desenha em 1x com AA)
def linha(img,pts,cor,esp):
    if len(pts)<2: return
    cv2.polylines(img,[np.round(pts*16).astype(np.int32)],False,cor,esp,cv2.LINE_AA,4)

# ---------- título ----------
CF="/System/Library/Fonts/Avenir Next Condensed.ttc"
def fonte(s,idx=8): return ImageFont.truetype(CF,s,index=idx)
def texto_esp(d,txt,cy,s,track,alpha,idx=8):
    f=fonte(s,idx); ws=[f.getlength(c) for c in txt]; tot=sum(ws)+track*(len(txt)-1)
    x=(W-tot)/2
    for c,w in zip(txt,ws):
        d.text((x,cy),c,font=f,fill=(255,255,255,int(255*alpha)),anchor='lm'); x+=w+track
    return (W-tot)/2,(W+tot)/2
def titulo(t):
    a0,a1,b0=0.45,5.3,6.0
    if t<a0 or t>b0: return None
    fade=min(ease((t-a0)/0.7), 1-ease((t-a1)/(b0-a1)) if t>a1 else 1)
    p=(t-a0)/(b0-a0)
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    y=300
    # linha 1
    al1=ease((t-a0)/0.6)*fade
    texto_esp(d,"ANDANDO",y,60,20+12*p,al1,idx=5)
    al2=ease((t-a0-0.25)/0.7)*fade
    texto_esp(d,"LOUCAMENTE",y+112,150,3+5*p,al2)
    al3=ease((t-a0-0.6)/0.7)*fade
    x0,x1=texto_esp(d,"EM BARCELONA",y+225,56,14+10*p,al3,idx=5)
    # filetes que se desenham dos lados de "EM BARCELONA"
    L=ease((t-a0-0.7)/0.8)*90
    if L>1:
        d.line([(x0-30-L,y+225),(x0-30,y+225)],fill=(255,226,110,int(255*fade)),width=5)
        d.line([(x1+30,y+225),(x1+30+L,y+225)],fill=(255,226,110,int(255*fade)),width=5)
    a=np.array(im).astype(np.float32)/255
    return a
def frase_ceu(t):
    if t<6.2: return None
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    rgb=lambda c:(c[2],c[1],c[0])
    itens=[("CRIAR",BR,6.3,120,330,-1),("NUNCA",AMAR,6.6,120,330,1),("FOI",BR,6.95,120,455,-1),("TÃO",CIANO,7.25,120,455,1),("FÁCIL",ROSA,7.65,210,610,0)]
    for txt,cor,t0,sz,y,lado in itens:
        p=(t-t0)/0.35
        if p<=0: continue
        sc=(1+0.3*np.exp(-5*p)*np.cos(9*p))*min(1,0.3+p) if p<2 else 1   # pop com rebote
        sc=max(sc,0.2) if p>0.05 else 0.2
        f=fonte(max(8,int(sz*min(sc,1.3))),8)
        wob=np.sin(t*5+t0*3)*2
        if lado==0: x=W/2
        else:
            fa=fonte(sz,8); par=[i for i in itens if i[4]==y]
            ws=[fa.getlength(i[0]) for i in par]; tot=sum(ws)+30
            x0=W/2-tot/2; x=x0+ws[0]/2 if lado<0 else x0+ws[0]+30+ws[1]/2
        d.text((x,y+wob),txt,font=f,fill=rgb(cor)+(255,),anchor='mm',stroke_width=8 if sz>150 else 6,stroke_fill=(30,22,26,255))
    return np.array(im).astype(np.float32)/255
# ---------- chão ----------
CR=np.load('desloc_linha.npy')
def faixa_muro():
    from PIL import Image,ImageDraw,ImageFont
    span=int(CR[-1].max())+W+400; MH=240
    im=Image.new('RGBA',(span,MH),(0,0,0,0)); d=ImageDraw.Draw(im)
    off=int(CR[-1].max())+200      # x da faixa = x_mundo + off
    rgb=lambda c:(c[2],c[1],c[0])
    fo=ImageFont.truetype(CF,88,index=8)
    def frase(cx,linhas,cores):
        k=0
        for li,pal_ in enumerate(linhas):
            ws=[fo.getlength(p) for p in pal_]; sp=26; tot=sum(ws)+sp*(len(ws)-1); x=cx-tot/2
            y=MH/2+(li-0.5)*86
            for p,w in zip(pal_,ws):
                c=cores[k]; k+=1
                d.text((x,y),p,font=fo,fill=rgb(c)+(255,),anchor='lm',stroke_width=6,stroke_fill=(30,22,26,255)); x+=w+sp
    def estrela(cx,cy,r,c):
        pts=[(cx+np.cos(a)*(r if k%2==0 else r*0.45),cy+np.sin(a)*(r if k%2==0 else r*0.45)) for k,a in enumerate(np.linspace(-np.pi/2,1.5*np.pi,11)[:-1])]
        d.polygon(pts,fill=rgb(c)+(255,),outline=(30,22,26,255),width=6)
    def coracao(cx,cy,r,c):
        tt=np.linspace(0,2*np.pi,80); x=16*np.sin(tt)**3; y=-(13*np.cos(tt)-5*np.cos(2*tt)-2*np.cos(3*tt)-np.cos(4*tt))
        d.polygon(list(zip(cx+x*r/17,cy+y*r/17)),fill=rgb(c)+(255,),outline=(30,22,26,255),width=6)
    def zigue(x0,cy,n,c):
        pts=[(x0+k*34,cy+(-28 if k%2 else 28)) for k in range(n)]
        d.line(pts,fill=(30,22,26,255),width=22,joint='curve'); d.line(pts,fill=rgb(c)+(255,),width=12,joint='curve')
    def bolinhas(x0,cy,c):
        for k in range(5): d.ellipse([x0+k*48-13,cy-13,x0+k*48+13,cy+13],fill=rgb(c)+(255,),outline=(30,22,26,255),width=5)
    def wx(q,x=540): return x-CR[q,600]+off
    r=np.random.RandomState(4); x=200
    formas=[estrela,coracao,zigue,bolinhas,estrela]
    while x<span-200:
        c=PAL[r.randint(len(PAL))]; f=formas[r.randint(len(formas))]
        if f is estrela: estrela(x,MH/2+r.randint(-40,40),50,c)
        elif f is coracao: coracao(x,MH/2+r.randint(-30,30),48,c)
        elif f is zigue: zigue(x-100,MH/2,7,c)
        else: bolinhas(x-100,MH/2,c)
        x+=r.randint(260,420)
    fo2=ImageFont.truetype(CF,118,index=8)
    pal_=[("BARCELONA",AMAR),("UAU!",ROSA),("GAUDÍ",CIANO),("CRIAR!",LIMA),("LOUCAMENTE",BR),("UAU!",LARANJA),("BCN",ROXO)]
    q=20; k=0
    while q<385 and k<len(pal_):
        c0=int(wx(q,300)); w_,cor=pal_[k]
        L_=fo2.getlength(w_); d.rectangle([c0-L_/2-70,0,c0+L_/2+70,MH],fill=(0,0,0,0))
        d.text((c0,MH/2+4),w_,font=fo2,fill=rgb(cor)+(255,),anchor='mm',stroke_width=7,stroke_fill=(30,22,26,255))
        q+=52; k+=1
    a=np.array(im).astype(np.float32)/255
    return a,off,MH
MURO,MOFF,MH=None,0,240
def pes(m):
    ys,xs=np.where(m[1100:]>0.5)
    if len(ys)==0: return None
    ys=ys+1100; yb=ys.max(); sel=ys>yb-90
    return xs[sel].min(),xs[sel].max(),yb

MURO,MOFF,MH=faixa_muro()
# redesenha as frases (o laço acima limpou a área)
ini=int(sys.argv[1]) if len(sys.argv)>1 else 0; fim=int(sys.argv[2]) if len(sys.argv)>2 else N
prev='prev' in sys.argv
out=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r','30','-i','-',
     '-c:v','libx264','-crf','16','-pix_fmt','yuv420p','linhas_mudo.mp4'],stdin=subprocess.PIPE) if not prev else None
for j in range(ini,fim):
    t=j/FPS
    fr=cv2.imread(f'quadros/{j+1:05d}.jpg').astype(np.float32)/255
    pm=masc(j)
    L=np.zeros((H*1,W*1,3),np.uint8)       # linhas (cor)
    A=np.zeros((H,W),np.uint8)             # alpha das linhas
    def tr(pts,cor,esp,alpha=1.0,borda=True):
        if len(pts)<2: return
        if borda: linha(L,pts,ESC,esp+7); linha(A,pts,int(235*alpha),esp+7)
        linha(L,pts,cor,esp); linha(A,pts,int(255*alpha),esp)
    gray=cv2.GaussianBlur(cv2.cvtColor((fr*255).astype(np.uint8),cv2.COLOR_BGR2GRAY),(0,0),2.2)
    dist=cv2.distanceTransform((pm<0.3).astype(np.uint8),cv2.DIST_L2,5)
    # ---------- tinta (chão em mosaico + muro pintado) ----------
    PC=np.zeros((H,W,3),np.float32); PA=np.zeros((H,W),np.float32)
    flat=np.percentile(T[j],85)
    cz=regiao(j,4)|regiao(j,0)
    cz[:int(flat)+300]=0
    ed=cv2.Canny(gray,35,80); ed=cv2.dilate(ed,np.ones((3,3),np.uint8))
    n,lab,st,cen=cv2.connectedComponentsWithStats(((ed==0)&(cz>0)).astype(np.uint8),4)
    ok=(st[:,4]>250)&(st[:,4]<20000); ok[0]=False
    ci=np.clip(cen.astype(int),0,[W-1,H-1])
    xw=cen[:,0]-CR[j,ci[:,1]//2]
    cxw=np.floor(xw/85).astype(int); cyw=np.floor(cen[:,1]/85).astype(int)
    hsh=(cxw*73856093)^(cyw*19349663)
    hsh=np.abs(hsh)%9973
    esc=(hsh%9)<5                       # ~40% das pedras pintadas
    idx=hsh%len(PAL)
    # longe dos pés: zona protegida em volta da pessoa
    pdist=dist[ci[:,1],ci[:,0]]
    prot=np.clip((pdist-110)/120,0,1)
    # entra numa onda da esquerda pra direita
    onda=np.clip(((t/1.1)*(W+500)-200-cen[:,0])/250,0,1)
    av=np.where(ok&esc,0.92*prot*onda,0).astype(np.float32)
    pal=np.array(PAL,np.float32)/255
    PA=np.maximum(PA,av[lab]); m_=av[lab]>0; PC[m_]=pal[idx][lab][m_]
    # muro: faixa pintada presa à parede
    rowc=int(flat)+190
    sh_=CR[j,min(rowc//2,959)]-MOFF
    Mw=cv2.warpAffine(MURO,np.float32([[1,0,sh_],[0,1,rowc-MH//2]]),(W,H),flags=cv2.INTER_LINEAR,borderValue=0)
    ma=Mw[...,3]
    cap=np.zeros((H,W),np.float32)
    for x in range(0,W,2): cap[int(T[j][x//2])+105:int(flat)+300,x:x+2]=1
    cap=cv2.GaussianBlur(cap,(0,0),3)
    ma=ma*cap*np.clip((dist-6)/10,0,1)
    sel=ma>0.01
    PC[sel]=Mw[...,:3][sel]; PA=np.maximum(PA,ma)
    L=np.zeros((H,W,3),np.uint8); A=np.zeros((H,W),np.uint8)
    # muro: topo amarelo + eco branco tracejado
    xs=np.arange(540)*2.0
    top=np.stack([xs,T[j]],1)
    fr_m=ease((t-0.1)/0.9)
    tm=tremer(top,j,1.5,1)
    tr(parcial(tm,fr_m),AMAR,11)
    eco=tremer(top+[0,34],j,1.5,2)
    for s in tracejar(parcial(eco,ease((t-0.3)/0.9)),38,22,-t*140): tr(s,CIANO,7)
    # prédios
    ceu=cv2.dilate(regiao(j,2,5),np.ones((31,31),np.uint8))
    pr=regiao(j,1,5); pr[int(np.median(T[j])):]=0
    for n,c in enumerate(contornos(pr,6000,4,7,ceu)):
        c=tremer(c,j,2.0,10+n)
        tr(parcial(c,ease((t-0.7-0.15*n)/1.0)),ROSA,9)
        # janelas/detalhes por dentro
    if t>1.3:
        inner=cv2.erode(pr,np.ones((25,25),np.uint8))
        e2=cv2.Canny(cv2.GaussianBlur(gray,(0,0),1.6),40,110)
        e2=cv2.dilate(e2,np.ones((2,2),np.uint8))
        pa=(e2>0)&(inner>0)
        A=np.maximum(A,(pa*255*0.8*ease((t-1.3)/1.0)).astype(np.uint8)); L[pa]=AMAR
    # árvores: contorno inteiro laranja + rabisco colorido cobrindo
    ar=regiao(j,3,7)
    for x in range(0,W,2): ar[int(T[j][x//2])-25:,x:x+2]=0
    ar=cv2.morphologyEx(ar,cv2.MORPH_OPEN,np.ones((15,15),np.uint8))
    nlab,lab,st,_=cv2.connectedComponentsWithStats(ar,8)
    ordem=[k for k in np.argsort(-st[:,4]) if k>0 and st[k,4]>9000 and st[k,1]>12][:4]
    yy,xx=np.mgrid[0:H,0:W]
    r=np.random.RandomState(j//3)
    for n,k in enumerate(ordem):
        m=(lab==k).astype(np.uint8)
        x0,y0,w0,h0=st[k,:4]
        cor=[ROXO,ROSA,CIANO,LIMA][n%4]
        # rabisco: hachura diagonal presa ao fundo, revelada de cima pra baixo
        rev=ease((t-1.0-0.35*n)/1.4)
        if rev>0:
            ang=0.9+r.randn()*0.03
            ph=((xx+CB[j]+ (yy*ang))%30)
            hat=(ph<9)&(m>0)&(yy<y0+h0*rev+1)
            hat=cv2.GaussianBlur(hat.astype(np.float32),(0,0),0.8)
            av=(hat*0.62*255).astype(np.uint8)
            sel=av>20; L[sel]=cor; A=np.maximum(A,av)
        for c in contornos(m,9000,2,11,None):
            c=tremer(c,j,3.0,30+n)
            tr(parcial(c,ease((t-0.9-0.35*n)/1.2)),LARANJA,8)
    a=A.astype(np.float32)/255
    col=L.astype(np.float32)/255
    # sombra + brilho
    sh=cv2.GaussianBlur(a,(0,0),5)*0.45
    glow=cv2.GaussianBlur(col*a[...,None],(0,0),9)*1.1
    lum=gray.astype(np.float32)/255; lm=cv2.GaussianBlur(lum,(0,0),25)+1e-3
    tex=np.clip(0.8+0.5*(lum/lm-1)+0.15*lm,0.45,1.15)[...,None]
    base=fr*(1-PA[...,None])+PC*tex*PA[...,None]
    bg=base*(1-sh[...,None])
    bg=1-(1-bg)*(1-np.clip(glow,0,1))
    bg=bg*(1-a[...,None])+col*a[...,None]
    tt=titulo(t)
    if tt is None: tt=frase_ceu(t)
    if tt is not None:
        ta=tt[...,3]; tsh=cv2.GaussianBlur(ta,(0,0),8)*0.5
        bg=bg*(1-tsh[...,None]); bg=bg*(1-ta[...,None])+tt[...,2::-1]*ta[...,None]
    o=bg*(1-pm[...,None])+fr*pm[...,None]
    o=(np.clip(o,0,1)*255).astype(np.uint8)
    if prev and j==fim-1: cv2.imwrite(f'prev_{j+1:05d}.jpg',o)
    elif out: out.stdin.write(o.tobytes())
    if j%50==0: print(j,flush=True)
if out: out.stdin.close(); out.wait()
