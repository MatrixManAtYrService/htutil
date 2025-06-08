{ inputs, pkgs, ... }:

let
  system = pkgs.stdenv.hostPlatform.system;
  checks = import ../checks/individual.nix { inherit inputs pkgs system; };
in

checks.pytest-py312
