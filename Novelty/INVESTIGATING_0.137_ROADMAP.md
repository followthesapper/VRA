# Roadmap to Explain R̄ ≈ 0.137: From Observation to Theory

**Date**: October 31, 2025
**Goal**: Uncover the mathematical origin of the observed phase coherence value
**Current Status**: Empirically confirmed, theoretically unexplained

---

## Overview: The Mystery

**What we know**:
- R̄ = 0.137 is reproducibly measured in VRA experiments
- It represents phase coherence of different bases: a¹, a², a³, ... at harmonic bins
- It causes 27% √M scaling efficiency
- It converges from higher values as M increases

**What we don't know**:
- WHY 0.137 specifically?
- Does it depend on N, ρ, or other parameters?
- What mathematical structure determines this value?
- Is there a closed-form expression?

---

## Strategy Roadmap

### Phase 1: Empirical Characterization (2-4 weeks)
**Goal**: Fully characterize the phenomenon before theorizing

### Phase 2: Pattern Recognition (1-2 weeks)
**Goal**: Look for known mathematical objects/distributions

### Phase 3: Theoretical Investigation (4-8 weeks)
**Goal**: Derive from first principles or connect to existing theory

### Phase 4: Validation & Generalization (2-3 weeks)
**Goal**: Test predictions, write rigorous proofs

---

## PHASE 1: Empirical Characterization

### 1.1: Parameter Sweep Study 📊 **HIGH PRIORITY**

**Question**: Is 0.137 universal or parameter-dependent?

**Experiment Design**:
```python
# Systematic sweep
N_values = [101, 251, 503, 1009, 2003, 5003, 10007]  # Primes
rho_bins = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]  # r/N ratios
M_values = [16, 32, 64, 128, 256]  # Number of bases
harmonic_bins = [1, 2, 3, 4, 5, ...]  # ℓ in k = ℓ·L/r

# For each configuration:
for N in N_values:
    for target_rho in rho_bins:
        # Find r ≈ target_rho * N with ord_N(a) = r
        for M in M_values:
            for ell in harmonic_bins:
                R_ell = measure_coherence_at_harmonic(N, r, M, ell)
                save_result(N, rho, M, ell, R_ell)
```

**Analysis**:
1. Plot R̄ vs ρ (regime dependence)
2. Plot R̄ vs N (modulus size dependence)
3. Plot R̄ vs ℓ (harmonic index dependence)
4. Check R̄(M) → R̄_∞ convergence rate

**Expected Outcomes**:
- If R̄ is constant → universal mathematical constant
- If R̄ = f(ρ) → regime-dependent phenomenon
- If R̄ = f(N) → finite-size effect with N
- If R̄ = f(ℓ) → harmonic-specific structure

**Time**: ~3-4 days (GPU-accelerated)

---

### 1.2: Phase Distribution Analysis 📈 **HIGH PRIORITY**

**Question**: What probability distribution do phases follow?

**Method**:
```python
# At each harmonic bin k = ℓ·L/r, extract phases from M bases
phases = np.angle(U_m[k])  # m = 1, 2, ..., M

# Test against standard circular distributions:
# 1. Von Mises: p(θ) ∝ exp(κ·cos(θ - μ))
# 2. Wrapped Cauchy: p(θ) ∝ 1 / (1 + ρ² - 2ρ·cos(θ - μ))
# 3. Wrapped Normal
# 4. Uniform

from scipy.stats import vonmises, circmean, circstd

# Fit von Mises
kappa_fit, mu_fit = fit_vonmises(phases)
R_predicted = scipy.special.i1(kappa_fit) / scipy.special.i0(kappa_fit)

# Compare to measured R̄
print(f"Measured R̄: {R_measured:.4f}")
print(f"Von Mises prediction (κ={kappa_fit:.4f}): {R_predicted:.4f}")

# Goodness-of-fit tests
ks_stat, p_value = kuiper_test(phases, vonmises(kappa_fit, mu_fit))
```

**If von Mises fits**:
- κ ≈ 0.278 would give R̄ = I₁(0.278)/I₀(0.278) ≈ 0.137
- Then the question becomes: **Why κ = 0.278?**

**If it doesn't fit**:
- Try other distributions
- Look at empirical CDF vs theoretical
- Check for multi-modal structure

**Time**: ~2 days

---

### 1.3: Convergence Rate Study 📉 **MEDIUM PRIORITY**

**Question**: How does R̄(M) → R̄_∞?

**Method**:
```python
# Fixed N, r, test many M values
M_values = [4, 8, 16, 32, 64, 128, 256, 512, 1024]

R_vs_M = []
for M in M_values:
    R = measure_coherence(N, r, M)
    R_vs_M.append(R)

# Fit convergence models:
# Model 1: R̄(M) = R̄_∞ + c/M
# Model 2: R̄(M) = R̄_∞ + c/M^α  (power law)
# Model 3: R̄(M) = R̄_∞ + c·exp(-M/M₀)  (exponential)

from scipy.optimize import curve_fit

# Model 1: Linear in 1/M
def model1(M, R_inf, c):
    return R_inf + c/M

params1, _ = curve_fit(model1, M_values, R_vs_M)
R_inf_est = params1[0]

print(f"Asymptotic R̄_∞ = {R_inf_est:.4f}")
print(f"Expected: 0.137")
```

**If linear convergence**: R̄(M) - R̄_∞ ∼ 1/M → Central Limit Theorem behavior
**If power law**: α ≠ 1 suggests more complex dependence
**If exponential**: Might indicate correlation length in base sequence

**Time**: ~1 day

---

### 1.4: Harmonic-by-Harmonic Analysis 🎵 **MEDIUM PRIORITY**

**Question**: Does R̄ vary across harmonics?

**Method**:
```python
# For a single (N, r, M) configuration
# Measure R̄_ℓ at each harmonic ℓ = 1, 2, ..., r-1

R_by_harmonic = []
for ell in range(1, r):
    k = ell * L // r  # Harmonic bin
    phases = [np.angle(U_m[k]) for m in range(M)]
    R_ell = np.abs(np.mean(np.exp(1j * np.array(phases))))
    R_by_harmonic.append(R_ell)

# Check for pattern
plt.plot(range(1, r), R_by_harmonic, 'o-')
plt.axhline(0.137, color='red', label='Overall mean')
plt.xlabel('Harmonic index ℓ')
plt.ylabel('R̄_ℓ')

# Statistics
print(f"Mean R̄: {np.mean(R_by_harmonic):.4f}")
print(f"Std R̄:  {np.std(R_by_harmonic):.4f}")
print(f"Min/Max: {np.min(R_by_harmonic):.4f} / {np.max(R_by_harmonic):.4f}")
```

**Possible outcomes**:
- **Uniform R̄_ℓ ≈ 0.137**: Suggests universal phase incoherence
- **R̄_ℓ increases with ℓ**: Low harmonics more coherent
- **R̄_ℓ varies randomly**: Each harmonic is independent sample

**Time**: ~1 day

---

## PHASE 2: Pattern Recognition

### 2.1: Known Constants Search 🔍

**Question**: Is 0.137 related to a known mathematical constant?

**Candidates to check**:

1. **Fine structure constant**: α ≈ 1/137.036
   ```
   Check if R̄ ≈ 1/137 = 0.00730 NO
   Check if R̄ ≈ √(1/137) = 0.0854 NO
   Check if R̄ ≈ 1/√(137/2π) = 0.213 CLOSE?
   ```

2. **Bessel function zeros**: I₁(κ)/I₀(κ) = 0.137 → κ ≈ 0.278
   ```python
   from scipy.special import i0, i1
   from scipy.optimize import fsolve

   def bessel_ratio(kappa):
       return i1(kappa) / i0(kappa) - 0.137

   kappa_solution = fsolve(bessel_ratio, 0.5)[0]
   print(f"κ = {kappa_solution:.6f}")  # Should get ≈ 0.278

   # Is 0.278 a special number?
   # 0.278 ≈ 2/7.19 ≈ 1/3.6 ≈ log(1.32)
   ```

3. **Exponential/logarithmic forms**:
   ```
   exp(-2) = 0.135  ✓ Very close!
   1/e² = 0.135    ✓ Same
   log(8)/log(e^4) = 0.130 Close
   (1/√2π) = 0.399 NO
   ```

4. **Combinatorial/number-theoretic**:
   ```
   1/φ³ = 0.236 (golden ratio) NO
   ζ(2) - 1 = 0.645 NO
   1/e - 1/e² = 0.233 NO
   ```

**Most promising**: **R̄ ≈ 1/e² = exp(-2) ≈ 0.1353**

**If confirmed**: Need to explain why modular phase coherence ~ exp(-2)

**Time**: ~2-3 hours

---

### 2.2: Random Walk on Groups 🚶 **HIGH PRIORITY**

**Question**: Is this a known phenomenon in harmonic analysis on finite groups?

**Literature to check**:

1. **Character Theory on Cyclic Groups**:
   - Diaconis & Shahshahani (1981): "Generating random permutations"
   - Shows convergence rates for random walks on groups
   - Might predict phase mixing rates

2. **Weyl Equidistribution**:
   - For sequence {a^n mod N}, phases θ_n = 2π(a^n mod N)/N
   - Weyl criterion for uniform distribution
   - Erdős-Turán inequality for discrepancy

3. **Exponential Sums**:
   - Gauss sums: Σ exp(2πi·n²/N)
   - Kloosterman sums: Σ exp(2πi·(an + bn⁻¹)/p)
   - These have known bounds related to √N

**Relevant formula from Diaconis**:
```
For random walk on group G with m steps:
Distance to uniformity ~ exp(-m·λ₂)

where λ₂ is second-largest eigenvalue of transition matrix
```

**Hypothesis**: R̄ might be related to mixing time of multiplicative group

**Action**:
```python
# Compute mixing matrix for Z*_N
# Transition: state a → a·g for random generator g
# Measure spectral gap λ₁ - λ₂
# Check if R̄ ∼ exp(-gap) or similar
```

**Time**: ~3-5 days (literature review + implementation)

---

### 2.3: Numerical Search for Formula 🧮 **LOW PRIORITY**

**Question**: Can symbolic regression find a formula?

**Method**: Use genetic programming to search for expressions

```python
import gplearn.genetic as gp

# Training data: (N, r, M) → R̄
X_train = np.array([[N, r, M] for ...])
y_train = np.array([R_bar_measured])

# Function set
function_set = ['add', 'sub', 'mul', 'div', 'sqrt', 'log', 'exp', 'sin', 'cos']

# Fit symbolic regressor
est_gp = gp.SymbolicRegressor(
    population_size=5000,
    generations=20,
    function_set=function_set,
    metric='mean absolute error',
    parsimony_coefficient=0.01,
    random_state=0
)

est_gp.fit(X_train, y_train)
print(est_gp._program)  # Best formula found
```

**Caution**: Results are suggestive, not rigorous proof

**Time**: ~2 days

---

## PHASE 3: Theoretical Investigation

### 3.1: Direct Phase Correlation Analysis 🔬 **HIGHEST PRIORITY**

**Question**: What is the explicit expression for phase correlations?

**Theoretical Setup**:
```
Bases: a^m for m = 1, 2, ..., M
Sequences: x_m[n] = a^(m·n) mod N  for n = 0, 1, ..., L-1
Phases: θ_m[n] = 2π · x_m[n] / N

At harmonic k = ℓ·L/r:
U_m[k] = Σ_n exp(i·θ_m[n]) · exp(-2πi·k·n/L)

Phase of U_m[k]: φ_m = arg(U_m[k])

Coherence: R̄ = |⟨exp(i·φ_m)⟩_m|
```

**Key insight**: φ_m depends on how {a^(m·n) mod N} aligns with harmonic frequency

**Approach**:
1. Write φ_m explicitly in terms of m, N, r, ℓ
2. Compute autocorrelation: ⟨exp(i·φ_m)·exp(-i·φ_{m'})⟩
3. Look for simplifications using:
   - Gauss sum identities
   - Character orthogonality
   - Modular arithmetic properties

**Mathematical tools**:
- Poisson summation formula
- Stationary phase approximation
- Weyl sum estimates

**Expected form**:
```
φ_m ≈ 2π·f(m, N, r, ℓ) + random part

where f might be something like:
f(m) = m²/N  or  m·log(a)/r  or similar
```

**If successful**: Compute R̄ = |⟨exp(2πi·f(m))⟩| analytically

**Time**: ~1-2 weeks (hard theoretical work)

---

### 3.2: Connection to Exponential Sums 📐 **HIGH PRIORITY**

**Question**: Are Gauss/Kloosterman sums involved?

**Gauss sums** (for phases in quadratic residues):
```
G(a, N) = Σ_{n=0}^{N-1} exp(2πi·a·n²/N)

Known result: |G(a, p)| = √p for prime p
```

**For VRA**: Not quadratic, but multiplicative
```
S_m = Σ_{n=0}^{r-1} exp(2πi·a^(m·n)/N)

This is a character sum over cyclic subgroup
```

**Literature**:
- Vinogradov bounds for exponential sums
- Burgess bounds for character sums
- Hooley-Heath-Brown work on multiplicative structure

**Typical bounds**:
```
|S_m| ≤ C·√N·log(N)

If M sums are averaged with random phases:
⟨|S_m|²⟩ ~ N
⟨S_m·S*_{m'}⟩ ~ N·δ_{mm'} + N·R̄ (if m ≠ m')

This gives: R̄ ~ 1/√M in worst case
```

**Check if**: R̄ = 0.137 matches predictions from sum bounds

**Time**: ~1 week (requires number theory background)

---

### 3.3: Statistical Mechanics Analogy 🌡️ **MEDIUM PRIORITY**

**Question**: Is this similar to any known statistical physics model?

**Analogy**:
```
VRA averaging ~ Partition function of spin system

M bases ~ M spins
Phase φ_m ~ Spin angle
Coherence R̄ ~ Order parameter

Energy: E = -Σ_m cos(φ_m - φ_mean)
```

**In stat mech**:
- R̄ = 0 → High temperature (disordered)
- R̄ = 1 → Low temperature (ordered)
- R̄ = 0.137 → Intermediate temperature?

**Check for**:
- Phase transitions (does R̄ jump discontinuously with ρ?)
- Critical exponents (how does R̄ scale near transitions?)
- Universality classes

**Known models**:
- XY model (classical spins on circle)
- Kuramoto model (coupled oscillators)
- Kosterlitz-Thouless transition

**If connection exists**: Use renormalization group / mean field theory

**Time**: ~1-2 weeks

---

### 3.4: Spectral Graph Theory 📊 **MEDIUM PRIORITY**

**Question**: Cayley graph spectrum related to R̄?

**Setup**:
```
Define Cayley graph of Z*_N:
- Vertices: elements of Z*_N
- Edges: a ~ a·g for generators g

Adjacency matrix A:
- A[a, b] = 1 if b = a·g for some g
- A[a, b] = 0 otherwise

Eigenvalues: λ₀ ≥ λ₁ ≥ ... ≥ λ_{φ(N)-1}
```

**Mixing time** related to spectral gap: Δ = λ₀ - λ₁

**Hypothesis**:
```
R̄ ~ exp(-M·Δ) or R̄ ~ λ₁/λ₀ or similar
```

**Check**:
```python
import networkx as nx

# Build Cayley graph
G = build_cayley_graph_ZNstar(N)

# Compute spectrum
eigenvalues = nx.adjacency_spectrum(G)
gap = eigenvalues[0] - eigenvalues[1]

# Compare to measured R̄
print(f"Spectral gap: {gap:.4f}")
print(f"Measured R̄: {R_measured:.4f}")
print(f"exp(-gap): {np.exp(-gap):.4f}")
```

**Time**: ~3-4 days

---

## PHASE 4: Validation & Generalization

### 4.1: Prediction Testing ✅

Once a theoretical model is developed:

```python
# If theory predicts R̄ = f(N, r, M, ...)
def theoretical_R_bar(N, r, M):
    # Your derived formula
    return result

# Test on unseen data
N_test = [1013, 2017, 5011]
r_test = [find_order(...)]
M_test = [64, 128]

for N, r, M in itertools.product(N_test, r_test, M_test):
    R_predicted = theoretical_R_bar(N, r, M)
    R_measured = measure_coherence(N, r, M)

    error = abs(R_predicted - R_measured)
    print(f"N={N}, r={r}, M={M}: pred={R_predicted:.4f}, meas={R_measured:.4f}, err={error:.4f}")
```

**Success criteria**:
- Mean absolute error < 0.01
- No systematic bias
- Holds across wide parameter range

---

### 4.2: Asymptotic Analysis 📈

For large-N behavior:

```
As N → ∞, does R̄ → 0.137?
Or does R̄ → 0?
Or does R̄ → f(ρ)?

Compute for N = 10^4, 10^5, 10^6 (may need optimized code)
```

---

### 4.3: Generalization to Other Groups 🔄

Test if the phenomenon extends:

**Elliptic curves**:
- Does ECC also show R̄ ≈ 0.137?
- Same value or different?

**Higher-rank groups**:
- GL(2, F_p), SL(2, F_p)
- Do they have similar coherence limits?

---

## Concrete Next Steps (Prioritized)

### Week 1-2: Quick Wins
1. ✅ **Check if R̄ ≈ exp(-2)**
   - Compare 0.137 vs 0.1353
   - If within 2%, strong evidence

2. ✅ **Parameter sweep** (1.1)
   - Run on GPU for N ∈ [101, 1009], M ∈ [16, 256]
   - Check if R̄ is constant or varies

3. ✅ **Phase distribution** (1.2)
   - Fit von Mises, extract κ
   - If κ ≈ 2 or other special value, investigate

### Week 3-4: Deeper Analysis
4. **Harmonic analysis** (1.4)
   - Check if R̄_ℓ varies with harmonic index

5. **Convergence study** (1.3)
   - Fit R̄(M) = R̄_∞ + c/M

6. **Literature review** (2.2)
   - Diaconis mixing times
   - Exponential sum bounds

### Week 5-8: Theoretical Work
7. **Direct calculation** (3.1)
   - Write φ_m explicitly
   - Compute autocorrelation

8. **Exponential sums** (3.2)
   - Connect to character sum theory
   - Apply known bounds

9. **Model refinement** (T6-A1 v2)
   - Add finite-M corrections
   - Test predictions

---

## Tools & Resources

### Code Implementation
```python
# Core analysis script
import numpy as np
from scipy.special import i0, i1
from scipy.optimize import fsolve
import matplotlib.pyplot as plt

def measure_coherence_vectorized(N, r, M, L=4096):
    """
    Efficient coherence measurement
    """
    # Find M bases with order r
    bases = find_bases_with_order(N, r, M)

    # Generate sequences
    seqs = generate_modular_sequences(N, bases, L)

    # Phase embedding
    phases = 2*np.pi * seqs / N
    u = np.exp(1j * phases)

    # FFT
    U = np.fft.fft(u, axis=1)

    # Find harmonic bins
    k_harmonics = [ell * L // r for ell in range(1, r)]

    # Coherence at each harmonic
    R_harmonics = []
    for k in k_harmonics:
        phasors = U[:, k] / np.abs(U[:, k])  # Normalize to unit circle
        R = np.abs(np.mean(phasors))
        R_harmonics.append(R)

    return np.mean(R_harmonics)
```

### Literature
- Diaconis & Shahshahani (1981): "Generating a random permutation with random transpositions"
- Terras (1999): "Fourier Analysis on Finite Groups and Applications"
- Montgomery & Vaughan (2007): "Multiplicative Number Theory I"
- Iwaniec & Kowalski (2004): "Analytic Number Theory"

### Mathematical Software
- SageMath: For exact group theory computations
- Mathematica: For symbolic manipulation of Bessel functions
- mpmath: For arbitrary precision (check if 0.137 has exact form)

---

## Success Metrics

**Tier 1** (Basic understanding):
- ✅ Confirm R̄ ≈ exp(-2) within 1%
- ✅ Measure parameter dependence (N, ρ, M)
- ✅ Identify phase distribution (von Mises or other)

**Tier 2** (Mathematical insight):
- ✅ Derive finite-M correction: R̄(M) = R̄_∞ + c/M^α
- ✅ Connect to known exponential sum bounds
- ✅ Explain convergence rate

**Tier 3** (Complete theory):
- ✅ Closed-form expression for R̄_∞
- ✅ Proof of convergence
- ✅ Generalization to other groups
- ✅ Publication in mathematical journal

---

## Expected Timeline

**Optimistic** (with focused effort):
- 2-3 months to basic understanding
- 6-12 months to rigorous theory
- 12-18 months to publication

**Realistic** (part-time work):
- 3-6 months to empirical characterization
- 12-18 months to theoretical framework
- 18-24 months to peer review

---

## Conclusion

The most promising approaches are:

1. **Check R̄ ≈ exp(-2)** ← Do this FIRST (1 hour)
2. **Parameter sweep** ← Characterize dependence (3 days)
3. **Random walk / mixing time connection** ← Literature exists (1 week)
4. **Direct phase correlation** ← Hard but fundamental (2 weeks)
5. **Exponential sum bounds** ← Number theory (2 weeks)

Start with empirical characterization (Phase 1), which will guide theoretical work (Phase 3).

The answer likely lies in **harmonic analysis on finite groups** or **character theory**, where similar phenomena are well-studied.
