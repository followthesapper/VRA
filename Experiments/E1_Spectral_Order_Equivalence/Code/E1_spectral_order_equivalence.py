#!/usr/bin/env python3
import json, argparse, numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Code" / "VRA"))

from core import (compute_averaged_spectrum, compute_precision_recall,
                      validated_radius, multiplicative_order, classify_regime)

def generate_cases():
    moduli = [997,1009,1013,2017,3001]
    L = 131072
    for N in moduli:
        # sample bases, dedupe orders
        seen = set()
        for a in range(2, min(N,400)):
            if np.gcd(a,N)==1:
                try:
                    r = multiplicative_order(a,N)
                    if r not in seen:
                        seen.add(r)
                        yield dict(N=N,r=r,L=L,M=16)
                except: pass

def expected_bins(r,Lzp):
    """Generate all expected harmonic bin locations for order r.

    Returns list of FFT bin indices corresponding to harmonics k*Lzp/r
    for k = 1, 2, ..., r-1.
    """
    return [ (k*Lzp)//r for k in range(1, r) ]

def run_case(N,r,L,M):
    # pick M bases with order r (simple scan; use your robust selector if available)
    bases = []
    a = 2
    while len(bases)<M and a<N:
        if np.gcd(a,N)==1:
            try:
                if multiplicative_order(a,N)==r: bases.append(a)
            except: pass
        a+=1
    if len(bases)<max(1,M//2):  # tolerate scarcity
        return None

    mag2 = compute_averaged_spectrum(N,bases,x0=1,length=L, zp=4, window="hann")
    Lzp = L*4
    R = validated_radius(Lzp)
    hb = expected_bins(r,Lzp)
    metrics = compute_precision_recall(mag2,hb,R)
    regime,_ = classify_regime(N,r)
    return dict(N=N,r=r,M=M,L=L,regime=regime,R=R,**metrics)

def main(out):
    Path(out).mkdir(parents=True, exist_ok=True)
    rows=[]
    for case in generate_cases():
        res = run_case(**case)
        if res: rows.append(res)
    p = Path(out)/"E1_results.json"
    p.write_text(json.dumps(rows,indent=2))
    print(f"[ok] {p}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="../Data")
    args=ap.parse_args()
    main(args.out)
