#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUST_MANIFEST="${ROOT_DIR}/packages/file_parser/rust/Cargo.toml"
WHEEL_DIR="${ROOT_DIR}/packages/file_parser/rust/target/wheels"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"

if [[ -f "${HOME}/.cargo/env" ]]; then
  # Ensure cargo/rustc are on PATH for this shell.
  # shellcheck disable=SC1090
  source "${HOME}/.cargo/env"
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "error: cargo not found. Install Rust toolchain first." >&2
  exit 1
fi

MATURIN="${ROOT_DIR}/.venv/bin/maturin"
if [[ ! -x "${MATURIN}" ]]; then
  MATURIN="$(command -v maturin || true)"
fi
if [[ -z "${MATURIN}" ]]; then
  echo "error: maturin not found. Run: uv sync --all-packages --group dev" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv not found. Install uv first." >&2
  exit 1
fi

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "error: ${VENV_PYTHON} missing. Run: uv sync --group dev" >&2
  exit 1
fi

echo "Building wheel with maturin..."
"${MATURIN}" build --release --manifest-path "${RUST_MANIFEST}" -o "${WHEEL_DIR}"

echo "Installing wheel into .venv..."
uv pip install --python "${VENV_PYTHON}" --reinstall --no-deps \
  "${WHEEL_DIR}/mainframe_tools-"*.whl

echo "Done. Verifying import..."
"${VENV_PYTHON}" -c "import mainframe_tools; print('mainframe_tools OK')"

