from __future__ import annotations
import hashlib, json, time
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from PIL import Image

class StageTimer:
    def __init__(self): self.ns = {}
    @contextmanager
    def stage(self, name):
        t0 = time.perf_counter_ns(); yield; dt = time.perf_counter_ns()-t0
        self.ns[name] = self.ns.get(name, 0) + dt
    def ms(self): return {k:v/1e6 for k,v in self.ns.items()}

def sha256(data: bytes) -> bytes: return hashlib.sha256(data).digest()
def shake(data: bytes, n: int) -> bytes: return hashlib.shake_256(data).digest(n)
def canonical_json(obj) -> bytes: return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode()

def load_rgb(path: str|Path, size: int|None=None):
    im=Image.open(path).convert("RGB")
    if size: im=im.resize((size,size), Image.Resampling.LANCZOS)
    return np.asarray(im, dtype=np.uint8)

def entropy_u8(data: bytes) -> float:
    a=np.frombuffer(data,dtype=np.uint8); counts=np.bincount(a,minlength=256); p=counts[counts>0]/len(a)
    return float(-(p*np.log2(p)).sum())

def adjacent_corr(data: bytes) -> float:
    a=np.frombuffer(data,dtype=np.uint8).astype(np.float64)
    if len(a)<2: return 0.0
    x,y=a[:-1],a[1:]
    sx,sy=x.std(),y.std()
    return float(np.corrcoef(x,y)[0,1]) if sx>0 and sy>0 else 0.0
