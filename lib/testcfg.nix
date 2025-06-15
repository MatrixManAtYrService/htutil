# Test configuration utilities
{ inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Test-specific vim package pinned for stability
  testVim = pkgs.vim.overrideAttrs (_: {
    pname = "htutil-test-vim";
    version = "9.1.1336";
    src = pkgs.fetchFromGitHub {
      owner = "vim";
      repo = "vim";
      rev = "v9.1.1336";
      sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
    };
  });

  # Shared test configuration
  testConfig = {
    # Common dependencies for htutil tests (ht binary is always required)
    baseDeps = with pkgs; [ uv testVim inputs.ht.packages.${system}.ht ];

    # htutil-specific environment variables
    baseEnv = {
      HTUTIL_TEST_VIM_TARGET = "${testVim}/bin/vim";
      # Make ht binary available in PATH for tests
      PATH = "${inputs.ht.packages.${system}.ht}/bin:$PATH";
    };

    # Helper to create Python test config with specific Python version
    pythonTestConfig = { pythonPkg ? pkgs.python3, name ? "python-testing" }: {
      extraDeps = with pkgs; [ uv pythonPkg testVim inputs.ht.packages.${system}.ht ];
      env = {
        HTUTIL_TEST_VIM_TARGET = "${testVim}/bin/vim";
        PATH = "${inputs.ht.packages.${system}.ht}/bin:$PATH";
      } // (if pythonPkg != pkgs.python3 then {
        UV_PYTHON = "${pythonPkg}/bin/python";
      } else { });
    };
  };

in
{
  inherit testVim testConfig;
} 