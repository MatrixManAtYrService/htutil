# Full checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checks fullChecks;
in
checks.makeCheckScript ({
  name = "htutil-checklist-full";
  suiteName = "Full Checks";
} // fullChecks)
