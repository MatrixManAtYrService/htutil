# Full checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checksLib fullChecks;
in
checksLib.makeCheckScript ({
  name = "htutil-checklist-full";
  suiteName = "Full Checks";
} // fullChecks)
