{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  checksFramework = inputs.checks.packages.${system}.default;
in

pkgs.writeShellScriptBin "checks-full-framework" ''
  set -euo pipefail
  
  # Use the universal check runner from framework
  exec ${checksFramework.runner}/bin/check-runner \
    --suite-name "Full Checks (Framework)" \
    "nix-formatting:path:/Users/matt/src/checks#default.nix-formatting" \
    "nix-linting:path:/Users/matt/src/checks#default.nix-linting" \
    "python-linting:path:/Users/matt/src/checks#default.python-linting" \
    "tests:.#check-pytest-single"
''
