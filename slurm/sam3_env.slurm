#!/bin/bash
#SBATCH --job-name=sam3-env
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=2:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/sam3_env_%j.log

set -uo pipefail

# Build the SAM 3 environment, following the upstream README verbatim rather than from
# memory. Commands as published at github.com/facebookresearch/sam3:
#
#   conda create -n sam3 python=3.12
#   pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
#   git clone https://github.com/facebookresearch/sam3.git && cd sam3 && pip install -e .
#
# cu128 matches Spartan's 12.8 driver, so this avoids the CUDA-version fight that the
# COLMAP build turned into. Requirements are Python 3.12+, PyTorch 2.7+, CUDA 12.6+.
#
# NO CHECKPOINTS ARE DOWNLOADED HERE. SAM 3 weights are access-gated: the README says
# "Before using SAM 3, please request access to the checkpoints on the SAM 3 Hugging Face
# repo". That request needs a human and Meta's approval, so the environment is built ready
# and the weights come later. SAM 3.1 (checkpoints released 2026-03-27) is the version to
# use, at huggingface.co/facebook/sam3.1.
#
# Authentication, when access is granted, is the USER's to do -- run `hf auth login` on
# Spartan. Do not paste a token into a chat; the same rule applied to the Mediaflux
# credential, and a token belongs in ~/.cache/huggingface/ with the permissions the tool
# sets, not in a transcript.
#
# Usage:
#   sbatch slurm/sam3_env.slurm

TOOLS=/data/gpfs/projects/punim2657/tools
ENV_PREFIX=$TOOLS/sam3
SRC=$TOOLS/src/sam3

echo "=== SAM 3 environment build started $(date) on $(hostname) ==="

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"

# Fail early if the wheel index is unreachable, rather than part-way through a 3 GB
# download. The compute nodes were verified to reach github and huggingface; the pytorch
# ROOT url returns 403, which is normal, so probe the actual index path instead.
echo "=== reachability ==="
for u in https://github.com https://huggingface.co https://download.pytorch.org/whl/cu128/; do
    code=$(timeout 30 curl -sS -o /dev/null -w "%{http_code}" "$u" 2>/dev/null)
    echo "  $u -> $code"
    [[ "$code" =~ ^(200|301|302)$ ]] || { echo "  UNREACHABLE, stopping" >&2; exit 1; }
done

if [[ -x "$ENV_PREFIX/bin/python" ]]; then
    echo "=== env already exists at $ENV_PREFIX, reusing ==="
else
    echo "=== creating env (python 3.12) ==="
    conda create -y -p "$ENV_PREFIX" python=3.12 || exit 1
fi
conda activate "$ENV_PREFIX"
export PYTHONNOUSERSITE=1
python -V

echo
echo "=== torch 2.10.0 + cu128 ==="
python -c "import torch" 2>/dev/null && echo "  torch already present" || \
    pip install --quiet torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print('  torch', torch.__version__, '| cuda build', torch.version.cuda)"

echo
echo "=== sam3 source ==="
mkdir -p "$(dirname "$SRC")"
if [[ -d "$SRC/.git" ]]; then
    git -C "$SRC" pull --ff-only 2>&1 | tail -2
else
    git clone --depth 1 https://github.com/facebookresearch/sam3.git "$SRC" 2>&1 | tail -2
fi
echo "  pinned at: $(git -C "$SRC" rev-parse --short HEAD 2>/dev/null)"

echo
echo "=== pip install -e . ==="
cd "$SRC" && pip install --quiet -e . 2>&1 | tail -5
echo "  (exit $?)"

echo
# Three fixes found by building it, none of which the README mentions.
#
# setuptools<81: the repo's model_builder.py imports pkg_resources, which setuptools
# REMOVED (a fresh Python 3.12 env lands on 84.0.0 and the import fails outright).
#
# einops, pycocotools, psutil: imported by sam3 but absent from its pyproject.toml
# dependency list, so `pip install -e .` does not pull them in.
echo "=== dependencies the upstream package does not declare ==="
pip install --quiet "setuptools<81" einops pycocotools psutil 2>&1 | tail -3
python -c "import pkg_resources, einops, pycocotools, psutil; print('  undeclared deps OK')" 2>&1 | tail -1

echo
echo "=== import check (no weights needed) ==="
python - <<'PY'
try:
    import sam3
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor
    print("  sam3 imports OK -- build_sam3_image_model and Sam3Processor available")
except Exception as e:
    print(f"  IMPORT FAILED: {type(e).__name__}: {e}")
    raise SystemExit(1)
PY

echo
echo "=== huggingface auth status (expected: not logged in yet) ==="
python -c "
from huggingface_hub import HfFolder
t = HfFolder.get_token()
print('  token present' if t else '  no token -- run: hf auth login')
" 2>/dev/null || echo "  huggingface_hub not importable yet"

echo
echo "NEXT, and only you can do it:"
echo "  1. Request access at https://huggingface.co/facebook/sam3.1"
echo "  2. Once approved, on Spartan, ALL FOUR LINES -- conda is not on PATH by default"
echo "     here, so 'conda activate' alone fails with 'command not found':"
echo
echo "       module load Miniforge3/24.7.1-2"
echo "       eval \"\$(conda shell.bash hook)\""
echo "       conda activate $ENV_PREFIX"
echo "       hf auth login"
echo
echo "     (paste the token into that prompt, not into a chat)"
echo "  3. Then the 6-frame test can run."
echo "=== finished $(date) ==="
