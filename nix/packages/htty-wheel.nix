# Build htty wheel with bundled ht binary
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  htPackage = inputs.ht.packages.${system}.ht;

  # Platform-specific wheel tags based on the target system
  platformTag = {
    "x86_64-linux" = "linux_x86_64";
    "aarch64-linux" = "linux_aarch64";
    "x86_64-darwin" = "macosx_10_9_x86_64";
    "aarch64-darwin" = "macosx_11_0_arm64";
  }.${system} or "any";

  # ABI tag - use none since the Python code is compatible across versions
  # Only the bundled ht binary is platform-specific, not the Python ABI
  abiTag = "none";
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

  # Find the generated wheel and rename it with correct platform tags
  ORIGINAL_WHEEL=$(ls $out/*.whl | head -1)
  ORIGINAL_NAME=$(basename "$ORIGINAL_WHEEL")

  # Extract version from the original filename
  VERSION=$(echo "$ORIGINAL_NAME" | sed 's/htty-\([^-]*\)-.*/\1/')

  # Create the new platform-specific filename
  NEW_NAME="htty-$VERSION-py3-${abiTag}-${platformTag}.whl"
  NEW_WHEEL="$out/$NEW_NAME"

  # Rename the wheel
  mv "$ORIGINAL_WHEEL" "$NEW_WHEEL"

  # Store the wheel filename for programmatic access
  echo "$NEW_NAME" > "$out/wheel-filename.txt"
  echo "$NEW_WHEEL" > "$out/wheel-path.txt"

  # Create a predictable symlink for easy reference
  ln -s "$NEW_NAME" "$out/htty-wheel.whl"

  # Show what was built
  echo "Built wheel package: $NEW_NAME"
  echo "Platform-specific wheel created for: ${system} -> ${platformTag}"
  ls -la $out/
''
