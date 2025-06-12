# Bundled htutil package with ht binary included
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
  
  # Create overlay that patches htutil to support bundled ht
  htutilPatchOverlay = final: prev: {
    htutil = prev.htutil.overridePythonAttrs (old: {
      # Patch the source before building
      preBuild = (old.preBuild or "") + ''
        # Patch ht.py to support HTUTIL_HT_BIN and bundled binary
        cat >> ht_patch.py << 'EOF'
import os
import re

with open('src/ht_util/ht.py', 'r') as f:
    content = f.read()

# Add get_ht_binary function after imports
patch = """
def get_ht_binary():
    \"\"\"Get the path to the ht binary.\"\"\"
    import os
    from pathlib import Path
    
    # Check for user-specified ht binary
    user_ht = os.environ.get('HTUTIL_HT_BIN')
    if user_ht and Path(user_ht).is_file() and os.access(user_ht, os.X_OK):
        return user_ht
    
    # Check for bundled ht binary
    module_dir = Path(__file__).parent
    bundled_ht = module_dir / '_bundled' / 'ht'
    if bundled_ht.exists() and bundled_ht.is_file():
        return str(bundled_ht)
    
    # Fall back to system PATH
    return "ht"

"""

# Find where to insert the function
lines = content.split('\n')
import_end = 0
for i, line in enumerate(lines):
    if line.strip() and not line.startswith('import') and not line.startswith('from'):
        import_end = i
        break

# Insert the function
lines.insert(import_end, patch)
content = '\n'.join(lines)

# Replace ht_cmd = ["ht", ...] with ht_cmd = [get_ht_binary(), ...]
content = re.sub(r'ht_cmd = \["ht"', 'ht_cmd = [get_ht_binary()', content)

with open('src/ht_util/ht.py', 'w') as f:
    f.write(content)
EOF
        
        python ht_patch.py
      '';
      
      # Include the ht binary in the package
      postInstall = (old.postInstall or "") + ''
        # Create _bundled directory in the package
        mkdir -p $out/${final.python.sitePackages}/ht_util/_bundled
        
        # Copy the ht binary
        cp ${htPackage}/bin/ht $out/${final.python.sitePackages}/ht_util/_bundled/
        chmod +x $out/${final.python.sitePackages}/ht_util/_bundled/ht
      '';
    });
  };
  
  # Construct the Python package set with our patches
  pythonSet = (pkgs.callPackage inputs.pyproject-nix.build.packages {
    python = pkgs.python311;
  }).overrideScope (
    pkgs.lib.composeManyExtensions [
      inputs.pyproject-build-systems.overlays.default
      overlay
      htutilPatchOverlay
    ]
  );
  
  # Get project metadata
  projectToml = builtins.fromTOML (builtins.readFile ../pyproject.toml);
  inherit (projectToml.project) version;
  
  # Create the htutil virtual environment with our patched version
  htutilBundledEnv = pythonSet.mkVirtualEnv "htutil-bundled-env" workspace.deps.default;
  
in
# Return the bundled package
pkgs.stdenvNoCC.mkDerivation {
  pname = "htutil-bundled";
  inherit version;
  src = htutilBundledEnv;
  
  buildPhase = ''
    mkdir -p $out/bin
    ln -s $src/bin/htutil $out/bin/
  '';
  
  meta = with pkgs.lib; {
    description = "A python wrapper around ht (with ht bundled, respects HTUTIL_HT_BIN env var)";
    homepage = "https://github.com/yourusername/htutil";
    license = licenses.mit;
    mainProgram = "htutil";
    platforms = platforms.unix;
  };
}
