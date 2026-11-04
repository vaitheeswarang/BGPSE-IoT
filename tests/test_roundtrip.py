import numpy as np
from bgpse.core import BGPSEContext,encrypt_image_bytes,decrypt_image_bytes
from bgpse.baselines import BASELINES

def test_bgpse_all_variants():
    data=np.arange(64*64*3,dtype=np.uint8).tobytes(); ctx=BGPSEContext()
    for v in ['full','core_only','static_sbox','shake_only','no_permutation','single_diffusion','no_outer_aead','no_provenance']:
        p,_=encrypt_image_bytes(data,(64,64,3),ctx,v); out,_=decrypt_image_bytes(p,ctx); assert out==data

def test_baselines():
    data=bytes(range(256))*20
    for name,(kind,fn) in BASELINES.items():
        ct,pt,t=fn(data); assert pt==data; assert len(ct)>0; assert t['encrypt']>=0
