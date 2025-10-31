#!/usr/bin/env python3
# E1D Phase-Aligned Stacking Test

import sys, numpy as np
from pathlib import Path
_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order

def fft_for_base(N, a, L, zp=1, window="hamming", x0=1):
    xs = modular_sequence(N, a, x0, L)
    u  = phase_embed(xs, N)
    w  = np.hamming(L) if window=="hamming" else np.ones(L)
    up = np.zeros(L*zp, dtype=np.complex128)
    up[:L] = u * w
    return np.fft.fft(up)

def snr_from_bins(U_stack, bins, noise_guard=2):
    # U_stack: (M, Lzp) complex spectra
    # COHERENT averaging: average complex, THEN square
    M, Lzp = U_stack.shape
    U_avg = np.mean(U_stack, axis=0)  # (Lzp,)
    mag2_avg = np.abs(U_avg) ** 2

    signal = np.mean(mag2_avg[bins])
    mask = np.ones(Lzp, dtype=bool)
    for k in bins:
        mask[max(0,k-noise_guard):min(Lzp,k+noise_guard+1)] = False
    noise = np.mean(mag2_avg[mask])
    return 10*np.log10(signal / (noise + 1e-30))

def main():
    N, a_ref = 997, 9
    r = multiplicative_order(a_ref, N)
    L, zp, window = 131072, 1, "hamming"

    # 64 bases of the same order
    bases = [pow(a_ref, m, N) for m in range(1, 65)]
    U = np.stack([fft_for_base(N, b, L, zp, window) for b in bases], axis=0)  # (M, Lzp)
    Lzp = U.shape[1]
    bins = [int(round(ell * Lzp / r)) for ell in range(1, r)]

    # Reference phases per harmonic from base 0
    ref = U[0, bins]
    ref_ph = np.angle(ref)

    M_values = [4, 8, 16, 32, 64]
    print(f"N={N}, r={r}, L={L}, M_values={M_values}\n")

    print("SNR(dB) vs M:")
    print("  M    naive_avg     phase_aligned_avg")
    for M in M_values:
        Us = U[:M]  # subset of bases

        # --- naive coherent average at full spectrum ---
        naive = np.mean(Us, axis=0)                  # (Lzp,)
        # compute SNR using only bins/guard
        snr_naive = snr_from_bins(Us, bins)

        # --- BINWISE PHASE ALIGNMENT just at the harmonic bins ---
        aligned = Us[:, bins] * np.exp(-1j*ref_ph)[None, :]   # rotate each base to match reference at each bin
        # averaged complex line per bin:
        line = np.mean(aligned, axis=0)                       # (len(bins),)
        # power at signal bins after alignment
        signal_pwr = np.mean(np.abs(line)**2)

        # noise estimate unchanged: use off-bin regions from Us (same as snr_from_bins)
        mask = np.ones(Lzp, dtype=bool)
        for k in bins: mask[max(0,k-2):min(Lzp,k+3)] = False
        noise_pwr = np.mean(np.abs(Us[:, mask])**2)

        snr_aligned = 10*np.log10(signal_pwr / (noise_pwr + 1e-30))

        print(f"{M:4d}   {snr_naive:10.2f}        {snr_aligned:10.2f}")

if __name__ == "__main__":
    main()
