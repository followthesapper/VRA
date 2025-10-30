#!/usr/bin/env python3
"""
Baseline Order-Finding Methods
================================

Implements baseline methods for comparison with VRA:
1. Brute-force divisor enumeration
2. Single-base FFT (no averaging)
3. Incoherent averaging (power spectrum averaging)
4. Baby-step giant-step
5. Pollard's rho (when applicable)

Author: Dylan Vaca
Date: October 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))

import numpy as np
import time
from vra_core import (
    multiplicative_order,
    compute_averaged_spectrum,
    compute_concentration,
    validated_radius
)


class BaselineOrderFinder:
    """Base class for order-finding methods"""

    def __init__(self, N):
        self.N = N
        self.reset_stats()

    def reset_stats(self):
        """Reset timing and resource statistics"""
        self.stats = {
            'runtime': 0,
            'num_trials': 0,
            'success': False,
            'found_order': None
        }

    def find_order(self, a):
        """Find order of base a (to be implemented by subclasses)"""
        raise NotImplementedError


class BruteForceOrder(BaselineOrderFinder):
    """Brute-force order finding by exponentiation"""

    def find_order(self, a, max_iter=None):
        """Find order by computing a^k mod N until a^r ≡ 1"""
        if max_iter is None:
            max_iter = self.N

        start = time.time()

        if np.gcd(a, self.N) != 1:
            self.stats['runtime'] = time.time() - start
            self.stats['success'] = False
            return None

        x = a % self.N
        for r in range(1, max_iter + 1):
            if x == 1:
                self.stats['runtime'] = time.time() - start
                self.stats['num_trials'] = r
                self.stats['success'] = True
                self.stats['found_order'] = r
                return r
            x = (x * a) % self.N

        self.stats['runtime'] = time.time() - start
        self.stats['num_trials'] = max_iter
        self.stats['success'] = False
        return None


class SingleBaseFFT(BaselineOrderFinder):
    """Single-base FFT spectral detector (no averaging)"""

    def __init__(self, N, L=65536, topk=11):
        super().__init__(N)
        self.L = L
        self.topk = topk

    def find_order(self, a, length=None):
        """Find order using single-base FFT"""
        if length is None:
            length = self.L // 8

        start = time.time()

        if np.gcd(a, self.N) != 1:
            self.stats['runtime'] = time.time() - start
            self.stats['success'] = False
            return None

        # Generate modular sequence
        x = 1
        seq = []
        for _ in range(length):
            x = (x * a) % self.N
            seq.append(np.exp(2j * np.pi * x / self.N))

        # Apply window
        window = np.hanning(len(seq))
        seq_windowed = np.array(seq) * window

        # Zero-pad and FFT
        seq_padded = np.pad(seq_windowed, (0, self.L - len(seq_windowed)))
        U = np.fft.fft(seq_padded)
        mag2 = np.abs(U)**2

        # Find top peaks
        top_bins = np.argsort(mag2)[-self.topk:][::-1]

        # Estimate order from fundamental frequency
        # The fundamental peak should be at approximately L/r
        if top_bins[0] == 0:
            main_peak = top_bins[1]  # Skip DC
        else:
            main_peak = top_bins[0]

        if main_peak > 0:
            estimated_r = self.L // main_peak
        else:
            estimated_r = None

        # Verify estimate
        if estimated_r is not None:
            actual_order = multiplicative_order(a, self.N, max_iter=self.N)
            success = (estimated_r == actual_order)
        else:
            success = False
            actual_order = None

        self.stats['runtime'] = time.time() - start
        self.stats['success'] = success
        self.stats['found_order'] = estimated_r
        self.stats['actual_order'] = actual_order

        return estimated_r if success else None


class IncoherentAveraging(BaselineOrderFinder):
    """Incoherent averaging: mean(|U_m|²) instead of |mean(U_m)|²"""

    def __init__(self, N, L=65536, topk=11):
        super().__init__(N)
        self.L = L
        self.topk = topk

    def find_order_multibase(self, bases, length=None):
        """Find order using incoherent averaging"""
        if length is None:
            length = self.L // 8

        start = time.time()

        M = len(bases)
        mag2_sum = np.zeros(self.L)

        for a in bases:
            if np.gcd(a, self.N) != 1:
                continue

            # Generate sequence
            x = 1
            seq = []
            for _ in range(length):
                x = (x * a) % self.N
                seq.append(np.exp(2j * np.pi * x / self.N))

            # Window and FFT
            window = np.hanning(len(seq))
            seq_windowed = np.array(seq) * window
            seq_padded = np.pad(seq_windowed, (0, self.L - len(seq_windowed)))
            U = np.fft.fft(seq_padded)

            # Accumulate power spectra (INCOHERENT)
            mag2_sum += np.abs(U)**2

        # Average power spectra
        mag2_avg = mag2_sum / M

        # Find top peaks
        top_bins = np.argsort(mag2_avg)[-self.topk:][::-1]

        if top_bins[0] == 0:
            main_peak = top_bins[1]
        else:
            main_peak = top_bins[0]

        if main_peak > 0:
            estimated_r = self.L // main_peak
        else:
            estimated_r = None

        # Verify
        if estimated_r is not None and len(bases) > 0:
            actual_order = multiplicative_order(bases[0], self.N, max_iter=self.N)
            success = (estimated_r == actual_order)
        else:
            success = False
            actual_order = None

        self.stats['runtime'] = time.time() - start
        self.stats['num_trials'] = M
        self.stats['success'] = success
        self.stats['found_order'] = estimated_r
        self.stats['actual_order'] = actual_order

        return estimated_r if success else None


class BabyStepGiantStep(BaselineOrderFinder):
    """Baby-step giant-step algorithm for order finding"""

    def find_order(self, a, upper_bound=None):
        """Find order using baby-step giant-step"""
        if upper_bound is None:
            upper_bound = min(self.N, 10000)  # Limit for memory

        start = time.time()

        if np.gcd(a, self.N) != 1:
            self.stats['runtime'] = time.time() - start
            self.stats['success'] = False
            return None

        m = int(np.ceil(np.sqrt(upper_bound)))

        # Baby steps: compute a^j for j = 0, 1, ..., m-1
        baby_steps = {}
        power = 1
        for j in range(m):
            if power == 1 and j > 0:
                # Found order
                self.stats['runtime'] = time.time() - start
                self.stats['success'] = True
                self.stats['found_order'] = j
                return j

            baby_steps[power] = j
            power = (power * a) % self.N

        # Giant steps: compute a^{-m*i} for i = 1, 2, ...
        # First compute a^{-m} mod N
        am = pow(a, m, self.N)
        am_inv = pow(am, -1, self.N)  # Modular inverse

        gamma = 1
        for i in range(1, m + 1):
            gamma = (gamma * am_inv) % self.N

            if gamma in baby_steps:
                j = baby_steps[gamma]
                r = i * m - j

                if r > 0:
                    # Verify
                    if pow(a, r, self.N) == 1:
                        self.stats['runtime'] = time.time() - start
                        self.stats['success'] = True
                        self.stats['found_order'] = r
                        return r

        self.stats['runtime'] = time.time() - start
        self.stats['success'] = False
        return None


class VRACoherentAveraging(BaselineOrderFinder):
    """VRA method with coherent averaging (for comparison)"""

    def __init__(self, N, L=65536, topk=11):
        super().__init__(N)
        self.L = L
        self.topk = topk

    def find_order_multibase(self, bases, length=None):
        """Find order using VRA coherent averaging"""
        if length is None:
            length = self.L // 8

        start = time.time()

        # Use vra_core
        mag2_avg = compute_averaged_spectrum(
            self.N, bases, x0=1, length=length, zp=8, window='hann'
        )

        # Find top peaks
        top_bins = np.argsort(mag2_avg)[-self.topk:][::-1]

        if top_bins[0] == 0:
            main_peak = top_bins[1]
        else:
            main_peak = top_bins[0]

        if main_peak > 0:
            estimated_r = self.L // main_peak
        else:
            estimated_r = None

        # Verify
        if estimated_r is not None and len(bases) > 0:
            actual_order = multiplicative_order(bases[0], self.N, max_iter=self.N)
            success = (estimated_r == actual_order)
        else:
            success = False
            actual_order = None

        self.stats['runtime'] = time.time() - start
        self.stats['num_trials'] = len(bases)
        self.stats['success'] = success
        self.stats['found_order'] = estimated_r
        self.stats['actual_order'] = actual_order

        return estimated_r if success else None


def benchmark_single_case(N, a, r, methods=['brute', 'single_fft', 'bsgs']):
    """Benchmark all methods on a single case

    Parameters:
        N (int): Modulus
        a (int): Base
        r (int): Known order (for verification)
        methods (list): Methods to test

    Returns:
        dict: Results for each method
    """
    results = {}

    if 'brute' in methods:
        bf = BruteForceOrder(N)
        found = bf.find_order(a, max_iter=min(r * 2, N))
        results['brute_force'] = {
            'found_order': found,
            'correct': (found == r),
            'runtime': bf.stats['runtime'],
            'trials': bf.stats['num_trials']
        }

    if 'single_fft' in methods:
        sf = SingleBaseFFT(N)
        found = sf.find_order(a)
        results['single_fft'] = {
            'found_order': found,
            'correct': (found == r),
            'runtime': sf.stats['runtime']
        }

    if 'bsgs' in methods:
        bsgs = BabyStepGiantStep(N)
        found = bsgs.find_order(a, upper_bound=min(r * 2, 10000))
        results['bsgs'] = {
            'found_order': found,
            'correct': (found == r),
            'runtime': bsgs.stats['runtime']
        }

    return results


if __name__ == '__main__':
    # Example usage
    print("Baseline Methods Test")
    print("=" * 70)

    N = 1009
    a = 11
    r = multiplicative_order(a, N, max_iter=N)

    print(f"N = {N}, a = {a}, r = {r}")
    print()

    results = benchmark_single_case(N, a, r)

    for method, result in results.items():
        print(f"{method}:")
        print(f"  Found: {result['found_order']}, Correct: {result['correct']}")
        print(f"  Runtime: {result['runtime']:.6f}s")
        if 'trials' in result:
            print(f"  Trials: {result['trials']}")
        print()
