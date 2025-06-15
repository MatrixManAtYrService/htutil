# Fast checks - assembles checks from the checks framework
{ inputs, pkgs, ... }:

let
  lib = inputs.self.lib.htutil-lib pkgs;
  inherit (lib) checksLib fastCheckPatterns htutilSrc;
  inherit (checksLib) makeChecks makeCheckScript;

  # Create the fast checks using the generalized function
  fastChecks = makeChecks {
    checkPatterns = fastCheckPatterns;
    src = htutilSrc;
    # No pythonEnv needed - will be created automatically for checks that need it
  };

in
makeCheckScript {
  name = "htutil-checks-fast";
  checks = fastChecks;
  extraChecks = [];
  suiteName = "Fast Checks";
}
