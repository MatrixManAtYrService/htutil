# Check definitions and utilities
{ inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) patterns;

  # Define which checks to include in fast checks - direct pattern references
  fastCheckPatterns = {
    inherit (patterns) deadnix statix nixpkgs-fmt ruff-check ruff-format pyright;
  };

  # Define which checks to include in full checks - fast checks plus pytest
  fullCheckPatterns = fastCheckPatterns // {
    inherit (patterns) pytest;
  };

  # Define which checks to include in release checks - full checks plus release-specific patterns
  releaseCheckPatterns = fullCheckPatterns // {
    inherit (patterns) fawltydeps release-tests python-version-test;
  };

in
{
  # Re-export the checks library for consumers
  inherit checksLib;
  
  # Source directory for all checks
  htutilSrc = ../.;
  
  # Export the check patterns for use in check files
  inherit fastCheckPatterns fullCheckPatterns releaseCheckPatterns;
} 