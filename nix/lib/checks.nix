# Check definitions and utilities
{ flake, inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the check definitions library
  checks = inputs.checkdef.lib pkgs;

  lib = flake.lib pkgs;
  inherit (lib.pypkg) pythonSet workspace;
  inherit (lib.testcfg) testConfig;

  htutilWheel = flake.packages.${system}.htutil-wheel;

  src = ../../.;

  # Extract version from pyproject.toml
  pyproject = builtins.fromTOML (builtins.readFile (src + "/pyproject.toml"));
  inherit (pyproject.project) version;

  # Define the Python environment builder function once
  # This function takes filtered source and builds the Python environment
  buildPythonEnv = filteredSrc:
    let
      # Load workspace from the filtered source
      filteredWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
        workspaceRoot = filteredSrc;
      };
      # Create python package set with proper overlays
      pythonSetFiltered = (pkgs.callPackage inputs.pyproject-nix.build.packages {
        python = pkgs.python3;
      }).overrideScope (
        pkgs.lib.composeManyExtensions [
          inputs.pyproject-build-systems.overlays.default
          (filteredWorkspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
        ]
      );
    in
    pythonSetFiltered.mkVirtualEnv "htutil-dev-env" filteredWorkspace.deps.all;

  fastChecks = {
    scriptChecks = {
      deadnixCheck = checks.deadnix { inherit src; };
      statixCheck = checks.statix { inherit src; };
      nixpkgsFmtCheck = checks.nixpkgs-fmt { inherit src; };
      ruffCheckCheck = checks.ruff-check { inherit src; };
      ruffFormatCheck = checks.ruff-format { inherit src; };
      trimWhitespaceCheck = checks.trim-whitespace {
        src = ./.;
        filePatterns = [ "*.py" "*.nix" "*.md" "*.txt" "*.yml" "*.yaml" ];
      };
      pyrightCheck = checks.pyright {
        inherit src;
        pythonEnv = pythonSet.mkVirtualEnv "htutil-pyright-env" workspace.deps.all;
      };
    };
    derivationChecks = { };
  };

  fullChecks = {
    inherit (fastChecks) scriptChecks;
    derivationChecks = {
      pytestTest = checks.pytest-env-builder {
        inherit src;
        envBuilder = buildPythonEnv;
        name = "pytest-test";
        description = "Cached unit tests (tests/ directory)";
        inherit testConfig;
        includePatterns = [ "src/**" "tests/**" "README.md" ];
        tests = [ "${src}/tests" ];
      };
    };
  };

  releaseChecks = {
    scriptChecks = fastChecks.scriptChecks // {
      fawltydepsCheck = checks.fawltydeps {
        inherit src;
        pythonEnv = pythonSet.mkVirtualEnv "htutil-fawltydeps-env" workspace.deps.all;
        ignoreUndeclared = [ "htutil" "pdoc" "pyright" ];
      };
      pdocCheck = checks.pdoc {
        inherit src;
        pythonEnv = pythonSet.mkVirtualEnv "htutil-pdoc-env" workspace.deps.all;
      };
    };
    derivationChecks = fullChecks.derivationChecks // {
      pytestRelease = checks.pytest-env-builder {
        inherit src;
        envBuilder = buildPythonEnv;
        name = "pytest-release";
        description = "Cached release tests (release_tests/ directory)";
        inherit testConfig;
        includePatterns = [ "src/**" "release_tests/**" "README.md" ];
        tests = [ "${src}/release_tests" ];
        wheelPath = "${htutilWheel}/htutil-${version}-py3-none-any.whl";
        wheelPathEnvVar = "HTUTIL_WHEEL_PATH";
      };
    };
  };

in
{
  inherit checks;
  inherit fastChecks fullChecks releaseChecks;
}
