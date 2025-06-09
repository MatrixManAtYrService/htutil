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

  # Load workspace for uv2nix
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../.;
  };

  # Create Python environment with dev dependencies using uv2nix properly
  # workspace.deps.all includes both default dependencies and all dev groups
  # This is the correct way to get all dependencies including dev groups
  htutilPythonEnvWithDev = htutilPackage.pythonSet.mkVirtualEnv "htutil-dev-env" workspace.deps.all;

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
    pythonEnv = htutilPythonEnvWithDev;
  };

  # Additional test check
  pytestCheck = makeCheckWithDeps {
    name = "pytest";
    description = "Python unit tests";
    src = htutilSrc;
    dependencies = [ htutilPythonEnvWithDev ] ++ testConfig.baseDeps;
    environment = testConfig.baseEnv // {
      # Handle both traditional withPackages (has sitePackages) and uv2nix mkVirtualEnv (doesn't)
      PYTHONPATH =
        if htutilPythonEnvWithDev ? sitePackages
        then "${htutilPythonEnvWithDev}/${htutilPythonEnvWithDev.sitePackages}"
        else "${htutilPythonEnvWithDev}/lib/python*/site-packages";
      # Make sure pytest and other executables are available
      PATH = "${htutilPythonEnvWithDev}/bin:$PATH";
    };
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
