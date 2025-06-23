# Build htty wheel with bundled ht binary
{ inputs, pkgs, targetSystem ? null, useOptimized ? false, ... }:

let
  # Use targetSystem if provided, otherwise use host platform
  system = if targetSystem != null then targetSystem else pkgs.stdenv.hostPlatform.system;

  # Choose appropriate ht package based on optimization flag and cross-compilation
  htPackage =
    if targetSystem != null then
    # Cross-compiled case
      if useOptimized then
        inputs.ht.packages.${pkgs.stdenv.hostPlatform.system}."${system}-optimized" or inputs.ht.packages.${pkgs.stdenv.hostPlatform.system}.${system}
      else
        inputs.ht.packages.${pkgs.stdenv.hostPlatform.system}.${system}
    else
    # Native build case
      if useOptimized then
        inputs.ht.packages.${system}.ht-optimized or inputs.ht.packages.${system}.ht
      else
        inputs.ht.packages.${system}.ht;

  # Enhanced platform tags following polars' exact PyPI strategy
  platformTag = {
    # Linux - match polars' glibc requirements
    "x86_64-linux" = "manylinux_2_17_x86_64.manylinux2014_x86_64";
    "aarch64-linux" = "manylinux_2_24_aarch64";

    # macOS - match polars' deployment targets
    "x86_64-darwin" = "macosx_10_12_x86_64";
    "aarch64-darwin" = "macosx_11_0_arm64";

    # Windows - following polars' naming
    "x86_64-windows" = "win_amd64";
    "aarch64-windows" = "win_arm64";
  }.${system} or "any";

  # Use abi3 (stable ABI) like polars instead of none
  abiTag = "cp39-abi3";

  # Include optimization info in wheel name for debugging
  nameSuffix =
    (if targetSystem != null then "-cross-${targetSystem}" else "") +
    (if useOptimized then "-optimized" else "");

  buildVariant = if useOptimized then "optimized" else "standard";
in
pkgs.runCommand "htty-wheel${nameSuffix}"
{
  nativeBuildInputs = with pkgs; [
    python312
    python312.pkgs.pip
    python312.pkgs.build
    python312.pkgs.wheel
    python312.pkgs.hatchling
    file # For binary analysis and validation
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

  # Bundle the ht binary with enhanced validation (polars-style)
  echo "🔧 Bundling ht binary from: ${htPackage}/bin/ht"
  echo "🎯 Build variant: ${buildVariant}"
  echo "🖥️  Target system: ${system}"

  cp ${htPackage}/bin/ht src/htty/_bundled/ht
  chmod +x src/htty/_bundled/ht

  # Enhanced binary validation
  echo "🔍 Validating bundled binary:"
  file src/htty/_bundled/ht

  # Test the binary works
  echo "⚙️  Testing binary functionality:"
  if src/htty/_bundled/ht --version > /dev/null 2>&1; then
    echo "✅ Binary version check passed"
    src/htty/_bundled/ht --version
  else
    echo "⚠️  Binary version check failed (may be expected for cross-compiled builds)"
  fi

  # Check binary size and architecture
  echo "📏 Binary details:"
  echo "   Size: $(ls -lh src/htty/_bundled/ht | awk '{print $5}')"
  echo "   Type: $(file src/htty/_bundled/ht | cut -d: -f2-)"

  # Create output directory
  mkdir -p $out

  # Build the wheel
  echo "🏗️  Building wheel..."
  ${pkgs.python312}/bin/python -m build --wheel --outdir $out

  # Find the generated wheel and rename it with correct platform tags
  ORIGINAL_WHEEL=$(ls $out/*.whl | head -1)
  ORIGINAL_NAME=$(basename "$ORIGINAL_WHEEL")

  # Extract version from the original filename
  VERSION=$(echo "$ORIGINAL_NAME" | sed 's/htty-\([^-]*\)-.*/\1/')

  # Create the new platform-specific filename
  NEW_NAME="htty-$VERSION-${abiTag}-${platformTag}.whl"
  NEW_WHEEL="$out/$NEW_NAME"

  # Rename the wheel
  mv "$ORIGINAL_WHEEL" "$NEW_WHEEL"

  # Store comprehensive metadata for CI and debugging
  echo "$NEW_NAME" > "$out/wheel-filename.txt"
  echo "$NEW_WHEEL" > "$out/wheel-path.txt"
  echo "${system}" > "$out/target-system.txt"
  echo "${buildVariant}" > "$out/build-variant.txt"
  echo "${if targetSystem != null then "cross-compiled" else "native"}" > "$out/build-type.txt"

  # Create a predictable symlink for easy reference
  ln -s "$NEW_NAME" "$out/htty-wheel.whl"

  # Enhanced build reporting (polars-inspired)
  echo ""
  echo "✅ Successfully built wheel package: $NEW_NAME"
  echo "🎯 Target platform: ${system} -> ${platformTag}"
  echo "⚡ Build variant: ${buildVariant}"
  echo "🔄 Build type: ${if targetSystem != null then "cross-compiled from ${pkgs.stdenv.hostPlatform.system}" else "native"}"
  echo "📦 Wheel size: $(ls -lh $NEW_WHEEL | awk '{print $5}')"
  echo "🔧 Bundled binary: $(file src/htty/_bundled/ht | cut -d: -f2-)"

  # Additional metadata for optimized builds
  ${if useOptimized then ''
    echo "🚀 CPU optimizations: ${if system == "x86_64-linux" || system == "x86_64-darwin"
      then "SSE3, SSSE3, SSE4.1, SSE4.2, POPCNT, AVX, AVX2"
      else if system == "aarch64-linux" || system == "aarch64-darwin"
      then "NEON"
      else "none"}"
  '' else ""}

  echo ""
  echo "📁 Build artifacts:"
  ls -la $out/
''
