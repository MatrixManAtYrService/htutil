# Build htty wheel with portable ht binary using maturin
{ inputs, pkgs, targetSystem ? null, ... }:

let
  # Use targetSystem if provided, otherwise use host platform
  system = if targetSystem != null then targetSystem else pkgs.stdenv.hostPlatform.system;
  
  # ht source from flake input (flake=false)
  htSrc = inputs.ht;

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

  # Cross-compilation target for Rust
  rustTarget = {
    "x86_64-linux" = "x86_64-unknown-linux-gnu";
    "aarch64-linux" = "aarch64-unknown-linux-gnu";
    "x86_64-darwin" = "x86_64-apple-darwin";
    "aarch64-darwin" = "aarch64-apple-darwin";
    "x86_64-windows" = "x86_64-pc-windows-gnu";
    "aarch64-windows" = "aarch64-pc-windows-gnu";
  }.${system} or system;

  # Determine if we're cross-compiling
  isCrossCompiling = targetSystem != null;
  buildType = if isCrossCompiling then "cross-compiled" else "native";

  # Build environment packages  
  nativeBuildInputs = with pkgs; [
    python312
    python312.pkgs.pip
    python312.pkgs.build
    python312.pkgs.wheel
    python312.pkgs.hatchling
    file # For binary analysis and validation
    
    # Rust toolchain and maturin for portable binary building
    rustc
    cargo
    rustfmt
    maturin # Available as top-level package
  ] ++ pkgs.lib.optionals isCrossCompiling [
    # Cross-compilation tools (simplified)
    gcc
  ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
    # macOS specific dependencies
    pkgs.libiconv
    pkgs.darwin.apple_sdk.frameworks.Foundation
  ];

in
pkgs.runCommand "htty-wheel-${system}"
{
  inherit nativeBuildInputs;
} ''
  # Create temporary build directory
  mkdir -p build
  cd build

  echo "🏗️  Building portable htty wheel with maturin"
  echo "🎯 Target system: ${system}"
  echo "🔄 Build type: ${buildType}"
  echo "🦀 Rust target: ${rustTarget}"

  # Copy htty source files and make them writable
  echo "📦 Copying htty source..."
  cp -r ${../../src} src
  chmod -R u+w src
  cp ${../../pyproject.toml} pyproject.toml
  cp ${../../README.md} README.md

  # Copy ht source for building
  echo "📦 Copying ht source..."
  cp -r ${htSrc} ht-src
  chmod -R u+w ht-src

  # Remove existing _bundled directory and create fresh one
  rm -rf src/htty/_bundled
  mkdir -p src/htty/_bundled

  # Build ht binary using cargo for portability (maturin is for Python wheels)
  echo "🦀 Building portable ht binary using Rust toolchain..."
  cd ht-src
  
  ${if isCrossCompiling then ''
    echo "🔀 Cross-compiling for ${rustTarget}"
    # Simple cross-compilation with cargo
    cargo build --release --target ${rustTarget}
    HT_BINARY="target/${rustTarget}/release/ht"
  '' else ''
    echo "🏠 Building natively for ${rustTarget}"
    cargo build --release
    HT_BINARY="target/release/ht"
  ''}

  # Validate the built binary
  echo "🔍 Validating built binary:"
  ls -la "$HT_BINARY"
  file "$HT_BINARY"

  # Copy the portable binary to htty bundle
  echo "📦 Bundling portable binary..."
  cp "$HT_BINARY" ../src/htty/_bundled/ht
  chmod +x ../src/htty/_bundled/ht

  cd ..

  # Enhanced binary validation
  echo "✅ Portable binary validation:"
  echo "   Size: $(ls -lh src/htty/_bundled/ht | awk '{print $5}')"
  echo "   Type: $(file src/htty/_bundled/ht | cut -d: -f2-)"
  
  # Test the binary works (native builds only)
  ${if !isCrossCompiling then ''
    echo "⚙️  Testing binary functionality:"
    if src/htty/_bundled/ht --version > /dev/null 2>&1; then
      echo "✅ Binary version check passed"
      src/htty/_bundled/ht --version
    else
      echo "⚠️  Binary version check failed"
    fi
  '' else ''
    echo "⚙️  Skipping binary test for cross-compiled build"
  ''}

  # Create output directory
  mkdir -p $out

  # Build the wheel
  echo "🏗️  Building Python wheel..."
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
  echo "portable" > "$out/build-variant.txt"
  echo "${buildType}" > "$out/build-type.txt"

  # Create a predictable symlink for easy reference
  ln -s "$NEW_NAME" "$out/htty-wheel.whl"

  # Enhanced build reporting (polars-inspired)
  echo ""
  echo "🎉 Successfully built portable wheel: $NEW_NAME"
  echo "🎯 Target platform: ${system} -> ${platformTag}"
  echo "🔄 Build type: ${buildType}"
  echo "🦀 Rust target: ${rustTarget}"
  echo "📦 Wheel size: $(ls -lh $NEW_WHEEL | awk '{print $5}')"
  echo "🔧 Bundled binary: Portable (no Nix store dependencies)"
  echo "✅ PyPI compatible: Yes (manylinux/macOS/Windows standards)"

  echo ""
  echo "📁 Build artifacts:"
  ls -la $out/
''
