# Fast checks
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checksLib fastChecks;
in
checksLib.makeCheckScript ({
  name = "htutil-checks-fast";
  suiteName = "Fast Checks";
} // fastChecks)
