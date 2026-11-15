import numpy as np, sys, json
from PIL import Image, ImageFilter
CW=816; S=2; AMP=0.55
def ss(t): t=np.clip(t,0,1); return t*t*(3-2*t)
def noise(h,w,corr,seed):
    from scipy.ndimage import gaussian_filter, zoom
    rng=np.random.default_rng(seed)
    g=max(corr//16,2)
    n=rng.standard_normal((h//16+3,w//16+3)).astype('float32')
    n=gaussian_filter(n,g/2.0)
    n=zoom(n,(h/n.shape[0],w/n.shape[1]),order=1)[:h,:w]
    n=(n-n.mean())/(n.std()+1e-6)
    return np.clip(n/2.2,-1,1)
def build(src,dst,H,focus=0.5,rt=200,rs=110,rb=100,seed=1):
    im=Image.open(src).convert('RGB')
    W2=CW*S; H2=int(round(H*S))
    sh=round(im.height*W2/im.width)
    im=im.resize((W2,sh),Image.LANCZOS)
    if sh>H2:
        ex=sh-H2; y0=int(round(ex*focus)); im=im.crop((0,y0,W2,y0+H2))
    elif sh<H2:
        H2=sh
    h,w=H2,W2
    ys=np.arange(h,dtype='float32')[:,None]; xs=np.arange(w,dtype='float32')[None,:]
    nt=noise(h,w,160,seed); nb=noise(h,w,160,seed+1); nl=noise(h,w,160,seed+2); nr=noise(h,w,160,seed+3)
    a=ss(ys/(rt*(1+AMP*nt)))
    a*=ss((h-1-ys)/(rb*(1+AMP*nb)))
    a*=ss(xs/(rs*(1+AMP*nl)))
    a*=ss((w-1-xs)/(rs*(1+AMP*nr)))
    c=np.asarray(im).astype('float32')
    par=np.array([228,216,184],dtype='float32')
    k=(0.65*(1-a))[...,None]
    c=c*(1-k)+par*k
    rgba=np.dstack([np.clip(c,0,255).astype('uint8'),(a*255).astype('uint8')])
    out=Image.fromarray(rgba,'RGBA')
    out.save(dst,quality=88,method=6)
    return h/S
