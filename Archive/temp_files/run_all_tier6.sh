#!/bin/bash
################################################################################
# Tier 6 Master Execution Script
#
# Runs all implemented Tier 6 experiments in sequence.
#
# Usage:
#   bash run_all_tier6.sh [quick|full|parallel]
#
# Modes:
#   quick    - Run only quick wins (T6-A2, T6-C1, T6-D1)
#   full     - Run all implemented experiments (default)
#   parallel - Run experiments in parallel (requires GNU parallel)
#
# Author: Dylan Vaca
# Date: October 31, 2025
################################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# Mode
MODE="${1:-full}"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Tier 6: Theory-First Experiments - Master Execution Script${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo -e "Mode: ${GREEN}${MODE}${NC}"
echo -e "Date: $(date)"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

# Log file
LOGDIR="../../Data/Experiments/Tier6"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/tier6_execution_$(date +%Y%m%d_%H%M%S).log"

echo -e "Logging to: ${YELLOW}${LOGFILE}${NC}"
echo ""

# Execution function
run_experiment() {
    local script=$1
    local name=$2

    if [ ! -f "$script" ]; then
        echo -e "${YELLOW}⚠ Skipping${NC} $name (not implemented)"
        return 0
    fi

    echo -e "${GREEN}▶ Running${NC} $name..."
    echo "---" | tee -a "$LOGFILE"
    echo "Experiment: $name" | tee -a "$LOGFILE"
    echo "Script: $script" | tee -a "$LOGFILE"
    echo "Start: $(date)" | tee -a "$LOGFILE"

    START_TIME=$(date +%s)

    if python3 "$script" >> "$LOGFILE" 2>&1; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo -e "${GREEN}✓ Complete${NC} $name (${ELAPSED}s)" | tee -a "$LOGFILE"
    else
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo -e "${RED}✗ Failed${NC} $name (${ELAPSED}s)" | tee -a "$LOGFILE"
        echo -e "${YELLOW}Check log for details:${NC} $LOGFILE"
    fi

    echo ""
}

# Quick wins (Phase 1)
QUICK_EXPERIMENTS=(
    "T6A2_shot_reduction_bound.py:T6-A2 Shot Reduction Bound"
    "T6C1_vqe_term_grouping.py:T6-C1 VQE Term Grouping"
    "T6D1_exoplanet_biosignature.py:T6-D1 Exoplanet Biosignature"
)

# Full suite
FULL_EXPERIMENTS=(
    "T6A2_shot_reduction_bound.py:T6-A2 Shot Reduction Bound"
    "T6C1_vqe_term_grouping.py:T6-C1 VQE Term Grouping"
    "T6D1_exoplanet_biosignature.py:T6-D1 Exoplanet Biosignature"
    "T6A1_coherence_transition.py:T6-A1 Coherence Transition (INTENSIVE)"
)

# Select experiments based on mode
if [ "$MODE" == "quick" ]; then
    EXPERIMENTS=("${QUICK_EXPERIMENTS[@]}")
elif [ "$MODE" == "parallel" ]; then
    echo -e "${YELLOW}Parallel mode not yet implemented. Running sequentially.${NC}"
    EXPERIMENTS=("${FULL_EXPERIMENTS[@]}")
else
    EXPERIMENTS=("${FULL_EXPERIMENTS[@]}")
fi

# Run experiments
TOTAL_START=$(date +%s)

for exp in "${EXPERIMENTS[@]}"; do
    IFS=':' read -r script name <<< "$exp"
    run_experiment "$script" "$name"
done

TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))

# Summary
echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Execution Complete${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo ""
echo -e "Total time: ${GREEN}${TOTAL_ELAPSED}s${NC} ($(($TOTAL_ELAPSED / 60))m $(($TOTAL_ELAPSED % 60))s)"
echo -e "Log file: ${YELLOW}${LOGFILE}${NC}"
echo ""
echo -e "Results saved to:"
echo -e "  Data:    ${YELLOW}../../Data/Experiments/Tier6/${NC}"
echo -e "  Figures: ${YELLOW}../../Figures/experiments/Tier6/${NC}"
echo ""
echo -e "${GREEN}All experiments complete!${NC}"
echo ""

# List results
echo -e "${BLUE}Generated Results:${NC}"
find "$LOGDIR" -name "*.json" -type f -mmin -60 | while read -r file; do
    echo -e "  📊 $file"
done

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Review findings in ${YELLOW}*_FINDINGS.md${NC} files"
echo -e "  2. Examine figures in ${YELLOW}Figures/experiments/Tier6/${NC}"
echo -e "  3. Run ${YELLOW}python analyze_tier6_results.py${NC} for aggregate analysis"
echo -e "  4. Document results in ${YELLOW}TIER6_SUMMARY.md${NC}"
echo ""
