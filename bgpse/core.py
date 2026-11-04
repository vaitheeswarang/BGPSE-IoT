from __future__ import annotations
import os, hashlib
import numpy as np
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .utils import StageTimer, sha256, canonical_json
from .primitives import (hkdf96,gfsr_seed_hierarchy,shake_seed_hierarchy,dynamic_affine_sbox,static_aes_sbox,
 keyed_permutation,byte_stream,ecdh_ephemeral,ecdsa_sign,hmac256,hmac_verify)

class BGPSEContext:
    def __init__(self):
        self.recipient_priv=ec.generate_private_key(ec.SECP256R1()); self.recipient_pub=self.recipient_priv.public_key()
        self.device_priv=ec.generate_private_key(ec.SECP256R1()); self.device_pub=self.device_priv.public_key()
        self.device_id="virtual-camera-001"; self.policy_id="policy-visual-001"; self.key_version=1

def _xor_accum_forward(u): return np.bitwise_xor.accumulate(u)
def _xor_accum_reverse(z): return np.bitwise_xor.accumulate(z[::-1])[::-1]
def _inv_forward(f):
    u=np.empty_like(f); u[0]=f[0]; u[1:]=np.bitwise_xor(f[1:],f[:-1]); return u
def _inv_reverse(c):
    z=np.empty_like(c); z[-1]=c[-1]; z[:-1]=np.bitwise_xor(c[:-1],c[1:]); return z

def encrypt_image_bytes(data:bytes,shape:tuple[int,int,int],ctx:BGPSEContext,variant:str="full"):
    tm=StageTimer(); nonce=os.urandom(16); meta={"device":ctx.device_id,"policy":ctx.policy_id,"version":1,"shape":shape,"key_version":ctx.key_version}
    with tm.stage("ecdh"):
        eph,shared=ecdh_ephemeral(ctx.recipient_pub)
    with tm.stage("hkdf"):
        ke,km,ka=hkdf96(shared,nonce,canonical_json(meta))
    with tm.stage("content_digest"):
        digest=sha256(data); kc=sha256(ke+nonce+digest+b"BGPSE-IoT-CONTENT-v1")
    with tm.stage("seed_hierarchy"):
        seeds=shake_seed_hierarchy(kc) if variant=="shake_only" else gfsr_seed_hierarchy(kc)
    with tm.stage("dynamic_sbox"):
        sbox,inv=static_aes_sbox() if variant=="static_sbox" else dynamic_affine_sbox(seeds["sbox"])
    x=np.frombuffer(data,dtype=np.uint8).copy(); n=len(x)
    with tm.stage("permutation"):
        perm=np.arange(n) if variant=="no_permutation" else keyed_permutation(seeds["perm"],n)
        p=x[perm]
    with tm.stage("mask_generation"):
        r1=byte_stream(seeds["mask1"],n,b"R1"); r2=byte_stream(seeds["mask2"],n,b"R2")
    with tm.stage("substitution"):
        u=sbox[np.bitwise_xor(p,r1)]
    with tm.stage("forward_diffusion"):
        f=_xor_accum_forward(u)
    with tm.stage("reverse_diffusion"):
        if variant=="single_diffusion": core=np.bitwise_xor(f,r2)
        else: core=_xor_accum_reverse(np.bitwise_xor(f,r2))
    aad=canonical_json(meta)
    outer_nonce=os.urandom(12)
    if variant in ("no_outer_aead","core_only"):
        outer=core.tobytes()
    else:
        with tm.stage("aes_gcm_outer"):
            outer=AESGCM(ka).encrypt(outer_nonce,core.tobytes(),aad)
    if variant=="core_only":
        tag=b""
    else:
        with tm.stage("hmac"):
            tag=hmac256(km,aad+outer_nonce+outer)
    record={"device":ctx.device_id,"policy":ctx.policy_id,"key_version":ctx.key_version,"cipher_hash":hashlib.sha256(outer).hexdigest(),"uri":"offchain://object/demo","sequence":1}
    recbytes=canonical_json(record)
    if variant in ("no_provenance","core_only"): sig=b""
    else:
        with tm.stage("ecdsa_sign"):
            sig=ecdsa_sign(ctx.device_priv,recbytes)
    packet={"meta":meta,"nonce":nonce,"eph_priv":eph,"ke":ke,"km":km,"ka":ka,"kc":kc,"seeds":seeds,"inv_sbox":inv,"perm":perm,
            "r1":r1,"r2":r2,"outer_nonce":outer_nonce,"outer":outer,"tag":tag,"record":record,"sig":sig,"variant":variant,"shape":shape}
    tm.ns["total_encrypt"] = sum(v for k,v in tm.ns.items() if k!="total_encrypt")
    return packet,tm.ms()

def decrypt_image_bytes(packet,ctx:BGPSEContext):
    tm=StageTimer(); aad=canonical_json(packet["meta"]); outer=packet["outer"]
    if packet["variant"]!="core_only":
        with tm.stage("hmac_verify"):
            if not hmac_verify(packet["km"],aad+packet["outer_nonce"]+outer,packet["tag"]): raise ValueError("HMAC verification failed")
    if packet["variant"] in ("no_outer_aead","core_only"): core_bytes=outer
    else:
        with tm.stage("aes_gcm_outer_decrypt"):
            core_bytes=AESGCM(packet["ka"]).decrypt(packet["outer_nonce"],outer,aad)
    c=np.frombuffer(core_bytes,dtype=np.uint8).copy(); r2=packet["r2"]
    with tm.stage("inverse_reverse_diffusion"):
        z=c if packet["variant"]=="single_diffusion" else _inv_reverse(c)
        f=np.bitwise_xor(z,r2)
    with tm.stage("inverse_forward_diffusion"):
        u=_inv_forward(f)
    with tm.stage("inverse_substitution"):
        p=np.bitwise_xor(packet["inv_sbox"][u],packet["r1"])
    with tm.stage("inverse_permutation"):
        x=np.empty_like(p); x[packet["perm"]]=p
    tm.ns["total_decrypt"] = sum(v for k,v in tm.ns.items() if k!="total_decrypt")
    return x.tobytes(),tm.ms()
