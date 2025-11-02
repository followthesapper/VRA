# T6-C1 Failure Analysis: Why the Experiment Failed

**Date**: October 31, 2025
**Experiment**: T6-C1 - VQE Term Grouping via VRA Coherence
**Result**: ❌ FAIL (legitimate scientific failure, not a code bug)
**Status**: **EXPERIMENT DESIGN FLAW IDENTIFIED**

---

## TL;DR

**The experiment has a fundamental flaw**: It tests whether grouping correlated terms reduces variance, but **grouping positively correlated observables INCREASES variance, not decreases it**. This is basic statistics, not a VRA limitation.

**Verdict**: ✅ **Code is correct**, ❌ **hypothesis is wrong**

---

## The Results (Counterintuitive!)

| Grouping Method | Variance Reduction | Interpretation |
|----------------|-------------------|----------------|
| **Random** | 1.04 ± 0.12 | Slightly worse (4% increase) |
| **VRA (high coherence)** | 1.56 ± 0.11 | **56% INCREASE** in variance! |
| **Optimal (true correlations)** | 1.61 ± 0.10 | **61% INCREASE** in variance! |

**Key observation**: The "optimal" grouping (using perfect knowledge of correlations) performs **WORSE** than random!

---

## Why This Happens: Basic Statistics

### Variance of Correlated Variables

When measuring independent observables X₁, X₂, ..., Xₙ:
```
Var(X₁ + X₂ + ... + Xₙ) = Var(X₁) + Var(X₂) + ... + Var(Xₙ)
```
(No correlation terms)

When measuring **grouped** (correlated) observables:
```
Var(X₁ + X₂ + ... + Xₙ) = Σᵢ Var(Xᵢ) + 2·Σᵢ<ⱼ Cov(Xᵢ, Xⱼ)
```

**If correlations are positive**: Cov(Xᵢ, Xⱼ) > 0
**Then**: Grouped variance > Independent variance

### What the Code Does

**Line 234** (naive/independent):
```python
var_naive = np.trace(Sigma) + n_terms * sigma_meas**2 / n_shots
```
- Sums only diagonal elements (individual variances)
- Correct for independent measurements

**Line 246** (grouped):
```python
group_cov = Sigma[np.ix_(group, group)]
group_var = np.sum(group_cov)  # ← Includes ALL correlations!
```
- Sums entire sub-covariance matrix
- **Includes positive off-diagonal correlation terms**
- Results in HIGHER variance!

### Numerical Example

Suppose 2 terms with:
- Var(X₁) = Var(X₂) = 1.0
- Cov(X₁, X₂) = 0.3 (positive correlation)

**Independent measurement**:
```
Var(X₁) + Var(X₂) = 1.0 + 1.0 = 2.0
```

**Grouped measurement**:
```
Var(X₁ + X₂) = Var(X₁) + Var(X₂) + 2·Cov(X₁, X₂)
             = 1.0 + 1.0 + 2·(0.3)
             = 2.6  ← 30% HIGHER!
```

**This is why "optimal" grouping makes things worse!**

---

## The Fundamental Misunderstanding

### What the Experiment Assumed

**Hypothesis** (from code line 8-11):
> "If terms share high VRA cross-coherence, grouping them reduces estimator variance"

**Expected**: High coherence → Low variance

**Reality**: High coherence → **HIGH variance** (when correlations are positive)

### What VQE Term Grouping Actually Does

In real VQE, grouping is about **commutativity**, not correlation:

1. **Pauli operators** can be grouped if they **commute**:
   - [X₁, Z₂] ≠ 0 → Cannot measure together
   - [Z₁, Z₂] = 0 → Can measure together

2. **Grouping saves shots** by:
   - Measuring multiple terms in one circuit
   - Reducing total circuit count
   - NOT by reducing variance of correlated measurements

3. **VRA coherence ≠ commutativity**:
   - VRA measures correlation in phase space
   - Has no information about Pauli operator structure
   - Can't determine which operators commute

---

## Why the Results Make Sense

### Random Grouping (~4% worse)
- Randomly mixes uncorrelated and correlated terms
- Slightly worse than independent due to some positive correlations
- **This is expected behavior**

### VRA Grouping (~56% worse)
- **Actively groups highly correlated terms together**
- Maximizes correlation within groups
- **This MAXIMIZES variance!**
- Opposite of what we want

### Optimal Grouping (~61% worse)
- Uses perfect knowledge of true correlations
- Groups most correlated terms together
- **Even worse than VRA!**
- Proves the strategy itself is backwards

---

## Is This a Bug or Real Science?

### ✅ The Code is Correct

Checked the implementation:
1. ✅ Covariance matrix generation is valid
2. ✅ Variance calculation is mathematically correct
3. ✅ Grouping algorithms work as intended
4. ✅ Statistics are properly computed

**No code bugs found.**

### ❌ The Hypothesis is Wrong

The experiment tests:
> "High coherence → Low variance"

**Reality**:
> "High coherence → High variance" (for positively correlated observables)

**This is not a VRA failure** - it's basic statistics!

---

## What This Experiment Actually Proved

### Scientific Value: High! 🎓

This is a **valuable negative result** that proves:

1. **VRA coherence does NOT help VQE term grouping**
   - Because it measures correlation, not commutativity

2. **Grouping correlated terms INCREASES variance**
   - Basic statistical fact, now experimentally confirmed

3. **VQE grouping requires operator structure knowledge**
   - Need to know Pauli operators, not just correlations
   - VRA can't replace commutation checks

### Honest Science ✅

- Experiment ran correctly
- Results are valid
- Hypothesis was falsified
- **This is what good science looks like!**

---

## Why Did We Think This Would Work?

### The Original Intuition

From `TIER6_SUMMARY.md:124-126`:
> "If VRA group Hamiltonian terms to minimize variance..."
> "Var_group / Var_naive ≤ 1 - λ_max(Σ_VRA)"

**The error**: Assumed that terms with high coherence should be grouped.

**Reality**: Terms with high coherence should be **separated** to minimize variance!

### The Correct Strategy

For variance reduction:
1. **Group ANTI-correlated terms** (negative covariance)
2. Positive + Negative correlations cancel
3. Results in lower net variance

But this requires:
- Negative correlations to exist
- Ability to identify them
- Still doesn't help VQE (need commutativity, not correlations)

---

## Implications for VRA

### What VRA CAN'T Do ❌

1. **Replace commutativity checks in VQE**
   - VRA measures correlation in modular arithmetic
   - Doesn't know about Pauli operator structure

2. **Reduce variance by grouping positively correlated observables**
   - Basic statistics prevents this
   - Not a VRA limitation, universal constraint

### What VRA CAN Do ✅

From successful experiments:
- E11: Feature extraction (36-47 dB SNR)
- E12: ML classification (80-85% accuracy)
- E14: Phase alignment validation
- T6-A1: Discovered R̄ ≈ exp(-2)

VRA excels at **signal processing and order detection**, not VQE term grouping.

---

## Recommendations

### For T6-C1

**Status**: ❌ **FAIL - Close Experiment**

**Reasoning**:
- Hypothesis is fundamentally flawed
- Results are correct but uninteresting
- Not a VRA limitation to fix

**Action**: Mark as "Hypothesis falsified, experiment closed"

### For VQE Applications

If you want VRA to help VQE:

1. **Test different hypothesis**:
   - Use VRA for **initial state preparation**
   - Use VRA for **convergence detection**
   - Use VRA for **circuit optimization**

2. **Don't use VRA for**:
   - Term grouping (needs operator structure)
   - Commutativity checks (different domain)

### For Future Experiments

**Lessons learned**:
1. ✅ Sanity check: Run "optimal" strategy first
2. ✅ If optimal fails, hypothesis might be wrong
3. ✅ Check basic statistics before complex theory
4. ✅ Negative results are valuable science

---

## Final Verdict

### Code Quality: ✅ CORRECT
- Well-written, clear, documented
- Math is sound
- Implementation is bug-free

### Experiment Design: ❌ FLAWED
- Tests wrong hypothesis
- Grouping correlated terms increases variance
- VRA can't determine commutativity

### Scientific Value: ✅ HIGH
- **Honest negative result**
- Proves VRA limitations clearly
- Prevents future wasted effort

### Recommendation: 📝 **Document and Move On**
- Add to "What VRA Can't Do" section
- Cite as example of proper falsification
- Focus on E11/E12 success cases

---

## Summary for Publication

**T6-C1 Result**:
> "We tested whether VRA coherence could guide VQE term grouping to reduce measurement variance. The experiment revealed that grouping positively correlated terms **increases** variance (56% increase), confirming basic statistical theory. This negative result establishes that VRA coherence, while valuable for signal processing tasks, does not substitute for operator commutativity analysis required in VQE term grouping."

**Status**: Hypothesis falsified ✅
**Conclusion**: Valid negative result, close experiment
**Impact**: Clarifies VRA's scope and prevents misapplication
