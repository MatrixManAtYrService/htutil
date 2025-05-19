{
  description = "A scenario that fastAPspy can fix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    flake-utils.url = "github:numtide/flake-utils";

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

  outputs = { self, nixpkgs, flake-utils, uv2nix, pyproject-nix, pyproject-build-systems, ht }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        python = pkgs.python312;
        workspace = uv2nix.lib.workspace.loadWorkspace { 
          workspaceRoot = ./.;
        };

        pythonSet = (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope (
          nixpkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            workspace.mkPyprojectOverlay { sourcePreference = "wheel"; }
          ]
        );

        pythonEnv = pythonSet.mkVirtualEnv "procose" workspace.deps.default;
      in
      {
        packages = {
          default = pythonEnv;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            nodejs
            ruff
            python312Packages.python-lsp-ruff
            pyright
            nixpkgs-fmt
            python312
            uv
            # Add the ht binary from the ht flake
            ht.packages.${system}.ht
          ];
        };
      });
}
