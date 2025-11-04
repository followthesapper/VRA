#!/usr/bin/env python3
"""
VRA Experiment Reproduction Script
===================================

Easily run any or all VRA experiments (E1-E27) with reproducibility verification.

Usage:
    python3 REPRODUCE.py --all                  # Run all experiments
    python3 REPRODUCE.py --experiment E1        # Run specific experiment
    python3 REPRODUCE.py --experiment E1 E3 E5  # Run multiple experiments
    python3 REPRODUCE.py --quick                # Run quick smoke tests only
    python3 REPRODUCE.py --category math        # Run by category

Categories:
    math        : E1-E3 (Mathematical Validation)
    ecc         : E4-E5 (Elliptic Curve Extension)
    quantum     : E6-E7 (Quantum Bridge)
    applied     : E8-E10 (Hybrid & Applied)
    ai          : E11-E16 (AI/ML Integration)
    theory      : E17-E27 (Theory-First Validation)
    theoretical : Theoretical Suite (A1-L1)

Author: Dylan Vaca
Date: November 2025
Version: 2.0 (Rewritten for E1-E27 structure)
"""

import sys
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class ExperimentRunner:
    """Manages running and verifying VRA experiments."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.vra_root = Path(__file__).parent.parent.parent
        self.experiments_dir = self.vra_root / "Experiments"
        self.output_dir = output_dir or (self.vra_root / "Data" / "Reproducibility")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'experiments': []
        }

        # Define all experiments with metadata
        self.experiment_catalog = {
            # Mathematical Validation
            'E1': {'name': 'Spectral-Order Equivalence', 'category': 'math',
                   'script': 'E1_spectral_order_equivalence.py'},
            'E2': {'name': 'Validated Radius Rule', 'category': 'math',
                   'script': 'E2_leakage_bounds_regression.py'},
            'E3': {'name': 'Phase Alignment Ablation', 'category': 'math',
                   'script': 'E3_phase_alignment_ablation.py'},

            # Elliptic Curve Extension
            'E4': {'name': 'ECC Order Detection', 'category': 'ecc',
                   'script': 'E4_ecc_order_detection.py'},
            'E5': {'name': 'ECC Scaling Grid', 'category': 'ecc',
                   'script': 'E5_ecc_scaling_grid.py'},

            # Quantum Bridge
            'E6': {'name': 'VRA vs QPE Pattern Comparison', 'category': 'quantum',
                   'script': 'E6_vra_vs_qpe_patterns.py'},
            'E7': {'name': 'Shot Reduction Study', 'category': 'quantum',
                   'script': 'E7_shot_reduction_study.py'},

            # Hybrid & Applied
            'E8': {'name': 'Semiprime Groundwork', 'category': 'applied',
                   'script': None},  # No main script identified
            'E9': {'name': 'Noise & Jitter Robustness', 'category': 'applied',
                   'script': None},
            'E10': {'name': 'Stationary Rational Tones', 'category': 'applied',
                    'script': None},

            # AI/ML Integration
            'E11': {'name': 'VRA Features Benchmark', 'category': 'ai',
                    'script': 'E11_vra_features.py'},
            'E12': {'name': 'VRA Tokens for Transformers', 'category': 'ai',
                    'script': 'E12_vra_tokens.py'},
            'E13': {'name': 'Learned Phase Alignment', 'category': 'ai',
                    'script': 'E13_learned_alignment.py'},
            'E14': {'name': 'Phase Stacking Validation', 'category': 'ai',
                    'script': 'E14_phase_stacking.py'},
            'E15': {'name': 'Base Selection Policy', 'category': 'ai',
                    'script': 'E15_base_selection.py'},
            'E16': {'name': 'L-Scaling Bootstrap', 'category': 'ai',
                    'script': 'E16_l_scaling.py'},

            # Theory-First Validation
            'E17': {'name': 'Coherence-Incoherence Transition', 'category': 'theory',
                    'script': 'E17_coherence_incoherence_transition.py'},
            'E18': {'name': 'Shot-Complexity Reduction', 'category': 'theory',
                    'script': 'E18_shot_complexity_reduction.py'},
            'E19': {'name': 'Random-Unitary Horizon', 'category': 'theory',
                    'script': 'E19_random_unitary_horizon.py'},
            'E20': {'name': 'Wormhole/ER=EPR Phases', 'category': 'theory',
                    'script': 'E20_wormhole_er_epr_phases.py'},
            'E21': {'name': 'Matter/Antimatter CP-Phase', 'category': 'theory',
                    'script': 'E21_matter_antimatter_cp_phase.py'},
            'E22': {'name': 'VQE Term Grouping', 'category': 'theory',
                    'script': 'E22_vqe_term_grouping.py'},
            'E23': {'name': 'Differentiable VRA Layer', 'category': 'theory',
                    'script': 'E23_differentiable_vra_layer.py'},
            'E24': {'name': 'Exoplanet Biosignature', 'category': 'theory',
                    'script': 'E24_exoplanet_biosignature.py'},
            'E25': {'name': 'Phonon/Polaron Discrimination', 'category': 'theory',
                    'script': 'E25_phonon_polaron_discrimination.py'},
            'E26': {'name': 'MHD/Alfvén Coherence', 'category': 'theory',
                    'script': 'E26_mhd_alfven_coherence.py'},
            'E27': {'name': 'Protein Normal Mode', 'category': 'theory',
                    'script': 'E27_protein_normal_mode.py'},
        }

    def log(self, message: str, level: str = "INFO"):
        """Print timestamped log message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def get_experiment_path(self, exp_id: str) -> Optional[Path]:
        """Get the full path to an experiment's code directory."""
        if exp_id not in self.experiment_catalog:
            return None

        # Find experiment directory
        exp_dir = None
        for d in self.experiments_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{exp_id}_"):
                exp_dir = d
                break

        if not exp_dir:
            return None

        return exp_dir / "Code"

    def run_experiment(self, exp_id: str, quick: bool = False) -> Dict:
        """Run a single experiment and return results."""
        if exp_id not in self.experiment_catalog:
            self.log(f"Unknown experiment: {exp_id}", "ERROR")
            return {'experiment': exp_id, 'success': False, 'error': 'Unknown experiment'}

        exp_info = self.experiment_catalog[exp_id]
        exp_name = f"{exp_id}: {exp_info['name']}"

        self.log(f"Running {exp_name}")

        # Check if script is defined
        if not exp_info['script']:
            self.log(f"  ⚠️  No main script defined for {exp_id}", "WARN")
            return {
                'experiment': exp_id,
                'name': exp_info['name'],
                'success': False,
                'skipped': True,
                'reason': 'No main script defined'
            }

        # Get experiment path
        code_dir = self.get_experiment_path(exp_id)
        if not code_dir or not code_dir.exists():
            self.log(f"  ❌ Experiment directory not found: {exp_id}", "ERROR")
            return {
                'experiment': exp_id,
                'name': exp_info['name'],
                'success': False,
                'error': 'Directory not found'
            }

        # Get script path
        script_path = code_dir / exp_info['script']
        if not script_path.exists():
            self.log(f"  ❌ Script not found: {script_path}", "ERROR")
            return {
                'experiment': exp_id,
                'name': exp_info['name'],
                'success': False,
                'error': f'Script not found: {exp_info["script"]}'
            }

        # Prepare command
        cmd = ['python3', str(script_path)]
        if quick:
            cmd.append('--quick')

        self.log(f"  Command: {' '.join(cmd)}")

        start_time = datetime.now()

        try:
            # Run with 10 minute timeout
            result = subprocess.run(
                cmd,
                cwd=str(code_dir),
                capture_output=True,
                text=True,
                timeout=600
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            success = result.returncode == 0

            if success:
                self.log(f"  ✅ Success ({duration:.1f}s)")
            else:
                self.log(f"  ❌ Failed ({duration:.1f}s)")
                if result.stderr:
                    self.log(f"  Error: {result.stderr[:200]}", "ERROR")

            return {
                'experiment': exp_id,
                'name': exp_info['name'],
                'category': exp_info['category'],
                'success': success,
                'duration_seconds': duration,
                'return_code': result.returncode,
                'stdout_lines': len(result.stdout.splitlines()),
                'stderr_preview': result.stderr[:500] if not success else None
            }

        except subprocess.TimeoutExpired:
            self.log(f"  ⏱️  Timeout (>10 minutes)", "WARN")
            return {
                'experiment': exp_id,
                'name': exp_info['name'],
                'success': False,
                'error': 'Timeout after 10 minutes'
            }

        except Exception as e:
            self.log(f"  ❌ Exception: {str(e)}", "ERROR")
            return {
                'experiment': exp_id,
                'name': exp_info['name'],
                'success': False,
                'error': str(e)
            }

    def run_experiments(self, exp_ids: List[str], quick: bool = False):
        """Run multiple experiments and save results."""
        self.log("=" * 70)
        self.log(f"VRA Experiment Reproduction - Running {len(exp_ids)} experiments")
        self.log("=" * 70)

        for exp_id in exp_ids:
            result = self.run_experiment(exp_id, quick=quick)
            self.results['experiments'].append(result)

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate and print summary of all runs."""
        total = len(self.results['experiments'])
        successful = sum(1 for r in self.results['experiments'] if r.get('success', False))
        failed = sum(1 for r in self.results['experiments'] if not r.get('success', False) and not r.get('skipped', False))
        skipped = sum(1 for r in self.results['experiments'] if r.get('skipped', False))

        self.log("=" * 70)
        self.log("SUMMARY")
        self.log("=" * 70)
        self.log(f"Total experiments: {total}")
        self.log(f"  ✅ Successful: {successful}")
        self.log(f"  ❌ Failed: {failed}")
        self.log(f"  ⚠️  Skipped: {skipped}")

        if failed > 0:
            self.log("\nFailed Experiments:")
            for r in self.results['experiments']:
                if not r.get('success', False) and not r.get('skipped', False):
                    exp_id = r['experiment']
                    name = r.get('name', 'Unknown')
                    error = r.get('error', 'Unknown error')
                    self.log(f"  - {exp_id} ({name}): {error}")

        # Save results
        output_file = self.output_dir / f"reproduction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.log(f"\nResults saved to: {output_file}")
        self.log("=" * 70)

    def list_experiments(self, category: Optional[str] = None):
        """List all available experiments."""
        print("\nAvailable Experiments:")
        print("=" * 70)

        categories = {}
        for exp_id, info in sorted(self.experiment_catalog.items()):
            cat = info['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((exp_id, info))

        for cat, experiments in sorted(categories.items()):
            if category and cat != category:
                continue

            print(f"\n{cat.upper()}:")
            for exp_id, info in experiments:
                status = "✓" if info['script'] else "⚠️ No script"
                print(f"  {exp_id}: {info['name']} [{status}]")

        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="VRA Experiment Reproduction Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 REPRODUCE.py --all                  # Run all experiments
  python3 REPRODUCE.py --experiment E1        # Run E1 only
  python3 REPRODUCE.py --experiment E1 E3 E5  # Run multiple
  python3 REPRODUCE.py --category math        # Run all math experiments
  python3 REPRODUCE.py --list                 # List all experiments
  python3 REPRODUCE.py --quick --all          # Quick validation
        """
    )

    parser.add_argument('--all', action='store_true',
                       help='Run all experiments')
    parser.add_argument('--experiment', nargs='+', metavar='ID',
                       help='Run specific experiments (e.g., E1 E2 E3)')
    parser.add_argument('--category', choices=['math', 'ecc', 'quantum', 'applied', 'ai', 'theory'],
                       help='Run all experiments in a category')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation only (where supported)')
    parser.add_argument('--list', action='store_true',
                       help='List all available experiments')
    parser.add_argument('--output', type=Path,
                       help='Output directory for results (default: Data/Reproducibility/)')

    args = parser.parse_args()

    runner = ExperimentRunner(output_dir=args.output)

    # Handle list
    if args.list:
        runner.list_experiments()
        return

    # Determine which experiments to run
    exp_ids = []

    if args.all:
        exp_ids = list(runner.experiment_catalog.keys())
    elif args.experiment:
        exp_ids = args.experiment
    elif args.category:
        exp_ids = [exp_id for exp_id, info in runner.experiment_catalog.items()
                   if info['category'] == args.category]
    else:
        parser.print_help()
        return

    # Run experiments
    runner.run_experiments(exp_ids, quick=args.quick)


if __name__ == "__main__":
    main()
