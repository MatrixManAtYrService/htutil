{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

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

in
pkgs.stdenv.mkDerivation {
  name = "htutil-pytest-simple";
  src = ./..;

  buildInputs = with pkgs; [
    uv
    python3
    inputs.ht.packages.${system}.ht
  ];

  buildPhase = ''
    export HOME=$(mktemp -d)
    export HTUTIL_TEST_VIM_TARGET="${htutil_test_vim_target}/bin/vim"
    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8
    export PYTHONIOENCODING=utf-8
    
    echo "🧪 Running Python tests..."
    echo "Python version: $(python --version)"
    echo "Home: $HOME"
    
    # Run the tests
    uv run pytest -v
  '';

  installPhase = ''
    mkdir -p $out
    echo "pytest-simple completed successfully" > $out/result
  '';
}
