# htutil checks using the enhanced checks framework with dependency injection
{ inputs, pkgs, system, ... }:

let
  # Import the enhanced checks framework
  checksFramework = inputs.checks.packages.${system}.default;

  # htutil-specific dependencies that need to be injected
  htutil-test-vim = pkgs.vim.overrideAttrs (_: {
    version = "9.1.1336";
    src = pkgs.fetchFromGitHub {
      owner = "vim";
      repo = "vim";
      rev = "v9.1.1336";
      sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
    };
  });

  # Create project-specific checks using the enhanced interface
  htutilChecks = checksFramework.makeProjectChecks {
    # Project dependencies available to all checks
    projectDeps = {
      vim = htutil-test-vim;
      ht = inputs.ht.packages.${system}.ht;
      python310 = pkgs.python310;
      python312 = pkgs.python312;
      uv = pkgs.uv;
    };

    # Project environment available to all checks
    projectEnv = {
      HTUTIL_TEST_VIM_TARGET = "@vim@/bin/vim";
      HOME = "$(mktemp -d)"; # Note: This will be evaluated at runtime
      LANG = "en_US.UTF-8";
      LC_ALL = "en_US.UTF-8";
      PYTHONIOENCODING = "utf-8";
    };

    # Individual check definitions
    checks = {
      pytest-single = {
        description = "Python tests (single version)";
        dependencies = with pkgs; [ python3 python3Packages.pytest ];
        script = ''
          echo "Running pytest with default Python version..."
          echo "Python version: $(python --version)"
          echo "Vim version: $(@vim@/bin/vim --version | head -1)"
          echo "Using vim target: $HTUTIL_TEST_VIM_TARGET"
          echo "HT version: $(@ht@/bin/ht --version)"
          echo ""
          
          # Install project in development mode
          @uv@/bin/uv sync
          
          # Run tests
          python -m pytest -v
        '';
      };

      pytest-py310 = {
        description = "Python tests (Python 3.10)";
        dependencies = with pkgs; [ python310Packages.pytest ];
        environment = {
          UV_PYTHON = "@python310@/bin/python";
        };
        script = ''
          echo "Running pytest with Python 3.10..."
          echo "Python version: $(@python310@/bin/python --version)"
          echo "Vim version: $(@vim@/bin/vim --version | head -1)"
          echo "Using vim target: $HTUTIL_TEST_VIM_TARGET"
          echo ""
          
          # Install project with specific Python version
          @uv@/bin/uv sync --python "@python310@/bin/python"
          
          # Run tests with specific Python version
          @python310@/bin/python -m pytest -v
        '';
      };

      pytest-py312 = {
        description = "Python tests (Python 3.12)";
        dependencies = with pkgs; [ python312Packages.pytest ];
        environment = {
          UV_PYTHON = "@python312@/bin/python";
        };
        script = ''
          echo "Running pytest with Python 3.12..."
          echo "Python version: $(@python312@/bin/python --version)"
          echo "Vim version: $(@vim@/bin/vim --version | head -1)"
          echo "Using vim target: $HTUTIL_TEST_VIM_TARGET"
          echo ""
          
          # Install project with specific Python version
          @uv@/bin/uv sync --python "@python312@/bin/python"
          
          # Run tests with specific Python version
          @python312@/bin/python -m pytest -v
        '';
      };
    };
  };

in
{
  # Use framework's standard checks (these work out of the box)
  inherit (checksFramework) nix-linting nix-formatting python-linting;

  # Add htutil-specific checks with dependency injection
  inherit (htutilChecks) pytest-single pytest-py310 pytest-py312;
}
