# Test configuration utilities
{ inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;
  inherit (pkgs) vim fetchFromGitHub uv python3;

  # Test-specific vim package pinned for stability
  testVim = vim.overrideAttrs (_: {
    pname = "htty-test-vim";
    version = "9.1.1336";
    src = fetchFromGitHub {
      owner = "vim";
      repo = "vim";
      rev = "v9.1.1336";
      sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
    };
  });

  # Shared test configuration
  testConfig = {
    # Common dependencies for htty tests (ht binary is always required)
    baseDeps = [ uv testVim inputs.ht.packages.${system}.ht ];

    # htty-specific environment variables
    baseEnv = {
      HTTY_TEST_VIM_TARGET = "${testVim}/bin/vim";
      # Make ht binary available in PATH for tests
      PATH = "${inputs.ht.packages.${system}.ht}/bin:$PATH";
      # Point htty directly to the ht binary to avoid warnings
      HTTY_HT_BIN = "${inputs.ht.packages.${system}.ht}/bin/ht";
    };

    # Helper to create Python test config with specific Python version
    pythonTestConfig = { pythonPkg ? python3 }: {
      extraDeps = [ uv pythonPkg testVim inputs.ht.packages.${system}.ht ];
      env = {
        HTTY_TEST_VIM_TARGET = "${testVim}/bin/vim";
        PATH = "${inputs.ht.packages.${system}.ht}/bin:$PATH";
        # Point htty directly to the ht binary to avoid warnings
        HTTY_HT_BIN = "${inputs.ht.packages.${system}.ht}/bin/ht";
      } // (if pythonPkg != python3 then {
        UV_PYTHON = "${pythonPkg}/bin/python";
      } else { });
    };
  };

in
{
  inherit testVim testConfig;
}
