# Python package utilities
{ inputs, ... }:

pkgs:
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

in
{
  inherit pythonSet workspace;
} 