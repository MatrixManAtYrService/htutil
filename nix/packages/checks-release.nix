# Release checks
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checksLib releaseChecks;
in
checksLib.makeCheckScript ({
  name = "htutil-checks-release";
  suiteName = "Release Checks";
} // releaseChecks)
