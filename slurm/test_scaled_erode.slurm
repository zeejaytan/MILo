#!/bin/bash
#SBATCH --job-name=scaled_erode
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=4:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/scaled_erode_%j.log
set -uo pipefail
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
for tool in DensifyPointCloud ReconstructMesh; do [[ -x "$OPENMVS_BIN/$tool" ]] || { echo "Missing $OPENMVS_BIN/$tool"; exit 1; }; done
echo "=== Scaled erode 4-6 per blob for $GROUP on $(hostname) $(date) ==="
nvidia-smi | head -5 || true
ls -lh "$W_BASE/scene.mvs" | head -5
MASK_SCALED="$W_BASE/masks/openmvs_scaled46/"
echo "Mask scaled: $MASK_SCALED ($(ls $MASK_SCALED/*.png 2>/dev/null | wc -l) files) - per-blob 4px small -> 6px large"
MASK_BASE="$W_BASE/masks/openmvs/"
echo "Mask base: $MASK_BASE ($(ls $MASK_BASE/*.png 2>/dev/null | wc -l) files)"

run_one(){
  local SUFFIX=$1
  local FUSE=$2
  local MASKPATH=$3
  local OUTDIR="$W_BASE/dense_test_${SUFFIX}"
  step "Test $SUFFIX: fuse=$FUSE mask=$MASKPATH -> $OUTDIR"
  rm -rf "$OUTDIR"
  mkdir -p "$OUTDIR"
  ln -s "$W_BASE/images" "$OUTDIR/images"
  ln -s "$W_BASE/sparse" "$OUTDIR/sparse"
  cp "$W_BASE/scene.mvs" "$OUTDIR/scene.mvs"
  "$OPENMVS_BIN/DensifyPointCloud" -w "$OUTDIR" -i "$OUTDIR/scene.mvs" -o "$OUTDIR/scene_dense.mvs" --cuda-device 0 --resolution-level 0 --number-views 8 --number-views-fuse "$FUSE" --crop-to-roi 0 --mask-path "$MASKPATH" --ignore-mask-label 0 2>&1 | tail -n 80
  echo "Densify $SUFFIX exit $?"
  ls -lh "$OUTDIR/scene_dense.mvs" "$OUTDIR"/*.ply 2>&1 | head -20
  "$OPENMVS_BIN/ReconstructMesh" -w "$OUTDIR" -i "$OUTDIR/scene_dense.mvs" -p "$OUTDIR/scene_dense.ply" -o "$OUTDIR/scene_dense_mesh.ply" --target-face-num 10000000 --crop-to-roi 0 2>&1 | tail -n 50
  echo "Reconstruct $SUFFIX exit $?"
  ls -lh "$OUTDIR/scene_dense_mesh.ply" 2>&1 | head -5
  python3 << PY
import numpy as np, re, struct
ply="$OUTDIR/scene_dense_mesh.ply"
scale=388.401128
with open(ply,'rb') as f:
    hdr=[]
    while True:
        l=f.readline()
        hdr.append(l.decode(errors='ignore'))
        if 'end_header' in l.decode(errors='ignore'):
            hdr_end=f.tell()
            break
    import re
    vcount=int(re.search(r'element vertex\s+(\d+)', ''.join(hdr)).group(1))
    f.seek(hdr_end)
    verts=np.fromfile(f, dtype=np.float32, count=vcount*3).reshape(vcount,3)
    verts_mm=verts*scale
    tip_c1=np.array([-104.8,-58.9,-57.6])
    tip_c5=np.array([139.2,9.9,-118.1])
    for label,tip in [("c1",tip_c1),("c5",tip_c5)]:
        d=np.linalg.norm(verts_mm-tip,axis=1)
        print(f"{label} nearest {d.min():.2f}mm within5 {(d<5).sum()} within10 {(d<10).sum()}")
    print(f"{ply} {vcount} verts bounds {verts_mm.min(axis=0)} {verts_mm.max(axis=0)}")
PY
  ls -lh "$OUTDIR" 2>&1 | head -20
}
run_one "scaled46_fuse5" 5 "$MASK_SCALED"
run_one "scaled46_fuse6" 6 "$MASK_SCALED"
step "All scaled tests done. Summary:"
ls -lh "$W_BASE"/dense_test_scaled*/scene_dense_mesh.ply 2>&1 | awk '{print $5, $9}'
echo "=== finished $(date) ==="
