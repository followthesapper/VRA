#!/usr/bin/env python3
"""
E5: ECC Scaling Grid
====================

Goal:
  Sweep (p, r_E, M, L) and evaluate sqrt(M)-like scaling of VRA precision
  and concentration over elliptic curve groups. Demonstrate that VRA's
  spectral concentration scales coherently across base multiplicity and curve size.

Pass Criteria:
  Median R² for sqrt(M) fit ≥ 0.90 in TRANS/LOW SNR regimes.

Outputs:
  - JSON: precision, recall, and scaling fits per test curve.
  - PNG: R² vs sqrt(M) plots.

Author: Dylan Vaca
Date: October 2025
"""

import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Local imports
dir_core = Path(__file__).resolve().parents[2] / 'Code' / 'Core'
sys.path.insert(0, str(dir_core))

from vra_core import compute_averaged_spectrum, compute_precision_recall, validated_radius
from ecc_vra_core import add, ecc_phase_embed, order_of_point

# Test elliptic curves (toy examples)
TEST_CURVES = [
    # p, a, b, P=(x,y), expected order rE
    (1019, 2, 3, (5, 376), 169),
    (1009, 2, 3, (7, 154), 168),
]

def expected_bins(rE, Lzp):
    K = min(rE, 100)
    return [int(round(k * Lzp / rE)) for k in range(1, K)]

def generate_ecc_series(P, a, p, steps):
    """Generate ECC phase-encoded sequence."""
    pts = []
    Q = P
    for _ in range(steps):
        pts.append(Q)
        Q = add(Q, P, a, p)
        if Q is None:
            break
    return ecc_phase_embed(pts, p)

def run_case(p, a, b, P, rE, L, M):
    seqs = []
    for m in range(M):
        seqs.append(generate_ecc_series(P, a, p, steps=min(rE, L//8)))
    mag2 = compute_averaged_spectrum(signal_list=seqs, zp=4, window='hann')
    Lzp = L * 4
    R = validated_radius(Lzp)
    hb = expected_bins(rE, Lzp)
    met = compute_precision_recall(mag2, hb, R)
    return float(met['precision']), float(met['recall'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='../../Data/Experiments/tier2/e5')
    parser.add_argument('--L', default='65536,131072,262144')
    parser.add_argument('--M', default='1,4,8,16,32')
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    Ls = [int(x) for x in args.L.split(',')]
    Ms = [int(x) for x in args.M.split(',')]

    all_rows = []

    for p, a, b, P, rE in TEST_CURVES:
        for L in Ls:
            precisions = []
            for M in Ms:
                try:
                    pr, rc = run_case(p, a, b, P, rE, L, M)
                    all_rows.append({'p': p, 'L': L, 'M': M, 'precision': pr, 'recall': rc, 'rE': rE})
                    precisions.append((M, pr))
                except Exception as e:
                    print(f"⚠️ ECC case failed p={p}, M={M}: {e}")
                    continue

            # Perform sqrt(M) regression fit
            Ms_arr = np.array([np.sqrt(m) for m, _ in precisions])
            Ys = np.array([pr for _, pr in precisions])
            if len(Ms_arr) >= 3:
                X = np.vstack([np.ones(len(Ms_arr)), Ms_arr]).T
                beta, *_ = np.linalg.lstsq(X, Ys, rcond=None)
                Y_hat = X @ beta
                ss_res = np.sum((Ys - Y_hat)**2)
                ss_tot = np.sum((Ys - np.mean(Ys))**2)
                R2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
                all_rows.append({'p': p, 'L': L, 'metric': 'R2_sqrtM_precision', 'value': float(R2)})

                # Plot scaling behavior
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.scatter(Ms_arr, Ys, label='Precision')
                ax.plot(Ms_arr, Y_hat, 'r--', label=f'Fit (R²={R2:.3f})')
                ax.set_title(f'E5: √M Scaling — p={p}, L={L}')
                ax.set_xlabel('√M')
                ax.set_ylabel('Precision')
                ax.grid(alpha=0.3)
                ax.legend()
                fig.savefig(out_dir / f'E5_scaling_p{p}_L{L}.png', dpi=180, bbox_inches='tight')
                plt.close(fig)

    # Save results
    out_json = out_dir / 'E5_ecc_scaling_grid.json'
    with open(out_json, 'w') as f:
        json.dump(all_rows, f, indent=2)
    print(f'✅ Saved ECC scaling grid results → {out_json}')

if __name__ == '__main__':
    main()
