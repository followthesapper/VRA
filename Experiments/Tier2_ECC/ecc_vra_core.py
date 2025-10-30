import numpy as np
# Minimal ECC over prime field (short Weierstrass y^2 = x^3 + ax + b mod p)
def inv_mod(x,p): return pow(x,p-2,p)
def add(P,Q,a,p):
    if P is None: return Q
    if Q is None: return P
    (x1,y1),(x2,y2)=P,Q
    if x1==x2 and (y1+y2)%p==0: return None
    if P!=Q:
        m = ((y2 - y1) * inv_mod((x2 - x1)%p,p)) % p
    else:
        m = ((3*x1*x1 + a) * inv_mod((2*y1)%p,p)) % p
    x3 = (m*m - x1 - x2) % p
    y3 = (m*(x1 - x3) - y1) % p
    return (x3,y3)

def mul(k,P,a,p):
    R=None; Q=P
    while k>0:
        if k&1: R=add(R,Q,a,p)
        Q=add(Q,Q,a,p); k>>=1
    return R

def order_of_point(P,a,p):
    # naive: double-and-add until infinity
    Q=P; n=1
    while Q is not None:
        Q=add(Q,P,a,p); n+=1
        if n>2*p: break
    return n

def ecc_phase_embed(points,p):
    # Use x(P)/p to phase-map; you can try more robust embeddings later.
    xs = np.array([pt[0] for pt in points], dtype=float)
    ph = np.exp(2j*np.pi*xs/p)
    return ph
