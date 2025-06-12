{ inputs, pkgs, ... }:

let
  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${pkgs.stdenv.hostPlatform.system}.lib;
  inherit (checksLib) makeCheckWithDeps;

  # Import shared test configuration
  testConfig = pkgs.callPackage ./lib/test-config.nix { inherit inputs; };

  # Release tests that verify htutil works across multiple Python versions using uv

  # Create a simple release test for a specific Python version
  # This just tests that `uv run htutil --help` works
  makeReleaseTest = python: version: makeCheckWithDeps {
    name = "htutil-release-py${version}";
    description = "Release test - verify uv run htutil --help works with Python ${version}";
    src = ../.;
    dependencies = [
      python
      pkgs.uv
    ] ++ testConfig.baseDeps;
    environment = testConfig.baseEnv // {
      # Force uv to use the specific Python version
      UV_PYTHON = "${python}/bin/python${version}";
      # Set writable cache directory for uv
      UV_CACHE_DIR = "$TMPDIR/uv-cache";
      UV_NO_SYNC = "1"; # Skip lock file sync to avoid unnecessary writes
    };
    script = ''
      echo "🚀 Testing htutil CLI with Python ${version}..."
      echo "Python version: $(python3 --version)"
      
      # Create writable cache directory
      mkdir -p "$UV_CACHE_DIR"
      
      # Test that uv run htutil --help works
      echo "🔍 Testing: uv run htutil --help..."
      uv run --python ${python}/bin/python${version} --with-editable . htutil --help
      
      echo "✅ Release test completed successfully for Python ${version}"
    '';
  };

in
# Default to Python 3.11 release test
makeReleaseTest pkgs.python311 "3.11"
