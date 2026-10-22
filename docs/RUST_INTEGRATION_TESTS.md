# Python/Rust integration test environment

## Setup and execution

Run from the repository root:

```bash
bash scripts/setup-rust-integration.sh
.venv/corn-rs/bin/python tests/test_integration.py
.venv/corn-rs/bin/python -m pytest tests/test_integration.py -v
```

Alternatively, activate the dedicated environment first:

```bash
source .venv/corn-rs/bin/activate
python tests/test_integration.py
```

The setup script creates a Python 3.12 environment inside the ignored `.venv/`
directory without replacing the original Python environment. It installs maturin
and pytest, runs `maturin develop --release` in `core-rust/corn-python`, then
executes the integration tests. A Rust toolchain and Python 3.12 (or uv) are
required. Package downloads require network access on first setup.

The extension is installed only in this environment. Running the system Python,
or the original `.venv/bin/python`, does not use this installation.

## Resolved blockers

- The original environment uses Python 3.9, while the binding package requires
  Python 3.11 or newer. System Python 3.14 is not supported by the existing
  PyO3 0.22 dependency. This test environment uses Python 3.12.
- The binding used old PyO3 dictionary/module APIs. It now uses `Bound`/`Py`
  APIs compatible with PyO3 0.22. Missing processing fields raise Python
  `KeyError` rather than panicking in Rust.
- Database repositories imported a record type from the disabled Python bridge.
  The shared persistence type now lives in `corn-infrastructure/src/raw_record.rs`;
  the bridge re-exports it to retain the existing type path if enabled later.
- The local macOS 27 SDK produced proc-macro libraries rejected by dyld with
  `mis-aligned LINKEDIT string pool`. When installed, the setup script selects
  the macOS 26.5 SDK and passes its SDK version to the linker. It also selects
  the CommandLineTools compiler explicitly to avoid the local Rosetta/xcrun
  architecture mismatch. Other platforms use their normal toolchain.
- The previous smoke script swallowed `ImportError` and exited successfully.
  The test now contains assertions and exits nonzero when the extension is
  unavailable or an assertion fails.

## Verification on 2026-10-22

Environment: macOS arm64 extension, CPython 3.12.13, PyO3 0.22.6,
maturin 1.15.0, rustc 1.96.1, pytest 9.1.1.

| Command | Observed result |
| --- | --- |
| `bash scripts/setup-rust-integration.sh` | Release build and editable installation succeeded; 9 tests passed. |
| `.venv/corn-rs/bin/python -m pytest tests/test_integration.py -v` | 9 passed, 2 subtests passed. |
| `.venv/corn-rs/bin/python tests/test_rust_services.py` | Existing smoke script completed all four service examples. |
| `python3 tests/test_integration.py` using system Python 3.14 | Exit 1 with installation/interpreter instructions, as expected. |
| `bash -n scripts/setup-rust-integration.sh` | Passed. |

Quality-score example: `calculate_quality_score(0.9, 1.0, 0.95)` returns `0.855`.
The nine assertion tests cover scoring, invalid scoring, processing, value
filtering, missing fields, invalid types, deduplication, validation and empty input.
These are real in-process Python/Rust binding tests, not HTTP/database end-to-end
tests. They do not establish that the Docker services or external sources work.

During linker investigation, Homebrew lld 23.1.4 and its LLVM 23.1.4/z3 5.3.1
dependencies were installed. The original active LLVM 22.1.8 and z3 4.16.0 opt
links were restored; the successful setup does not require lld. Existing unused
import and SQLx future-compatibility warnings remain non-blocking.
