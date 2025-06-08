{ inputs, pkgs, python ? pkgs.python310, ... }:

let
  # Allow overriding the Python version, default to 3.10 (closest to 3.9 in regular nixpkgs)
  # For Python 3.9, users can override with: inputs.nixpkgs-python.packages.${pkgs.system}."3.9"

  # Build htutil using the specified Python version
  htutil = python.pkgs.buildPythonApplication {
    pname = "htutil";
    version = "0.1.0";

    src = ../.;
    format = "pyproject";

    nativeBuildInputs = with python.pkgs; [
      hatchling
    ];

    propagatedBuildInputs = with python.pkgs; [
      ansi2html
      typer
    ];

    # Don't run tests during build
    doCheck = false;

    meta = with pkgs.lib; {
      description = "A python wrapper around ht (a headless terminal utility)";
      license = licenses.mit;
    };
  };

in
# Create a wrapper that includes ht in PATH
pkgs.symlinkJoin {
  name = "htutil-with-ht";
  paths = [ htutil ];
  buildInputs = [ pkgs.makeWrapper ];
  postBuild = ''
    wrapProgram $out/bin/htutil \
      --prefix PATH : ${inputs.ht.packages.${pkgs.system}.ht}/bin
  '';
}
