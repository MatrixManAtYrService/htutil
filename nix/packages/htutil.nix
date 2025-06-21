{ inputs, pkgs, ... }:

let
  lib = inputs.self.lib pkgs;
  inherit (lib.pypkg) pythonSet workspace;

  # Get project metadata
  projectToml = builtins.fromTOML (builtins.readFile ../../pyproject.toml);
  inherit (projectToml.project) version;

  # Create the htty virtual environment
  httyEnv = pythonSet.mkVirtualEnv "htty-env" workspace.deps.default;

in
# Main htty package - clean and simple
pkgs.stdenvNoCC.mkDerivation {
  pname = "htty";
  inherit version;
  src = httyEnv;

  buildPhase = ''
    mkdir -p $out/bin
    cp -r $src/* $out/
  '';

  meta = with pkgs.lib; {
    description = "htty is a set of python convenience functions for the ht terminal utility, this package does not contain the ht binary.  Indicate the ht binary path via htty_HT_BINARY or use the htty-wheel output instead (which bundles it).";
    homepage = "https://github.com/yourusername/htty";
    license = licenses.mit;
    mainProgram = "htty";
    platforms = platforms.unix;
  };
}
