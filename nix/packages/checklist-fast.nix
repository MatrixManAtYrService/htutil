# Fast checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checks fastChecks;
in
checks.makeCheckScript ({
  name = "htutil-checklist-fast";
  suiteName = "Fast Checks";
} // fastChecks)
