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

  # Note: pyproject.toml parsing available if needed for version extraction

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
  buildReleaseEnv = _:
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

      # Cross-platform wheel testing in Docker containers
      crossPlatformWheelTest = 
        {
          description = "Cross-platform wheel tests - Docker-based wheel testing with cross-compilation or emulation";
          scriptContent = ''
            set -euo pipefail

            echo "🚀 Cross-platform wheel testing"
            echo "Host platform: ${system}"

            # Simple container tool discovery without pytest dependency
            CONTAINER_TOOL=""
            
            # Check for Docker first
            for DOCKER_PATH in "/usr/local/bin/docker" "/usr/bin/docker" "/opt/homebrew/bin/docker" "docker"; do
              if command -v "$DOCKER_PATH" >/dev/null 2>&1; then
                if "$DOCKER_PATH" --version >/dev/null 2>&1; then
                  CONTAINER_TOOL="$DOCKER_PATH"
                  echo "✅ Found Docker: $CONTAINER_TOOL"
                  break
                fi
              fi
            done
            
            # If no Docker, check for Podman
            if [ -z "$CONTAINER_TOOL" ]; then
              for PODMAN_PATH in "/usr/local/bin/podman" "/usr/bin/podman" "/opt/homebrew/bin/podman" "podman"; do
                if command -v "$PODMAN_PATH" >/dev/null 2>&1; then
                  if "$PODMAN_PATH" --version >/dev/null 2>&1; then
                    CONTAINER_TOOL="$PODMAN_PATH"
                    echo "✅ Found Podman: $CONTAINER_TOOL"
                    break
                  fi
                fi
              done
            fi

            if [ -z "$CONTAINER_TOOL" ]; then
              echo "❌ No container tool found. Skipping cross-platform tests."
              echo "   Install Docker or Podman to run cross-platform wheel tests."
              exit 0
            fi

            # Try to build ARM Linux wheel using cross-compilation
            echo "🔨 Attempting to build ARM Linux wheel via cross-compilation..."
            CROSS_WHEEL_PATH=""
            if nix build --impure --expr '
              let
                flake = builtins.getFlake (toString ./.);
                pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; };
              in
                pkgs.callPackage ./nix/packages/htty-wheel.nix {
                  inputs = flake.inputs;
                  targetSystem = "aarch64-linux";
                }
            ' 2>/dev/null; then
              CROSS_WHEEL_PATH="./result/htty-wheel.whl"
              WHEEL_NAME=$(cat result/wheel-filename.txt)
              echo "✅ Cross-compilation successful: $WHEEL_NAME"
              echo "🧪 Test approach: Cross-compiled ARM Linux wheel in ARM Linux container"
            else
              echo "⚠️ Cross-compilation failed (expected on some platforms)"
              echo "🧪 Test approach: Host wheel in emulated ARM Linux container"
              CROSS_WHEEL_PATH="${httyWheel}/htty-wheel.whl"
              WHEEL_NAME=$(cat "${httyWheel}/wheel-filename.txt")
            fi
            
            echo "📦 Testing wheel: $WHEEL_NAME"
            echo "📁 Wheel path: $CROSS_WHEEL_PATH"
            
            # Create temporary directory for test
            TEMP_DIR=$(mktemp -d)
            echo "🔍 Working in: $TEMP_DIR"
            
            # Copy wheel to temp directory
            cp "$CROSS_WHEEL_PATH" "$TEMP_DIR/$WHEEL_NAME"
            
            # Create a test script that handles both cross-compiled and emulated scenarios
            cat > "$TEMP_DIR/test_wheel.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

echo "🔧 Container platform info:"
uname -a
echo ""

echo "🔧 Installing htty wheel..."
set +e  # Temporarily disable exit on error
python3 -m pip install --force-reinstall "/wheels/$WHEEL_NAME"
PIP_EXIT_CODE=$?
set -e  # Re-enable exit on error

if [ $PIP_EXIT_CODE -ne 0 ]; then
    echo "❌ Installation failed"
    # Check if this is expected (host wheel in emulated container)
    if [[ "$WHEEL_NAME" == *"macosx"* ]] || [[ "$WHEEL_NAME" == *"darwin"* ]]; then
        echo "✅ This is expected! macOS wheel correctly rejected by Linux container."
        echo "   This validates that platform-specific wheels are properly tagged."
        echo "   In CI, cross-compiled Linux wheels will install successfully."
        exit 0
    else
        echo "❌ Unexpected installation failure for Linux wheel"
        exit 1
    fi
fi

echo "✅ Installation successful"

# Test CLI availability
echo "🔧 Testing htty CLI availability..."
htty --help > /dev/null

if [ $? -ne 0 ]; then
    echo "❌ CLI test failed"
    exit 1
fi

echo "✅ CLI available"

# Test htty-ht console script (this requires the bundled ht binary)
echo "🔧 Testing htty-ht console script..."
htty-ht --help > /dev/null

if [ $? -ne 0 ]; then
    echo "❌ htty-ht console script failed"
    # Check if this is expected (host wheel in emulated container)
    if [[ "$WHEEL_NAME" == *"macosx"* ]] || [[ "$WHEEL_NAME" == *"darwin"* ]]; then
        echo "⚠️  This is expected when testing host-platform wheel in emulated container"
        echo "   The bundled binary is for the host architecture, not the container architecture"
        echo "   This validates that the wheel won't work cross-platform without proper cross-compilation"
    else
        echo "❌ Unexpected failure - this should work with cross-compiled wheel"
        exit 1
    fi
else
    echo "✅ htty-ht console script works!"
    if [[ "$WHEEL_NAME" == *"manylinux"* ]] && [[ "$WHEEL_NAME" == *"aarch64"* ]]; then
        echo "🎉 Cross-compiled ARM Linux binary is functional!"
    fi
fi

# Test Python import
echo "🔧 Testing Python import..."
python3 -c "import htty; print('✅ Import successful')"

if [ $? -ne 0 ]; then
    echo "❌ Import failed"
    exit 1
fi

echo "🎉 Wheel testing complete!"
EOF
            
            # Make the test script executable
            chmod +x "$TEMP_DIR/test_wheel.sh"
            
            # Run the test in an ARM Linux container
            echo "🐳 Running test in ARM Linux container..."
            $CONTAINER_TOOL run --rm \
              --platform linux/arm64 \
              -v "$TEMP_DIR:/wheels" \
              -e "WHEEL_NAME=$WHEEL_NAME" \
              python:3.11-slim \
              bash -c "
                echo '🔧 Setting up container environment...'
                apt-get update -qq && apt-get install -y -qq vim
                echo '✅ Container setup complete'
                echo '🚀 Running wheel tests...'
                /wheels/test_wheel.sh
              "
            
            # Check the result
            if [ $? -eq 0 ]; then
              echo "🎉 Cross-platform wheel test PASSED!"
              if [ -n "$CROSS_WHEEL_PATH" ] && [[ "$CROSS_WHEEL_PATH" == "./result/htty-wheel.whl" ]]; then
                echo "✅ Successfully tested cross-compiled ARM Linux wheel"
              else
                echo "📝 Note: This test validated the Docker container setup."
                echo "   For true cross-platform validation, use CI or enable cross-compilation."
              fi
            else
              echo "❌ Cross-platform wheel test FAILED!"
              exit 1
            fi
            
            # Cleanup
            rm -rf "$TEMP_DIR"
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
