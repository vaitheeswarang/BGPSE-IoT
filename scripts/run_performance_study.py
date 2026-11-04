import argparse,json
from pathlib import Path
from bgpse.benchmark import run
from bgpse.stats import run as stats
from bgpse.plots import run as plots
p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('--outdir',default='results/performance'); a=p.parse_args(); cfg=json.load(open(a.config)); out=Path(a.outdir); run(cfg,out); stats(out); plots(out); print(f'Completed. Results: {out.resolve()}')
