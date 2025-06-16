# Full checks
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checksLib fullChecks;
in
checksLib.makeCheckScript ({
  name = "htutil-checks-full";
  suiteName = "Full Checks";
} // fullChecks)
