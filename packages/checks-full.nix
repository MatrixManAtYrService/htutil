# Full checks - includes fast checks plus unit tests
{ inputs, pkgs, perSystem, ... }:

let
  lib = inputs.self.lib.htutil-lib pkgs;
  inherit (lib) pythonSet workspace testConfig checksLib fullCheckPatterns htutilSrc;
  inherit (checksLib) makeChecks makeCheckScript;

  # Create Python environment with dev dependencies using uv2nix properly
  htutilPythonEnvWithDev = pythonSet.mkVirtualEnv "htutil-dev-env" workspace.deps.all;

  # Create the full checks (fast checks + pytest) with the dev Python environment
  fullChecks = makeChecks {
    checkPatterns = fullCheckPatterns;
    src = htutilSrc;
    pythonEnv = htutilPythonEnvWithDev;
    inherit testConfig; # Pass testConfig for pytest
  };

in
makeCheckScript {
  name = "htutil-checks-full";
  checks = fullChecks;
  extraChecks = [];
  suiteName = "Full Checks";
}
