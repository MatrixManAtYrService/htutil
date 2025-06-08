{ inputs, pkgs, ... }:

# The default package is htutil
import ./htutil.nix { inherit inputs pkgs; }
