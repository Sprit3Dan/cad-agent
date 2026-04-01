#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.env"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

die() {
  echo "[cad-agent] error: $*" >&2
  exit 1
}

log() {
  echo "[cad-agent] $*" >&2
}

show_help() {
  cat <<'EOF'
CAD Agent gateway (agent-friendly command gateway)

Usage:
  ./cad.sh <command> [args...]

Commands:
  setup
      Create local venv and install dependencies.

  doctor
      Validate runtime (venv + key packages).

  build [CLI args...]
      Build model from executable code file.
      Example:
        ./cad.sh build --code-file workspace/part.py --name part

  render [CLI args...]
      Build + render PNG.
      Example:
        ./cad.sh render --code-file workspace/part.py --name part --mode 3d --view iso --output renders/part_iso.png

  export [CLI args...]
      Build + export stl/step/3mf.
      Example:
        ./cad.sh export --code-file workspace/part.py --name part --format stl --output exports/part.stl

  measure [CLI args...]
      Build + measure dimensions/geometry.
      Example:
        ./cad.sh measure --code-file workspace/part.py --name part

  all --code-file <file> [--name <name>] [--view <view>] [--stl <path>] [--step <path>] [--render <path>]
      Convenience pipeline: render + measure + stl export + step export.

  cli [args...]
      Raw passthrough to src.cli.
      Example:
        ./cad.sh cli --help

  shell
      Open interactive shell.

  help
      Show this help.

Notes:
  - This gateway always uses .env/bin/python.
  - Run './cad.sh setup' once before first use.
EOF
}

ensure_venv() {
  [[ -x "${PYTHON_BIN}" ]] || die "venv not found. Run: ./cad.sh setup"
}

run_cli() {
  ensure_venv
  "${PYTHON_BIN}" -m src.cli "$@"
}

cmd_setup() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    log "creating virtual environment at .env"
    python3 -m venv "${VENV_DIR}"
  fi
  log "upgrading pip"
  "${PYTHON_BIN}" -m pip install --upgrade pip
  log "installing dependencies"
  "${PYTHON_BIN}" -m pip install -r "${ROOT_DIR}/requirements.txt"
  log "setup complete"
}

cmd_doctor() {
  ensure_venv
  "${PYTHON_BIN}" -V
  "${PYTHON_BIN}" -m pip --version
  "${PYTHON_BIN}" - <<'PY'
import importlib.util
pkgs = ["build123d", "numpy", "PIL", "trimesh", "matplotlib", "cairosvg", "svgwrite"]
missing = [p for p in pkgs if importlib.util.find_spec(p) is None]
if missing:
    raise SystemExit(f"Missing packages: {missing}")
print("doctor: ok")
PY
}

cmd_all() {
  ensure_venv

  local code_file=""
  local name="default"
  local view="iso"
  local render_out="renders/model_iso.png"
  local stl_out="exports/model.stl"
  local step_out="exports/model.step"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-file) code_file="$2"; shift 2 ;;
      --name) name="$2"; shift 2 ;;
      --view) view="$2"; shift 2 ;;
      --render) render_out="$2"; shift 2 ;;
      --stl) stl_out="$2"; shift 2 ;;
      --step) step_out="$2"; shift 2 ;;
      *)
        die "unknown flag for all: $1"
        ;;
    esac
  done

  [[ -n "${code_file}" ]] || die "all requires --code-file <file>"

  mkdir -p "$(dirname "${render_out}")" "$(dirname "${stl_out}")" "$(dirname "${step_out}")"

  log "rendering 3d preview"
  run_cli render --code-file "${code_file}" --name "${name}" --mode 3d --view "${view}" --output "${render_out}"

  log "measuring model"
  run_cli measure --code-file "${code_file}" --name "${name}"

  log "exporting STL"
  run_cli export --code-file "${code_file}" --name "${name}" --format stl --output "${stl_out}"

  log "exporting STEP"
  run_cli export --code-file "${code_file}" --name "${name}" --format step --output "${step_out}"
}

main() {
  local cmd="${1:-help}"
  shift || true

  case "${cmd}" in
    help|-h|--help) show_help ;;
    setup) cmd_setup "$@" ;;
    doctor) cmd_doctor "$@" ;;
    build) run_cli build "$@" ;;
    render) run_cli render "$@" ;;
    export) run_cli export "$@" ;;
    measure) run_cli measure "$@" ;;
    all) cmd_all "$@" ;;
    cli) run_cli "$@" ;;
    shell) exec /bin/bash ;;
    *)
      die "unknown command: ${cmd}. Run './cad.sh help'"
      ;;
  esac
}

main "$@"