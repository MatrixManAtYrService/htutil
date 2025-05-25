#!/usr/bin/env bash
set -e

echo "Running all formatters and linters..."

echo "1. Formatting with nixpkgs-fmt..."
nixpkgs-fmt flake.nix

echo "2. Running ruff check with auto-fix..."
ruff check --fix src/

echo "3. Running ruff format..."
ruff format src/

echo "All checks completed!"
