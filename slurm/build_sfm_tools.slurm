#!/bin/bash
#SBATCH --job-name=build-sfm
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
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
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/build_sfm_tools.slurm

TOOLS=/data/gpfs/projects/punim2657/tools
ENV_PREFIX=$TOOLS/sfm
OPENMVS_SRC=$TOOLS/src/openMVS
VCG_SRC=$TOOLS/src/VCG
OPENMVS_BUILD=$TOOLS/src/openMVS_build
OPENMVS_PREFIX=$TOOLS/openmvs-2.4.0

COLMAP_VERSION="${COLMAP_VERSION:-4.1.1}"
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
if [[ ! -x "$ENV_PREFIX/bin/colmap" ]]; then
    conda create -y -p "$ENV_PREFIX" -c conda-forge \
        "colmap=${COLMAP_VERSION}=cuda*" \
        cmake ninja pkg-config \
        opencv cgal-cpp boost-cpp eigen glew gmp mpfr \
        libpng libjpeg-turbo libtiff zlib
else
    echo "environment already present at $ENV_PREFIX"
fi
conda activate "$ENV_PREFIX"

step "verify COLMAP has CUDA compiled in"
colmap -h 2>&1 | head -3
if ! colmap -h 2>&1 | head -3 | grep -qi cuda; then
    echo "COLMAP reports no CUDA support — the cpu_ build was installed." >&2
    exit 1
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
# CUDA from the module system, not conda: it must match the driver on the GPU nodes, and
# the module is what every other job here already uses.
module load GCC/11.3.0 OpenMPI/4.1.4 CUDA/11.8.0
export CUDA_HOME="${EBROOTCUDA:?}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
nvcc --version | tail -2

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

step "summary"
echo "COLMAP   : $ENV_PREFIX/bin/colmap"
colmap -h 2>&1 | sed -n '1,2p'
echo "OpenMVS  : $OPENMVS_PREFIX/bin/OpenMVS"
echo
echo "The old toolchain is untouched:"
echo "  COLMAP 3.9  : module load COLMAP/3.9-CUDA-11.7.0"
echo "  OpenMVS 2.3 : /data/gpfs/projects/punim2657/Photogrammetry/openmvs/install/bin/OpenMVS"
echo
echo "The binaries link against CUDA and cannot be exercised on this CPU node; the first"
echo "reconstruction on a GPU node is what proves them."
echo "=== finished $(date) ==="
