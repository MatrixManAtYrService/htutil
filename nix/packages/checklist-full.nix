# Full checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checks fullChecks;
in
checks.runner ({
  name = "htutil-checklist-full";
  suiteName = "Full Checks";
} // fullChecks)
