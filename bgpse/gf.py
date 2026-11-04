def gf_mul(a:int,b:int)->int:
    p=0
    for _ in range(8):
        if b & 1: p ^= a
        hi=a & 0x80
        a=(a<<1)&0xff
        if hi: a ^= 0x1b
        b >>= 1
    return p

def gf_pow(a:int,n:int)->int:
    r=1
    while n:
        if n&1:r=gf_mul(r,a)
        a=gf_mul(a,a); n>>=1
    return r

def gf_inv(a:int)->int:
    if a==0: raise ValueError("0 has no inverse")
    return gf_pow(a,254)
