# Fast checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checksLib fastChecks;
in
checksLib.makeCheckScript ({
  name = "htutil-checklist-fast";
  suiteName = "Fast Checks";
} // fastChecks)
