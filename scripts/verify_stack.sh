#!/usr/bin/env bash
set -euo pipefail

echo "== Secure Boot =="
if command -v mokutil >/dev/null 2>&1; then
  mokutil --sb-state || true
else
  echo "mokutil not installed"
fi

echo
echo "== NVIDIA devices =="
ls /dev/nvidia* 2>/dev/null || echo "No /dev/nvidia* devices"

echo
echo "== nvidia-smi =="
command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi || echo "nvidia-smi missing or failing"

echo
echo "== Python / venv =="
python3 --version
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -c "import torch; print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print('device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)"
  python -c "import numpy, pandas, sklearn; print('numpy', numpy.__version__); print('pandas', pandas.__version__); print('sklearn', sklearn.__version__)"
else
  echo ".venv not found in current directory"
fi
