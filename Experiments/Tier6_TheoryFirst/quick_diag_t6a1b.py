#!/usr/bin/env python3
import argparse, math, json, sys, random
from collections import Counter
import numpy as np

# ------------------------------
# Utils
# ------------------------------
def is_probable_prime(n):
    if n < 2: return False
    small = [2,3,5,7,11,13,17,19,23,29]
    for p in small:
        if n == p: return True
        if n % p == 0: return n == p
    # Miller-Rabin (deterministic for 32-bit; good enough here)
    d, s = n-1, 0
    while d % 2 == 0:
        d >>= 1; s += 1
    for a in [2,7,61]:
        if a % n == 0: 
            continue
        x = pow(a, d, n)
        if x == 1 or x == n-1:
            continue
        skip = False
        for _ in range(s-1):
            x = (x*x) % n
            if x == n-1:
                skip = True; break
        if skip: 
            continue
        return False
    return True

def prime_factors_of(n):
    fac = Counter()
    d = 2
    while d * d <= n:
        while n % d == 0:
            fac[d] += 1
            n //= d
        d += 1 if d == 2 else 2  # skip evens after 2
    if n > 1: fac[n] += 1
    return fac

def pow_mod(a, e, m):
    return pow(a, e, m)

def has_exact_order(a, r, N, primes_of_r):
    if pow_mod(a, r, N) != 1:
        return False
    for p in primes_of_r:
        if pow_mod(a, r // p, N) == 1:
            return False
    return True

def sample_bases_exact_order(N, r, M, seed=0):
    rnd = np.random.default_rng(seed)
    primes_of_r = list(prime_factors_of(r).keys())
    bases = []
    attempts = 0
    while len(bases) < M and attempts < 50*N:
        a = int(rnd.integers(2, N-1))
        if math.gcd(a, N) != 1:
            attempts += 1; continue
        if has_exact_order(a, r, N, primes_of_r):
            bases.append(a)
        attempts += 1
    return bases

# ------------------------------
# Signals & measurements
# ------------------------------
def build_sequences(N, bases, L):
    # x_{n+1} = a * x_n (mod N), phase = 2π x / N, signal = e^{i phase}
    seqs = []
    for a in bases:
        x = 1
        s = np.empty(L, dtype=np.complex128)
        for n in range(L):
            x = (x * a) % N
            s[n] = np.exp(1j * (2*np.pi * x / N))
        seqs.append(s)
    return np.asarray(seqs)  # (M, L)

def integer_bin_measure(seqs, r, Kmax):
    # Read at integer bins nearest to k*L/r
    M, L = seqs.shape
    R_list, mag_list = [], []
    for k in range(1, Kmax+1):
        f = k * L / r
        bin_idx = int(round(f))
        if bin_idx >= L//2: break
        ph = np.fft.fft(seqs, axis=1)[:, bin_idx]
        mag = np.abs(ph)
        unit = np.where(mag>0, ph/mag, 0)
        mean_ph = unit.mean()
        R_list.append(abs(mean_ph))
        mag_list.append(mag.mean())
    return np.asarray(R_list), np.asarray(mag_list)

def fractional_bin_measure(seqs, r, Kmax):
    # Direct DFT at fractional f = k*L/r
    M, L = seqs.shape
    n = np.arange(L)
    R_list, mag_list = [], []
    for k in range(1, Kmax+1):
        f = k * L / r
        if f >= L//2: break
        kernel = np.exp((-2j*np.pi*f/L) * n)
        ph = (seqs * kernel).sum(axis=1)
        mag = np.abs(ph)
        unit = np.where(mag>0, ph/mag, 0)
        mean_ph = unit.mean()
        R_list.append(abs(mean_ph))
        mag_list.append(mag.mean())
    return np.asarray(R_list), np.asarray(mag_list)

def summarize(R, mag, topk_list, label):
    if len(R) == 0:
        print(f"[{label}]   (no harmonics)"); return
    mean_all = float(np.mean(R))
    print(f"[{label}]   K={len(R):2d} | mean(all)={mean_all:.6f} | "
          f"mag: min/med/max = {np.min(mag):.3e}/{np.median(mag):.3e}/{np.max(mag):.3e}")
    for K in topk_list:
        if len(R) >= K:
            idx = np.argsort(mag)[-K:]
            gated = float(np.mean(R[idx]))
            print(f"    top-{K:2d} gated mean = {gated:.6f}")
    # distribution snippet
    strong = int(np.sum(R >= 0.10))
    print(f"    harmonics with R_ℓ ≥ 0.10: {strong}/{len(R)}")
    head = np.round(R[:12], 3)
    print(f"    first 12 R_ℓ: {head}")

# ------------------------------
# Main
# ------------------------------
def main():
    ap = argparse.ArgumentParser(description="T6-A1b diagnostic (exact-order bases, integer vs fractional, TOP-K sweep).")
    ap.add_argument("--N", type=int, default=12289, help="prime modulus")
    ap.add_argument("--r", type=int, default=2048, help="target order (must divide N-1)")
    ap.add_argument("--L", type=int, default=16384, help="sequence length")
    ap.add_argument("--M", type=int, default=64, help="number of bases")
    ap.add_argument("--Kmax", type=int, default=50, help="max harmonics to evaluate")
    ap.add_argument("--topk", type=str, default="16,24,32", help="comma list of TOP-K to gate")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--bases_json", type=str, default="", help="optional path to read bases (JSON list)")
    ap.add_argument("--save_bases", type=str, default="", help="optional path to save sampled bases (JSON)")
    ap.add_argument("--also_r", type=str, default="", help="optional comma list of extra r to test (same N,L,M)")
    args = ap.parse_args()

    N, r, L, M, Kmax, seed = args.N, args.r, args.L, args.M, args.Kmax, args.seed
    topk_list = [int(x) for x in args.topk.split(",") if x.strip()]

    # sanity
    print(f"N={N}, prime? {is_probable_prime(N)} | r={r}, L={L}, L/r={(L/r):.3f}")
    if (N-1) % r != 0:
        print(f"[WARN] r={r} does not divide N-1={N-1}. Exact-order bases cannot exist here.")
        sys.exit(0)

    # base source
    if args.bases_json:
        with open(args.bases_json, "r") as f:
            bases = json.load(f)
        print(f"[A] Loaded {len(bases)} bases from {args.bases_json}")
        if len(bases) > M:
            bases = bases[:M]
    else:
        print("[A] Sampling bases of EXACT order r...")
        bases = sample_bases_exact_order(N, r, M, seed=seed)
        print(f"    Found {len(bases)}/{M} bases of exact order r.")
        if len(bases) < M:
            print("    [WARN] Could not reach M; proceed with fewer (diagnostic still valid).")
        if args.save_bases:
            with open(args.save_bases, "w") as f:
                json.dump(bases, f)
            print(f"    Saved bases → {args.save_bases}")

    # sequences
    print("\n[B] Building sequences...")
    seqs = build_sequences(N, bases, L)

    # integer peaks
    print("\n[C] INTEGER-peak measurement:")
    R_int, mag_int = integer_bin_measure(seqs, r, Kmax)
    summarize(R_int, mag_int, topk_list, label="INTEGER peaks")

    # fractional peaks
    print("\n[D] FRACTIONAL-peak measurement:")
    R_frac, mag_frac = fractional_bin_measure(seqs, r, Kmax)
    summarize(R_frac, mag_frac, topk_list, label="FRACTIONAL peaks")

    # compare int vs frac
    if len(R_int) and len(R_frac):
        diff = float(np.mean(np.abs(R_int - R_frac)))
        print(f"\n[Δ] mean |INTEGER−FRACTIONAL| over K={min(len(R_int),len(R_frac))}: {diff:.6e}")
        if diff < 1e-3:
            print("    → Peak detuning is NOT the issue (they match).")
        else:
            print("    → Noticeable detuning: investigate L alignment or fractional readout.")

    # optional: test other r on the same N
    if args.also_r:
        print("\n[E] Extra r sweep:")
        for rs in args.also_r.split(","):
            r2 = int(rs)
            if (N-1) % r2 != 0:
                print(f"  r={r2}: skip (does not divide N-1).")
                continue
            print(f"\n  r={r2}: sampling {M} exact-order bases…")
            bases2 = sample_bases_exact_order(N, r2, M, seed=seed+42)
            print(f"    exact-order bases: {len(bases2)}")
            if len(bases2) == 0:
                print("    (no bases)"); continue
            seqs2 = build_sequences(N, bases2, L)
            R2, mag2 = fractional_bin_measure(seqs2, r2, Kmax)
            summarize(R2, mag2, topk_list, label=f"FRACTIONAL peaks @ r={r2}")

    # explicit comparison to exp(-2)
    expm2 = math.exp(-2)
    if len(R_frac):
        mean_all = float(np.mean(R_frac))
        print(f"\n[F] Compare to exp(-2)={expm2:.6f}")
        print(f"    FRACTIONAL mean(all) = {mean_all:.6f} | err = {100*abs(mean_all-expm2)/expm2:5.2f}%")
        for K in topk_list:
            if len(R_frac) >= K:
                idx = np.argsort(mag_frac)[-K:]
                gated = float(np.mean(R_frac[idx]))
                print(f"    FRACTIONAL top-{K:2d} = {gated:.6f} | err = {100*abs(gated-expm2)/expm2:5.2f}%")

if __name__ == "__main__":
    main()
