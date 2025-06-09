# Release checks - includes full checks plus multi-version testing
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns makeCheckWithDeps;

  # Import shared test configuration
  testConfig = pkgs.callPackage ./test-config.nix { inherit inputs; };

  # Get htutil's Python environment from uv2nix
  htutilPackage = import ./default.nix { inherit inputs pkgs; };
  htutilPythonEnv = htutilPackage.pythonEnv;

  # Create individual check derivations for htutil
  htutilSrc = ../.;

  # All the fast checks
  deadnixCheck = patterns.deadnix { src = htutilSrc; };
  statixCheck = patterns.statix { src = htutilSrc; };
  nixpkgsFmtCheck = patterns.nixpkgs-fmt { src = htutilSrc; };
  ruffCheckCheck = patterns.ruff-check { src = htutilSrc; };
  ruffFormatCheck = patterns.ruff-format { src = htutilSrc; };
  pyrightCheck = patterns.pyright {
    src = htutilSrc;
    pythonEnv = htutilPythonEnv;
  };

  # Test checks for different Python versions
  makePytestCheck = pythonPkg: makeCheckWithDeps {
    name = "pytest-${pythonPkg.python.pythonVersion}";
    description = "Python unit tests with ${pythonPkg.python.pythonVersion}";
    src = htutilSrc;
    dependencies = [
      (pythonPkg.withPackages (ps: with ps; [
        ansi2html
        typer
        rich
        pytest
        structlog
      ]))
    ] ++ testConfig.baseDeps;
    environment = testConfig.baseEnv;
    script = ''
      echo "🧪 Running pytest with Python ${pythonPkg.python.pythonVersion}..."
      pytest -v tests/
    '';
  };

  pytest310Check = makePytestCheck pkgs.python310Packages;
  pytest311Check = makePytestCheck pkgs.python311Packages;
  pytest312Check = makePytestCheck pkgs.python312Packages;

in
pkgs.writeShellScriptBin "htutil-checks-release" ''
  set -euo pipefail
  
  echo "🚀 Running htutil release checks (linting + multi-version tests)..."
  echo ""
  
  # Run checks using the framework runner with derivation paths
  ${runner}/bin/check-runner \
    "deadnix:${deadnixCheck}" \
    "statix:${statixCheck}" \
    "nixpkgs-fmt:${nixpkgsFmtCheck}" \
    "ruff-check:${ruffCheckCheck}" \
    "ruff-format:${ruffFormatCheck}" \
    "pyright:${pyrightCheck}" \
    "pytest-3.10:${pytest310Check}" \
    "pytest-3.11:${pytest311Check}" \
    "pytest-3.12:${pytest312Check}" \
    --suite-name "Release Checks"
''
