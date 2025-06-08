{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  runners = import ../checks/runners.nix { inherit inputs pkgs system; };
in

runners.fast
