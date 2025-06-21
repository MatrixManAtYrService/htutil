.PHONY: help clean build-ht bundle-ht wheel dev-install test lint format

# Default target
help:
	@echo "Available targets:"
	@echo "  wheel        - Build wheel with bundled ht binary (runs build-ht, bundle-ht, then builds wheel)"
	@echo "  build-ht     - Clone and build the ht binary from the fork"
	@echo "  bundle-ht    - Copy built ht binary to bundled directory"
	@echo "  dev-install  - Install development dependencies"
	@echo "  test         - Run test suite"
	@echo "  lint         - Run linting"
	@echo "  format       - Run code formatting"
	@echo "  clean        - Clean up build artifacts"

# Variables
HT_DIR := ./ht-build
HT_BINARY := $(HT_DIR)/target/release/ht
BUNDLED_DIR := src/htty/_bundled
BUNDLED_BINARY := $(BUNDLED_DIR)/ht

# Build the ht binary from the fork
build-ht:
	@echo "Building ht binary from fork..."
	@if [ ! -d "$(HT_DIR)" ]; then \
		echo "Cloning ht fork..."; \
		git clone https://github.com/MatrixManAtYrService/ht.git $(HT_DIR); \
	fi
	@cd $(HT_DIR) && cargo build --release
	@echo "ht binary built at $(HT_BINARY)"

# Bundle the ht binary into the Python package
bundle-ht: $(HT_BINARY)
	@echo "Bundling ht binary..."
	@mkdir -p $(BUNDLED_DIR)
	@cp $(HT_BINARY) $(BUNDLED_BINARY)
	@chmod +x $(BUNDLED_BINARY)
	@echo "ht binary bundled at $(BUNDLED_BINARY)"

# Build the wheel with bundled binary
wheel: bundle-ht
	@echo "Building wheel..."
	@uv add --dev build hatchling
	@uv run python -m build --wheel
	@echo "Wheel built in dist/"
	@ls -la dist/*.whl

# Install development dependencies
dev-install:
	@echo "Installing development dependencies..."
	@uv sync --dev

# Run tests
test:
	@echo "Running tests..."
	@uv run pytest tests

# Run linting
lint:
	@echo "Running linting..."
	@uv run ruff check .

# Run formatting
format:
	@echo "Running formatting..."
	@uv run ruff format .

# Clean up build artifacts
clean:
	@echo "Cleaning up..."
	@rm -rf $(HT_DIR)
	@rm -rf $(BUNDLED_DIR)
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

# Check if ht binary exists
$(HT_BINARY):
	@if [ ! -f "$(HT_BINARY)" ]; then \
		echo "ht binary not found, building..."; \
		$(MAKE) build-ht; \
	fi 