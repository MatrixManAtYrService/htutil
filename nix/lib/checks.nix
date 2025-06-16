# Check definitions and utilities
{ flake, inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the check definitions library
  checks = inputs.checkdef.lib pkgs;

  lib = flake.lib pkgs;
  inherit (lib.pypkg) pythonEnvWithDev;
  inherit (lib.testcfg) testConfig;

  htutilWheel = flake.packages.${system}.htutil-wheel;

  src = ../../.;

  fastChecks = {
    scriptChecks = {
      deadnixCheck = checks.deadnix { inherit src; };
      statixCheck = checks.statix { inherit src; };
      nixpkgsFmtCheck = checks.nixpkgs-fmt { inherit src; };
      ruffCheckCheck = checks.ruff-check { inherit src; };
      ruffFormatCheck = checks.ruff-format { inherit src; };
      trimWhitespaceCheck = checks.trim-whitespace {
        inherit src;
        filePatterns = [ "*.py" "*.nix" "*.md" "*.txt" "*.yml" "*.yaml" ];
      };
      pyrightCheck = checks.pyright {
        inherit src;
        pythonEnv = pythonEnvWithDev;
      };
    };
    derivationChecks = { };
  };

  fullChecks = {
    inherit (fastChecks) scriptChecks;
    derivationChecks = {
      pytestTest = checks.pytest-cached {
        inherit src;
        pythonEnv = pythonEnvWithDev;
        name = "pytest-test";
        description = "Cached unit tests (tests/ directory)";
        inherit testConfig;
        includePatterns = [ "src/**" "tests/**" "pyproject.toml" ];
        testDirs = [ "${src}/tests" ];
      };
    };
  };

  releaseChecks = {
    scriptChecks = fastChecks.scriptChecks // {
      fawltydepsCheck = checks.fawltydeps {
        inherit src;
        pythonEnv = pythonEnvWithDev;
        ignoreUndeclared = [ "htutil" ];
      };
      pdocCheck = checks.pdoc {
        inherit src;
        pythonEnv = pythonEnvWithDev;
      };
    };
    derivationChecks = fullChecks.derivationChecks // {
      pytestRelease = checks.pytest-cached {
        inherit src;
        pythonEnv = pythonEnvWithDev;
        name = "pytest-release";
        description = "Cached release tests (release_tests/ directory)";
        inherit testConfig;
        includePatterns = [ "src/**" "release_tests/**" "pyproject.toml" ];
        testDirs = [ "${src}/release_tests" ];
        wheelPath = "${htutilWheel}/htutil-0.1.0-py3-none-any.whl";
        wheelPathEnvVar = "HTUTIL_WHEEL_PATH";
      };
    };
  };

in
{
  inherit checks;
  inherit fastChecks fullChecks releaseChecks;
}
