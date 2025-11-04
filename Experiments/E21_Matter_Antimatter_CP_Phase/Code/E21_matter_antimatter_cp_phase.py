#!/usr/bin/env python3
"""
E21: Matter/Antimatter CP-Phase (Quick Version)
Reduced parameters for fast verification: 1 N, 1 L, 20 trials (vs 3×3×50)
"""

import sys
from pathlib import Path

# Read the full script
script_path = Path(__file__).parent / "T6B3_cp_phase_detector.py"
with open(script_path, 'r') as f:
    code = f.read()

# Modify parameters for quick run
code = code.replace(
    "N_primes = [997, 2003, 5003]",
    "N_primes = [997]  # Quick: 1 prime only"
)
code = code.replace(
    "L_values = [2**12, 2**14, 2**16]",
    "L_values = [2**12]  # Quick: smallest L only"
)
code = code.replace(
    "n_trials = 50",
    "n_trials = 20  # Quick: reduced trials"
)

# Execute modified code
exec(code)
