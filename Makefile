.PHONY: help install test examples clean data figs all

# Default target
help:
	@echo "VRA - Vaca Resonance Analysis"
	@echo "=============================="
	@echo ""
	@echo "Available targets:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make test       - Run quick smoke test"
	@echo "  make examples   - Run example analyses"
	@echo "  make data       - Generate all experimental data"
	@echo "  make figs       - Generate all figures"
	@echo "  make all        - Run everything (install + data + figs)"
	@echo "  make clean      - Remove generated files"
	@echo ""

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Done! VRA is ready to use."

# Quick smoke test
test:
	@echo "Running smoke test (r=168, M=1,4,8)..."
	python3 vra.py run --N 1009 --r 168 --M 1,4,8 --output results/test/
	@echo "Smoke test passed!"

# Show examples
examples:
	python3 vra.py examples

# Generate all data
data: install
	@echo "Generating experimental data..."
	@mkdir -p results/reproduction
	@echo "  [1/3] Running r=126 transition test..."
	cd Code/FP4_Regime_Map && python3 transition_test_r168.py --config ../../Data/r126_transition/same_order_bases_1009_r121.json --output ../../results/reproduction/
	@echo "  [2/3] Running r=168 transition test..."
	cd Code/FP4_Regime_Map && python3 transition_test_r168.py --config ../../Data/r168_transition/same_order_bases_1009_r168.json --output ../../results/reproduction/
	@echo "  [3/3] Running robustness sweep..."
	cd Code/FP2_Leakage && python3 robustness_sweep.py --output ../../results/reproduction/
	@echo "Data generation complete! Check results/reproduction/"

# Generate all figures
figs: install
	@echo "Generating figures..."
	@mkdir -p results/figures
	@echo "  [1/1] Running regime map analysis..."
	cd Code/FP4_Regime_Map && python3 regime_map_analysis.py --output ../../results/figures/
	@echo "Figure generation complete! Check results/figures/"

# Run everything
all: install data figs
	@echo ""
	@echo "================================================"
	@echo "VRA reproduction complete!"
	@echo "================================================"
	@echo "Data:    results/reproduction/"
	@echo "Figures: results/figures/"
	@echo ""

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf results/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

# Quick start for new users
quickstart: install
	@echo ""
	@echo "VRA Quick Start"
	@echo "==============="
	@echo ""
	@echo "Dependencies installed! Try:"
	@echo ""
	@echo "  1. Run a quick test:"
	@echo "     make test"
	@echo ""
	@echo "  2. See usage examples:"
	@echo "     make examples"
	@echo ""
	@echo "  3. Run full reproduction:"
	@echo "     make all"
	@echo ""
