# htty Package Outputs

This directory contains the essential Nix packages for htty, following Blueprint conventions.

## Package Structure

### Main Packages

#### `htty.nix`
The main htty package:
- Contains htty with all Python dependencies
- Uses system `ht` binary from PATH or `HTTY_HT_BIN` environment variable
- Clean, minimal package for most use cases
- Build with: `nix build .#htty`

Usage:
```bash
# Build and use with system ht
nix build .#htty
./result/bin/htty -- echo "Hello"

# Use with custom ht binary
HTTY_HT_BIN=/path/to/custom/ht ./result/bin/htty -- echo "Hello"
```

#### `htty-bundled.nix`
Self-contained package with bundled ht binary:
- Includes both htty and the ht binary
- No external dependencies required
- Perfect for distribution or isolated environments
- Build with: `nix build .#htty-bundled`

Usage:
```bash
# Build self-contained package
nix build .#htty-bundled

# Works without ht in PATH
./result/bin/htty -- echo "Hello"

# Still respects HTTY_HT_BIN if set
HTTY_HT_BIN=/custom/ht ./result/bin/htty -- echo "Hello"
```

#### `htty-release-tests.nix`
Comprehensive release testing package:
- Tests across multiple Python versions
- Validates package integrity
- Used for release verification
- Build with: `nix build .#htty-release-tests`

### Supporting Files

#### `lib/` Directory
Contains shared utilities and configuration:
- `internal.nix`: Common Python environment setup
- `htty-packages.nix`: Package exports for Blueprint
- `test-config.nix`: Shared test configuration
- `test-vim.nix`: Pinned vim version for stable testing

## HTTY_HT_BIN Environment Variable

All packages support the `HTTY_HT_BIN` environment variable with this precedence:

1. **`HTTY_HT_BIN`**: User-specified ht binary (if valid and executable)
2. **Bundled ht**: Built-in ht binary (htty-bundled only)
3. **System PATH**: Default `ht` command

## Blueprint Integration

Packages are automatically discovered by Blueprint:
- `htty` → Main package
- `htty-bundled` → Bundled variant
- `htty-release-tests` → Testing package

View all packages: `nix flake show`

## Development

For development with immediate rebuilds on source changes:
```bash
# Enter development environment
nix develop

# Run with hot reloading
nix run .#htty -- your-command

# Run tests
nix build .#checks-full
```

## Distribution

- **Individual users**: Use `htty` (requires ht on system)
- **Self-contained deployment**: Use `htty-bundled`
- **Custom ht binary**: Set `HTTY_HT_BIN` environment variable

## Notes

- All packages use uv2nix for dependency management
- Clean separation between bundled and unbundled variants
- Full test coverage for environment variable functionality
- Follows Nix best practices for package organization
