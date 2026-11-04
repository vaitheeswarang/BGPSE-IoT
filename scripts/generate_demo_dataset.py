from pathlib import Path
from bgpse.datasets import generate_demo
import argparse
p=argparse.ArgumentParser(); p.add_argument('--root',default='datasets/demo'); p.add_argument('--n',type=int,default=3); a=p.parse_args(); generate_demo(Path(a.root),a.n); print(f'Demo images written to {a.root}')
