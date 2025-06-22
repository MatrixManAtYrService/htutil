# Distribution checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checks distributionChecks;
in
checks.runner ({
  name = "htty-checklist-dist";
  suiteName = "Distribution Checks";
} // distributionChecks)
