# Release checks - uses reusable patterns from checks flake (includes multi-version tests)
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns;

  # Import shared test configuration
  testConfig = pkgs.callPackage ./test-config.nix { inherit inputs; };

  # Apply check patterns to htutil source with multi-version Python testing
  htutilSrc = ../.; # htutil source root

  # Create individual checks for different Python versions
  nixLinting = patterns.nixLinting { src = htutilSrc; };
  nixFormatting = patterns.nixFormatting { src = htutilSrc; };
  pythonLinting = patterns.pythonLinting { src = htutilSrc; };

  # Python tests with different versions using shared config
  pythonTest310 = patterns.pythonTesting (
    { src = htutilSrc; name = "pytest-py310"; } //
    (testConfig.pythonTestConfig { pythonPkg = pkgs.python310; })
  );

  pythonTest312 = patterns.pythonTesting (
    { src = htutilSrc; name = "pytest-py312"; } //
    (testConfig.pythonTestConfig { pythonPkg = pkgs.python312; })
  );

in
pkgs.writeShellScriptBin "htutil-checks-release" ''
  set -euo pipefail
  
  echo "🚀 Running htutil release checks (linting + multi-version tests)..."
  echo ""
  
  # Run checks using the framework runner with derivation paths
  ${runner}/bin/check-runner \
    "nix-linting:${nixLinting}" \
    "nix-formatting:${nixFormatting}" \
    "python-linting:${pythonLinting}" \
    "pytest-py310:${pythonTest310}" \
    "pytest-py312:${pythonTest312}" \
    --suite-name "Release Checks"
''
