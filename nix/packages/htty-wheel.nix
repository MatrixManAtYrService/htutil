# Build htty wheel with bundled ht binary
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  htPackage = inputs.ht.packages.${system}.ht;
in
pkgs.runCommand "htty-wheel"
{
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
  cp -r ${../../src} src
  chmod -R u+w src
  cp ${../../pyproject.toml} pyproject.toml
  cp ${../../README.md} README.md

  # Remove existing _bundled directory and create fresh one
  rm -rf src/htty/_bundled
  mkdir -p src/htty/_bundled

  # Bundle the ht binary
  cp ${htPackage}/bin/ht src/htty/_bundled/ht
  chmod +x src/htty/_bundled/ht
  echo "Bundled ht binary from: ${htPackage}/bin/ht"

  # Create output directory
  mkdir -p $out

  # Build the wheel
  ${pkgs.python312}/bin/python -m build --wheel --outdir $out

  # Find the actual wheel filename for programmatic access
  WHEEL_FILE=$(ls $out/*.whl | head -1)
  WHEEL_NAME=$(basename "$WHEEL_FILE")

  # Store the wheel filename for programmatic access
  echo "$WHEEL_NAME" > "$out/wheel-filename.txt"
  echo "$WHEEL_FILE" > "$out/wheel-path.txt"

  # Show what was built
  echo "Built wheel package: $WHEEL_NAME"
  ls -la $out/
''
