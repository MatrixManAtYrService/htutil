{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  checks = import ../checks/individual.nix { inherit inputs pkgs system; };
in

checks.ruff-check
