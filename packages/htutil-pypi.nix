# Build distributable wheels and sdists for htutil
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
  
  # Get the htutil package from the set
  htutilPackage = pythonSet.htutil;
  
  # Build script that creates both wheel and sdist
  buildDist = pkgs.writeShellScriptBin "build-htutil-dist" ''
    set -e
    echo "Building htutil distribution packages..."
    
    # Create a temporary directory for the build
    WORKDIR=$(mktemp -d)
    trap "rm -rf $WORKDIR" EXIT
    
    # Copy source files
    cp -r ${../.}/* $WORKDIR/ 2>/dev/null || true
    cd $WORKDIR
    
    # Use the Python environment with build tools
    export PATH="${pythonSet.python}/bin:${pythonSet.hatchling}/bin:$PATH"
    
    # Build the distribution
    ${pythonSet.python}/bin/python -m build --wheel --sdist
    
    # Copy artifacts to output
    mkdir -p $out
    cp dist/* $out/
    
    echo "Built packages:"
    ls -la $out/
  '';
  
in
# Default to the main htutil package
htutilPackage
