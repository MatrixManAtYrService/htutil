{ inputs, pkgs, ... }:

let
  htutilPackages = import ./lib/htutil-packages.nix { inherit inputs pkgs; };
in
htutilPackages.default 