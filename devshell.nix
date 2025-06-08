{ pkgs, inputs, system, ... }:

let
  # Pin vim to specific version for test stability
  htutil_test_vim_target = pkgs.vim.overrideAttrs (oldAttrs: {
    version = "9.1.1336";
    src = pkgs.fetchFromGitHub {
      owner = "vim";
      repo = "vim";
      rev = "v9.1.1336";
      sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
    };
  });
in

pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs
    ruff
    python3.pkgs.python-lsp-ruff
    pyright
    nixpkgs-fmt
    python3
    uv
    pre-commit
    inputs.ht.packages.${system}.ht
  ];

  shellHook = ''
    export HTUTIL_TEST_VIM_TARGET="${htutil_test_vim_target}/bin/vim"
  '';
}
