#!/usr/bin/env python3
import numpy as np, argparse, json
from pathlib import Path
import sys
sys.path += ["../../Code/Core"]
from vra_core import compute_averaged_spectrum, multiplicative_order
from qpe_sim import qpe_histogram

def main(out):
    Path(out).mkdir(parents=True, exist_ok=True)
    N=1009; a=2; L=131072; M=16; r=168  # choose any validated case
    mag2 = compute_averaged_spectrum(N, bases=[a]*(M), length=L, zp=4, window="hann")
    Lzp=L*4

    # Aggregate VRA power into r buckets near k*Lzp/r
    buckets=np.zeros(r)
    rad=max(1,int(0.002*Lzp))  # small neighborhood
    for k in range(r):
        c = int(round(k*Lzp/r))
        lo=max(0,c-rad); hi=min(Lzp-1,c+rad)
        buckets[k]+=mag2[lo:hi].sum()

    hist,_=qpe_histogram(r, shots=10000, bins=r)
    # Spearman rho
    from scipy.stats import spearmanr
    rho,_=spearmanr(buckets, hist)
    Path(out,"E6_bridge_correlation.json").write_text(json.dumps({
        "N":N,"r":r,"rho_spearman":float(rho)
    }, indent=2))
    print("[ok] E6 rho=",rho)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="../../Data/Experiments/tier3/e6")
    args=ap.parse_args(); main(args.out)
