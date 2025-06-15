{ inputs, pkgs, perSystem, ... }:

let
  lib = inputs.self.lib.htutil-lib pkgs;
  inherit (lib) pythonSet workspace testConfig checksLib releaseCheckPatterns htutilSrc;
  inherit (checksLib) makeChecks makeCheckScript;

  # Create Python environment with dev dependencies using uv2nix properly
  htutilPythonEnvWithDev = pythonSet.mkVirtualEnv "htutil-dev-env" workspace.deps.all;

  # Build the wheel using htutil-wheel package from perSystem
  htutilWheel = perSystem.self.htutil-wheel;

  # Create all release checks using the patterns
  releaseChecks = makeChecks {
    checkPatterns = releaseCheckPatterns;
    src = htutilSrc;
    pythonEnv = htutilPythonEnvWithDev;
    inherit testConfig; # Pass testConfig for pytest
    ignoreUndeclared = [ "htutil" ]; # Ignore self-import for fawltydeps
    # Additional parameters for release-specific checks
    wheel = htutilWheel; # For release-tests pattern
    wheelPathEnvVar = "HTUTIL_WHEEL_PATH"; # For release-tests pattern
    pythonVersion = pkgs.python311; # For python-version-test pattern
    pythonVersionString = "3.11"; # For python-version-test pattern
  };

in
makeCheckScript {
  name = "htutil-checks-release";
  checks = releaseChecks;
  suiteName = "Release Checks";
}
