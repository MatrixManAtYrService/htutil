{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  directChecks = import ../checks/direct-checks.nix { inherit inputs pkgs system; };
in

directChecks.pytest-single
