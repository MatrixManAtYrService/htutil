# Fast checks - uses reusable patterns from checks flake
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns;

  # Apply check patterns to htutil source
  htutilSrc = ../.; # htutil source root
  htutilChecks = patterns.fastCheckSuite {
    src = htutilSrc;
    projectName = "htutil";
  };

in
pkgs.writeShellScriptBin "htutil-checks-fast" ''
  set -euo pipefail
  
  echo "🚀 Running htutil fast checks (linting)..."
  echo ""
  
  # Run checks using the framework runner with derivation paths
  ${runner}/bin/check-runner \
    "nix-linting:${htutilChecks.nix-linting}" \
    "nix-formatting:${htutilChecks.nix-formatting}" \
    "python-linting:${htutilChecks.python-linting}" \
    --suite-name "Fast Checks"
''
