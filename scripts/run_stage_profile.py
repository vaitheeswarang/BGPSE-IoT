import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from bgpse.utils import load_rgb
from bgpse.core import BGPSEContext,encrypt_image_bytes,decrypt_image_bytes
p=argparse.ArgumentParser(); p.add_argument('image'); p.add_argument('--size',type=int,default=512); p.add_argument('--repetitions',type=int,default=20); p.add_argument('--out',default='results/stage_profile_single.csv'); a=p.parse_args()
arr=load_rgb(a.image,a.size); data=arr.tobytes(); ctx=BGPSEContext(); rows=[]
for i in range(a.repetitions):
 pkt,st=encrypt_image_bytes(data,arr.shape,ctx,'full'); pt,dst=decrypt_image_bytes(pkt,ctx); assert pt==data
 for k,v in st.items(): rows.append({'rep':i,'direction':'encrypt','stage':k,'ms':v})
 for k,v in dst.items(): rows.append({'rep':i,'direction':'decrypt','stage':k,'ms':v})
Path(a.out).parent.mkdir(parents=True,exist_ok=True); pd.DataFrame(rows).to_csv(a.out,index=False); print(a.out)
