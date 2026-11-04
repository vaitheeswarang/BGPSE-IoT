from pathlib import Path
import pandas as pd, numpy as np
import matplotlib.pyplot as plt

def savefig(p): plt.tight_layout(); plt.savefig(p,dpi=400,bbox_inches='tight'); plt.close()
def run(indir:Path):
    figs=indir/'figures'; figs.mkdir(exist_ok=True)
    s=pd.read_csv(indir/'timing_summary.csv')
    for size in sorted(s['size'].unique()):
      d=s[s['size']==size].sort_values('encrypt_median_ms')
      plt.figure(figsize=(9,5)); plt.barh(d.method,d.encrypt_median_ms); plt.xscale('log'); plt.xlabel('Median encryption time (ms, log scale)'); plt.ylabel('Method'); plt.title(f'Encryption latency comparison ({size}×{size})'); savefig(figs/f'latency_{size}.png')
      plt.figure(figsize=(9,5)); plt.barh(d.method,d.throughput_median_MBps); plt.xscale('log'); plt.xlabel('Median throughput (MB/s, log scale)'); plt.ylabel('Method'); plt.title(f'Encryption throughput comparison ({size}×{size})'); savefig(figs/f'throughput_{size}.png')
    st=pd.read_csv(indir/'bgpse_stage_timing_summary.csv'); st=st[~st.stage.isin(['total_encrypt'])]
    for size in sorted(st['size'].unique()):
      d=st[st['size']==size].sort_values('median_ms')
      plt.figure(figsize=(8,5)); plt.barh(d.stage,d.median_ms); plt.xlabel('Median stage time (ms)'); plt.ylabel('BGPSE-IoT stage'); plt.title(f'BGPSE-IoT stage-wise runtime ({size}×{size})'); savefig(figs/f'stage_runtime_{size}.png')
    ab=pd.read_csv(indir/'bgpse_ablation_summary.csv')
    for size in sorted(ab['size'].unique()):
      d=ab[ab['size']==size].sort_values('encrypt_ms')
      plt.figure(figsize=(8,5)); plt.barh(d.variant,d.encrypt_ms); plt.axvline(float(d.full_ms.iloc[0]),linestyle='--',linewidth=1,label='Full BGPSE-IoT'); plt.xlabel('Median encryption time (ms)'); plt.ylabel('Ablation'); plt.title(f'BGPSE-IoT timing ablation ({size}×{size})'); plt.legend(); savefig(figs/f'ablation_{size}.png')
    # security-vs-latency overview
    d=s[s['size']==s['size'].max()]
    plt.figure(figsize=(7,5)); plt.scatter(d.encrypt_median_ms,d.entropy_mean)
    for _,r in d.iterrows(): plt.annotate(r.method,(r.encrypt_median_ms,r.entropy_mean),fontsize=7,xytext=(3,3),textcoords='offset points')
    plt.xscale('log'); plt.xlabel('Median encryption time (ms, log scale)'); plt.ylabel('Mean ciphertext entropy (bits/byte)'); plt.title('Latency–ciphertext-entropy trade-off'); savefig(figs/'latency_entropy_tradeoff.png')
