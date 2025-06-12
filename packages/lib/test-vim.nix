# Test-specific vim package pinned for stability
{ pkgs }:

pkgs.vim.overrideAttrs (_: {
  pname = "htutil-test-vim";
  version = "9.1.1336";
  src = pkgs.fetchFromGitHub {
    owner = "vim";
    repo = "vim";
    rev = "v9.1.1336";
    sha256 = "sha256-fF1qRPdVzQiYH/R0PSmKR/zFVVuCtT6lPN1x1Th5SgA=";
  };
})
