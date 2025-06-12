{ inputs, pkgs, ... }:

let
  # Helper function to build htutil for a specific Python version
  buildHtutilForPython = python: python.pkgs.buildPythonPackage {
    pname = "htutil";
    version = "0.1.0";

    src = ../.;
    format = "pyproject";

    nativeBuildInputs = with python.pkgs; [
      hatchling
      # Don't use 'build' package to avoid sphinx dependency issues
    ];

    propagatedBuildInputs = with python.pkgs; [
      ansi2html
      typer
      rich
    ];

    # Don't run tests during build - we'll test the installed package separately
    doCheck = false;

    # Use standard Python package building
    # The wheel will be available in the Nix store

    meta = with pkgs.lib; {
      description = "A python wrapper around ht (a headless terminal utility)";
      license = licenses.mit;
    };

    # The built package is available directly
  };

in
# Default to Python 3.11
buildHtutilForPython pkgs.python311
