# Individual check components that can be built separately
{ pkgs, inputs, system, ... }:

let
  # Pin vim to specific version for test stability
  htutil_test_vim_target = pkgs.vim.overrideAttrs (_: {
    version = "9.1.1336";
    src = pkgs.fetchFromGitHub {
      owner = "vim";
      repo = "vim";
      rev = "v9.1.1336";
      sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
    };
  });

  commonEnv = ''
    export HOME=$(mktemp -d)
    export HTUTIL_TEST_VIM_TARGET="${htutil_test_vim_target}/bin/vim"
  '';

  # Create a check component that outputs a clear result
  makeCheck = name: description: inputs: script: pkgs.stdenv.mkDerivation {
    name = "check-${name}";
    src = ./..;
    buildInputs = inputs;

    buildPhase = ''
      ${commonEnv}
      
      echo "======================================"
      echo "🔍 ${description}"
      echo "======================================"
      echo ""
      
      set -e  # Exit on any error
      
      ${script}
      
      echo ""
      echo "✅ ${description} - PASSED"
      echo "======================================"
    '';

    installPhase = ''
      mkdir -p $out
      echo "${description} - PASSED" > $out/result
      echo "${name}" > $out/check-name
      echo "${description}" > $out/description
    '';
  };

in

{
  inherit makeCheck;

  # Individual check definitions
  nixfmt = makeCheck "nixfmt" "Nix file formatting"
    (with pkgs; [ nixpkgs-fmt ])
    ''
      echo "Checking Nix file formatting with nixpkgs-fmt..."
      find . -name "*.nix" -not -path "./.git/*" -exec nixpkgs-fmt --check {} \;
    '';

  ruff-check = makeCheck "ruff-check" "Python linting (ruff check)"
    (with pkgs; [ ruff python3 ])
    ''
      echo "Running ruff check on Python files..."
      if find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | grep -q .; then
        find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -print0 | xargs -0 ruff check
      else
        echo "No Python files found to check"
      fi
    '';

  ruff-format = makeCheck "ruff-format" "Python formatting (ruff format)"
    (with pkgs; [ ruff python3 ])
    ''
      echo "Checking Python file formatting with ruff..."
      if find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | grep -q .; then
        find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -print0 | xargs -0 ruff format --check
      else
        echo "No Python files found to check"
      fi
    '';

  pytest-single = makeCheck "pytest-single" "Python tests (single version)"
    (with pkgs; [ uv python3 ] ++ [ inputs.ht.packages.${system}.ht ])
    ''
      echo "Running pytest with default Python version..."
      echo "Python version: $(python --version)"
      uv run pytest -v
    '';

  pytest-py310 = makeCheck "pytest-py310" "Python tests (Python 3.10)"
    (with pkgs; [ uv python310 ] ++ [ inputs.ht.packages.${system}.ht ])
    ''
      echo "Running pytest with Python 3.10..."
      export UV_PYTHON="${pkgs.python310}/bin/python"
      ${pkgs.python310}/bin/python --version
      uv run --python "${pkgs.python310}/bin/python" pytest -v
    '';

  pytest-py312 = makeCheck "pytest-py312" "Python tests (Python 3.12)"
    (with pkgs; [ uv python312 ] ++ [ inputs.ht.packages.${system}.ht ])
    ''
      echo "Running pytest with Python 3.12..."
      export UV_PYTHON="${pkgs.python312}/bin/python"
      ${pkgs.python312}/bin/python --version
      uv run --python "${pkgs.python312}/bin/python" pytest -v
    '';

  # Nix linting check using deadnix to detect unused code
  nil-check = makeCheck "nil-check" "Nix linting (deadnix)"
    (with pkgs; [ deadnix ])
    ''
      echo "Running deadnix to detect unused Nix code..."
      
      # Find all .nix files in the project
      nix_files=$(find . -name "*.nix" -not -path "./.*" -not -path "./result*" | sort)
      
      if [ -z "$nix_files" ]; then
        echo "No .nix files found to check"
        exit 0
      fi
      
      echo "Checking $(echo "$nix_files" | wc -l) Nix files:"
      echo "$nix_files" | sed 's/^/  /'
      echo ""
      
      # Run deadnix on all files
      exit_code=0
      
      # deadnix returns exit code 1 if it finds issues
      if ! deadnix_output=$(deadnix $nix_files 2>&1); then
        echo "❌ Found unused/dead Nix code:"
        echo "$deadnix_output" | sed 's/^/  /'
        exit_code=1
      else
        echo "✅ No unused code detected by deadnix"
      fi
      
      # Also run basic syntax checks
      for file in $nix_files; do
        if ! nix-instantiate --parse "$file" >/dev/null 2>&1; then
          echo "❌ Syntax error in $file:"
          nix-instantiate --parse "$file" 2>&1 | sed 's/^/  /'
          exit_code=1
        fi
      done
      
      if [ $exit_code -eq 0 ]; then
        echo ""
        echo "✅ All Nix files passed linting checks"
      else
        echo ""
        echo "❌ Some Nix files have linting issues"
        exit 1
      fi
    '';
}
