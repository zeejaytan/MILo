#!/usr/bin/env python3
"""
Build a MILo dataset from an existing COLMAP run of the pottery photogrammetry pipeline.

The sherd captures already have a turntable-tuned COLMAP reconstruction produced by
`Photogrammetry/pipeline/bin/pipeline_main.sh`. There is no reason to run structure-from-
motion a second time: MILo reads the same sparse model. This script wires the two together
without copying a single photograph.

What it makes, given a `work_colmap_openmvs/` directory:

    <out>/images/          -> symlink to <work>/dense/images   (COLMAP's undistorted views)
    <out>/sparse/0/           copy of <work>/dense/sparse      (MILo wants the "0" level)
    <out>/images_masked/      RGBA copies, alpha = the sherd mask   (only with masks)
    <out>/mask_overlays/      a handful of PNGs to LOOK at before training
    <out>/capture.json        provenance: paths, counts, scale factor, held-out views

Masks matter here. On a turntable the backdrop is the one thing that does not move with
the sherd, so training on unmasked photographs spends Gaussians modelling the background
and softens the sherd's silhouette. This script refuses to guess: it checks that every
mask lines up with the undistorted view it belongs to, and if it cannot prove that, it
stops and says so rather than producing a dataset that trains on the wrong thing.

Usage:
    python scripts/colmap_to_milo.py \\
        --work /data/gpfs/projects/punim2657/Rabati2025/16062025/work_colmap_openmvs \\
        --out  /data/gpfs/projects/punim2657/MILo/data/16062025

    # proceed without masks, knowing the backdrop will be reconstructed too
    python scripts/colmap_to_milo.py --work ... --out ... --no-masks
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image as PILImage

# Reuse MILo's own COLMAP reader rather than writing a second one: if it can parse the
# model, so can training. Loaded from its file rather than imported as `scene.colmap_loader`
# — the package's __init__ drags in torch and the whole scene stack, which this script has
# no use for and which would stop it running outside the training environment.
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_colmap_loader():
    import importlib.util

    path = _REPO_ROOT / "milo" / "scene" / "colmap_loader.py"
    spec = importlib.util.spec_from_file_location("milo_colmap_loader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_colmap = _load_colmap_loader()
read_extrinsics_binary = _colmap.read_extrinsics_binary
read_extrinsics_text = _colmap.read_extrinsics_text
read_intrinsics_binary = _colmap.read_intrinsics_binary
read_intrinsics_text = _colmap.read_intrinsics_text

# MILo holds out every Nth view for evaluation (llffhold in scene/dataset_readers.py).
# Recorded here so the comparison stage knows which views neither method ever saw.
LLFF_HOLD = 8


class AdapterError(RuntimeError):
    pass


def read_colmap_model(sparse_dir: Path):
    """Return (extrinsics, intrinsics) from a COLMAP model directory, bin or txt."""
    if (sparse_dir / "images.bin").exists():
        return (
            read_extrinsics_binary(str(sparse_dir / "images.bin")),
            read_intrinsics_binary(str(sparse_dir / "cameras.bin")),
        )
    if (sparse_dir / "images.txt").exists():
        return (
            read_extrinsics_text(str(sparse_dir / "images.txt")),
            read_intrinsics_text(str(sparse_dir / "cameras.txt")),
        )
    raise AdapterError(f"No COLMAP model (images.bin/.txt) in {sparse_dir}")


def link_or_copy(src: Path, dst: Path, copy: bool = False) -> str:
    """Symlink src -> dst, falling back to a copy where symlinks are unavailable."""
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not copy:
        try:
            dst.symlink_to(src, target_is_directory=src.is_dir())
            return "symlink"
        except (OSError, NotImplementedError):
            pass
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return "copy"


def read_scale_factor(work: Path) -> dict:
    """
    Read the millimetre scale for this capture, if it has been measured.

    Two things can be true and they lead to different actions, so both are reported:
      - a factor exists in <work>/scale/SCALE.txt, and
      - whether pipeline/bin/scale_apply.py has already baked it into the sparse model,
        in which case the model (and any mesh from it) is ALREADY metric and applying
        the factor again would shrink the sherd by that factor a second time.
    """
    out = {"scale_factor": None, "scale_source": None, "already_applied": None}
    scale_dir = work / "scale"
    scale_file = scale_dir / "SCALE.txt"
    if scale_file.exists():
        try:
            out["scale_factor"] = float(scale_file.read_text().strip().split()[0])
            out["scale_source"] = str(scale_file)
        except (ValueError, IndexError):
            out["scale_source"] = f"{scale_file} (unparseable)"
    # scale_apply.py writes this log only when it has rewritten the sparse model.
    applied_log = scale_dir / "scale_log.txt"
    out["already_applied"] = applied_log.exists()
    return out


def build_masked_images(
    work: Path,
    images_dir: Path,
    out_dir: Path,
    image_names: list[str],
    overlay_dir: Path,
    n_overlays: int = 6,
) -> dict:
    """
    Write RGBA copies of the undistorted views with the sherd mask in the alpha channel.

    MILo (via 3DGS's reader) picks the alpha channel up automatically when an image has
    four channels, and this fork's train.py patch is what actually applies it to the loss.

    Filenames keep the ORIGINAL extension on purpose. readColmapCameras looks the image up
    by the exact name recorded in the COLMAP model, extension included; a file renamed to
    .png would simply not be found. PIL identifies the format from the file's contents, so
    PNG bytes under a .JPG name load correctly.
    """
    masks_dir = work / "masks_user"
    if not masks_dir.is_dir():
        raise AdapterError(
            f"No masks at {masks_dir}.\n"
            "Generate them with the photogrammetry pipeline first:\n"
            "  python pipeline/bin/maskbuild.py user-init   --images <photos> --work <work>\n"
            "  (edit mask_build_user/coarse_model.ply -> edited_model.ply)\n"
            "  python pipeline/bin/maskbuild.py user-project --work <work> "
            "--mesh <work>/mask_build_user/edited_model.ply\n"
            "Or pass --no-masks to train on the backdrop as well, knowing that it will "
            "consume Gaussians and soften the sherd's outline."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)

    missing, mismatched, coverage = [], [], []
    overlay_stride = max(1, len(image_names) // n_overlays)

    for idx, name in enumerate(sorted(image_names)):
        img_path = images_dir / name
        mask_path = masks_dir / (Path(name).stem + ".png")
        if not mask_path.exists():
            missing.append(name)
            continue

        img = PILImage.open(img_path).convert("RGB")
        mask = PILImage.open(mask_path).convert("L")

        # A mask of the wrong size is the failure that would otherwise pass silently:
        # the masks are projected from the coarse build, while these views come out of
        # COLMAP's undistorter, and the two need not share a resolution or a distortion
        # model. Resampling would hide the misalignment rather than fix it.
        if mask.size != img.size:
            mismatched.append((name, mask.size, img.size))
            continue

        arr = np.asarray(mask)
        coverage.append(float((arr > 127).mean()))

        rgba = img.copy()
        rgba.putalpha(mask)
        rgba.save(out_dir / name, format="PNG")

        if idx % overlay_stride == 0 and len(list(overlay_dir.glob("*.png"))) < n_overlays:
            _write_overlay(img, mask, overlay_dir / f"overlay_{Path(name).stem}.png")

    if mismatched:
        head = "\n".join(f"    {n}: mask {m} vs image {i}" for n, m, i in mismatched[:5])
        raise AdapterError(
            f"{len(mismatched)} mask(s) do not match their undistorted view:\n{head}\n"
            "The masks were projected from a different camera geometry than the images "
            "MILo will train on. Re-project them against the undistorted sparse model "
            f"in the workspace under {work}, or pass --no-masks."
        )
    if missing:
        raise AdapterError(
            f"{len(missing)} of {len(image_names)} views have no mask "
            f"(first: {missing[:3]}). A partly-masked capture trains on backdrop in the "
            "unmasked views only, which is worse than either extreme. Regenerate the "
            "masks or pass --no-masks."
        )

    return {
        "masks_dir": str(masks_dir),
        "masked_images": len(image_names),
        "mask_coverage_mean": float(np.mean(coverage)) if coverage else None,
        "mask_coverage_min": float(np.min(coverage)) if coverage else None,
        "mask_coverage_max": float(np.max(coverage)) if coverage else None,
    }


def _write_overlay(img: PILImage.Image, mask: PILImage.Image, path: Path) -> None:
    """Draw the mask boundary over the photograph so a person can check it by eye."""
    rgb = np.asarray(img).astype(np.float32)
    m = (np.asarray(mask) > 127).astype(np.float32)

    # 1-pixel boundary via the difference between the mask and its shifted copies.
    edge = np.zeros_like(m)
    edge[1:, :] = np.maximum(edge[1:, :], np.abs(m[1:, :] - m[:-1, :]))
    edge[:, 1:] = np.maximum(edge[:, 1:], np.abs(m[:, 1:] - m[:, :-1]))

    out = rgb * (0.35 + 0.65 * m[..., None])          # dim the background
    out[edge > 0] = np.array([255.0, 0.0, 0.0])        # red boundary
    PILImage.fromarray(out.clip(0, 255).astype(np.uint8)).save(path)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a MILo dataset from a pottery-photogrammetry COLMAP run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--work", required=True, type=Path,
                    help="work_colmap_openmvs directory of an existing capture")
    ap.add_argument("--out", required=True, type=Path,
                    help="MILo dataset directory to create (e.g. .../MILo/data/16062025)")
    ap.add_argument("--dense-dir", default="dense",
                    help="name of the undistorted workspace inside --work. The pipeline "
                         "writes 'dense'; dense_from_model.slurm writes 'dense_<tag>' so "
                         "that a corrected model does not overwrite an earlier one. Which "
                         "one is used matters more than any training setting: on tree A01 "
                         "the GLOMAP model collapsed the turntable rotation and duplicated "
                         "every sherd, while scoring the BETTER reprojection error.")
    ap.add_argument("--no-masks", action="store_true",
                    help="skip masking; trains on the backdrop as well")
    ap.add_argument("--copy", action="store_true",
                    help="copy the images too (only if the filesystem forbids symlinks)")
    ap.add_argument("--link-sparse", action="store_true",
                    help="symlink the sparse model instead of copying it; MILo will then "
                         "write points3D.ply into the photogrammetry work directory")
    args = ap.parse_args()

    work: Path = args.work.resolve()
    out: Path = args.out.resolve()

    dense = work / args.dense_dir
    src_images = dense / "images"
    src_sparse = dense / "sparse"
    if not src_images.is_dir():
        raise AdapterError(
            f"No undistorted images at {src_images}. Run the COLMAP stage first:\n"
            f"  bash pipeline/bin/pipeline_main.sh <date>/<tree>"
        )
    if not src_sparse.is_dir():
        raise AdapterError(f"No undistorted sparse model at {src_sparse}")

    if not (src_sparse / "points3D.bin").exists() and not (src_sparse / "points3D.txt").exists():
        raise AdapterError(
            f"No points3D in {src_sparse}. MILo initialises its Gaussians from the sparse "
            "point cloud and cannot start without it."
        )

    out.mkdir(parents=True, exist_ok=True)

    # Images are symlinked — a full-resolution capture is not duplicated.
    mode_images = link_or_copy(src_images, out / "images", copy=args.copy)

    # The sparse model is COPIED, deliberately. MILo writes points3D.ply into sparse/0
    # the first time it loads a scene (scene/dataset_readers.py). Through a symlink that
    # write would land inside the photogrammetry pipeline's own work directory. The model
    # is a few tens of megabytes against many gigabytes of photographs, so copying it
    # costs nothing worth having.
    mode_sparse = link_or_copy(src_sparse, out / "sparse" / "0", copy=not args.link_sparse)

    extrinsics, intrinsics = read_colmap_model(out / "sparse" / "0")
    image_names = [im.name for im in extrinsics.values()]

    # Every registered view must resolve to a file on disk. A model that references an
    # image the undistorter never wrote will fail deep inside training instead of here.
    absent = [n for n in image_names if not (src_images / n).exists()]
    if absent:
        raise AdapterError(
            f"{len(absent)} of {len(image_names)} registered views are missing from "
            f"{src_images} (first: {absent[:3]})"
        )

    models = sorted({intrinsics[c].model for c in intrinsics})
    if not set(models) <= {"PINHOLE", "SIMPLE_PINHOLE"}:
        print(
            f"[warn] undistorted model reports camera type(s) {models}; COLMAP's "
            "undistorter normally emits PINHOLE. Check that --output_type is default.",
            file=sys.stderr,
        )

    mask_info = {"masks_dir": None, "masked_images": 0}
    images_arg = "images"
    if not args.no_masks:
        mask_info = build_masked_images(
            work=work,
            images_dir=src_images,
            out_dir=out / "images_masked",
            image_names=image_names,
            overlay_dir=out / "mask_overlays",
        )
        images_arg = "images_masked"

    held_out = sorted(image_names)[::LLFF_HOLD]
    scale = read_scale_factor(work)

    capture = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "work_dir": str(work),
        "dataset_dir": str(out),
        "source_images": str(src_images),
        "source_sparse": str(src_sparse),
        "link_mode": {"images": mode_images, "sparse": mode_sparse},
        "n_images_registered": len(image_names),
        "n_images_on_disk": len(list(src_images.iterdir())),
        "camera_models": models,
        "masks": mask_info,
        "train_images_arg": images_arg,
        "llffhold": LLFF_HOLD,
        "held_out_views": held_out,
        "scale": scale,
    }
    (out / "capture.json").write_text(json.dumps(capture, indent=2))

    print(f"Dataset ready: {out}")
    print(f"  views registered : {len(image_names)}")
    print(f"  images dir       : {images_arg} ({mode_images})")
    if mask_info["masked_images"]:
        print(
            f"  mask coverage    : mean {mask_info['mask_coverage_mean']:.1%} "
            f"(min {mask_info['mask_coverage_min']:.1%}, "
            f"max {mask_info['mask_coverage_max']:.1%})"
        )
        print(f"  LOOK AT THESE first: {out / 'mask_overlays'}")
    else:
        print("  masks            : NONE — the backdrop will be reconstructed too")
    if scale["scale_factor"] is not None:
        state = "already applied to the sparse model" if scale["already_applied"] \
            else "measured but NOT applied"
        print(f"  scale            : {scale['scale_factor']:.9f} ({state})")
    else:
        print("  scale            : not measured — meshes will be in arbitrary units")
    print(f"  held out         : every {LLFF_HOLD}th view ({len(held_out)} views)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AdapterError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        sys.exit(1)
