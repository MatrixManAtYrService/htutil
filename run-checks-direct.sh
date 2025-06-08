#!/usr/bin/env bash

set -euo pipefail

# Simple check runner for htutil while checks framework is being improved
# This will be replaced once the framework supports dependency injection

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Running htutil checks (direct implementation)"
echo "=================================================="
echo ""

# Track results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=()

run_check() {
    local check_name="$1"
    local description="$2"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo "[$TOTAL_CHECKS] Running check: $check_name"
    echo "📋 $description"
    
    if nix build "$PROJECT_ROOT#$check_name" --no-link; then
        echo "✅ $check_name - PASSED"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "❌ $check_name - FAILED"
        FAILED_CHECKS+=("$check_name")
    fi
    
    echo ""
}

# Determine which checks to run based on argument
case "${1:-full}" in
    "fast")
        echo "Running fast checks (linting only)..."
        run_check "nixfmt" "Nix file formatting"
        run_check "ruff-check" "Python linting (ruff check)"
        run_check "ruff-format" "Python formatting (ruff format)"
        ;;
    "full")
        echo "Running full checks (linting + single version tests)..."
        run_check "nixfmt" "Nix file formatting"
        run_check "ruff-check" "Python linting (ruff check)"
        run_check "ruff-format" "Python formatting (ruff format)"
        run_check "pytest-single" "Python tests (single version)"
        ;;
    "release")
        echo "Running release checks (linting + multi-version tests)..."
        run_check "nixfmt" "Nix file formatting"
        run_check "ruff-check" "Python linting (ruff check)"
        run_check "ruff-format" "Python formatting (ruff format)"
        run_check "pytest-py310" "Python tests (Python 3.10)"
        run_check "pytest-py312" "Python tests (Python 3.12)"
        ;;
    *)
        echo "Usage: $0 [fast|full|release]"
        echo ""
        echo "  fast    - Linting only"
        echo "  full    - Linting + single version tests (default)"
        echo "  release - Linting + multi-version tests"
        exit 1
        ;;
esac

# Summary
echo "=================================================="
echo "📊 CHECK SUMMARY"
echo "=================================================="
echo "  Total checks:    $TOTAL_CHECKS"
echo "  Passed:          $PASSED_CHECKS | Failed: $((TOTAL_CHECKS - PASSED_CHECKS))"

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo ""
    echo "🎉 All checks passed!"
    exit 0
else
    echo ""
    echo "❌ Failed checks:"
    for check in "${FAILED_CHECKS[@]}"; do
        echo "  - $check"
    done
    echo ""
    echo "Some checks failed. Please review the output above."
    exit 1
fi
