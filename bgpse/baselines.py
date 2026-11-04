from __future__ import annotations
import os, hashlib
import numpy as np
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from .utils import StageTimer, sha256, shake
from .primitives import aes_ctr_encrypt,aes_ctr_decrypt,aes_cbc_encrypt,aes_cbc_decrypt,hmac256,hmac_verify,dynamic_affine_sbox,keyed_permutation

MASTER=sha256(b"BGPSE-IoT reproducible baseline master key v1")

def _k(label): return sha256(MASTER+label)

def aes_gcm(data):
    tm=StageTimer(); key=_k(b"AESGCM"); nonce=os.urandom(12)
    with tm.stage("encrypt"): ct=AESGCM(key).encrypt(nonce,data,None)
    with tm.stage("decrypt"): pt=AESGCM(key).decrypt(nonce,ct,None)
    return ct,pt,tm.ms()

def chacha(data):
    tm=StageTimer(); key=_k(b"CHACHA"); nonce=os.urandom(12)
    with tm.stage("encrypt"): ct=ChaCha20Poly1305(key).encrypt(nonce,data,None)
    with tm.stage("decrypt"): pt=ChaCha20Poly1305(key).decrypt(nonce,ct,None)
    return ct,pt,tm.ms()

def aes_ctr_hmac(data):
    tm=StageTimer(); ke=_k(b"CTR"); km=_k(b"CTRHMAC"); iv=os.urandom(16)
    with tm.stage("encrypt"): ct=aes_ctr_encrypt(ke,iv,data); tag=hmac256(km,iv+ct)
    with tm.stage("decrypt"):
        if not hmac_verify(km,iv+ct,tag): raise ValueError("tag")
        pt=aes_ctr_decrypt(ke,iv,ct)
    return ct+tag,pt,tm.ms()

def aes_cbc_hmac(data):
    tm=StageTimer(); ke=_k(b"CBC"); km=_k(b"CBCHMAC"); iv=os.urandom(16)
    with tm.stage("encrypt"): ct=aes_cbc_encrypt(ke,iv,data); tag=hmac256(km,iv+ct)
    with tm.stage("decrypt"):
        if not hmac_verify(km,iv+ct,tag): raise ValueError("tag")
        pt=aes_cbc_decrypt(ke,iv,ct)
    return ct+tag,pt,tm.ms()

def ecies_aesgcm(data):
    tm=StageTimer(); recip=ec.generate_private_key(ec.SECP256R1())
    with tm.stage("ecdh"):
        eph=ec.generate_private_key(ec.SECP256R1()); shared=eph.exchange(ec.ECDH(),recip.public_key())
    with tm.stage("hkdf"): key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=b"ECIES-P256-AESGCM").derive(shared)
    nonce=os.urandom(12)
    with tm.stage("encrypt"): ct=AESGCM(key).encrypt(nonce,data,None)
    with tm.stage("decrypt"):
        shared2=recip.exchange(ec.ECDH(),eph.public_key()); key2=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=b"ECIES-P256-AESGCM").derive(shared2); pt=AESGCM(key2).decrypt(nonce,ct,None)
    d=tm.ms(); d["encrypt"]=d.get("ecdh",0)+d.get("hkdf",0)+d.get("encrypt",0)
    return ct,pt,d

def _rule90_stream(seed:bytes,n:int)->bytes:
    state=int.from_bytes(sha256(seed)[:8],"little") or 1; out=bytearray()
    mask=(1<<64)-1
    while len(out)<n:
        left=((state<<1)&mask)|(state>>63); right=(state>>1)|((state&1)<<63); state=left^right
        out.extend(state.to_bytes(8,"little"))
    return bytes(out[:n])

def ca_ecc_reference(data):
    """Technique-family reference only; NOT an exact reproduction of EHIES-ECCCA or another paper."""
    tm=StageTimer(); recip=ec.generate_private_key(ec.SECP256R1())
    with tm.stage("ecdh"):
        eph=ec.generate_private_key(ec.SECP256R1()); shared=eph.exchange(ec.ECDH(),recip.public_key())
    with tm.stage("ca_stream"): ks=_rule90_stream(shared,len(data))
    with tm.stage("encrypt"): ct=np.bitwise_xor(np.frombuffer(data,dtype=np.uint8),np.frombuffer(ks,dtype=np.uint8)).tobytes()
    with tm.stage("decrypt"): pt=np.bitwise_xor(np.frombuffer(ct,dtype=np.uint8),np.frombuffer(ks,dtype=np.uint8)).tobytes()
    d=tm.ms(); d["encrypt"]=d.get("ecdh",0)+d.get("ca_stream",0)+d.get("encrypt",0)
    return ct,pt,d

def ecc_dynamic_sbox_reference(data):
    """Technique-family reference only; NOT an exact reproduction of a specific published ECC dynamic-S-box cipher."""
    tm=StageTimer(); recip=ec.generate_private_key(ec.SECP256R1())
    with tm.stage("ecdh"):
        eph=ec.generate_private_key(ec.SECP256R1()); shared=eph.exchange(ec.ECDH(),recip.public_key())
    with tm.stage("sbox"): s,inv=dynamic_affine_sbox(shared)
    with tm.stage("perm"): perm=keyed_permutation(shared,len(data))
    x=np.frombuffer(data,dtype=np.uint8); p=x[perm]
    with tm.stage("encrypt"): ct=s[p].tobytes()
    with tm.stage("decrypt"):
        q=inv[np.frombuffer(ct,dtype=np.uint8)]; rec=np.empty_like(q); rec[perm]=q; pt=rec.tobytes()
    d=tm.ms(); d["encrypt"]=d.get("ecdh",0)+d.get("sbox",0)+d.get("perm",0)+d.get("encrypt",0)
    return ct,pt,d

BASELINES={
 "AES-256-GCM":("standard",aes_gcm),
 "ChaCha20-Poly1305":("standard",chacha),
 "AES-CTR-HMAC-SHA256":("standard",aes_ctr_hmac),
 "AES-CBC-HMAC-SHA256":("standard",aes_cbc_hmac),
 "ECIES-P256-AESGCM":("standard-hybrid",ecies_aesgcm),
 "CA-ECC-Reference":("literature-family-reference",ca_ecc_reference),
 "ECC-DynamicSBox-Reference":("literature-family-reference",ecc_dynamic_sbox_reference),
}
