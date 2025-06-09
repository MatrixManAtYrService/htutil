# Fast checks - assembles checks from the checks framework
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns;

  # Get htutil's Python environment from uv2nix  
  htutilPackage = import ./default.nix { inherit inputs pkgs; };

  # For pyright, create an environment that includes pytest manually
  # since the test files need it
  htutilPythonEnvWithTest = pkgs.python3.withPackages (ps: [
    ps.pytest
    ps.typer
    ps.rich
    ps.ansi2html
  ]);

  # Create individual check derivations for htutil
  htutilSrc = ../.;

  # Build the individual checks
  deadnixCheck = patterns.deadnix { src = htutilSrc; };
  statixCheck = patterns.statix { src = htutilSrc; };
  nixpkgsFmtCheck = patterns.nixpkgs-fmt { src = htutilSrc; };
  ruffCheckCheck = patterns.ruff-check { src = htutilSrc; };
  ruffFormatCheck = patterns.ruff-format { src = htutilSrc; };
  pyrightCheck = patterns.pyright {
    src = htutilSrc;
    pythonEnv = htutilPythonEnvWithTest;
  };

in
pkgs.writeShellScriptBin "htutil-checks-fast" ''
  set -euo pipefail
  
  echo "🚀 Running htutil fast checks (linting)..."
  echo ""
  
  # Run checks using the framework runner with derivation paths
  ${runner}/bin/check-runner \
    "deadnix:${deadnixCheck}" \
    "statix:${statixCheck}" \
    "nixpkgs-fmt:${nixpkgsFmtCheck}" \
    "ruff-check:${ruffCheckCheck}" \
    "ruff-format:${ruffFormatCheck}" \
    "pyright:${pyrightCheck}" \
    --suite-name "Fast Checks"
''
