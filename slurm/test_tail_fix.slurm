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

MASK_BASE="$W_BASE/masks/openmvs/"
echo "Mask base: $MASK_BASE ($(ls $MASK_BASE/*.png 2>/dev/null | wc -l) files)"

run_one(){
  local SUFFIX=$1
  local FUSE=$2
  local MASKPATH=$3
  local OUTDIR="$W_BASE/dense_test_${SUFFIX}"
  echo
  step "Test $SUFFIX: fuse=$FUSE mask=$MASKPATH -> $OUTDIR"
  rm -rf "$OUTDIR"
  mkdir -p "$OUTDIR"
  # Link required data for OpenMVS working dir: images, sparse, and scene.mvs
  ln -s "$W_BASE/images" "$OUTDIR/images"
  ln -s "$W_BASE/sparse" "$OUTDIR/sparse"
  cp "$W_BASE/scene.mvs" "$OUTDIR/scene.mvs"
  # Also link masks if needed? No, mask-path is absolute, so not needed
  "$OPENMVS_BIN/DensifyPointCloud" -w "$OUTDIR" -i "$OUTDIR/scene.mvs" -o "$OUTDIR/scene_dense.mvs" \
    --cuda-device 0 --resolution-level 0 --number-views 8 --number-views-fuse "$FUSE" --crop-to-roi 0 \
    --mask-path "$MASKPATH" --ignore-mask-label 0 2>&1 | tail -n 80
  echo "Densify $SUFFIX exit $?"
  ls -lh "$OUTDIR/scene_dense.mvs" "$OUTDIR"/*.ply 2>&1 | head -20
  ls -lh "$OUTDIR/fused.ply" 2>&1 | head -5 || echo "no fused.ply"
  ls "$OUTDIR"/*.ply 2>&1 | head -5
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

run_one "fuse7" 7 "$MASK_BASE"
run_one "fuse8" 8 "$MASK_BASE"

step "B: Creating dilated masks (erode white 3px) -> $W_BASE/masks/openmvs_dilate3/"
DILATED="$W_BASE/masks/openmvs_dilate3/"
rm -rf "$DILATED"
mkdir -p "$DILATED"
python3 << 'PY'
import glob, os, cv2, numpy as np, PIL.Image
src="/data/gpfs/projects/punim2657/Rabati2025/03072025/N01/work_colmap_openmvs/dense_incremental/masks/openmvs"
dst="/data/gpfs/projects/punim2657/Rabati2025/03072025/N01/work_colmap_openmvs/dense_incremental/masks/openmvs_dilate3"
os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(src+"/*.png")):
    im=PIL.Image.open(f)
    if im.mode!="L":
        arr=np.array(im.convert("L"))
    else:
        arr=np.array(im)
    kernel=np.ones((7,7),np.uint8)
    eroded=cv2.erode(arr, kernel, iterations=1)
    eroded=np.where(eroded>127,255,0).astype(np.uint8)
    out=os.path.join(dst, os.path.basename(f))
    PIL.Image.fromarray(eroded).save(out)
    if "8241" in f:
        print(f"{os.path.basename(f)} white { (arr==255).sum()} -> { (eroded==255).sum()} diff {(arr==255).sum()-(eroded==255).sum()}")

PY
ls "$DILATED" | wc -l | xargs echo "dilated masks count:"
ls -lh "$DILATED" | head -5

run_one "dilate3_fuse5" 5 "$DILATED"
run_one "dilate3_fuse7" 7 "$DILATED"

step "All tests done. Summary listing:"
ls -lh "$W_BASE"/dense_test_*/scene_dense_mesh.ply 2>&1 | awk '{print $5, $9}'
echo "=== finished $(date) ==="
