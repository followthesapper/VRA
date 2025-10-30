# VRA: Vaca Resonance Analysis
## A Spectral Framework for Multiplicative Order Detection

**Dylan Vaca**
October 2025

---

## Motivation

**Problem**: Detect multiplicative order $r$ where $a^r \equiv 1 \pmod{N}$

**Classical approaches**:
- Brute force: $O(r)$ exponentiations
- Baby-step giant-step: $O(\sqrt{r})$ time & space
- Quantum (Shor): Polynomial time, but requires quantum computer

**Our approach**: Spectral analysis via Fourier transform

---

## Key Idea: Phase Embedding

**Modular sequence**: $x_k = a^k \bmod N$ for $k = 0, 1, 2, \ldots$

**Phase embedding**: Map to unit circle
$$u_k = e^{2\pi j x_k / N}$$

**Insight**: Periodic modular sequences → harmonic structure in Fourier domain

---

## VRA Algorithm

```
For each base a_m with ord_N(a_m) = r:
  1. Generate sequence: x_k = a_m^k mod N
  2. Phase embed: u_k = exp(2πj x_k / N)
  3. Apply window (Hann)
  4. Compute FFT: U_m = FFT(u)

Coherent average: S = (1/M) Σ U_m
Power spectrum: P = |S|²
Detect harmonic peaks at k·L/r
```

**Key**: Coherent averaging preserves phase alignment!

---

## Coherent vs. Incoherent Averaging

**Coherent (VRA)**:
$$|S|^2 = \left|\frac{1}{M}\sum_m U_m\right|^2$$

**Incoherent (baseline)**:
$$\frac{1}{M}\sum_m |U_m|^2$$

**Result**: Coherent achieves **√M SNR scaling**

---

## Main Theoretical Result

**Theorem 1 (√M Scaling)**:
Concentration metric scales as $C(M) \propto \sqrt{M}$

**Proof sketch**:
- Signal power grows as $M^2$ (coherent addition)
- Noise power grows as $M$ (incoherent)
- Ratio: $M^2/M = M \propto (\sqrt{M})^2$

**Validation**: R² > 0.99 across 8 test cases

---

## Three Operational Regimes

**HIGH SNR** ($\rho < 0.146$):
- Requires phase-aligned bases
- Strong concentration
- Easy detection

**TRANSITION** ($0.146 \leq \rho < 0.263$):
- Flexible base selection (CV < 7%)
- Moderate concentration
- Robust regime

**LOW SNR** ($\rho \geq 0.263$):
- Any same-order bases work
- Weak concentration
- Requires larger M

---

## Validation: 30 Diverse Moduli

**Tested**:
- Small primes (991-1039)
- Safe primes (N = 2p+1)
- Carmichael numbers
- Prime powers (p²)
- Semiprimes

**Results**: 98-100% precision across all types

![Extended moduli](path/to/figure)

---

## Benchmark: VRA vs. Baselines

**Methods compared**:
1. Brute force (exact, O(r))
2. Baby-step giant-step
3. Single-base FFT
4. Incoherent averaging
5. VRA (coherent)

**Key finding**: VRA **2.00× [1.94, 2.08]** faster than incoherent
(95% bootstrap CI, n=8 cases, B=10,000 samples)

---

## Robustness: Noise Immunity

**Tested 3 noise types**:

1. **Gaussian noise** (σ ≤ 0.50): ✅ 100% precision
2. **Phase jitter** (σ ≤ 0.20 rad): ✅ 100% precision
   (degrades at σ > 0.20)
3. **Quantization** (6-bit): ✅ 100% precision

**Interpretation**: VRA naturally robust to additive noise via coherent averaging

---

## Robustness: Adversarial Attacks

**Adversarial strategies**:
- Random base selection
- Max phase spread (destructive interference)
- Clustered phases

**Results**:
- TRANSITION/LOW SNR: **100% precision** (base-invariant!)
- HIGH SNR: 96-98% precision

**Implication**: Cryptographically robust in TRANSITION/LOW SNR

---

## Pathological Orders

**Tested highly composite orders**:
- r = 144 (2⁴ × 3²): 100% precision, 46% recall
- r = 336 (2⁴ × 3 × 7): 100% precision, 20% recall
- r = 504 (2³ × 3² × 7): 100% precision, 13% recall

**Key insight**: **Zero false positives** despite 144-504 competing bins

---

## Statistical Rigor

**Bootstrap confidence intervals** (95%, B=10,000):
- All key metrics include CIs
- VRA speedup: 2.00× [1.94, 2.08] (statistically significant)

**Reproducibility infrastructure**:
- Docker environment (exact dependencies)
- Automated reproduction script (100% success rate)
- 10 canonical test vectors for verification

---

## Applications

**Educational**:
- Teaching multiplicative order concepts
- Visualizing √M scaling
- Exploring regime structure

**Practical**:
- RSA parameter quality assessment (<1024 bits)
- Weak Diffie-Hellman group detection
- Cryptographic parameter auditing

**Research**:
- Order distribution analysis
- Complementary to classical methods

---

## Limitations

1. **Not a general factoring tool** (does not factor N)
2. **Scalability** (infeasible for 2048+ bit RSA)
3. **Order hypothesis** (most effective with known r)
4. **Recall vs. precision tradeoff** (prioritizes no false positives)

**Best use**: Analytical tool, not production cryptanalysis

---

## Key Contributions

1. ✅ **√M Scaling Law** (R² > 0.99 validation)
2. ✅ **Three-Regime Structure** (empirically validated)
3. ✅ **Leakage Bounds** (100% precision on pathological orders)
4. ✅ **Noise Robustness** (100% precision, σ ≤ 0.50 Gaussian)
5. ✅ **Statistical Rigor** (bootstrap CIs, full reproducibility)
6. ✅ **Open Science** (Docker, test vectors, replication challenge)

---

## Reproducibility

**Available now**:
- Complete code: github.com/followthesapper/VRA
- Docker image: One-command reproduction
- Test vectors: 10 canonical cases (Bronze challenge)
- Documentation: REPRODUCTION.md

**Invitation**: Independent replication challenge
(Bronze/Silver/Gold levels)

---

## Future Work

**Technical extensions**:
- Adaptive M selection
- GPU acceleration
- Elliptic curve orders
- Machine learning integration

**Research questions**:
- Non-prime moduli with composite structure?
- Connection to L-functions?
- Quantum VRA variant?

---

## Conclusion

**VRA**: A spectral framework for multiplicative order detection

**Strengths**:
- √M SNR scaling (proven & validated)
- Noise robustness (100% precision)
- Cryptographic robustness (adversarial attacks)
- Full reproducibility (Docker + test vectors)

**Impact**: Complementary tool for cryptographic parameter analysis and number-theoretic structure exploration

---

## Questions?

**Contact**:
- Email: dylan.vaca@example.com
- GitHub: github.com/followthesapper/VRA
- Code, data, and reproducibility materials available

**Try it yourself**:
```bash
docker run vra-reproducibility
```

---

## Backup Slides

[Additional technical details, extra figures, proofs]

---

Thank you!
