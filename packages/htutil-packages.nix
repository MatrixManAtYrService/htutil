{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Import internal utilities
  internal = import ./lib/internal.nix { inherit inputs pkgs; };
  inherit (internal) pythonSet workspace;

  # Get the htutil package
  inherit (pythonSet) htutil;

  # Create a Python environment with htutil and all its dependencies
  pythonEnv = pythonSet.mkVirtualEnv "htutil-env" workspace.deps.default;

in
{
  # Export only derivations for packages output - use htutil as default for now
  default = htutil;
  inherit htutil;
}
