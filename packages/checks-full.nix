# Full checks - uses reusable patterns from checks flake (includes tests)
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns;

  # Import shared test configuration
  testConfig = pkgs.callPackage ./test-config.nix { inherit inputs; };

  # Apply check patterns to htutil source with test dependencies
  htutilSrc = ../.; # htutil source root
  htutilChecks = patterns.fullCheckSuite {
    src = htutilSrc;
    projectName = "htutil";
    extraDeps = testConfig.baseDeps;
    env = testConfig.baseEnv;
  };

in
pkgs.writeShellScriptBin "htutil-checks-full" ''
  set -euo pipefail
  
  echo "🚀 Running htutil full checks (linting + tests)..."
  echo ""
  
  # Run checks using the framework runner with derivation paths
  ${runner}/bin/check-runner \
    "nix-linting:${htutilChecks.nix-linting}" \
    "nix-formatting:${htutilChecks.nix-formatting}" \
    "python-linting:${htutilChecks.python-linting}" \
    "python-testing:${htutilChecks.python-testing}" \
    --suite-name "Full Checks"
''
