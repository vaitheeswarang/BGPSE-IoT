from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon

def holm(pvals):
    m=len(pvals); order=np.argsort(pvals); out=np.empty(m,float); prev=0
    for rank,idx in enumerate(order):
        val=min(1.0,(m-rank)*pvals[idx]); prev=max(prev,val); out[idx]=prev
    return out

def run(indir:Path):
    df=pd.read_csv(indir/'baseline_timing_results.csv'); pivot=df.pivot_table(index='image_id',columns='method',values='encrypt_ms',aggfunc='first').dropna()
    rows=[]
    if pivot.shape[1]>=3:
        stat,p=friedmanchisquare(*[pivot[c].values for c in pivot.columns]); rows.append(dict(test='Friedman',comparison='all matched methods',statistic=stat,p=p,holm_p=np.nan,median_ratio=np.nan))
    proposed='BGPSE-IoT-Full'; pvals=[]; tmp=[]
    if proposed in pivot:
      for c in pivot.columns:
        if c==proposed: continue
        try: st,p=wilcoxon(pivot[proposed],pivot[c],zero_method='wilcox',alternative='two-sided')
        except ValueError: st,p=np.nan,1.0
        ratio=float(np.median(pivot[proposed]/pivot[c])); tmp.append((c,st,p,ratio)); pvals.append(p)
      hp=holm(np.array(pvals)) if pvals else []
      for (c,st,p,ratio),h in zip(tmp,hp): rows.append(dict(test='Wilcoxon signed-rank',comparison=f'{proposed} vs {c}',statistic=st,p=p,holm_p=h,median_ratio=ratio))
    pd.DataFrame(rows).to_csv(indir/'timing_statistical_tests.csv',index=False)
    # summary tables
    s=df.groupby(['method','kind','size'],as_index=False).agg(n=('encrypt_ms','size'),encrypt_median_ms=('encrypt_ms','median'),encrypt_mean_ms=('encrypt_ms','mean'),decrypt_median_ms=('decrypt_ms','median'),throughput_median_MBps=('throughput_MBps','median'),entropy_mean=('entropy','mean'),abs_corr_mean=('abs_corr','mean'))
    s.to_csv(indir/'timing_summary.csv',index=False)
    stg=pd.read_csv(indir/'bgpse_stage_timing_results.csv'); ss=stg.groupby(['size','direction','stage'],as_index=False).agg(median_ms=('median_ms','median'),mean_ms=('mean_ms','mean'),p95_ms=('p95_ms','median'))
    enc=ss[ss.direction=='encrypt'].copy(); totals=enc[enc.stage=='total_encrypt'][['size','median_ms']].rename(columns={'median_ms':'total_ms'}); enc=enc.merge(totals,on='size',how='left'); enc['contribution_pct']=100*enc['median_ms']/enc['total_ms']; enc.to_csv(indir/'bgpse_stage_timing_summary.csv',index=False)
    dec=ss[ss.direction=='decrypt'].copy(); dt=dec[dec.stage=='total_decrypt'][['size','median_ms']].rename(columns={'median_ms':'total_ms'}); dec=dec.merge(dt,on='size',how='left'); dec['contribution_pct']=100*dec['median_ms']/dec['total_ms']; dec.to_csv(indir/'bgpse_decrypt_stage_timing_summary.csv',index=False)
    ab=pd.read_csv(indir/'bgpse_ablation_timing_results.csv'); a=ab.groupby(['size','variant'],as_index=False).encrypt_ms.median(); full=s[s.method=='BGPSE-IoT-Full'][['size','encrypt_median_ms']].rename(columns={'encrypt_median_ms':'full_ms'}); a=a.merge(full,on='size'); a['delta_vs_full_pct']=100*(a.encrypt_ms-a.full_ms)/a.full_ms; a.to_csv(indir/'bgpse_ablation_summary.csv',index=False)
