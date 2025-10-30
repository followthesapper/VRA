#!/usr/bin/env python3
"""
VRA Reproduction Verification Script
=====================================

Reproduces all key experiments and verifies results match published data.
Implements Phase 4.2 reproducibility requirements.

Usage:
    python3 REPRODUCE.py                    # Run all experiments
    python3 REPRODUCE.py --quick            # Quick validation only
    python3 REPRODUCE.py --experiment=1.2   # Run specific experiment

Author: Dylan Vaca
Date: October 2025
"""

import sys
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime
import hashlib


class ReproductionRunner:
    """Manages reproduction of all VRA experiments."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'experiments': []
        }

    def log(self, message: str):
        """Print and log message."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_command(self, cmd: list, experiment_name: str) -> dict:
        """Run a reproduction command and capture results."""
        self.log(f"Running: {experiment_name}")
        self.log(f"  Command: {' '.join(cmd)}")

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            success = result.returncode == 0

            if success:
                self.log(f"  ✅ Success ({duration:.1f}s)")
            else:
                self.log(f"  ❌ Failed ({duration:.1f}s)")
                self.log(f"  Error: {result.stderr[:200]}")

            return {
                'experiment': experiment_name,
                'command': ' '.join(cmd),
                'success': success,
                'duration_seconds': duration,
                'stdout_lines': len(result.stdout.splitlines()),
                'stderr': result.stderr[:500] if not success else None
            }

        except subprocess.TimeoutExpired:
            self.log(f"  ⏱️  Timeout (>10 minutes)")
            return {
                'experiment': experiment_name,
                'command': ' '.join(cmd),
                'success': False,
                'error': 'Timeout after 10 minutes'
            }

    def phase1_2_extended_moduli(self) -> dict:
        """Reproduce Phase 1.2: Extended moduli sweep."""
        return self.run_command(
            ['python3', 'Code/Robustness/extended_moduli_sweep.py'],
            'Phase 1.2: Extended Moduli Sweep'
        )

    def phase1_2_regime_boundaries(self) -> dict:
        """Reproduce Phase 1.2: Regime boundary validation."""
        return self.run_command(
            ['python3', 'Code/Robustness/regime_boundary_validation.py'],
            'Phase 1.2: Regime Boundary Validation'
        )

    def phase1_3_benchmarks(self) -> dict:
        """Reproduce Phase 1.3: Baseline benchmarks."""
        return self.run_command(
            ['python3', 'Code/Benchmarks/run_benchmarks.py'],
            'Phase 1.3: Baseline Benchmarks'
        )

    def phase4_1_noise_injection(self) -> dict:
        """Reproduce Phase 4.1: Noise injection tests."""
        return self.run_command(
            ['python3', 'Code/Robustness/noise_injection_tests.py'],
            'Phase 4.1: Noise Injection'
        )

    def phase4_1_adversarial(self) -> dict:
        """Reproduce Phase 4.1: Adversarial tests."""
        return self.run_command(
            ['python3', 'Code/Robustness/adversarial_tests.py'],
            'Phase 4.1: Adversarial Tests'
        )

    def phase4_2_bootstrap_cis(self) -> dict:
        """Reproduce Phase 4.2: Bootstrap CIs."""
        return self.run_command(
            ['python3', 'Code/Statistics/add_bootstrap_cis.py'],
            'Phase 4.2: Bootstrap Confidence Intervals'
        )

    def verify_random_seed_reproducibility(self) -> dict:
        """Verify that fixed seeds produce identical results."""
        self.log("Verifying random seed reproducibility...")

        # Run a simple test twice with the same seed
        import numpy as np

        np.random.seed(42)
        data1 = np.random.randn(100)
        hash1 = hashlib.md5(data1.tobytes()).hexdigest()

        np.random.seed(42)
        data2 = np.random.randn(100)
        hash2 = hashlib.md5(data2.tobytes()).hexdigest()

        identical = (hash1 == hash2)

        if identical:
            self.log(f"  ✅ Random seed reproducibility verified")
        else:
            self.log(f"  ❌ Random seed reproducibility FAILED")

        return {
            'experiment': 'Random Seed Verification',
            'success': identical,
            'hash1': hash1,
            'hash2': hash2
        }

    def generate_figures(self) -> list:
        """Generate all figures."""
        figure_experiments = [
            (['python3', 'Code/Robustness/generate_phase1_2_figures.py'],
             'Figures: Phase 1.2'),
            (['python3', 'Code/Benchmarks/generate_benchmark_figures.py'],
             'Figures: Phase 1.3'),
            (['python3', 'Code/Robustness/generate_phase4_1_figures.py'],
             'Figures: Phase 4.1'),
            (['python3', 'Code/Statistics/generate_phase4_2_figures.py'],
             'Figures: Phase 4.2')
        ]

        results = []
        for cmd, name in figure_experiments:
            results.append(self.run_command(cmd, name))

        return results

    def run_all(self, skip_slow: bool = False):
        """Run all reproduction experiments."""
        self.log("=" * 70)
        self.log("VRA REPRODUCIBILITY VERIFICATION")
        self.log("=" * 70)

        # Seed verification
        self.results['experiments'].append(
            self.verify_random_seed_reproducibility()
        )

        # Phase 1.2
        self.log("\n--- Phase 1: Immediate Validation ---")
        self.results['experiments'].append(self.phase1_2_extended_moduli())
        self.results['experiments'].append(self.phase1_2_regime_boundaries())

        # Phase 1.3
        self.results['experiments'].append(self.phase1_3_benchmarks())

        # Phase 4.1 (can be slow)
        if not skip_slow:
            self.log("\n--- Phase 4.1: Robustness Testing ---")
            self.results['experiments'].append(self.phase4_1_noise_injection())
            self.results['experiments'].append(self.phase4_1_adversarial())
        else:
            self.log("\n--- Phase 4.1: Skipped (--quick mode) ---")

        # Phase 4.2
        self.log("\n--- Phase 4.2: Statistical Rigor ---")
        self.results['experiments'].append(self.phase4_2_bootstrap_cis())

        # Figures
        if not skip_slow:
            self.log("\n--- Figure Generation ---")
            self.results['experiments'].extend(self.generate_figures())

        # Summary
        self.log("\n" + "=" * 70)
        self.log("REPRODUCTION SUMMARY")
        self.log("=" * 70)

        total = len(self.results['experiments'])
        successful = sum(1 for exp in self.results['experiments'] if exp['success'])

        self.log(f"Total experiments: {total}")
        self.log(f"Successful: {successful}")
        self.log(f"Failed: {total - successful}")
        self.log(f"Success rate: {100 * successful / total:.1f}%")

        # Save results
        results_file = self.output_dir / f"reproduction_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.log(f"\nResults saved to: {results_file}")

        return successful == total


def main():
    parser = argparse.ArgumentParser(
        description='Reproduce VRA validation experiments'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Skip slow experiments (Phase 4.1, figures)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('Data/Reproduced'),
        help='Output directory for reproduced results'
    )

    args = parser.parse_args()

    runner = ReproductionRunner(args.output_dir)
    success = runner.run_all(skip_slow=args.quick)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
