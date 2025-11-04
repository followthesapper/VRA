#!/usr/bin/env python3
"""
E18: Shot-Complexity Reduction (Quick Version)
Wrapper that calls T6A2_shot_reduction_GPU.py with VERY reduced parameters for fast verification.
"""

import subprocess
import sys
from pathlib import Path

# Call the full GPU version with minimal parameters for quick validation
script_dir = Path(__file__).parent
full_script = script_dir / "T6A2_shot_reduction_GPU.py"

# VERY quick parameters: 10 trials (vs 500), max 500 shots (vs 5000), smaller r_max
quick_args = [
    sys.executable, str(full_script),
    "--trials", "10",
    "--max_shots", "500",
    "--r_max", "256"  # vs 512
]

print(f"Running E18 (quick mode): {' '.join(quick_args)}")
sys.exit(subprocess.call(quick_args))
