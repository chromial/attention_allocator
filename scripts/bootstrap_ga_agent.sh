#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
#PROJECT_DIR="${PROJECT_DIR:-$HOME/projects/ga_agent}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

NVIDIA_DRIVER_PKG="${NVIDIA_DRIVER_PKG:-nvidia-driver-580-open}"
NVIDIA_UTILS_PKG="${NVIDIA_UTILS_PKG:-nvidia-utils-580}"

TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu121}"

log() { printf "\n\033[1m==>\033[0m %s\n" "$*"; }
warn() { printf "\n\033[1;33m[WARN]\033[0m %s\n" "$*"; }
die() { printf "\n\033[1;31m[ERR]\033[0m %s\n" "$*"; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }

secure_boot_enabled() {
  # Returns 0 if enabled, 1 if disabled/unknown
  if command -v mokutil >/dev/null 2>&1; then
    mokutil --sb-state 2>/dev/null | grep -qi "SecureBoot enabled"
  else
    return 1
  fi
}

has_nvidia_devices() {
  ls /dev/nvidia* >/dev/null 2>&1
}

stage1() {
  log "Stage 1: OS deps + NVIDIA driver"
  need_cmd sudo
  need_cmd apt

  log "Updating apt"
  sudo apt update

  log "Installing baseline packages"
  sudo apt install -y \
    ca-certificates curl git build-essential \
    "${PYTHON_BIN}" "${PYTHON_BIN}-venv" python3-pip \
    mokutil pciutils

  if secure_boot_enabled; then
    warn "Secure Boot is ENABLED. NVIDIA driver may fail to load unless MOK is enrolled."
    warn "If your firmware is flaky (MSI often is), consider disabling Secure Boot in BIOS."
  else
    log "Secure Boot appears disabled (good)."
  fi

  log "Installing NVIDIA driver: ${NVIDIA_DRIVER_PKG}"
  sudo apt install -y "${NVIDIA_DRIVER_PKG}"

  log "Installing NVIDIA utils (nvidia-smi): ${NVIDIA_UTILS_PKG}"
  sudo apt install -y "${NVIDIA_UTILS_PKG}" || warn "Could not install ${NVIDIA_UTILS_PKG} (may still be fine)."

  log "Stage 1 done."
  warn "Reboot required now. Run: sudo reboot"
  warn "After reboot run: ./bootstrap_ga_agent.sh stage2"
}

stage2() {
  log "Stage 2: Verify GPU stack, then Python env + ML deps"

  if secure_boot_enabled; then
    die "Secure Boot is ENABLED. Disable it (or complete MOK enrollment) before continuing."
  fi

  if ! has_nvidia_devices; then
    die "No /dev/nvidia* devices. Driver not loaded. Run: nvidia-smi and fix driver before stage2."
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    warn "nvidia-smi missing; installing ${NVIDIA_UTILS_PKG}"
    sudo apt install -y "${NVIDIA_UTILS_PKG}"
  fi

  log "nvidia-smi:"
  nvidia-smi || die "nvidia-smi failed; driver still not healthy."

  log "Ensure project dir: ${PROJECT_DIR}"
  mkdir -p "${PROJECT_DIR}"
  cd "${PROJECT_DIR}"

  log "Create venv: ${VENV_DIR}"
  if [ ! -d "${VENV_DIR}" ]; then
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  else
    warn "Venv exists; reusing."
  fi

  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"

  log "Upgrade pip"
  pip install --upgrade pip

  log "Install torch CUDA wheels"
  pip install torch --index-url "${TORCH_INDEX_URL}"

  log "Install ML/data deps (Murphy shield)"
  pip install -U numpy pandas scikit-learn

  log "Verify Python packages + CUDA"
  python - << 'EOF'
import numpy as np, pandas as pd, sklearn, torch
print("numpy:", np.__version__)
print("pandas:", pd.__version__)
print("sklearn:", sklearn.__version__)
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
    print("torch cuda:", torch.version.cuda)
EOF

  log "Freeze requirements"
  pip freeze > requirements.txt

  log "Done. Your environment is set and pinned."
  log "Next: python main.py"
}

usage() {
  cat << 'EOF'
Usage:
  ./bootstrap_ga_agent.sh stage1   # installs OS deps + NVIDIA driver; then you reboot
  ./bootstrap_ga_agent.sh stage2   # verifies driver/CUDA; sets up venv + installs deps; freezes requirements
EOF
}

case "${1:-}" in
  stage1) stage1 ;;
  stage2) stage2 ;;
  -h|--help|help|"") usage ;;
  *) die "Unknown argument: $1" ;;
esac
