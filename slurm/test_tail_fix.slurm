#!/bin/bash
#SBATCH --job-name=tail_fix
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=4:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/tail_fix_%j.log

set -uo pipefail

# Tail artefact A/B tests for 03072025/N01
# - Already verified tail exists in dense point cloud (fused.ply 528k) and in scene_dense_mesh.ply before RefineMesh
#   (see local renders /tmp/compare_c1_dense_vs_refined.png). RefineMesh is not the source.
# - This job isolates two levers:
#   A) number_views_fuse 5 -> 7 and 8 (stricter fusion, drops points seen in <7/8 views)
#   B) dilated ignore region (erode white by 3px) at clamp contacts
# All runs reuse the same sparse solve (dense_incremental/scene.mvs, 119 cams, 88k points) so geometry is comparable.

GROUP="03072025/N01"
W_BASE="/data/gpfs/projects/punim2657/Rabati2025/03072025/N01/work_colmap_openmvs/dense_incremental"
TOOLS=/data/gpfs/projects/punim2657/tools
OPENMVS_BIN=$TOOLS/openmvs-2.4.0/bin/OpenMVS
SFM_ENV=$TOOLS/sfm

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$SFM_ENV/lib:${LD_LIBRARY_PATH:-}"

step(){ echo; echo "=== $* ($(date +%H:%M:%S)) ==="; }

for tool in DensifyPointCloud ReconstructMesh; do
  [[ -x "$OPENMVS_BIN/$tool" ]] || { echo "Missing $OPENMVS_BIN/$tool"; exit 1; }
done

echo "=== Tail fix A/B for $GROUP on $(hostname) $(date) ==="
nvidia-smi | head -5 || true
ls -lh "$W_BASE/scene.mvs" "$W_BASE/masks/openmvs/" | head -20

# Keep original undistorted masks as baseline
MASK_BASE="$W_BASE/masks/openmvs/"
echo "Mask base: $MASK_BASE ($(ls $MASK_BASE/*.png 2>/dev/null | wc -l) files)"

# Helper: run densify+fuse->reconstruct for a given suffix and fuse param and mask path
run_one(){
  local SUFFIX=$1   # e.g. fuse7, fuse8, dilate3
  local FUSE=$2
  local MASKPATH=$3 # must end with /
  local OUTDIR="$W_BASE/dense_test_${SUFFIX}"
  echo
  step "Test $SUFFIX: Densify fuse=$FUSE mask=$MASKPATH -> $OUTDIR"
  rm -rf "$OUTDIR"
  mkdir -p "$OUTDIR"
  # Reuse scene.mvs and sparse/images from W_BASE: Densify -w controls working dir, -i is input, -o is output
  # We need a minimal scene.mvs copy? Densify reads -w for cache; easiest is to run with -w $OUTDIR but -i $W_BASE/scene.mvs
  # It will write depth maps under $OUTDIR/stereo etc.
  "$OPENMVS_BIN/DensifyPointCloud" -w "$OUTDIR" -i "$W_BASE/scene.mvs" -o "$OUTDIR/scene_dense.mvs" \
    --cuda-device 0 --resolution-level 0 --number-views 8 --number-views-fuse "$FUSE" --crop-to-roi 0 \
    --mask-path "$MASKPATH" --ignore-mask-label 0 2>&1 | tail -n 50
  echo "Densify $SUFFIX exit $?"
  ls -lh "$OUTDIR/scene_dense.mvs" "$OUTDIR"/*.ply 2>&1 | head -20
  # Also capture depth count and fused ply size
  ls -lh "$OUTDIR/fused.ply" 2>&1 | head -5 || echo "no fused.ply yet - Densify writes scene_dense.ply"
  ls "$OUTDIR"/*.ply 2>&1 | head -5
  "$OPENMVS_BIN/ReconstructMesh" -w "$OUTDIR" -i "$OUTDIR/scene_dense.mvs" -p "$OUTDIR/scene_dense.ply" -o "$OUTDIR/scene_dense_mesh.ply" --target-face-num 10000000 --crop-to-roi 0 2>&1 | tail -n 30
  echo "Reconstruct $SUFFIX exit $?"
  ls -lh "$OUTDIR/scene_dense_mesh.ply" 2>&1 | head -5
  # Quick QC: count vertices and check for tail tip proximity (python)
  python3 << PY
import numpy as np, re, struct, os
ply="$OUTDIR/scene_dense_mesh.ply"
# ply is in colmap units, need scale 388.4 to mm for comparison
scale=388.401128
with open(ply,'rb') as f:
    hdr=[]
    while True:
        l=f.readline()
        hdr.append(l.decode(errors='ignore'))
        if 'end_header' in l.decode(errors='ignore'):
            hdr_end=f.tell()
            break
    txt=''.join(hdr)
    import re
    vcount=int(re.search(r'element vertex\s+(\d+)',txt).group(1))
    f.seek(hdr_end)
    verts=np.fromfile(f, dtype=np.float32, count=vcount*3).reshape(vcount,3)
    verts_mm=verts*scale
    # tail tips from baseline refined
    tip_c1=np.array([-104.8,-58.9,-57.6])
    tip_c5=np.array([139.2,9.9,-118.1])
    for label,tip in [("c1",tip_c1),("c5",tip_c5)]:
        d=np.linalg.norm(verts_mm-tip,axis=1)
        print(f"{label} nearest {d.min():.2f}mm within5 {(d<5).sum()} within10 {(d<10).sum()}")
    print(f"{ply} {vcount} verts bounds {verts_mm.min(axis=0)} {verts_mm.max(axis=0)}")
PY
  ls -lh "$OUTDIR" 2>&1 | head -20
}

# A) Strict fusion tests (same masks, higher fuse)
run_one "fuse7" 7 "$MASK_BASE"
run_one "fuse8" 8 "$MASK_BASE"

# B) Dilated ignore region: erode white by 3px (so expand black)
step "B: Creating dilated masks (erode white 3px) -> $W_BASE/masks/openmvs_dilate3/"
DILATED="$W_BASE/masks/openmvs_dilate3/"
rm -rf "$DILATED"
mkdir -p "$DILATED"
python3 << 'PY'
import glob, os, cv2, numpy as np, PIL.Image
src="/data/gpfs/projects/punim2657/Rabati2025/03072025/N01/work_colmap_openmvs/dense_incremental/masks/openmvs"
dst="/data/gpfs/projects/punim2657/Rabati2025/03072025/N01/work_colmap_openmvs/dense_incremental/masks/openmvs_dilate3"
os.makedirs(dst, exist_ok=True)
import pathlib
for f in sorted(glob.glob(src+"/*.png")):
    im=PIL.Image.open(f)
    # masks are RGB but white region is (255,255,255), black is (0,0,0); convert to L
    if im.mode!="L":
        arr=np.array(im.convert("L"))
    else:
        arr=np.array(im)
    # White=255 keep, black=0 ignore. Erode white by 3px => kernel 3
    # Use 3 iterations of 3x3 == 3px radius? Single iteration with 7x7 gives 3px each side
    kernel=np.ones((7,7),np.uint8)
    eroded=cv2.erode(arr, kernel, iterations=1)
    # Preserve exactly binary 0/255
    eroded=np.where(eroded>127,255,0).astype(np.uint8)
    out=os.path.join(dst, os.path.basename(f))
    PIL.Image.fromarray(eroded).save(out)
    # stats for first few
    if "8241" in f or "8242" in f:
        print(f"{os.path.basename(f)} white { (arr==255).sum()} -> { (eroded==255).sum()} diff {(arr==255).sum()-(eroded==255).sum()}")

PY
ls "$DILATED" | wc -l | xargs echo "dilated masks count:"
ls -lh "$DILATED" | head -5

run_one "dilate3_fuse5" 5 "$DILATED"
run_one "dilate3_fuse7" 7 "$DILATED"

step "All tests done. Summary listing:"
ls -lh "$W_BASE"/dense_test_*/scene_dense_mesh.ply 2>&1 | awk '{print $5, $9}'
echo "=== finished $(date) ==="
