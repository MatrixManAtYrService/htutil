{ pkgs, inputs, system, ... }:

let
  # Get test vim from lib using Blueprint pattern
  lib = inputs.self.lib pkgs;
  inherit (lib.testcfg) testVim;
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs
    ruff
    python3.pkgs.python-lsp-ruff
    pyright
    nixpkgs-fmt
    nil # Nix language server
    nixd # Advanced Nix language server
    deadnix # Detects dead/unused Nix code
    statix # Comprehensive Nix static analyzer (BEST coverage)
    python3
    uv
    pre-commit
    inputs.ht.packages.${system}.ht
  ];

  shellHook = ''
    export HTUTIL_TEST_VIM_TARGET="${testVim}/bin/vim"
    export HTUTIL_HT_BIN="${inputs.ht.packages.${system}.ht}/bin/ht"
  '';
}
