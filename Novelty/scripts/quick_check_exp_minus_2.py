#!/usr/bin/env python3
"""
QUICK CHECK: Is R̄ ≈ exp(-2)?

This is the FIRST thing to check before deeper investigation.
"""

import numpy as np
from scipy.special import i0, i1

# The measured value from E1D
R_measured_E1D = 0.137

# The value from T6-A1 experiments
R_measured_T6A1_avg = 0.1855
R_measured_T6A1_M64 = 0.14

# Candidate constants
candidates = {
    "exp(-2)": np.exp(-2),
    "1/e²": 1 / (np.e**2),
    "exp(-3/2)": np.exp(-1.5),
    "exp(-√2)": np.exp(-np.sqrt(2)),
    "1/√(2π)": 1 / np.sqrt(2*np.pi),
    "2/e³": 2 / (np.e**3),
    "log(2)²/3": (np.log(2)**2) / 3,
    "1/(2e)": 1 / (2*np.e),
    "√(log(2))": np.sqrt(np.log(2)),
}

print("="*70)
print("QUICK CHECK: Is R̄ related to a known constant?")
print("="*70)
print()
print("Measured values:")
print(f"  E1D:           R̄ = {R_measured_E1D:.6f}")
print(f"  T6-A1 (avg):   R̄ = {R_measured_T6A1_avg:.6f}")
print(f"  T6-A1 (M=64):  R̄ = {R_measured_T6A1_M64:.6f}")
print()
print("-"*70)
print(f"{'Candidate':<20} {'Value':>12} {'Error (E1D)':>15} {'% Diff':>10}")
print("-"*70)

best_match = None
best_error = float('inf')

for name, value in sorted(candidates.items(), key=lambda x: abs(x[1] - R_measured_E1D)):
    error = R_measured_E1D - value
    pct_diff = 100 * error / R_measured_E1D

    if abs(error) < best_error:
        best_error = abs(error)
        best_match = (name, value)

    marker = "★" if abs(error) < 0.005 else " "
    print(f"{marker} {name:<18} {value:>12.6f} {error:>+15.6f} {pct_diff:>+9.2f}%")

print("-"*70)
print()

if best_match:
    name, value = best_match
    print(f"🎯 BEST MATCH: {name}")
    print(f"   Value:      {value:.6f}")
    print(f"   E1D:        {R_measured_E1D:.6f}")
    print(f"   Difference: {abs(value - R_measured_E1D):.6f} ({100*abs(value - R_measured_E1D)/R_measured_E1D:.2f}%)")
    print()

    if abs(value - R_measured_E1D) < 0.005:
        print("✅ STRONG MATCH! Deviation < 0.5%")
        print()
        print(f"HYPOTHESIS: R̄_∞ = {name} = {value:.6f}")
        print()
        print("Next steps:")
        print(f"  1. Confirm with higher-precision measurements")
        print(f"  2. Explain WHY R̄ = {name} from modular arithmetic")
        print(f"  3. Derive from character theory / exponential sums")
    elif abs(value - R_measured_E1D) < 0.01:
        print("✓ Good match (within 1%)")
        print("  → Worth investigating further")
    else:
        print("⚠️  No exact match found")
        print("  → R̄ = 0.137 may not be a simple constant")
        print("  → Could be parameter-dependent or more complex expression")

print()
print("="*70)
print("VON MISES CONCENTRATION PARAMETER")
print("="*70)
print()
print("If phases follow von Mises distribution:")
print("  R̄ = I₁(κ) / I₀(κ)")
print()

# Solve for κ
def bessel_ratio(kappa):
    return i1(kappa) / i0(kappa)

# Find κ that gives R̄ = 0.137
from scipy.optimize import fsolve

kappa_E1D = fsolve(lambda k: bessel_ratio(k) - R_measured_E1D, 0.5)[0]
kappa_T6A1 = fsolve(lambda k: bessel_ratio(k) - R_measured_T6A1_avg, 0.5)[0]

print(f"For R̄ = {R_measured_E1D:.6f} (E1D):    κ = {kappa_E1D:.6f}")
print(f"For R̄ = {R_measured_T6A1_avg:.6f} (T6-A1): κ = {kappa_T6A1:.6f}")
print()

# Check if κ is a special value
kappa_candidates = {
    "1/4": 0.25,
    "2/7": 2/7,
    "1/e": 1/np.e,
    "log(2)": np.log(2),
    "1/3": 1/3,
    "√2/5": np.sqrt(2)/5,
}

print("Is κ a known constant?")
print("-"*50)
for name, val in sorted(kappa_candidates.items(), key=lambda x: abs(x[1] - kappa_E1D)):
    error = kappa_E1D - val
    pct = 100 * abs(error) / kappa_E1D
    marker = "★" if abs(error) < 0.005 else " "
    print(f"{marker} {name:<15} κ = {val:.6f}  (error: {error:+.6f}, {pct:.1f}%)")

print()
print("="*70)
print("CONCLUSION")
print("="*70)
print()

if 'exp(-2)' in candidates and abs(candidates['exp(-2)'] - R_measured_E1D) < 0.005:
    print("🎉 EUREKA! R̄ ≈ exp(-2) = 1/e²")
    print()
    print("This suggests a FUNDAMENTAL connection to exponential decay!")
    print()
    print("Physical interpretations:")
    print("  1. Two-step decorrelation process")
    print("  2. Coupling constant in phase dynamics")
    print("  3. Related to partition function / free energy")
    print()
    print("Theoretical directions:")
    print("  → Random walk with two characteristic lengths")
    print("  → Stationary distribution of some Markov process")
    print("  → Renormalization group fixed point")
else:
    print("No simple constant match found.")
    print("R̄ = 0.137 is likely:")
    print("  1. Parameter-dependent: R̄(N, ρ, M)")
    print("  2. A more complex expression involving multiple terms")
    print("  3. An asymptotic value of some series or integral")
    print()
    print("Recommended next steps:")
    print("  → Parameter sweep to check N, ρ dependence")
    print("  → Literature review on character correlations")
    print("  → Direct theoretical calculation of phase statistics")

print()
