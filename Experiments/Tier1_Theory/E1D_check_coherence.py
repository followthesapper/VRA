#!/usr/bin/env python3
# E1D Phase Coherence Check

import sys, numpy as np
from pathlib import Path
# repo wiring
_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order

def fft_for_base(N, a, L, zp=1, window="hamming", x0=1):
    xs = modular_sequence(N, a, x0, L)
    u  = phase_embed(xs, N)                  # complex unit-modulus series
    w  = np.hamming(L) if window=="hamming" else np.ones(L)
    up = np.zeros(L*zp, dtype=np.complex128)
    up[:L] = u * w
    return np.fft.fft(up)

def main():
    # --- choose a classic E1D case ---
    N, a_ref = 997, 9
    r = multiplicative_order(a_ref, N)  # e.g., 83
    L, zp, window = 131072, 1, "hamming"

    # build a set of M bases of the same order r
    # (mix a_ref and other generators of the same subgroup)
    bases = [pow(a_ref, m, N) for m in range(1, 65)]  # 64 different bases
    M = len(bases)

    # FFTs for each base (complex)
    U = np.stack([fft_for_base(N, b, L, zp, window) for b in bases], axis=0)
    Lzp = U.shape[1]

    # expected harmonic bins (skip DC)
    bins = [int(round(ell * Lzp / r)) for ell in range(1, r)]

    # resultant-length (circular coherence) per harmonic
    R = []
    for k in bins:
        vecs = U[:, k] / np.abs(U[:, k] + 1e-30)       # unit phasors
        R.append(np.abs(np.mean(vecs)))                # 0..1, 1 = perfect alignment
    R = np.array(R)

    print(f"N={N}, r={r}, M={M}, L={L}, bins={len(bins)}")
    print(f"Resultant length (phase coherence) across bases:")
    print(f"  mean R: {R.mean():.3f}, median R: {np.median(R):.3f}, max R: {R.max():.3f}")
    # quick histogram buckets
    hist, edges = np.histogram(R, bins=[0, .2, .4, .6, .8, 1.0])
    print("  R histogram (0-.2, .2-.4, .4-.6, .6-.8, .8-1.0):", hist.tolist())

    # Optional: write CSV for plotting downstream
    out = _REPO / "Data" / "Experiments" / "Tier1" / "E1D" / "coherence_R.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(out, R, delimiter=",")
    print(f"[ok] saved per-harmonic R to {out}")

if __name__ == "__main__":
    main()
