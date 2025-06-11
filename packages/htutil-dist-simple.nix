# Simple distributable htutil package
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  
  # Load workspace from uv.lock
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../.;
  };
  
  # Create overlay from workspace
  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };
  
  # Construct the Python package set
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python311;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      overlay
    ]
  );
  
  # Get project metadata
  projectToml = builtins.fromTOML (builtins.readFile ../pyproject.toml);
  inherit (projectToml.project) version;
  
  # Create the htutil virtual environment
  htutilEnv = pythonSet.mkVirtualEnv "htutil-env" workspace.deps.default;
  
in
# Return the derivation directly
pkgs.stdenvNoCC.mkDerivation {
  pname = "htutil";
  inherit version;
  src = htutilEnv;
  
  buildPhase = ''
    mkdir -p $out/bin
    ln -s $src/bin/htutil $out/bin/
  '';
  
  meta = with pkgs.lib; {
    description = "A python wrapper around ht (a headless terminal utility)";
    homepage = "https://github.com/yourusername/htutil";
    license = licenses.mit;
    mainProgram = "htutil";
    platforms = platforms.unix;
  };
}
