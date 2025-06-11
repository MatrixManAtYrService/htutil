# Distributable htutil package using uv2nix patterns
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  
  # Use Python 3.11 as a good default (matching isd-tui)
  python = pkgs.python311;
  
  # Load workspace from uv.lock
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../.;
  };
  
  # Create overlay from workspace
  overlay = workspace.mkPyprojectOverlay {
    # Prefer wheel format for better compatibility
    sourcePreference = "wheel";
  };
  
  # Build system overlay for pyproject standards
  pyprojectOverrides = _final: _prev: {
    # Add any necessary build fixups here if needed
  };
  
  # Construct the Python package set
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    inherit python;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      overlay
      pyprojectOverrides
    ]
  );
  
  # Get project metadata
  projectToml = builtins.fromTOML (builtins.readFile ../pyproject.toml);
  inherit (projectToml.project) version;
  
  # Create the htutil virtual environment
  htutilEnv = pythonSet.mkVirtualEnv "htutil-env" workspace.deps.default;
  
  # Get htutil from pythonSet
  inherit (pythonSet) htutil;
  
in
{
  # Main distributable package (matches isd-tui pattern)
  default = pkgs.stdenvNoCC.mkDerivation {
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
  };
  
  # Alias for backward compatibility
  inherit htutil;
  
  # Development environment with all dependencies
  htutil-dev = pythonSet.mkVirtualEnv "htutil-dev-env" workspace.deps.all;
}
