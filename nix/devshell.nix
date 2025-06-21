{ pkgs, inputs, system, ... }:

let
  # Get test vim from lib using Blueprint pattern
  lib = inputs.self.lib pkgs;
  inherit (lib.testcfg) testVim;
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    cargo
    ruff
    python3.pkgs.python-lsp-ruff
    pyright
    nixpkgs-fmt
    nil
    nixd
    deadnix
    statix
    python3
    uv
    inputs.ht.packages.${system}.ht
  ];

  shellHook = ''
    export htty_TEST_VIM_TARGET="${testVim}/bin/vim"
    export htty_HT_BIN="${inputs.ht.packages.${system}.ht}/bin/ht"
  '';
}
