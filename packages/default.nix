{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  python = pkgs.python3;

  # Load the workspace from uv.lock
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../.;
  };

  # Create the python package set with proper overlays
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    inherit python;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      (workspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
    ]
  );

  # Get the htutil package
  inherit (pythonSet) htutil;

  # Create a Python environment with htutil and all its dependencies
  pythonEnv = pythonSet.mkVirtualEnv "htutil-env" workspace.deps.default;

  # Create a wrapper that includes ht in PATH
  htutilWithHt = pkgs.symlinkJoin {
    name = "htutil-with-ht";
    paths = [ htutil ];
    buildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      wrapProgram $out/bin/htutil \
        --prefix PATH : ${inputs.ht.packages.${system}.ht}/bin
    '';
  };

in
{
  # Export both the wrapped package and the Python environment
  default = htutilWithHt;
  inherit pythonEnv htutil pythonSet;
  htutil-with-ht = htutilWithHt;
}
