PY=python3
DATA=../Data/Experiments
FIGS=../Figures/Experiments

all: tier1 tier2 tier3 tier4

tier1:
	$(PY) Tier1_Theory/E1_spectral_order_equivalence.py --out $(DATA)/tier1/e1
	$(PY) Tier1_Theory/E2_leakage_bounds_regression.py --out $(DATA)/tier1/e2
	$(PY) Tier1_Theory/E3_phase_alignment_ablation.py --out $(DATA)/tier1/e3

tier2:
	$(PY) Tier2_ECC/E4_ecc_order_detection.py --out $(DATA)/tier2/e4
	$(PY) Tier2_ECC/E5_ecc_scaling_grid.py --out $(DATA)/tier2/e5

tier3:
	$(PY) Tier3_QuantumBridge/E6_vra_vs_qpe_patterns.py --out $(DATA)/tier3/e6
	$(PY) Tier3_QuantumBridge/E7_shot_reduction_study.py --out $(DATA)/tier3/e7

tier4:
	$(PY) Tier4_HybridApplied/E8_semiprime_groundwork.py --out $(DATA)/tier4/e8
	$(PY) Tier4_HybridApplied/E9_noise_and_jitter_map.py --out $(DATA)/tier4/e9
	$(PY) Tier4_HybridApplied/E10_physics_signal_pilot.py --out $(DATA)/tier4/e10)
