# Bundled htutil package with ht binary and HTUTIL_HT_BIN support
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  
  # Get the ht package from the flake input
  htPackage = inputs.ht.packages.${system}.ht;
  
  # Load workspace from uv.lock
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../.;
  };
  
  # Create patched source
  patchedSrc = pkgs.stdenvNoCC.mkDerivation {
    name = "htutil-patched-source";
    src = ../.;
    nativeBuildInputs = [ pkgs.python311 ];
    
    buildPhase = ''
      cp -r . $out
      cd $out
      
      # Apply the patch to support HTUTIL_HT_BIN
      python ${./patch_ht.py} src/ht_util/ht.py
    '';
  };
  
  # Create workspace from patched source
  patchedWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = patchedSrc;
  };
  
  # Create overlay from patched workspace
  overlay = patchedWorkspace.mkPyprojectOverlay {
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
  htutilEnv = pythonSet.mkVirtualEnv "htutil-bundled-env" patchedWorkspace.deps.default;
  
in
# Create final package with bundled ht
pkgs.stdenvNoCC.mkDerivation {
  pname = "htutil-bundled";
  inherit version;
  
  dontUnpack = true;
  buildInputs = [ pkgs.makeWrapper ];
  
  buildPhase = ''
    # Create directory structure
    mkdir -p $out/bin
    mkdir -p $out/lib/python3.11/site-packages
    
    # Copy the Python environment
    cp -r ${htutilEnv}/lib/python*/site-packages/* $out/lib/python3.11/site-packages/
    cp -r ${htutilEnv}/bin/* $out/bin/
    
    # Copy the ht binary to bundled location
    mkdir -p $out/lib/python3.11/site-packages/ht_util/_bundled
    cp ${htPackage}/bin/ht $out/lib/python3.11/site-packages/ht_util/_bundled/
    chmod +x $out/lib/python3.11/site-packages/ht_util/_bundled/ht
    
    # Create a wrapper that provides helpful environment info
    mv $out/bin/htutil $out/bin/.htutil-unwrapped
    makeWrapper $out/bin/.htutil-unwrapped $out/bin/htutil \
      --run 'if [ -n "$HTUTIL_HT_BIN" ]; then echo "Note: HTUTIL_HT_BIN is set to: $HTUTIL_HT_BIN" >&2; fi' \
      --set-default HTUTIL_BUNDLED_HT "${htPackage}/bin/ht"
  '';
  
  meta = with pkgs.lib; {
    description = "A python wrapper around ht (with ht bundled, respects HTUTIL_HT_BIN env var)";
    homepage = "https://github.com/yourusername/htutil";
    license = licenses.mit;
    mainProgram = "htutil";
    platforms = platforms.unix;
  };
}
