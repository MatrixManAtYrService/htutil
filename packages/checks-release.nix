# Release checks - includes full checks plus multi-version testing
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns makeCheckWithDeps;

  # Import shared test configuration
  testConfig = pkgs.callPackage ./test-config.nix { inherit inputs; };

  # Get release tests for different Python versions
  releaseTests = pkgs.callPackage ./htutil-release-tests.nix { inherit inputs; };

in
pkgs.writeShellScriptBin "htutil-checks-release" ''
  set -euo pipefail
  
  echo "🚀 Running htutil release checks..."
  echo "This tests 'uv run htutil --help' across multiple Python versions."
  echo ""
  
  # Run only the release tests (no linting - that's covered by checks-fast/checks-full)
  ${runner}/bin/check-runner \
    "release-py3.10:${releaseTests.py310}" \
    "release-py3.11:${releaseTests.py311}" \
    "release-py3.12:${releaseTests.py312}" \
    --suite-name "Release Checks"
''
