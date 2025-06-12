# Bundled htutil package with ht binary included (direct approach)
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  
  # Get the ht package from the flake input
  htPackage = inputs.ht.packages.${system}.ht;
  
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
  
  # Create a patched version of the htutil source
  htutilPatchedSrc = pkgs.stdenvNoCC.mkDerivation {
    name = "htutil-patched-src";
    src = ../.;
    
    buildPhase = ''
      cp -r . $out
      
      # Patch ht.py to add get_ht_binary function
      cat > patch_ht.py << 'EOF'
import re

with open('src/ht_util/ht.py', 'r') as f:
    content = f.read()

# Add import os if not present
if 'import os' not in content:
    content = 'import os\n' + content

# Add get_ht_binary function after imports
func_def = '''

def get_ht_binary():
    """Get the path to the ht binary."""
    import os
    from pathlib import Path
    
    # Check for user-specified ht binary
    user_ht = os.environ.get('HTUTIL_HT_BIN')
    if user_ht:
        if Path(user_ht).is_file() and os.access(user_ht, os.X_OK):
            return user_ht
        else:
            import sys
            print(f"Warning: HTUTIL_HT_BIN='{user_ht}' is not a valid executable", file=sys.stderr)
    
    # Check for bundled ht binary
    module_dir = Path(__file__).parent
    bundled_ht = module_dir / '_bundled' / 'ht'
    if bundled_ht.exists() and bundled_ht.is_file():
        return str(bundled_ht)
    
    # Fall back to system PATH
    return "ht"

'''

# Insert the function after imports
lines = content.split('\n')
import_end = 0
for i, line in enumerate(lines):
    if line.strip() and not line.startswith('import') and not line.startswith('from'):
        import_end = i
        break

lines.insert(import_end, func_def)
content = '\n'.join(lines)

# Replace ht_cmd = ["ht", ...] with ht_cmd = [get_ht_binary(), ...]
content = re.sub(r'ht_cmd = \["ht"', 'ht_cmd = [get_ht_binary()', content)

with open('src/ht_util/ht.py', 'w') as f:
    f.write(content)
EOF
      
      cd $out && python patch_ht.py
    '';
  };
  
  # Create a new workspace with our patched source
  patchedWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = htutilPatchedSrc;
  };
  
  # Create overlay from patched workspace
  patchedOverlay = patchedWorkspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };
  
  # Construct the Python package set with patched source
  patchedPythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python311;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      patchedOverlay
    ]
  );
  
  # Create the htutil virtual environment with patched version
  htutilBundledEnv = patchedPythonSet.mkVirtualEnv "htutil-bundled-env" patchedWorkspace.deps.default;
  
in
# Build the final package with bundled ht
pkgs.stdenvNoCC.mkDerivation {
  pname = "htutil-bundled";
  inherit version;
  
  buildInputs = [ htutilBundledEnv ];
  
  buildPhase = ''
    # Create output directory structure
    mkdir -p $out/bin
    mkdir -p $out/${pkgs.python311.sitePackages}/ht_util/_bundled
    
    # Copy htutil binary
    ln -s ${htutilBundledEnv}/bin/htutil $out/bin/
    
    # Copy Python packages
    cp -r ${htutilBundledEnv}/lib/python*/site-packages/* $out/${pkgs.python311.sitePackages}/ || true
    
    # Copy the ht binary to the bundled location
    cp ${htPackage}/bin/ht $out/${pkgs.python311.sitePackages}/ht_util/_bundled/
    chmod +x $out/${pkgs.python311.sitePackages}/ht_util/_bundled/ht
  '';
  
  installPhase = ''
    # Create a wrapper that sets PYTHONPATH correctly
    mv $out/bin/htutil $out/bin/.htutil-wrapped
    cat > $out/bin/htutil << EOF
#!/bin/sh
export PYTHONPATH="$out/${pkgs.python311.sitePackages}:\$PYTHONPATH"
exec $out/bin/.htutil-wrapped "\$@"
EOF
    chmod +x $out/bin/htutil
  '';
  
  meta = with pkgs.lib; {
    description = "A python wrapper around ht (with ht bundled, respects HTUTIL_HT_BIN env var)";
    homepage = "https://github.com/yourusername/htutil";
    license = licenses.mit;
    mainProgram = "htutil";
    platforms = platforms.unix;
  };
}
