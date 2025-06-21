# Release checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checks releaseChecks;
in
checks.runner ({
  name = "htty-checklist-release";
  suiteName = "Release Checks";
} // releaseChecks)
