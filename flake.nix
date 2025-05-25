{
  description = "A scenario that fastAPspy can fix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };

    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    ht = {
      url = "path:/Users/matt/src/ht";
    };
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.git-hooks.flakeModule
      ];
      
      systems = [ 
        "x86_64-linux" 
        "aarch64-linux" 
        "x86_64-darwin" 
        "aarch64-darwin" 
      ];
      
      perSystem = { config, self', inputs', system, pkgs, ... }: 
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
        {
          devShells.default = pkgs.mkShell {
            buildInputs = with pkgs; [
              nodejs
              ruff
              python312Packages.python-lsp-ruff
              pyright
              nixpkgs-fmt
              python312
              uv
              inputs.ht.packages.${system}.ht
            ];

            shellHook = ''
              export HTUTIL_TEST_VIM_TARGET="${htutil_test_vim_target}/bin/vim"
            '';
          };

          # Configure pre-commit hooks
          pre-commit = {
            check.enable = true;
            settings = {
              hooks = {
                # Enable ruff for Python linting and formatting
                ruff.enable = true;
                ruff-format.enable = true;
                
                # Additional useful hooks
                nixpkgs-fmt.enable = true;
              };
            };
          };
        };
      
      flake = {
        # Any flake-level attributes can go here
      };
    };
}
