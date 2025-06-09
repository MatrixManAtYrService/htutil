{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the checks library and patterns
  checksLib = inputs.checks.packages.${system}.lib;
  inherit (checksLib) runner patterns makeCheckWithDeps;

  # Import shared test configuration
  testConfig = pkgs.callPackage ./test-config.nix { inherit inputs; };

  # Get htutil's Python environment from uv2nix
  htutilPackage = import ./default.nix { inherit inputs pkgs; };
  htutilPythonEnv = htutilPackage.pythonEnv;

  # Load workspace for uv2nix
  workspace = inputs.uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ../.;
  };

  # Create Python environment with dev dependencies using uv2nix properly
  htutilPythonEnvWithDev = htutilPackage.pythonSet.mkVirtualEnv "htutil-dev-env" workspace.deps.all;

  # Create individual check derivations for htutil
  htutilSrc = ../.;

  # All the fast checks
  deadnixCheck = patterns.deadnix { src = htutilSrc; };
  statixCheck = patterns.statix { src = htutilSrc; };
  nixpkgsFmtCheck = patterns.nixpkgs-fmt { src = htutilSrc; };
  ruffCheckCheck = patterns.ruff-check { src = htutilSrc; };
  ruffFormatCheck = patterns.ruff-format { src = htutilSrc; };
  pyrightCheck = patterns.pyright {
    src = htutilSrc;
    pythonEnv = htutilPythonEnvWithDev;
  };

  # Additional test check
  pytestCheck = makeCheckWithDeps {
    name = "pytest";
    description = "Python unit tests";
    src = htutilSrc;
    dependencies = [ htutilPythonEnvWithDev ] ++ testConfig.baseDeps;
    environment = testConfig.baseEnv // {
      # Handle both traditional withPackages (has sitePackages) and uv2nix mkVirtualEnv (doesn't)
      PYTHONPATH =
        if htutilPythonEnvWithDev ? sitePackages
        then "${htutilPythonEnvWithDev}/${htutilPythonEnvWithDev.sitePackages}"
        else "${htutilPythonEnvWithDev}/lib/python*/site-packages";
      # Make sure pytest and other executables are available
      PATH = "${htutilPythonEnvWithDev}/bin:$PATH";
    };
    script = ''
      echo "🧪 Running pytest..."
      pytest -vv tests/
    '';
  };
in

pkgs.writeShellApplication {
  name = "htutil-checks-with-cache-detection";

  runtimeInputs = with pkgs; [
    nix
    jq
  ];

  text = ''
    set -euo pipefail
    
    echo "🔍 Analyzing cache status for htutil checks..."
    echo ""
    
    # Get all derivations that would be built
    echo "📋 Getting derivation information..."
    derivation_info=$(nix derivation show .#checks-full 2>/dev/null)
    
    # Extract the main derivation path
    main_drv=$(echo "$derivation_info" | jq -r 'keys[0]')
    echo "Main derivation: $main_drv"
    
    # Extract input derivations
    input_drvs=$(echo "$derivation_info" | jq -r '.[] | .inputDrvs | keys[]' | grep -v stdenv | grep -v bash | head -7)
    
    echo ""
    echo "📊 Checking cache status for each check..."
    
    cached_count=0
    build_count=0
    
    # Function to check cache status using nix build --dry-run
    check_cache_status() {
      local name="$1"
      local drv_path="$2"
      
      # Use nix build --dry-run to check if building is needed
      dry_run_output=$(nix build --dry-run "$drv_path" 2>&1 || true)
      
      if [ -z "$dry_run_output" ]; then
        echo "  💾 $name - CACHED"
        ((cached_count++))
        return 0
      else
        echo "  🔨 $name - NEEDS BUILDING"
        echo "    ($dry_run_output)"
        ((build_count++))
        return 1
      fi
    }
    
    # Check each derivation
    while IFS= read -r drv; do
      # Extract check name from derivation path
      check_name=$(basename "$drv" | sed 's/\.drv$//' | sed 's/^[^-]*-//')
      check_cache_status "$check_name" "$drv"
    done <<< "$input_drvs"
    
    echo ""
    echo "📈 Cache Analysis Summary:"
    echo "   • $cached_count checks cached"
    echo "   • $build_count checks need building"
    
    if [ $build_count -gt 0 ]; then
      echo ""
      echo "🔨 Building and executing checks..."
      echo ""
    else
      echo ""
      echo "💾 All checks cached - executing with cached results..."
      echo ""
    fi
    
    # Now run the actual checks with proper cache status detection
    # Run the check framework which will now show accurate cache status
    ${runner}/bin/check-runner \
      "deadnix:${deadnixCheck}" \
      "statix:${statixCheck}" \
      "nixpkgs-fmt:${nixpkgsFmtCheck}" \
      "ruff-check:${ruffCheckCheck}" \
      "ruff-format:${ruffFormatCheck}" \
      "pyright:${pyrightCheck}" \
      "pytest:${pytestCheck}" \
      --suite-name "Full Checks (Cache-Aware)"
  '';
}
