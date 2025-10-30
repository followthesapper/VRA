"""
VRA Baselines Package
=====================

Baseline implementations for comparison with VRA to establish novelty.

Modules:
    - rpt: Ramanujan Periodicity Transform (RPT) implementation
    - comparison: Head-to-head VRA vs. RPT comparison framework
    - statistical_tests: Statistical analysis of novelty claims
    - prove_novelty: Formal novelty proof script
    - figures.novelty: Novelty validation figure generation
    - figures.proof: Statistical proof figure generation

Author: Dylan Vaca
Date: October 2025
"""

from .rpt import (
    ramanujan_sum,
    build_rpt_dictionary,
    rpt_periodogram,
    detect_period_rpt,
    rpt_precision_recall,
)

from .comparison import (
    find_bases_with_order,
    generate_vra_signal,
    generate_rpt_signal,
    evaluate_vra_vs_rpt_single,
    sweep_grid,
    generate_test_grid,
)

from .statistical_tests import (
    bootstrap_diff,
    analyze_overall_advantage,
    analyze_by_regime,
    analyze_sqrtM_scaling,
    analyze_runtime_advantage,
    check_novelty_criteria,
    generate_novelty_report,
)

__all__ = [
    # RPT baseline
    "ramanujan_sum",
    "build_rpt_dictionary",
    "rpt_periodogram",
    "detect_period_rpt",
    "rpt_precision_recall",
    # Comparison
    "find_bases_with_order",
    "generate_vra_signal",
    "generate_rpt_signal",
    "evaluate_vra_vs_rpt_single",
    "sweep_grid",
    "generate_test_grid",
    # Statistical tests
    "bootstrap_diff",
    "analyze_overall_advantage",
    "analyze_by_regime",
    "analyze_sqrtM_scaling",
    "analyze_runtime_advantage",
    "check_novelty_criteria",
    "generate_novelty_report",
]
