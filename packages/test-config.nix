# Shared test configuration for htutil checks
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Import test-vim dependency
  testVim = pkgs.callPackage ./test-vim.nix { };

in
{
  # Common dependencies for htutil tests
  baseDeps = with pkgs; [ uv inputs.ht.packages.${system}.ht testVim ];

  # htutil-specific environment variables
  baseEnv = {
    HTUTIL_TEST_VIM_TARGET = "${testVim}/bin/vim";
  };

  # Helper to create Python test config with specific Python version
  pythonTestConfig = { pythonPkg ? pkgs.python3, name ? "python-testing" }: {
    extraDeps = with pkgs; [ uv pythonPkg inputs.ht.packages.${system}.ht testVim ];
    env = {
      HTUTIL_TEST_VIM_TARGET = "${testVim}/bin/vim";
    } // (if pythonPkg != pkgs.python3 then {
      UV_PYTHON = "${pythonPkg}/bin/python";
    } else { });
  };
}
