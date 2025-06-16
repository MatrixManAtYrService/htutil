# Check definitions and utilities
{ flake, inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library
  checksLib = inputs.checks.lib pkgs;
  inherit (checksLib) patterns;

  lib = flake.lib pkgs;
  inherit (lib.pypkg) pythonEnvWithDev;
  inherit (lib.testcfg) testConfig;

  htutilWheel = flake.packages.${system}.htutil-wheel;

  src = ../../.;

  fastChecks = {
    scriptChecks = {
      deadnixCheck = patterns.deadnix { inherit src; };
      statixCheck = patterns.statix { inherit src; };
      nixpkgsFmtCheck = patterns.nixpkgs-fmt { inherit src; };
      ruffCheckCheck = patterns.ruff-check { inherit src; };
      ruffFormatCheck = patterns.ruff-format { inherit src; };
      pyrightCheck = patterns.pyright {
        inherit src;
        pythonEnv = pythonEnvWithDev;
      };
    };
    derivationChecks = { };
  };

  fullChecks = {
    inherit (fastChecks) scriptChecks;
    derivationChecks = {
      pytestTest = patterns.pytest-cached {
        inherit src;
        pythonEnv = pythonEnvWithDev;
        name = "pytest-test";
        description = "Cached unit tests (tests/ directory)";
        inherit testConfig;
        includePaths = [ "${src}/src" "${src}/tests" "${src}/pyproject.toml" ];
        testDirs = [ "${src}/tests" ];
      };
    };
  };

  releaseChecks = {
    scriptChecks = fastChecks.scriptChecks // {
      fawltydepsCheck = patterns.fawltydeps {
        inherit src;
        pythonEnv = pythonEnvWithDev;
        ignoreUndeclared = [ "htutil" ];
      };
      pdocCheck = patterns.pdoc {
        inherit src;
        pythonEnv = pythonEnvWithDev;
      };
    };
    derivationChecks = fullChecks.derivationChecks // {
      pytestRelease = patterns.pytest-cached {
        inherit src;
        pythonEnv = pythonEnvWithDev;
        name = "pytest-release";
        description = "Cached release tests (release_tests/ directory)";
        inherit testConfig;
        includePaths = [ "${src}/src" "${src}/release_tests" "${src}/pyproject.toml" ];
        testDirs = [ "${src}/release_tests" ];
        wheelPath = "${htutilWheel}/htutil-0.1.0-py3-none-any.whl";
        wheelPathEnvVar = "HTUTIL_WHEEL_PATH";
      };
    };
  };

in
{
  inherit checksLib;
  inherit fastChecks fullChecks releaseChecks;
}
