# Temporary htutil-specific checks while the checks framework is being improved
{ inputs, pkgs, system, ... }:

let
  # htutil-specific dependencies that need to be injected into checks
  htutil-test-vim = pkgs.vim.overrideAttrs (_: {
    version = "9.1.1336";
    src = pkgs.fetchFromGitHub {
      owner = "vim";
      repo = "vim";
      rev = "v9.1.1336";
      sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
    };
  });

  # htutil-specific environment that should be injectable
  htutil-test-env = ''
    export HOME=$(mktemp -d)
    export HTUTIL_TEST_VIM_TARGET="${htutil-test-vim}/bin/vim"
    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8
    export PYTHONIOENCODING=utf-8
  '';

  # Generic check builder (this should eventually come from checks framework)
  makeDirectCheck = name: description: dependencies: script: pkgs.stdenv.mkDerivation {
    name = "htutil-check-${name}";
    src = ./..;
    buildInputs = dependencies;

    buildPhase = ''
      ${htutil-test-env}
      
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
  # Simple, direct pytest implementations
  # These will be easy to migrate once checks framework supports dependency injection

  pytest-single = makeDirectCheck
    "pytest-single"
    "Python tests (single version)"
    (with pkgs; [ uv python3 python3Packages.pytest ] ++ [ inputs.ht.packages.${system}.ht htutil-test-vim ])
    ''
      echo "Running pytest with default Python version..."
      echo "Python version: $(python --version)"
      echo "Vim version: $(vim --version | head -1)"
      
      # Install project in development mode
      uv sync
      
      # Run tests directly
      python -m pytest -v
    '';

  pytest-py310 = makeDirectCheck
    "pytest-py310"
    "Python tests (Python 3.10)"
    (with pkgs; [ uv python310 python310Packages.pytest ] ++ [ inputs.ht.packages.${system}.ht htutil-test-vim ])
    ''
      echo "Running pytest with Python 3.10..."
      export UV_PYTHON="${pkgs.python310}/bin/python"
      ${pkgs.python310}/bin/python --version
      echo "Vim version: $(vim --version | head -1)"
      
      # Install project in development mode  
      uv sync --python "${pkgs.python310}/bin/python"
      
      # Run tests directly
      ${pkgs.python310}/bin/python -m pytest -v
    '';

  pytest-py312 = makeDirectCheck
    "pytest-py312"
    "Python tests (Python 3.12)"
    (with pkgs; [ uv python312 python312Packages.pytest ] ++ [ inputs.ht.packages.${system}.ht htutil-test-vim ])
    ''
      echo "Running pytest with Python 3.12..."
      export UV_PYTHON="${pkgs.python312}/bin/python"
      ${pkgs.python312}/bin/python --version
      echo "Vim version: $(vim --version | head -1)"
      
      # Install project in development mode
      uv sync --python "${pkgs.python312}/bin/python"
      
      # Run tests directly  
      ${pkgs.python312}/bin/python -m pytest -v
    '';

  # Note: Formatting and linting checks should come from the framework
  # For now, we'll implement them directly too

  ruff-check = makeDirectCheck
    "ruff-check"
    "Python linting (ruff check)"
    (with pkgs; [ ruff python3 ])
    ''
      echo "Running ruff check on Python files..."
      if find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | grep -q .; then
        find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -print0 | xargs -0 ruff check
      else
        echo "No Python files found to check"
      fi
    '';

  ruff-format = makeDirectCheck
    "ruff-format"
    "Python formatting (ruff format)"
    (with pkgs; [ ruff python3 ])
    ''
      echo "Checking Python file formatting with ruff..."
      if find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | grep -q .; then
        find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" -print0 | xargs -0 ruff format --check
      else
        echo "No Python files found to check"
      fi
    '';

  nixfmt = makeDirectCheck
    "nixfmt"
    "Nix file formatting"
    (with pkgs; [ nixpkgs-fmt ])
    ''
      echo "Checking Nix file formatting with nixpkgs-fmt..."
      find . -name "*.nix" -not -path "./.git/*" -exec nixpkgs-fmt --check {} \;
    '';
}
