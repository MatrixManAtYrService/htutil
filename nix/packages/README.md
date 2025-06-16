# htutil Package Outputs

This directory contains the essential Nix packages for htutil, following Blueprint conventions.

## Package Structure

### Main Packages

#### `htutil.nix`
The main htutil package:
- Contains htutil with all Python dependencies
- Uses system `ht` binary from PATH or `HTUTIL_HT_BIN` environment variable
- Clean, minimal package for most use cases
- Build with: `nix build .#htutil`

Usage:
```bash
# Build and use with system ht
nix build .#htutil
./result/bin/htutil -- echo "Hello"

# Use with custom ht binary
HTUTIL_HT_BIN=/path/to/custom/ht ./result/bin/htutil -- echo "Hello"
```

#### `htutil-bundled.nix`
Self-contained package with bundled ht binary:
- Includes both htutil and the ht binary
- No external dependencies required
- Perfect for distribution or isolated environments
- Build with: `nix build .#htutil-bundled`

Usage:
```bash
# Build self-contained package
nix build .#htutil-bundled

# Works without ht in PATH
./result/bin/htutil -- echo "Hello"

# Still respects HTUTIL_HT_BIN if set
HTUTIL_HT_BIN=/custom/ht ./result/bin/htutil -- echo "Hello"
```

#### `htutil-release-tests.nix`
Comprehensive release testing package:
- Tests across multiple Python versions
- Validates package integrity
- Used for release verification
- Build with: `nix build .#htutil-release-tests`

### Supporting Files

#### `lib/` Directory
Contains shared utilities and configuration:
- `internal.nix`: Common Python environment setup
- `htutil-packages.nix`: Package exports for Blueprint
- `test-config.nix`: Shared test configuration
- `test-vim.nix`: Pinned vim version for stable testing

## HTUTIL_HT_BIN Environment Variable

All packages support the `HTUTIL_HT_BIN` environment variable with this precedence:

1. **`HTUTIL_HT_BIN`**: User-specified ht binary (if valid and executable)
2. **Bundled ht**: Built-in ht binary (htutil-bundled only)
3. **System PATH**: Default `ht` command

## Blueprint Integration

Packages are automatically discovered by Blueprint:
- `htutil` → Main package
- `htutil-bundled` → Bundled variant
- `htutil-release-tests` → Testing package

View all packages: `nix flake show`

## Development

For development with immediate rebuilds on source changes:
```bash
# Enter development environment
nix develop

# Run with hot reloading
nix run .#htutil -- your-command

# Run tests
nix build .#checks-full
```

## Distribution

- **Individual users**: Use `htutil` (requires ht on system)
- **Self-contained deployment**: Use `htutil-bundled`
- **Custom ht binary**: Set `HTUTIL_HT_BIN` environment variable

## Notes

- All packages use uv2nix for dependency management
- Clean separation between bundled and unbundled variants
- Full test coverage for environment variable functionality
- Follows Nix best practices for package organization
