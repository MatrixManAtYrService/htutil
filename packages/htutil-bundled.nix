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
  
  # Create a wrapper script that handles ht binary location
  htutilWrapper = pkgs.writeShellScriptBin "htutil" ''
    # If HTUTIL_HT_BIN is set, use that instead of bundled ht
    if [ -n "$HTUTIL_HT_BIN" ]; then
      # Verify the provided binary exists and is executable
      if [ -x "$HTUTIL_HT_BIN" ]; then
        export _HTUTIL_HT_PATH="$HTUTIL_HT_BIN"
      else
        echo "Warning: HTUTIL_HT_BIN='$HTUTIL_HT_BIN' is not executable, falling back to bundled ht" >&2
        export _HTUTIL_HT_PATH="${htPackage}/bin/ht"
      fi
    else
      # Use the bundled ht binary
      export _HTUTIL_HT_PATH="${htPackage}/bin/ht"
    fi
    
    # Execute the actual htutil with Python environment
    exec ${htutilEnv}/bin/htutil "$@"
  '';
  
  # Patch to make htutil use the environment variable
  htPyPatch = pkgs.writeText "ht_py_patch.py" ''
    import sys
    import re

    # Read the original ht.py
    with open(sys.argv[1], 'r') as f:
        content = f.read()

    # Add the import for os at the top if not already present
    if 'import os' not in content:
        lines = content.split('\n')
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_idx = i + 1
        lines.insert(import_idx, 'import os')
        content = '\n'.join(lines)

    # Replace the ht command initialization
    # Find the line: ht_cmd = ["ht", "--subscribe", ...]
    content = re.sub(
        r'ht_cmd = \["ht"',
        'ht_cmd = [os.environ.get("_HTUTIL_HT_PATH", "ht")',
        content
    )

    # Write the patched file
    with open(sys.argv[1], 'w') as f:
        f.write(content)
  '';
  
in
# Return a derivation that includes both htutil and the wrapper
pkgs.stdenvNoCC.mkDerivation {
  pname = "htutil-bundled";
  inherit version;
  
  src = htutilEnv;
  
  nativeBuildInputs = [ pkgs.python311 ];
  
  buildPhase = ''
    # Copy the htutil environment
    cp -r $src $out
    
    # Patch ht.py to use the environment variable
    python ${htPyPatch} $out/lib/python*/site-packages/ht_util/ht.py
    
    # Replace the htutil binary with our wrapper
    rm -f $out/bin/htutil
    cp ${htutilWrapper}/bin/htutil $out/bin/htutil
  '';
  
  installPhase = ''
    # Everything is already in place from buildPhase
    echo "Installation complete"
  '';
  
  meta = with pkgs.lib; {
    description = "A python wrapper around ht (with ht bundled, respects HTUTIL_HT_BIN env var)";
    homepage = "https://github.com/yourusername/htutil";
    license = licenses.mit;
    mainProgram = "htutil";
    platforms = platforms.unix;
  };
}
