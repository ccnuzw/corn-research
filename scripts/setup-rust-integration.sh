#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${CORN_RUST_VENV:-$ROOT/.venv/corn-rs}"

# Keep the existing application environment intact; PyO3 0.22 needs an older Python.
if [[ ! -x "$VENV/bin/python" ]]; then
    if command -v uv >/dev/null 2>&1; then
        uv venv --python 3.12 "$VENV"
    elif command -v python3.12 >/dev/null 2>&1; then
        python3.12 -m venv "$VENV"
    else
        echo 'Install Python 3.12 (or uv), then rerun this script.' >&2
        exit 1
    fi
fi

"$VENV/bin/python" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12 for this test environment"'
if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$VENV/bin/python" 'maturin>=1.4,<2' 'pytest>=8,<10'
else
    "$VENV/bin/python" -m pip install 'maturin>=1.4,<2' 'pytest>=8,<10'
fi

export VIRTUAL_ENV="$VENV"
export PATH="$VENV/bin:$PATH"
if [[ "$(uname -s)" == Darwin ]]; then
    # Avoid Rosetta's xcrun dispatch to an incompatible CommandLineTools library.
    TOOLS=/Library/Developer/CommandLineTools
    if [[ -x "$TOOLS/usr/bin/clang" ]]; then
        export CC="${CC:-$TOOLS/usr/bin/clang}"
        export CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER="${CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER:-$CC}"
        if [[ -d "$TOOLS/SDKs/MacOSX.sdk" ]]; then
            export SDKROOT="${SDKROOT:-$TOOLS/SDKs/MacOSX.sdk}"
        fi
    fi
    # The installed macOS 27 SDK produces proc-macro dylibs rejected by dyld.
    if [[ -d "$TOOLS/SDKs/MacOSX26.5.sdk" ]]; then
        export SDKROOT="$TOOLS/SDKs/MacOSX26.5.sdk"
        export RUSTFLAGS="${RUSTFLAGS:-} -C link-arg=-Wl,-sdk_version,26.5"
    fi
fi

cd "$ROOT/core-rust/corn-python"
maturin develop --release
cd "$ROOT"
"$VENV/bin/python" tests/test_integration.py
echo "Run again: $VENV/bin/python tests/test_integration.py"
