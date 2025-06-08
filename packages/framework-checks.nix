# Simple integration with checks framework
{ inputs, pkgs, system }:

let
  # Get the checks framework
  checksFramework = inputs.checks.packages.${system}.default;

  # Create check runners that use the framework
  mkRunner = name: description: checkSpecs:
    pkgs.writeShellScriptBin name ''
      set -euo pipefail
      
      # Use the universal check runner from framework
      exec ${checksFramework.runner}/bin/check-runner \
        --suite-name "${description}" \
        ${builtins.concatStringsSep " \\\n        " (map (spec: ''"${spec}"'') checkSpecs)}
    '';

in
{
  # Fast checks (linting only)
  checks-fast = mkRunner "checks-fast" "Fast Checks (Linting)" [
    "nix-formatting:path:/Users/matt/src/checks#default.nix-formatting"
    "nix-linting:path:/Users/matt/src/checks#default.nix-linting"
    "python-linting:path:/Users/matt/src/checks#default.python-linting"
  ];

  # Full checks (linting + tests)  
  checks-full = mkRunner "checks-full" "Full Checks (Linting + Tests)" [
    "nix-formatting:path:/Users/matt/src/checks#default.nix-formatting"
    "nix-linting:path:/Users/matt/src/checks#default.nix-linting"
    "python-linting:path:/Users/matt/src/checks#default.python-linting"
    "tests:.#check-pytest-single"
  ];

  # Also expose the framework runner directly
  check-runner = checksFramework.runner;
}
