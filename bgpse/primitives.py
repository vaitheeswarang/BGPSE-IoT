from __future__ import annotations
import hashlib, hmac, os
import numpy as np
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.exceptions import InvalidSignature
from .constants import AES_SBOX
from .gf import gf_mul, gf_inv
from .utils import sha256, shake

def hkdf96(shared:bytes,salt:bytes,info:bytes)->tuple[bytes,bytes,bytes]:
    out=HKDF(algorithm=hashes.SHA256(),length=96,salt=salt,info=info).derive(shared)
    return out[:32],out[32:64],out[64:]

def gfsr_seed_hierarchy(key:bytes)->dict[str,bytes]:
    raw=shake(b"GFSR-INIT"+key,521*4)
    s=np.frombuffer(raw,dtype='<u4').copy()
    # two complete warm-up/mixing passes using R521-style two-lag XOR recurrence
    for _ in range(2):
        for i in range(521): s[i] ^= s[(i-353)%521]
    mixed=s.tobytes()
    return {
        "sbox": sha256(mixed+b"SBOX"),
        "perm": sha256(mixed+b"PERM"),
        "mask1": sha256(mixed+b"MASK1"),
        "mask2": sha256(mixed+b"MASK2"),
    }

def shake_seed_hierarchy(key:bytes)->dict[str,bytes]:
    return {k:sha256(key+k.encode()) for k in ["sbox","perm","mask1","mask2"]}

def dynamic_affine_sbox(key:bytes)->tuple[np.ndarray,np.ndarray]:
    d=sha256(b"DYN-SBOX"+key)
    a_in = d[0] or 1; a_out=d[1] or 1; b_in=d[2]; b_out=d[3]
    # non-zero GF multipliers are invertible linear maps over GF(2)^8
    s=np.empty(256,dtype=np.uint8)
    base=np.frombuffer(AES_SBOX,dtype=np.uint8)
    for x in range(256):
        y=gf_mul(a_in,x)^b_in
        z=int(base[y])
        s[x]=gf_mul(a_out,z)^b_out
    inv=np.empty(256,dtype=np.uint8); inv[s]=np.arange(256,dtype=np.uint8)
    return s,inv

def static_aes_sbox()->tuple[np.ndarray,np.ndarray]:
    s=np.frombuffer(AES_SBOX,dtype=np.uint8).copy(); inv=np.empty(256,dtype=np.uint8); inv[s]=np.arange(256,dtype=np.uint8); return s,inv

def keyed_permutation(seed:bytes,n:int)->np.ndarray:
    scores=np.frombuffer(shake(b"PERM"+seed,n*8),dtype='<u8')
    return np.argsort(scores,kind='stable')

def byte_stream(seed:bytes,n:int,label:bytes)->np.ndarray:
    return np.frombuffer(shake(label+seed,n),dtype=np.uint8).copy()

def ecdh_ephemeral(recipient_pub):
    eph=ec.generate_private_key(ec.SECP256R1()); shared=eph.exchange(ec.ECDH(),recipient_pub); return eph,shared

def ecdsa_sign(priv,data:bytes)->bytes: return priv.sign(data,ec.ECDSA(hashes.SHA256()))
def ecdsa_verify(pub,sig,data:bytes)->bool:
    try: pub.verify(sig,data,ec.ECDSA(hashes.SHA256())); return True
    except InvalidSignature: return False

def hmac256(key:bytes,data:bytes)->bytes: return hmac.new(key,data,hashlib.sha256).digest()
def hmac_verify(key:bytes,data:bytes,tag:bytes)->bool: return hmac.compare_digest(hmac256(key,data),tag)

def aes_ctr_encrypt(key:bytes,nonce16:bytes,data:bytes)->bytes:
    e=Cipher(algorithms.AES(key),modes.CTR(nonce16)).encryptor(); return e.update(data)+e.finalize()
def aes_ctr_decrypt(key:bytes,nonce16:bytes,data:bytes)->bytes: return aes_ctr_encrypt(key,nonce16,data)

def aes_cbc_encrypt(key:bytes,iv:bytes,data:bytes)->bytes:
    pad=PKCS7(128).padder(); p=pad.update(data)+pad.finalize(); e=Cipher(algorithms.AES(key),modes.CBC(iv)).encryptor(); return e.update(p)+e.finalize()
def aes_cbc_decrypt(key:bytes,iv:bytes,data:bytes)->bytes:
    d=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor(); p=d.update(data)+d.finalize(); u=PKCS7(128).unpadder(); return u.update(p)+u.finalize()
