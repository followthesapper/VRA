#!/usr/bin/env python3
# E1D Shifted Copies Baseline (should show √M scaling)

import sys, numpy as np
from pathlib import Path
_REPO = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO / "Code" / "VRA"))
from core import modular_sequence, phase_embed, multiplicative_order

def fft_of_shifted(N, a, L, shift, zp=1, window="hamming", x0=1):
    xs = modular_sequence(N, a, x0, L)
    u  = phase_embed(xs, N)
    u  = np.roll(u, shift)                             # circular time shift (pure phase in freq)

    # Window handling
    if window == "none":
        w = np.ones(L)
    elif window == "hamming":
        w = np.hamming(L)
    elif window == "hann":
        w = np.hanning(L)
    else:
        w = np.ones(L)

    up = np.zeros(L*zp, dtype=np.complex128)
    up[:L] = u * w
    return np.fft.fft(up)

def snr_at_harmonics(U_stack, r, noise_guard=2):
    M, Lzp = U_stack.shape
    bins = [int(round(ell * Lzp / r)) for ell in range(1, r)]

    # COHERENT averaging: average complex, THEN square
    U_avg = np.mean(U_stack, axis=0)  # (Lzp,)
    mag2_avg = np.abs(U_avg) ** 2

    signal = np.mean(mag2_avg[bins])
    mask = np.ones(Lzp, dtype=bool)
    for k in bins:
        mask[max(0,k-noise_guard):min(Lzp,k+noise_guard+1)] = False
    noise = np.mean(mag2_avg[mask])
    return 10*np.log10(signal/(noise+1e-30))

def main():
    N, a = 997, 9
    r = multiplicative_order(a, N)   # e.g., 83
    L, zp, window = 131072, 1, "none"  # NO WINDOWING!

    M_values = [4, 8, 16, 32, 64]
    print(f"N={N}, a={a}, r={r}, L={L}\nSNR(dB) for shifted copies (should show ~+3 dB per doubling):")
    print("  M      SNR(dB)")
    for M in M_values:
        shifts = np.random.default_rng(0).integers(0, L, size=M)  # random circular shifts
        U = np.stack([fft_of_shifted(N, a, L, int(s), zp, window) for s in shifts], axis=0)
        # Coherent average of the SAME signal up to time-shift ⇒ should be alignable at every bin automatically
        snr = snr_at_harmonics(U, r)
        print(f"{M:4d}    {snr:8.2f}")

if __name__ == "__main__":
    main()
