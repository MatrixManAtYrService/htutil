{ inputs, pkgs, system }:

let
  # Import individual checks
  checks = import ./individual.nix { inherit inputs pkgs system; };

  # Create a runner script that uses our Python check runner
  mkRunner = name: description: checkList:
    pkgs.writeShellScriptBin name ''
      set -euo pipefail
      
      # Add uv to the PATH
      export PATH="${pkgs.uv}/bin:$PATH"
      
      # Find the project root directory
      PROJECT_ROOT="$(pwd)"
      
      # Look for check_runner.py in common locations
      if [ -f "$PROJECT_ROOT/check_runner.py" ]; then
        RUNNER_SCRIPT="$PROJECT_ROOT/check_runner.py"
      elif [ -f "$(dirname "$(readlink -f "$0")")/../check_runner.py" ]; then
        RUNNER_SCRIPT="$(dirname "$(readlink -f "$0")")/../check_runner.py"
      else
        echo "Error: Could not find check_runner.py"
        exit 1
      fi
      
      # Build the arguments for the Python runner
      args=()
      ${builtins.concatStringsSep "\n" (map (check: 
        ''args+=("${check.name}:.#${check.package}")''
      ) checkList)}
      
      # Run the Python check runner using uv
      cd "$PROJECT_ROOT"
      uv run python "$RUNNER_SCRIPT" --suite-name "${description}" "''${args[@]}"
    '';

in
{
  fast = mkRunner "run-checks-fast" "Fast Checks (Linting)" [
    { name = "nixfmt"; package = "check-nixfmt"; }
    { name = "ruff-check"; package = "check-ruff-check"; }
    { name = "ruff-format"; package = "check-ruff-format"; }
  ];

  full = mkRunner "run-checks-full" "Full Checks (Linting + Tests)" [
    { name = "nixfmt"; package = "check-nixfmt"; }
    { name = "ruff-check"; package = "check-ruff-check"; }
    { name = "ruff-format"; package = "check-ruff-format"; }
    { name = "pytest-single"; package = "check-pytest-single"; }
  ];

  release = mkRunner "run-checks-release" "Release Checks (Linting + Multi-version Tests)" [
    { name = "nixfmt"; package = "check-nixfmt"; }
    { name = "ruff-check"; package = "check-ruff-check"; }
    { name = "ruff-format"; package = "check-ruff-format"; }
    { name = "pytest-py310"; package = "check-pytest-py310"; }
    { name = "pytest-py312"; package = "check-pytest-py312"; }
  ];
}
