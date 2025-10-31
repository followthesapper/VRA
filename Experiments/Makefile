PY=python3
DATA=../Data/Experiments
FIGS=../Figures/Experiments

all: tier1 tier2 tier3 tier4

tier1:
	$(PY) Tier1_Theory/E1_spectral_order_equivalence.py --out $(DATA)/Tier1/E1
	$(PY) Tier1_Theory/E2_leakage_bounds_regression.py --out $(DATA)/Tier1/E2
	$(PY) Tier1_Theory/E3_phase_alignment_ablation.py --out $(DATA)/Tier1/E3

tier2:
	$(PY) Tier2_ECC/E4_ecc_order_detection.py --out $(DATA)/Tier2/E4
	$(PY) Tier2_ECC/E5_ecc_scaling_grid.py --out $(DATA)/Tier2/E5

tier3:
	$(PY) Tier3_QuantumBridge/E6_vra_vs_qpe_patterns.py --out $(DATA)/Tier3/E6
	$(PY) Tier3_QuantumBridge/E7_shot_reduction_study.py --out $(DATA)/Tier3/E7

tier4:
	$(PY) Tier4_HybridApplied/E8_semiprime_groundwork.py --out $(DATA)/Tier4/E8
	$(PY) Tier4_HybridApplied/E9_noise_and_jitter_map.py --out $(DATA)/Tier4/E9
	$(PY) Tier4_HybridApplied/E10_physics_signal_pilot.py --out $(DATA)/Tier4/E10
