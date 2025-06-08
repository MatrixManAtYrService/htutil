{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  checks = import ../checks/htutil-checks.nix { inherit inputs pkgs system; };
in

checks.pytest-single
