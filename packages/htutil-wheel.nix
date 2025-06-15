# Build htutil wheel with bundled ht binary
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
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
  rm -rf src/htutil/_bundled
  mkdir -p src/htutil/_bundled
  
  # Bundle the ht binary
  cp ${htPackage}/bin/ht src/htutil/_bundled/ht
  chmod +x src/htutil/_bundled/ht
  echo "Bundled ht binary from: ${htPackage}/bin/ht"
  
  # Create output directory
  mkdir -p $out
  
  # Build the wheel
  ${pkgs.python312}/bin/python -m build --wheel --outdir $out
  
  # Show what was built
  echo "Built wheel package:"
  ls -la $out/
''
