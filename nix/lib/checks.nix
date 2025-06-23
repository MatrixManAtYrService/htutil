# Check definitions and utilities
{ flake, inputs, ... }:

pkgs:
let
  inherit (pkgs.stdenv.hostPlatform) system;

  # Get the check definitions library
  checks = inputs.checkdef.lib pkgs;

  lib = flake.lib pkgs;
  inherit (lib.pypkg) pythonSet workspace;
  inherit (lib.testcfg) testConfig testVim;

  httyWheel = flake.packages.${system}.htty-wheel;

  src = ../../.;

  # Extract version from pyproject.toml
  pyproject = builtins.fromTOML (builtins.readFile (src + "/pyproject.toml"));
  inherit (pyproject.project) version;

  # Create a local wheels directory with the pre-fetched dependency
  wheelCache = pkgs.runCommand "wheel-cache"
    {
      nativeBuildInputs = [ pkgs.python3 pkgs.python3.pkgs.pip pkgs.python3.pkgs.wheel pkgs.python3.pkgs.ansi2html ];
    } ''
        mkdir -p $out/wheels

        # Create a wheel from the nixpkgs ansi2html package
        # We'll create a simple wheel structure manually
        WHEEL_DIR="$TMPDIR/ansi2html_wheel"
        mkdir -p "$WHEEL_DIR/ansi2html"

        # Copy the ansi2html module from nixpkgs
        cp -r ${pkgs.python3.pkgs.ansi2html}/${pkgs.python3.sitePackages}/ansi2html/* "$WHEEL_DIR/ansi2html/"

        # Create a simple wheel using the existing package
        cd "$WHEEL_DIR"
        cat > create_wheel.py << 'EOF'
    import zipfile
    import os
    import sys
    import hashlib

    wheel_name = 'ansi2html-1.9.2-py3-none-any.whl'
    output_dir = sys.argv[1]

    def calculate_hash(file_path):
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    record_entries = []

    with zipfile.ZipFile(os.path.join(output_dir, wheel_name), 'w') as wheel:
        # Add all ansi2html files
        for root, dirs, files in os.walk('ansi2html'):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = file_path
                wheel.write(file_path, arcname)

                # Calculate hash and size for RECORD
                file_hash = calculate_hash(file_path)
                file_size = os.path.getsize(file_path)
                record_entries.append(f"{arcname},sha256={file_hash},{file_size}")

        # Add metadata files
        metadata = """Name: ansi2html
    Version: 1.9.2
    Summary: Convert ANSI colored text to HTML
    Home-page: https://github.com/pycontribs/ansi2html
    License: MIT
    Classifier: Development Status :: 5 - Production/Stable
    Classifier: Intended Audience :: Developers
    Classifier: License :: OSI Approved :: MIT License
    Classifier: Programming Language :: Python :: 3
    """
        wheel.writestr('ansi2html-1.9.2.dist-info/METADATA', metadata)
        record_entries.append("ansi2html-1.9.2.dist-info/METADATA,,")

        wheel_info = """Wheel-Version: 1.0
    Generator: manual
    Root-Is-Purelib: true
    Tag: py3-none-any
    """
        wheel.writestr('ansi2html-1.9.2.dist-info/WHEEL', wheel_info)
        record_entries.append("ansi2html-1.9.2.dist-info/WHEEL,,")

        # Add top_level.txt
        top_level = "ansi2html\n"
        wheel.writestr('ansi2html-1.9.2.dist-info/top_level.txt', top_level)
        record_entries.append("ansi2html-1.9.2.dist-info/top_level.txt,,")

        # Add RECORD file (must be last and reference itself)
        record_entries.append("ansi2html-1.9.2.dist-info/RECORD,,")
        record_content = "\n".join(record_entries) + "\n"
        wheel.writestr('ansi2html-1.9.2.dist-info/RECORD', record_content)

    print('Created wheel:', wheel_name)
    EOF

        ${pkgs.python3}/bin/python create_wheel.py "$out/wheels"

        echo "Prepared wheel cache:"
        ls -la $out/wheels/
  '';

  # Define the Python environment builder function once
  # This function takes filtered source and builds the Python environment
  buildPythonEnv = filteredSrc:
    let
      # Load workspace from the filtered source
      filteredWorkspace = inputs.uv2nix.lib.workspace.loadWorkspace {
        workspaceRoot = filteredSrc;
      };
      # Create python package set with proper overlays
      pythonSetFiltered = (pkgs.callPackage inputs.pyproject-nix.build.packages {
        python = pkgs.python3;
      }).overrideScope (
        pkgs.lib.composeManyExtensions [
          inputs.pyproject-build-systems.overlays.default
          (filteredWorkspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
        ]
      );

      # Create base Python environment
      basePythonEnv = pythonSetFiltered.mkVirtualEnv "htty-dev-env" filteredWorkspace.deps.all;

      # Add test dependencies to the environment
      testEnv = pkgs.buildEnv {
        name = "htty-test-env";
        paths = [ basePythonEnv ] ++ testConfig.baseDeps;
      };
    in
    testEnv;

  # Release environment builder that includes multiple Python versions and wheel setup
  # This is a CLEAN environment without htty pre-installed - for testing wheel installation
  buildReleaseEnv = filteredSrc:
    let
      # Create a wrapper that provides python3.10, python3.11, python3.12 commands
      pythonVersions = pkgs.runCommand "python-versions" { } ''
        mkdir -p $out/bin
        ln -s ${pkgs.python310}/bin/python $out/bin/python3.10
        ln -s ${pkgs.python311}/bin/python $out/bin/python3.11
        ln -s ${pkgs.python312}/bin/python $out/bin/python3.12
      '';

      # Create a minimal Python environment with just basic tools (no htty)
      # This ensures we're testing wheel installation in a clean environment
      minimalPythonEnv = pkgs.buildEnv {
        name = "minimal-python-env";
        paths = [
          pkgs.python3
          pkgs.python3.pkgs.pip
          pkgs.python3.pkgs.virtualenv
          pkgs.python3.pkgs.pytest # Need pytest to run the tests
        ];
      };

      # Create an environment that includes the wheel cache and multiple Python versions
      # but does NOT include htty (so we can test installing it from the wheel)
      releaseEnv = pkgs.buildEnv {
        name = "htty-release-env";
        paths = [
          minimalPythonEnv # Clean Python environment without htty
          pythonVersions # Multiple Python versions
          wheelCache # Pre-downloaded dependency wheels
        ] ++ testConfig.baseDeps; # Test dependencies (ht binary, vim, etc.)
      };
    in
    releaseEnv;

  fastChecks = {
    scriptChecks = {
      deadnixCheck = checks.deadnix { inherit src; };
      statixCheck = checks.statix { inherit src; };
      nixpkgsFmtCheck = checks.nixpkgs-fmt { inherit src; };
      ruffCheckCheck = checks.ruff-check { inherit src; };
      ruffFormatCheck = checks.ruff-format { inherit src; };
      trimWhitespaceCheck = checks.trim-whitespace {
        src = ./.;
        filePatterns = [ "*.py" "*.nix" "*.md" "*.txt" "*.yml" "*.yaml" ];
      };
      pyrightCheck = checks.pyright {
        inherit src;
        pythonEnv = pythonSet.mkVirtualEnv "htty-pyright-env" workspace.deps.all;
      };
    };
    derivationChecks = { };
  };

  fullChecks = {
    inherit (fastChecks) scriptChecks;
    derivationChecks = {
      pytestTest = checks.pytest-env-builder {
        inherit src;
        envBuilder = buildPythonEnv;
        name = "pytest-test";
        description = "Fast unit tests (tests/fast/ directory)";
        inherit testConfig;
        includePatterns = [ "src/**" "tests/**" "README.md" ];
        tests = [ "${src}/tests/fast" ];
      };
    };
  };

  releaseChecks = {
    scriptChecks = fastChecks.scriptChecks // {
      fawltydepsCheck = checks.fawltydeps {
        inherit src;
        pythonEnv = pythonSet.mkVirtualEnv "htty-fawltydeps-env" workspace.deps.all;
        ignoreUndeclared = [ "htty" ];
        ignoreUnused = [ "pdoc" "ruff" "pyright" "build" "hatchling" ];
      };
      pdocCheck = checks.pdoc {
        inherit src;
        pythonEnv = pythonSet.mkVirtualEnv "htty-pdoc-env" workspace.deps.all;
        modulePath = "src/htty";
      };
    };
    derivationChecks = fullChecks.derivationChecks // {
      pytestRelease = checks.pytest-env-builder {
        inherit src;
        envBuilder = buildReleaseEnv;
        name = "pytest-release";
        description = "Release tests with multiple Python versions";
        testConfig = testConfig // {
          extraEnvVars = testConfig.extraEnvVars or { } // {
            WHEEL_CACHE_DIR = "${wheelCache}";
            # Set wheel path via environment variable - read the actual wheel filename
            HTTY_WHEEL_PATH =
              let
                wheelFilename = builtins.readFile "${httyWheel}/wheel-filename.txt";
                # Remove any trailing newline from the filename using string manipulation
                cleanFilename = builtins.replaceStrings [ "\n" ] [ "" ] wheelFilename;
              in
              "${httyWheel}/${cleanFilename}";
          };
        };
        includePatterns = [ "src/**" "tests/**" "README.md" ];
        tests = [ "${src}/tests/slow" ];
        # Add extra dependencies to make wheel cache available
        extraDeps = [ wheelCache ];
      };
    };
  };

  distributionChecks = {
    scriptChecks = {
      # Distribution tests that need access to system Docker/Podman
      # Run as a script check to avoid Nix sandbox restrictions
      distributionTest = {
        description = "Distribution tests - Docker-based PyPI installation tests";
        scriptContent = ''
          set -euo pipefail

          # Set up environment with all necessary tools
          export PATH="${inputs.ht.packages.${pkgs.stdenv.hostPlatform.system}.ht}/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:$PATH"
          export CONTAINER_TOOL="/usr/local/bin/docker"
          export HTTY_TEST_CONTAINER_MODE="system-path"
          export HTTY_TEST_VIM_TARGET="${testVim}/bin/vim"
          export HTTY_HT_BIN="${inputs.ht.packages.${pkgs.stdenv.hostPlatform.system}.ht}/bin/ht"

          echo "🔍 Distribution test environment setup:"
          echo "PATH: $PATH"
          echo "CONTAINER_TOOL: $CONTAINER_TOOL"

          # Better Docker detection
          echo "🔍 Docker detection:"
          if [ -f "/usr/local/bin/docker" ]; then
            echo "  /usr/local/bin/docker exists: $(ls -la /usr/local/bin/docker)"
            if [ -x "/usr/local/bin/docker" ]; then
              echo "  /usr/local/bin/docker is executable"
              echo "  Trying to run: /usr/local/bin/docker --version"
              /usr/local/bin/docker --version || echo "  Docker version failed: $?"
            else
              echo "  /usr/local/bin/docker is not executable"
            fi
          else
            echo "  /usr/local/bin/docker does not exist"
          fi

          echo "Docker available: $(if command -v docker >/dev/null 2>&1; then echo "yes"; else echo "no"; fi)"
          echo "HTTY_HT_BIN: $HTTY_HT_BIN"
          echo "HTTY_TEST_VIM_TARGET: $HTTY_TEST_VIM_TARGET"

          # Create a temporary working directory and copy source
          TEMP_DIR=$(mktemp -d)
          echo "🔍 Working in temporary directory: $TEMP_DIR"

          # Copy source files to writable location
          cp -r "${src}"/* "$TEMP_DIR"/
          cd "$TEMP_DIR"

          # Run the distribution tests using uv
          echo "🚀 Running htty distribution tests..."
          exec ${pkgs.uv}/bin/uv run --frozen pytest tests/dist/test_pypi_installation.py -v
        '';
      };
    };
    derivationChecks = { };
  };

in
{
  inherit checks;
  inherit fastChecks fullChecks releaseChecks distributionChecks;
}
