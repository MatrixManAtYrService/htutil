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
{
  # The actual htutil package (wheel format)
  htutil = htutilPackage;
  
  # Script to build distribution artifacts
  build-dist = buildDist;
  
  # Pre-built wheel directly from uv2nix
  wheel = pkgs.runCommand "htutil-wheel" {} ''
    mkdir -p $out
    cp ${htutilPackage}/*.whl $out/ 2>/dev/null || echo "No wheel found in package"
    
    # If no wheel in package, build one
    if [ ! -f $out/*.whl ]; then
      cd ${../.}
      ${pythonSet.python}/bin/python -m build --wheel --outdir $out
    fi
  '';
  
  # Source distribution
  sdist = pkgs.runCommand "htutil-sdist" {} ''
    mkdir -p $out
    cd ${../.}
    ${pythonSet.python}/bin/python -m build --sdist --outdir $out
  '';
}
