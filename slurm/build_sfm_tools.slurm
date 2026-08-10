#!/bin/bash
#SBATCH --job-name=build-sfm
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=08:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/build_sfm_%j.log

set -euo pipefail

# Build current COLMAP and OpenMVS for the pottery captures.
#
# WHY. Spartan's COLMAP module is 3.9, built from a commit dated 2023-10-09 and installed
# in October 2023 — nearly three years old and a major version behind. Upstream is 4.1.1.
# Two changes since then bear on the registration trouble on these captures:
#
#   * COLMAP 4.0 absorbed GLOMAP as a first-class `global_mapper`. It solves all camera
#     poses together instead of growing from a seed pair, so it does not have the failure
#     that registered 2 of 68 photographs on A11.
#   * One-to-many matches are now kept in the correspondence graph. Previously only
#     one-to-one matches were used during reconstruction, discarding verified matches.
#
# The locally built OpenMVS is 2.3.0 (October 2025); upstream is 2.4.0.
#
# HOW. COLMAP comes prebuilt with CUDA from conda-forge, so it is installed, not compiled.
# OpenMVS is not packaged anywhere and must be built — but its dependencies (OpenCV, CGAL,
# Boost, Eigen) come from conda-forge rather than vcpkg, which is what made the previous
# build take hours: vcpkg compiles all of them from source, conda-forge ships them built.
#
# Nothing here touches the existing COLMAP module or the existing OpenMVS install. Both
# stay exactly where they are, so a comparison against the old toolchain remains possible
# and nothing that currently works is put at risk.
#
# WHY A GPU NODE. Compiling does not need one — nvcc cross-compiles, and the target
# architectures are set explicitly below rather than auto-detected. Two other things do:
#   * Linking. Anything touching the CUDA driver API needs libcuda.so.1, which ships with
#     the driver and is absent on CPU nodes. A stub exists for this, but only if cmake
#     finds it; on the login node OpenMVS already failed with
#     "libcuda.so.1: cannot open shared object file".
#   * Testing. A build that COMPILES is not a build that WORKS. Verifying here costs
#     minutes; discovering it during a reconstruction wastes a GPU job and muddles the
#     diagnosis of whatever else that run was meant to answer.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/build_sfm_tools.slurm

TOOLS=/data/gpfs/projects/punim2657/tools
ENV_PREFIX=$TOOLS/sfm
OPENMVS_SRC=$TOOLS/src/openMVS
VCG_SRC=$TOOLS/src/VCG
OPENMVS_BUILD=$TOOLS/src/openMVS_build
OPENMVS_PREFIX=$TOOLS/openmvs-2.4.0

COLMAP_VERSION="${COLMAP_VERSION:-4.1.1}"
# cuda | cpu. The cpu build still provides global_mapper, which is CPU work anyway, so it
# is a real fallback rather than a defeat if the CUDA override below does not hold.
COLMAP_BUILD="${COLMAP_BUILD:-cuda}"
# 1 = compile COLMAP against the CUDA 12.8 toolkit instead of installing the conda
# package. This is the honest way out of the driver-version problem rather than a
# fallback: every conda-forge COLMAP CUDA build demands a 12.9 driver and Spartan's is
# 12.8, so the packaged route needs CONDA_OVERRIDE_CUDA and depends on CUDA's
# minor-version compatibility holding for every code path the reconstruction touches.
# Compiled against 12.8, the binary needs 12.8, and that is the end of the question.
# The constraint belongs to the colmap PACKAGE, not to its dependencies, so ceres, eigen,
# freeimage, glog, flann and the rest still come prebuilt from conda-forge and only
# COLMAP itself is compiled.
COLMAP_FROM_SOURCE="${COLMAP_FROM_SOURCE:-0}"
COLMAP_SRC=$TOOLS/src/colmap
COLMAP_BUILD_DIR=$TOOLS/src/colmap_build
OPENMVS_TAG="${OPENMVS_TAG:-v2.4.0}"
NPROC="${SLURM_CPUS_PER_TASK:-16}"

echo "=== SfM toolchain build started $(date) on $(hostname) ==="
echo "COLMAP  : $COLMAP_VERSION (conda-forge, CUDA build)"
echo "OpenMVS : $OPENMVS_TAG (source)"
echo "Prefix  : $TOOLS"

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
export PYTHONNOUSERSITE=1

mkdir -p "$TOOLS/src"

# ---------------------------------------------------------------------------------------
step() { echo; echo "=== $* ==="; }

step "COLMAP $COLMAP_VERSION + OpenMVS build dependencies (conda-forge)"
# The CUDA variant is selected explicitly: conda will otherwise happily pick the cpu_
# build, which would silently drop GPU feature extraction and matching and only show up
# as a very slow reconstruction.
#
# EVERY conda-forge COLMAP 4.x CUDA build declares `__cuda >= 12.9`. Spartan's driver is
# 570.211.01, which supports CUDA 12.8 — one minor version short, so the solver refuses:
#   "nothing provides __cuda >=12.9 needed by colmap-4.1.1-cuda_129ha585b08_1"
#
# That declaration is conda-forge's packaging metadata, not an NVIDIA requirement. CUDA
# 12.x guarantees minor-version compatibility: a binary built against the 12.9 runtime
# runs on any 12.x driver, unless it calls a driver entry point introduced after the
# driver's own version. Overriding the check is therefore reasonable, but it IS a
# gamble — which is precisely why the GPU verification below is not optional. If COLMAP
# cannot initialise the GPU, this job fails rather than leaving a toolchain that installs
# cleanly and dies during a reconstruction.
export CONDA_OVERRIDE_CUDA="${CONDA_OVERRIDE_CUDA:-12.9}"
echo "CONDA_OVERRIDE_CUDA=$CONDA_OVERRIDE_CUDA (driver reports CUDA 12.8)"
# Only what OpenMVS needs to BUILD is listed. An earlier attempt also pinned boost-cpp,
# zlib, libpng, libjpeg-turbo and libtiff, and the solve failed: boost-cpp is the retired
# package name and conflicts with COLMAP's libboost >=1.90, while pinning zlib conflicts
# with the libzlib >=1.3.2 that libsqlite wants. The image libraries arrive with opencv
# anyway. Naming fewer packages leaves the solver free to find a consistent set.
if [[ ! -d "$ENV_PREFIX" ]]; then
    if [[ "$COLMAP_FROM_SOURCE" == "1" ]]; then
        # COLMAP's own build dependencies, plus OpenMVS's. No colmap package, so no
        # __cuda constraint enters the solve at all.
        conda create -y -p "$ENV_PREFIX" -c conda-forge \
            cmake ninja pkg-config git \
            ceres-solver eigen freeimage glew glog gflags flann metis sqlite lz4 \
            opencv cgal-cpp libboost-devel gmp mpfr
    else
        conda create -y -p "$ENV_PREFIX" -c conda-forge \
            "colmap=${COLMAP_VERSION}=${COLMAP_BUILD}*" \
            cmake ninja pkg-config \
            opencv cgal-cpp libboost-devel eigen glew gmp mpfr
    fi
else
    echo "environment already present at $ENV_PREFIX"
fi
conda activate "$ENV_PREFIX"

# CUDA comes from the module system for everything compiled here, so the binaries need
# exactly the driver this cluster has.
module load GCC/11.3.0 OpenMPI/4.1.4 CUDA/12.8.0
export CUDA_HOME="${EBROOTCUDA:?}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
nvcc --version | tail -2

if [[ "$COLMAP_FROM_SOURCE" == "1" ]]; then
    step "COLMAP $COLMAP_VERSION from source, against CUDA 12.8"
    if [[ ! -d "$COLMAP_SRC/.git" ]]; then
        git clone --depth 1 --branch "$COLMAP_VERSION" \
            https://github.com/colmap/colmap.git "$COLMAP_SRC"
    fi
    rm -rf "$COLMAP_BUILD_DIR"
    cmake -S "$COLMAP_SRC" -B "$COLMAP_BUILD_DIR" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$ENV_PREFIX" \
        -DCMAKE_PREFIX_PATH="$ENV_PREFIX" \
        -DCUDA_ENABLED=ON \
        -DCMAKE_CUDA_ARCHITECTURES="80;89;90" \
        -DGUI_ENABLED=OFF \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cmake --build "$COLMAP_BUILD_DIR" -j "$NPROC"
    cmake --install "$COLMAP_BUILD_DIR"
fi

step "verify the COLMAP build variant is the one asked for"
colmap -h 2>&1 | head -3
if [[ "$COLMAP_BUILD" == "cuda" || "$COLMAP_FROM_SOURCE" == "1" ]]; then
    if ! colmap -h 2>&1 | head -3 | grep -qi cuda; then
        echo "Expected a CUDA-enabled COLMAP but it reports none." >&2
        exit 1
    fi
fi

step "OpenMVS sources ($OPENMVS_TAG)"
if [[ ! -d "$OPENMVS_SRC/.git" ]]; then
    git clone --depth 1 --branch "$OPENMVS_TAG" \
        https://github.com/cdcseacave/openMVS.git "$OPENMVS_SRC"
else
    git -C "$OPENMVS_SRC" fetch --depth 1 origin "$OPENMVS_TAG"
    git -C "$OPENMVS_SRC" checkout -q FETCH_HEAD
fi
# VCG is a header-only library OpenMVS needs and does not vendor.
if [[ ! -d "$VCG_SRC/.git" ]]; then
    git clone --depth 1 https://github.com/cdcseacave/VCG.git "$VCG_SRC"
fi
grep -E "OpenMVS_(MAJOR|MINOR|PATCH)_VERSION " "$OPENMVS_SRC/CMakeLists.txt" | head -3

step "configure OpenMVS"
# CUDA 12.8 was already loaded above and is used for everything compiled in this job:
# it is the highest the driver supports, so the binaries run here without relying on
# minor-version compatibility. An earlier version loaded 11.8 at this point, which would
# have built OpenMVS against a different CUDA from COLMAP in the same environment.
echo "building against CUDA $(nvcc --version | sed -n 's/.*release \([0-9.]*\).*/\1/p' | tail -1)"

rm -rf "$OPENMVS_BUILD"; mkdir -p "$OPENMVS_BUILD"
cmake -S "$OPENMVS_SRC" -B "$OPENMVS_BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$OPENMVS_PREFIX" \
    -DCMAKE_PREFIX_PATH="$ENV_PREFIX" \
    -DVCG_ROOT="$VCG_SRC" \
    -DOpenMVS_USE_CUDA=ON \
    -DOpenMVS_USE_OPENMP=ON \
    -DOpenMVS_BUILD_TOOLS=ON \
    -DCMAKE_CUDA_ARCHITECTURES="80;89;90" \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5

step "build OpenMVS with $NPROC cores"
cmake --build "$OPENMVS_BUILD" -j "$NPROC"
cmake --install "$OPENMVS_BUILD"

step "what was installed"
ls "$OPENMVS_PREFIX/bin/OpenMVS" 2>/dev/null || ls "$OPENMVS_PREFIX/bin"

step "verify on the GPU"
# The point of building here. A binary that compiled and linked is not a binary that
# runs: the driver library only exists on a node with a GPU, so this is the first moment
# either tool can actually be exercised.
FAILED=0

echo "--- OpenMVS binaries load the driver library"
for tool in DensifyPointCloud ReconstructMesh RefineMesh InterfaceCOLMAP TextureMesh; do
    if "$OPENMVS_PREFIX/bin/OpenMVS/$tool" --help >/dev/null 2>&1; then
        echo "    $tool: runs"
    else
        # --help exits non-zero in some OpenMVS tools; a missing library does not even
        # get that far, so distinguish the two.
        if "$OPENMVS_PREFIX/bin/OpenMVS/$tool" --help 2>&1 | grep -qi "cannot open shared object"; then
            echo "    $tool: FAILED to load libraries" >&2; FAILED=1
        else
            echo "    $tool: runs (non-zero exit from --help, which is normal)"
        fi
    fi
done

echo "--- COLMAP sees the GPU"
# Feature extraction with use_gpu 1 on an empty database exercises the CUDA/OpenGL path
# far enough to fail loudly if the GPU is unusable, without needing any images.
TMPDB=$(mktemp -d)/probe.db
if colmap feature_extractor --database_path "$TMPDB" --image_path "$TOOLS/src" \
        --SiftExtraction.use_gpu 1 2>&1 | grep -qiE "cuda error|no cuda|failed to initialize"; then
    echo "    COLMAP could not use the GPU" >&2; FAILED=1
else
    echo "    COLMAP GPU path initialised"
fi

echo "--- global mapper present (the reason for upgrading)"
if colmap help 2>&1 | grep -q global_mapper || colmap global_mapper -h >/dev/null 2>&1; then
    echo "    global_mapper: available"
else
    echo "    global_mapper: MISSING — this build cannot do global SfM" >&2; FAILED=1
fi

step "summary"
echo "COLMAP   : $ENV_PREFIX/bin/colmap"
colmap -h 2>&1 | sed -n '1,2p'
echo "OpenMVS  : $OPENMVS_PREFIX/bin/OpenMVS"
echo
echo "The old toolchain is untouched:"
echo "  COLMAP 3.9  : module load COLMAP/3.9-CUDA-11.7.0"
echo "  OpenMVS 2.3 : /data/gpfs/projects/punim2657/Photogrammetry/openmvs/install/bin/OpenMVS"

if [[ "$FAILED" -ne 0 ]]; then
    echo
    echo "BUILD COMPLETED BUT VERIFICATION FAILED — do not reconstruct with this." >&2
    echo >&2
    echo "If the failure is COLMAP not initialising the GPU, the 12.9-over-12.8 override" >&2
    echo "did not hold. There is a fallback that costs little: the global mapper is CPU" >&2
    echo "work, so the cpu_ build of COLMAP 4.1.1 still provides the thing we upgraded" >&2
    echo "for. Feature extraction and matching can keep using the GPU through the" >&2
    echo "existing COLMAP 3.9 module, whose database 4.x reads. Rebuild with:" >&2
    echo "  COLMAP_BUILD=cpu sbatch slurm/build_sfm_tools.slurm" >&2
    echo "and set MAPPER=global in reconstruct_group.slurm as usual." >&2
    exit 1
fi
echo
echo "Verified on $(hostname) with a GPU present."
echo "=== finished $(date) ==="
