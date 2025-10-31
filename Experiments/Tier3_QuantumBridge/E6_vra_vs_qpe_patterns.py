#!/usr/bin/env python3
import numpy as np, argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "Code" / "VRA"))
from core import compute_averaged_spectrum, multiplicative_order
from qpe_sim import qpe_histogram

def main(out):
    Path(out).mkdir(parents=True, exist_ok=True)
    N=1009; a=2; L=131072; M=16; r=168  # choose any validated case
    mag2 = compute_averaged_spectrum(N, bases=[a]*M, x0=1, length=L, zp=4, window="hann")
    Lzp=L*4

    # Aggregate VRA power into r buckets near k*Lzp/r
    buckets=np.zeros(r)
    rad=max(1,int(0.002*Lzp))  # small neighborhood
    for k in range(r):
        c = int(round(k*Lzp/r))
        lo=max(0,c-rad); hi=min(Lzp-1,c+rad)
        buckets[k]+=mag2[lo:hi].sum()

    hist,_=qpe_histogram(r, shots=10000, bins=r)

    # Spearman rho (manual implementation to avoid scipy/numpy compatibility)
    def spearman_rho(x, y):
        """Compute Spearman rank correlation"""
        n = len(x)
        if n != len(y):
            return 0.0
        # Rank transformation
        rx = np.argsort(np.argsort(x))
        ry = np.argsort(np.argsort(y))
        # Pearson correlation of ranks
        rx_mean = rx.mean()
        ry_mean = ry.mean()
        num = ((rx - rx_mean) * (ry - ry_mean)).sum()
        den = np.sqrt(((rx - rx_mean)**2).sum() * ((ry - ry_mean)**2).sum())
        return num / den if den > 0 else 0.0

    rho = spearman_rho(buckets, hist)
    Path(out,"E6_bridge_correlation.json").write_text(json.dumps({
        "N":N,"r":r,"rho_spearman":float(rho)
    }, indent=2))
    print("[ok] E6 rho=",rho)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="../../Data/Experiments/Tier3/E6")
    args=ap.parse_args(); main(args.out)
