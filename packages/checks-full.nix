# Full checks - includes fast checks plus tests
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

  # Additional test check
  pytestCheck = makeCheckWithDeps {
    name = "pytest";
    description = "Python unit tests";
    src = htutilSrc;
    dependencies = [ htutilPythonEnv ] ++ testConfig.baseDeps;
    environment = testConfig.baseEnv;
    script = ''
      echo "🧪 Running pytest..."
      pytest -v tests/
    '';
  };

in
pkgs.writeShellScriptBin "htutil-checks-full" ''
  set -euo pipefail
  
  echo "🚀 Running htutil full checks (linting + tests)..."
  echo ""
  
  # Run checks using the framework runner with derivation paths
  ${runner}/bin/check-runner \
    "deadnix:${deadnixCheck}" \
    "statix:${statixCheck}" \
    "nixpkgs-fmt:${nixpkgsFmtCheck}" \
    "ruff-check:${ruffCheckCheck}" \
    "ruff-format:${ruffFormatCheck}" \
    "pyright:${pyrightCheck}" \
    "pytest:${pytestCheck}" \
    --suite-name "Full Checks"
''
