# htutil check runners using the universal checks framework
{ inputs, pkgs, system }:

let
  # Get the universal check runner from the framework
  checksFramework = inputs.checks.packages.${system}.default;

  # Create a runner that uses the framework's Python runner
  mkRunner = name: description: checkList:
    pkgs.writeShellScriptBin name ''
      set -euo pipefail
      
      # Use the checks framework runner
      runner="${checksFramework.runner}/bin/check-runner"
      
      # Build the arguments for the runner
      args=()
      ${builtins.concatStringsSep "\n" (map (check: 
        ''args+=("${check.name}:.#${check.package}")''
      ) checkList)}
      
      # Run the universal check runner
      "$runner" --suite-name "${description}" "''${args[@]}"
    '';

in
{
  fast = mkRunner "run-checks-fast" "Fast Checks (Linting)" [
    { name = "nix-formatting"; package = "check-nix-formatting"; }
    { name = "nix-linting"; package = "check-nix-linting"; }
    { name = "python-linting"; package = "check-python-linting"; }
  ];

  full = mkRunner "run-checks-full" "Full Checks (Linting + Tests)" [
    { name = "nix-formatting"; package = "check-nix-formatting"; }
    { name = "nix-linting"; package = "check-nix-linting"; }
    { name = "python-linting"; package = "check-python-linting"; }
    { name = "pytest-single"; package = "check-pytest-single"; }
  ];

  release = mkRunner "run-checks-release" "Release Checks (Linting + Multi-version Tests)" [
    { name = "nix-formatting"; package = "check-nix-formatting"; }
    { name = "nix-linting"; package = "check-nix-linting"; }
    { name = "python-linting"; package = "check-python-linting"; }
    { name = "pytest-py310"; package = "check-pytest-py310"; }
    { name = "pytest-py312"; package = "check-pytest-py312"; }
  ];
}
