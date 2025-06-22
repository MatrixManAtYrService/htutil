# Build htty source distribution
{ inputs, pkgs, ... }:

pkgs.runCommand "htty-sdist"
{
  nativeBuildInputs = with pkgs; [
    python312
    python312.pkgs.pip
    python312.pkgs.build
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

  # Create output directory
  mkdir -p $out

  # Build the source distribution
  ${pkgs.python312}/bin/python -m build --sdist --outdir $out

  # Show what was built
  echo "Built source distribution:"
  ls -la $out/
''
