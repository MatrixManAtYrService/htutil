# Build htutil wheel with bundled ht binary
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  
  # Get the ht package from the flake input  
  htPackage = inputs.ht.packages.${system}.ht;
  
in
pkgs.runCommand "htutil-wheel" {
  nativeBuildInputs = with pkgs; [
    python312
    python312.pkgs.pip
    python312.pkgs.build
    python312.pkgs.wheel
    python312.pkgs.hatchling
  ];
} ''
  # Create temporary build directory
  mkdir -p build
  cd build
  
  # Copy source files and make them writable
  cp -r ${../src} src
  chmod -R u+w src
  cp ${../pyproject.toml} pyproject.toml
  cp ${../README.md} README.md
  
  # Remove existing _bundled directory and create fresh one
  rm -rf src/ht_util/_bundled
  mkdir -p src/ht_util/_bundled
  
  # Add the bundled ht binary
  cp ${htPackage}/bin/ht src/ht_util/_bundled/ht
  chmod +x src/ht_util/_bundled/ht
  
  # Create output directory
  mkdir -p $out
  
  # Build the wheel
  ${pkgs.python312}/bin/python -m build --wheel --outdir $out
  
  # Show what was built
  echo "Built wheel package:"
  ls -la $out/
''
