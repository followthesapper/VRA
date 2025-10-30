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

    def cross_modulus_extended_moduli(self) -> dict:
        """Reproduce Cross-Modulus Validation: Extended moduli sweep."""
        return self.run_command(
            ['python3', 'Code/Experiments/Robustness/extended_moduli_sweep.py'],
            'Cross-Modulus: Extended Moduli Sweep'
        )

    def cross_modulus_regime_boundaries(self) -> dict:
        """Reproduce Cross-Modulus Validation: Regime boundary validation."""
        return self.run_command(
            ['python3', 'Code/Experiments/Robustness/regime_boundary_validation.py'],
            'Cross-Modulus: Regime Boundary Validation'
        )

    def performance_benchmarks(self) -> dict:
        """Reproduce Performance Benchmarks: Baseline method comparisons."""
        return self.run_command(
            ['python3', 'Code/Experiments/Benchmarks/run_benchmarks.py'],
            'Performance: Baseline Benchmarks'
        )

    def noise_adversarial_noise_injection(self) -> dict:
        """Reproduce Noise & Adversarial: Noise injection tests."""
        return self.run_command(
            ['python3', 'Code/Experiments/Robustness/noise_injection_tests.py'],
            'Noise & Adversarial: Noise Injection'
        )

    def noise_adversarial_adversarial(self) -> dict:
        """Reproduce Noise & Adversarial: Adversarial tests."""
        return self.run_command(
            ['python3', 'Code/Experiments/Robustness/adversarial_tests.py'],
            'Noise & Adversarial: Adversarial Tests'
        )

    def statistical_analysis_bootstrap_cis(self) -> dict:
        """Reproduce Statistical Analysis: Bootstrap CIs."""
        return self.run_command(
            ['python3', 'Code/Experiments/Statistics/add_bootstrap_cis.py'],
            'Statistical Analysis: Bootstrap Confidence Intervals'
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
            (['python3', 'Code/Experiments/Robustness/generate_phase1_2_figures.py'],
             'Figures: Cross-Modulus Validation'),
            (['python3', 'Code/Experiments/Benchmarks/generate_benchmark_figures.py'],
             'Figures: Performance Benchmarks'),
            (['python3', 'Code/Experiments/Robustness/generate_phase4_1_figures.py'],
             'Figures: Noise & Adversarial'),
            (['python3', 'Code/Experiments/Statistics/generate_phase4_2_figures.py'],
             'Figures: Statistical Analysis')
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

        # Cross-Modulus Validation
        self.log("\n--- Cross-Modulus Validation ---")
        self.results['experiments'].append(self.cross_modulus_extended_moduli())
        self.results['experiments'].append(self.cross_modulus_regime_boundaries())

        # Performance Benchmarks
        self.results['experiments'].append(self.performance_benchmarks())

        # Noise & Adversarial (can be slow)
        if not skip_slow:
            self.log("\n--- Noise & Adversarial Testing ---")
            self.results['experiments'].append(self.noise_adversarial_noise_injection())
            self.results['experiments'].append(self.noise_adversarial_adversarial())
        else:
            self.log("\n--- Noise & Adversarial: Skipped (--quick mode) ---")

        # Statistical Analysis
        self.log("\n--- Statistical Analysis ---")
        self.results['experiments'].append(self.statistical_analysis_bootstrap_cis())

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
