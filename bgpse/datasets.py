from __future__ import annotations
from pathlib import Path
from PIL import Image
import numpy as np
EXT={'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.webp'}

def discover(root:Path):
    rows=[]
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in EXT:
            rel=p.relative_to(root); dataset=rel.parts[0] if len(rel.parts)>1 else 'images'; rows.append((dataset,p))
    return rows

def generate_demo(root:Path,n_per_dataset=3,seed=42):
    rng=np.random.default_rng(seed); names=['kodak','usc_sipi','bsds500','div2k','medmnist']
    for ds in names:
        d=root/ds; d.mkdir(parents=True,exist_ok=True)
        for i in range(n_per_dataset):
            h,w=(320,480) if i%2==0 else (512,512)
            yy,xx=np.mgrid[:h,:w]
            base=np.stack([(xx*255/max(1,w-1)),(yy*255/max(1,h-1)),((xx+yy)*255/max(1,h+w-2))],axis=-1)
            noise=rng.normal(0,18,(h,w,3)); a=np.clip(base+noise,0,255).astype(np.uint8)
            Image.fromarray(a).save(d/f'{ds}_{i:03d}.png')
