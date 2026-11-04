from bgpse.primitives import dynamic_affine_sbox

def test_sbox_bijective():
    s,inv=dynamic_affine_sbox(b'x'*32); assert len(set(map(int,s)))==256
    for i in range(256): assert int(inv[int(s[i])])==i
