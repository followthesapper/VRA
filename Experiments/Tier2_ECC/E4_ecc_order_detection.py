#!/usr/bin/env python3
import numpy as np, argparse, json
from pathlib import Path
from ecc_vra_core import add, mul, order_of_point, ecc_phase_embed
import sys
sys.path += ["../../Code/Core"]
from vra_core import compute_averaged_spectrum, compute_precision_recall, validated_radius

def sample_cycle(G,a,p,steps):
    pts=[G]; Q=G
    for _ in range(steps-1):
        Q=add(Q,G,a,p)
        if Q is None: break
        pts.append(Q)
    return pts

def expected_bins(r,Lzp):
    K=min(r,100)
    return [ (k*Lzp)//r for k in range(1,K) ]

def main(out):
    Path(out).mkdir(parents=True, exist_ok=True)
    # Example small curve y^2=x^3+ax+b over p
    p=1009; a=2; b=3
    # Pick a starting point known to be on curve (toy: small brute)
    # For a quick start, assume P=(x,y) found offline (replace with your finder)
    P=(5, np.sqrt((5**3 + a*5 + b) % p) if True else 1)  # replace with a valid point!
    # In practice, use a small on-curve point you’ve precomputed.

    rE = 168  # replace with actual order_of_point(P,a,p)
    L=131072; M=16

    cycles=[]
    for m in range(M):
        pts = sample_cycle(P,a,p,steps=min(rE, L//8))
        cycles.append(ecc_phase_embed(pts,p))

    # Stack time series → average spectra (reuse your core)
    mag2 = compute_averaged_spectrum(signal_list=cycles, zp=4, window="hann")
    Lzp=L*4; R=validated_radius(Lzp)
    hb = expected_bins(rE,Lzp)
    metrics = compute_precision_recall(mag2,hb,R)
    Path(out,"E4_ecc_order_detection.json").write_text(json.dumps({
        "p":p,"a":a,"b":b,"rE":rE,"L":L,"M":M,**metrics
    }, indent=2))
    print("[ok] E4 complete")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="../../Data/Experiments/tier2/e4")
    args=ap.parse_args()
    main(args.out)
