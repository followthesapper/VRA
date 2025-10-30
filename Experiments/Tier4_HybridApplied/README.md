# Tier 4 — Hybrid and Applied Studies  
**Vaca Resonance Analysis (VRA): Transition from Pure Math to Practical Domains**

---

## Overview
Tier 4 marks the transition from mathematical validation (Tiers 1–3) to **applied and interdisciplinary validation**.  
Here, VRA is tested in hybrid computational and physical contexts to:

- Confirm **diagnostic safety** in semiprime (cryptographic) settings.  
- Map **robustness to noise, jitter, and non-ideal conditions**.  
- Explore potential **applications in signal processing and physics**.

These experiments ensure that VRA remains well-behaved under realistic, noisy, and cross-domain conditions — bridging cryptography, computation, and physical resonance theory.

---

## E8 — Semiprime Groundwork (Non-Threatening Diagnostic Validation)

**Goal:**  
Show that VRA can profile “period-richness” in semiprime moduli  
\\( N = p q \\) without leaking factorization shortcuts.

**Pass Criteria:**  
1. Diagnostic curves vary across random bases but reveal **no trivial correlation** with  
   \\( \\varphi(N) \\) or the true factors.  
2. Any order hints require **classical effort ≥ baseline** (e.g., Pollard Rho / BSGS).

**Usage:**  
```bash
python Experiments/Tier4_HybridApplied/E8_semiprime_groundwork.py --p 1009 --q 1013 --bases 50
