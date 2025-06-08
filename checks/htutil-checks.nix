# htutil-specific checks using the universal checks framework
{ inputs, pkgs, system, ... }:

let
  # Import the checks framework
  checksFramework = inputs.checks.packages.${system}.default;

  # Use the framework's makeCheck function for htutil-specific tests
  inherit (checksFramework) makeCheck;

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
    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8
    export PYTHONIOENCODING=utf-8
  '';

in
{
  # Use framework checks directly
  inherit (checksFramework)
    nix-linting
    nix-formatting
    python-linting;

  # htutil-specific tests
  pytest-single = makeCheck "pytest-single" "Python tests (single version)"
    (with pkgs; [ uv python3 ] ++ [ inputs.ht.packages.${system}.ht ])
    ''
      ${commonEnv}
      echo "Running pytest with default Python version..."
      echo "Python version: $(python --version)"
      uv run pytest -v
    '';

  pytest-py310 = makeCheck "pytest-py310" "Python tests (Python 3.10)"
    (with pkgs; [ uv python310 ] ++ [ inputs.ht.packages.${system}.ht ])
    ''
      ${commonEnv}
      echo "Running pytest with Python 3.10..."
      export UV_PYTHON="${pkgs.python310}/bin/python"
      ${pkgs.python310}/bin/python --version
      uv run --python "${pkgs.python310}/bin/python" pytest -v
    '';

  pytest-py312 = makeCheck "pytest-py312" "Python tests (Python 3.12)"
    (with pkgs; [ uv python312 ] ++ [ inputs.ht.packages.${system}.ht ])
    ''
      ${commonEnv}
      echo "Running pytest with Python 3.12..."
      export UV_PYTHON="${pkgs.python312}/bin/python"
      ${pkgs.python312}/bin/python --version
      uv run --python "${pkgs.python312}/bin/python" pytest -v
    '';
}
