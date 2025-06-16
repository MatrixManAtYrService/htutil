# Release checklist
{ flake, pkgs, ... }:

let
  lib = flake.lib pkgs;
  inherit (lib.checks) checksLib releaseChecks;
in
checksLib.makeCheckScript ({
  name = "htutil-checklist-release";
  suiteName = "Release Checks";
} // releaseChecks)
