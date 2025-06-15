{ inputs, pkgs, perSystem, ... }:

let
  lib = inputs.self.lib.htutil-lib pkgs;
  inherit (lib) pythonSet workspace;

  # Get project metadata
  projectToml = builtins.fromTOML (builtins.readFile ../pyproject.toml);
  inherit (projectToml.project) version;

  # Create the htutil virtual environment
  htutilEnv = pythonSet.mkVirtualEnv "htutil-env" workspace.deps.default;

in
# Main htutil package - clean and simple
pkgs.stdenvNoCC.mkDerivation {
  pname = "htutil";
  inherit version;
  src = htutilEnv;

  buildPhase = ''
    mkdir -p $out/bin
    cp -r $src/* $out/
  '';

  meta = with pkgs.lib; {
    description = "htutil is a set of python convenience functions for the ht terminal utility, this package does not contain the ht binary.  Indicate the ht binary path via HTUTIL_HT_BINARY or use the htutil-wheel output instead (which bundles it).";
    homepage = "https://github.com/yourusername/htutil";
    license = licenses.mit;
    mainProgram = "htutil";
    platforms = platforms.unix;
  };
}
