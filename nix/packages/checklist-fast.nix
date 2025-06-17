# Fast checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checks fastChecks;
in
checks.runner ({
  name = "htutil-checklist-fast";
  suiteName = "Fast Checks";
} // fastChecks)
