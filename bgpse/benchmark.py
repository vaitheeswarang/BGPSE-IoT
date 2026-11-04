from __future__ import annotations
import time, json
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image
from .datasets import discover
from .utils import load_rgb, entropy_u8, adjacent_corr
from .core import BGPSEContext,encrypt_image_bytes,decrypt_image_bytes
from .baselines import BASELINES

def _p95(x): return float(np.percentile(x,95))
def run(cfg:dict,outdir:Path):
    outdir.mkdir(parents=True,exist_ok=True); root=Path(cfg['dataset_root']); rows=[]; stage_rows=[]; ab_rows=[]
    items=discover(root)
    if not items: raise RuntimeError(f'No images found under {root}')
    allowed=set(cfg.get('datasets',[]))
    if allowed: items=[x for x in items if x[0] in allowed]
    # deterministic per-dataset limit
    lim=cfg.get('limit_per_dataset'); selected=[]
    for ds in sorted(set(d for d,_ in items)):
        sub=sorted([p for d,p in items if d==ds]); selected += [(ds,p) for p in (sub[:lim] if lim else sub)]
    sizes=cfg.get('sizes',[256,512]); reps=int(cfg.get('repetitions',5)); ctx=BGPSEContext()
    methods=list(cfg.get('methods',list(BASELINES)))
    for ds,p in selected:
      for size in sizes:
        arr=load_rgb(p,size); data=arr.tobytes(); image_id=f'{ds}/{p.name}@{size}'
        # standard/reference baselines
        for name in methods:
          kind,fn=BASELINES[name]; encs=[]; decs=[]; ct=None
          for _ in range(reps):
            ct,pt,t=fn(data); assert pt==data; encs.append(t['encrypt']); decs.append(t.get('decrypt',0.0))
          rows.append(dict(image_id=image_id,dataset=ds,file=p.name,size=size,method=name,kind=kind,
             encrypt_ms=float(np.median(encs)),decrypt_ms=float(np.median(decs)),throughput_MBps=(len(data)/1048576)/(np.median(encs)/1000),
             ciphertext_bytes=len(ct),entropy=entropy_u8(ct[:len(data)]),abs_corr=abs(adjacent_corr(ct[:len(data)]))))
        # full BGPSE direct benchmark, stage profile on every rep
        encs=[]; decs=[]; lastpkt=None
        stage_collect={}; dec_stage_collect={}
        for _ in range(reps):
          pkt,st=encrypt_image_bytes(data,arr.shape,ctx,'full'); pt,dst=decrypt_image_bytes(pkt,ctx); assert pt==data; lastpkt=pkt
          encs.append(st['total_encrypt']); decs.append(dst['total_decrypt'])
          for k,v in st.items(): stage_collect.setdefault(k,[]).append(v)
          for k,v in dst.items(): dec_stage_collect.setdefault(k,[]).append(v)
        rows.append(dict(image_id=image_id,dataset=ds,file=p.name,size=size,method='BGPSE-IoT-Full',kind='proposed',
             encrypt_ms=float(np.median(encs)),decrypt_ms=float(np.median(decs)),throughput_MBps=(len(data)/1048576)/(np.median(encs)/1000),
             ciphertext_bytes=len(lastpkt['outer']),entropy=entropy_u8(lastpkt['outer'][:len(data)]),abs_corr=abs(adjacent_corr(lastpkt['outer'][:len(data)]))))
        for k,v in stage_collect.items():
            stage_rows.append(dict(image_id=image_id,dataset=ds,size=size,direction='encrypt',stage=k,median_ms=float(np.median(v)),mean_ms=float(np.mean(v)),p95_ms=_p95(v)))
        for k,v in dec_stage_collect.items():
            stage_rows.append(dict(image_id=image_id,dataset=ds,size=size,direction='decrypt',stage=k,median_ms=float(np.median(v)),mean_ms=float(np.mean(v)),p95_ms=_p95(v)))
        # ablations
        for variant in cfg.get('ablations',['core_only','static_sbox','shake_only','no_permutation','single_diffusion','no_outer_aead','no_provenance']):
          vals=[]
          for _ in range(max(1,min(reps,3))):
            pkt,st=encrypt_image_bytes(data,arr.shape,ctx,variant); pt,_=decrypt_image_bytes(pkt,ctx); assert pt==data; vals.append(st['total_encrypt'])
          ab_rows.append(dict(image_id=image_id,dataset=ds,size=size,variant=variant,encrypt_ms=float(np.median(vals))))
    pd.DataFrame(rows).to_csv(outdir/'baseline_timing_results.csv',index=False)
    pd.DataFrame(stage_rows).to_csv(outdir/'bgpse_stage_timing_results.csv',index=False)
    pd.DataFrame(ab_rows).to_csv(outdir/'bgpse_ablation_timing_results.csv',index=False)
    return rows
