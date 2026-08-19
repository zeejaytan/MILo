"""Generate COLMAP masks for a whole tree with SAM 3, via the transformers API.

Replaces the standalone-repo version. The Hugging Face model card documents this path and
it avoids every problem the GitHub README route produced: no cloned repo, no editable
install, no `pkg_resources` against a setuptools that removed it, no undeclared
einops/pycocotools/psutil, and no bfloat16 autocast context to discover from example
notebooks. One dependency instead of a source tree.

WHAT PROMPT. This matters more than any parameter. On tree A01 the model returned ZERO
detections at every threshold down to 0.05 for "pottery", "ceramic", "sherd" and "pottery
fragment" -- it has no concept of pottery at all. It scores "clay fragment" at 0.88-0.91
and finds every sherd on the tree. Testing only the obvious words would have condemned SAM
3 as unusable for this material.

ORIENTATION. These files carry EXIF 8. COLMAP reads stored pixels and ignores the tag, so
masks must be written in stored orientation. Segmenting upright scored marginally better
(0.91 vs 0.88) but returned IDENTICAL counts, so this segments in stored orientation and
skips the invertible-rotation step -- one less thing to get silently wrong.

NAMING. COLMAP wants "<image filename>.png", keeping the original extension:
A11_0704.JPG -> A11_0704.JPG.png. The existing maskbuild tool writes "<stem>.png", which
COLMAP will not match, and a mask it cannot find is a mask it silently ignores.

FOUR MASK SETS, because the stages want different things and the difference is the whole
point of masking more than once:

  masks_object/   sherds AND the whole rig -- everything but the backdrop. FOR SOLVING THE
                  CAMERAS. The rod, clamps, base and dial all turn WITH the sherds, so in
                  the object's frame they never move and their features are consistent; the
                  painted metal and machined threads are the best-conditioned features in
                  the frame. Only the static room hurts, and removing it took A02 from a
                  folded 262 deg solve to a correct 348 deg one.
  masks_measure/  sherds AND the blue base, but NOT the clamps or rod. FOR BUILDING THE
                  SURFACE. The clamps are what has to be edited out of every mesh by hand,
                  and a clamp jaw resting on a sherd fuses to it, so they cannot be
                  separated afterwards as connected components. Removing them in 2D, before
                  any geometry exists, is the only point at which they come apart cleanly.
                  The base stays because it is the scale reference.
  masks_dial/     sherds, the base AND the turntable dial, but still no clamps or rod.
                  ALSO FOR BUILDING THE SURFACE, and the difference from masks_measure is
                  not about what should end up in the mesh -- it is about what dense stereo
                  needs in order to build the plate at all. OpenMVS applies masks BEFORE
                  depth estimation, so masking down to the plate leaves a smooth, almost
                  featureless surface with no textured neighbours to propagate depth from,
                  and on A03 it reconstructed the plate twice, at an angle. The graduated
                  dial sits directly behind the plate and is the nearest strongly textured
                  thing to it. A02, whose dense stage saw the whole scene, had no such
                  trouble with the same settings.
  masks_sherds/   sherds only. Kept for a sherds-only variant; note it has NO base, so a
                  mesh built from it cannot be checked against the 190 x 130 mm plate.

GROWN FOR SOLVING, SHRUNK FOR BUILDING. masks_object is dilated so features sitting on the
outline survive to be matched. Every other set is ERODED, because the same pixel is the
worst one in the frame for stereo: it straddles object and clamp, the patch being matched is
half of each, and the depth that comes back is wrong. Those wrong depths are what put spikes
on A03's sherds, and the part of one close enough to lie inside the sherd's own outline
survives silhouette carving -- which is blind there by construction.

WHY THE BASE IS SUBTRACTED, NOT JUST PROMPTED. The clamps are painted the same blue as the
base plate, so "blue board" also lands on clamp bodies. Prompting alone cannot separate two
objects of the same colour and material; subtracting the hardware mask from the base mask
can, and the per-frame figures printed at the end say how much of the base survived it.

Usage:
    python sam3_masks.py --images <dir> --out <dir> [--overlay-every 20]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

# Every prompt below was chosen by sweeping, not guessing, because the obvious word keeps
# returning nothing: "pottery"/"ceramic"/"sherd" score ZERO, and so do "blue plate" and
# "turntable". Scores are from tree A01, black backdrop / lit grey backdrop.
SHERD_PROMPTS = ["clay fragment"]                       # 0.93 / 0.92

# The rig is now split three ways, because masks_measure needs to keep the base while
# dropping the hardware. For masks_object they are unioned straight back together, so
# over-inclusion BETWEEN these groups is still harmless there -- only grabbing backdrop
# would hurt. It is masks_measure that depends on the split being right.
HARDWARE_PROMPTS = [
    "metal rod",            # 0.84 / 0.79  the rod, the arms and the clamps: what has to go
    "metal",
]
BASE_PROMPTS = [
    "blue board",           # 0.94 / 0.77  THE SCALE REFERENCE: a known 190 x 130 mm plate,
    "blue metal plate",     # 0.84 / 0.53  which every sherd measurement is derived from
]
TURNTABLE_PROMPTS = [
    "dial",                 # 0.81 / 0.36  graduated, rotates with the tree, strongly
    "round base",           # 0.54 / 0.74  textured -- useful rigid features for SOLVING,
]                           #              but not wanted in the finished surface


def encode_image(processor, model, image, device):
    """Encode the photograph ONCE. Sam3Model.forward accepts vision_embeds, so the vision
    tower does not have to re-run for every prompt -- which is what made the first
    transformers version 13.5 s/frame against 0.04 s on the standalone API."""
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.inference_mode():
        return model.get_vision_features(inputs["pixel_values"])


def union_mask(processor, model, vision_embeds, prompts, device, threshold, target_hw):
    """Union of all instances matched by any prompt, at the SEGMENTATION size.

    Deliberately not at full resolution. post_process_instance_segmentation upsamples
    every instance separately, and "metal rod" alone returns 24-89 of them; asking for
    5568x3712 each meant up to 1.8 billion pixels of mask resampling per frame, which is
    what actually made this slow -- not the vision encoder. The union is one mask, so it
    is cheaper to combine here and upscale once afterwards.
    """
    total = np.zeros(target_hw, bool)
    detail = {}
    for prompt in prompts:
        txt = processor(text=prompt, return_tensors="pt").to(device)
        with torch.inference_mode():
            outputs = model(vision_embeds=vision_embeds,
                            input_ids=txt["input_ids"],
                            attention_mask=txt.get("attention_mask"))
        res = processor.post_process_instance_segmentation(
            outputs, threshold=threshold, mask_threshold=0.5,
            target_sizes=[target_hw])[0]
        masks = res.get("masks")
        scores = res.get("scores")
        n = 0
        if masks is not None and len(masks):
            m = masks.detach().cpu().numpy()
            if m.ndim == 4:
                m = m[:, 0]
            total |= np.any(m > 0.5, axis=0)
            n = int(len(m))
        best = float(scores.max()) if scores is not None and len(scores) else 0.0
        detail[prompt] = dict(instances=n, best=round(best, 3))
    return total, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="facebook/sam3")
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--seg-side", type=int, default=2000,
                    help="segment at this longest side, then upscale the mask to full "
                         "resolution. Masks gate feature extraction, so a few pixels of "
                         "slop is harmless and the dilation below covers it.")
    ap.add_argument("--dilate", type=int, default=8,
                    help="grow the SOLVING mask (masks_object), so features ON the "
                         "silhouette survive to be matched")
    ap.add_argument("--erode-surface", type=int, default=6,
                    help="SHRINK the surface masks (masks_measure, masks_dial, "
                         "masks_sherds) by this many pixels instead of growing them. "
                         "Opposite directions on purpose. For SOLVING, a feature sitting on "
                         "the outline is useful and worth keeping. For BUILDING SURFACE it "
                         "is the worst pixel in the frame: it straddles object and clamp, "
                         "stereo has to match a patch that is half each, and the depth it "
                         "returns is wrong. Those wrong depths are what left a stub of "
                         "clamp welded to A03's sherds after the long spikes were carved "
                         "away -- the stub sits against the sherd, inside its outline, "
                         "where silhouette carving is blind by construction. Eroding costs "
                         "a known ~1 mm rim of real surface; not eroding costs an unknown "
                         "lump of invented one. Set to 0 to keep the old behaviour.")
    ap.add_argument("--overlay-every", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    # OFF, because the risk it defended against was measured and does not exist, while the
    # damage it does was measured and is severe. On tree A03 it destroyed 97% of the base
    # plate: 112 of 165 frames ended with NO scale reference at all.
    #
    # The worry was that "blue board" would also land on the clamps, which are painted the
    # same blue. sam3_prompt_diag.py says otherwise -- "blue board" claims 1.5% of the
    # frame and 83-100% of the plate, i.e. the plate and nothing else. What actually
    # happens is the reverse: "metal" claims 100% of the plate, because it is a blue METAL
    # plate, so subtracting the hardware mask subtracts the base along with it.
    #
    # masks_measure is a KEEP mask, so precise base prompts are all it ever needed.
    ap.add_argument("--subtract-hardware", action="store_true",
                    help="subtract the hardware mask from the base mask. OFF by default: "
                         "'metal' claims the blue metal plate, so this erases the scale "
                         "reference. Only useful if a future tree's base prompts really "
                         "do bleed onto the clamps -- check with sam3_prompt_diag.py "
                         "before turning it on.")
    args = ap.parse_args()

    import cv2
    from transformers import Sam3Model, Sam3Processor

    paths = sorted(p for p in args.images.iterdir()
                   if p.suffix.lower() in (".jpg", ".jpeg"))
    if args.limit:
        paths = paths[:args.limit]
    if not paths:
        sys.exit(f"no photographs in {args.images}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")
    if device == "cuda":
        print(f"  {torch.cuda.get_device_name(0)}")
    model = Sam3Model.from_pretrained(args.model).to(device)
    processor = Sam3Processor.from_pretrained(args.model)
    model.eval()
    print(f"  {args.model} loaded")

    dirs = {k: args.out / k for k in
            ("masks_sherds", "masks_object", "masks_measure", "masks_dial", "overlays")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    kern = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * args.dilate + 1, 2 * args.dilate + 1))
    kern_er = (cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * args.erode_surface + 1, 2 * args.erode_surface + 1))
        if args.erode_surface else None)
    SOLVING = {"masks_object"}          # the only set that is matched, not built from
    rows, t0 = [], time.time()

    for i, path in enumerate(paths):
        # No exif_transpose: COLMAP reads the stored pixels, so the mask must match them.
        full = Image.open(path).convert("RGB")
        W, H = full.size
        small = full.copy()
        small.thumbnail((args.seg_side, args.seg_side))

        sw, sh = small.size
        vision_embeds = encode_image(processor, model, small, device)
        sherds, sd = union_mask(processor, model, vision_embeds, SHERD_PROMPTS,
                                device, args.threshold, (sh, sw))
        hardware, hd = union_mask(processor, model, vision_embeds, HARDWARE_PROMPTS,
                                  device, args.threshold, (sh, sw))
        base_raw, bd = union_mask(processor, model, vision_embeds, BASE_PROMPTS,
                                  device, args.threshold, (sh, sw))
        table, td = union_mask(processor, model, vision_embeds, TURNTABLE_PROMPTS,
                               device, args.threshold, (sh, sw))
        rig = hardware | base_raw | table
        obj = sherds | rig

        # The base plate minus anything the hardware prompts also claimed. The clamps are
        # painted the same blue, so "blue board" lands on them too and no prompt separates
        # two objects of one colour. A sherd is never subtracted: sherds win over hardware,
        # because a clamp jaw crossing a sherd must not punch a hole in the pottery.
        base = base_raw & ~hardware if args.subtract_hardware else base_raw
        measure = sherds | base
        # Same keep-set plus the dial, purely to give the featureless plate a textured
        # neighbour for dense stereo to propagate depth from. The clamps and rod stay out.
        measure_dial = measure | table

        for name, m in (("masks_sherds", sherds), ("masks_object", obj),
                        ("masks_measure", measure), ("masks_dial", measure_dial)):
            out = cv2.resize(m.astype(np.uint8) * 255, (W, H),
                             interpolation=cv2.INTER_NEAREST)
            if name in SOLVING:
                if args.dilate:
                    out = cv2.dilate(out, kern)
            elif kern_er is not None:
                out = cv2.erode(out, kern_er)
            cv2.imwrite(str(dirs[name] / (path.name + ".png")), out)

        n_sherd = sum(v["instances"] for v in sd.values())
        rows.append(dict(frame=path.name, sherd_instances=n_sherd,
                         sherd_best=max(v["best"] for v in sd.values()),
                         sherd_coverage=round(float(sherds.mean()), 4),
                         object_coverage=round(float(obj.mean()), 4),
                         measure_coverage=round(float(measure.mean()), 4),
                         dial_coverage=round(float(measure_dial.mean()), 4),
                         base_raw_coverage=round(float(base_raw.mean()), 4),
                         base_kept_coverage=round(float(base.mean()), 4),
                         base_best=max(v["best"] for v in bd.values())))

        if i % args.overlay_every == 0:
            # Three colours, because the whole question is whether the base and the
            # hardware came apart. Painted last wins, so green over blue means a pixel the
            # base prompts claimed and the hardware prompts did not.
            vis = np.asarray(small).copy()
            def tint(m, rgb, a):
                sel = m.astype(bool)
                vis[sel] = ((1 - a) * vis[sel] + a * np.array(rgb)).astype(np.uint8)
            tint(hardware | table, (80, 80, 255), 0.30)     # blue  = dropped from the mesh
            tint(base, (80, 235, 120), 0.40)                # green = base plate, KEPT
            tint(sherds, (255, 80, 80), 0.45)               # red   = sherds, KEPT
            Image.fromarray(vis).save(dirs["overlays"] / f"{path.stem}.jpg", quality=85)

        if (i + 1) % 20 == 0 or i == len(paths) - 1:
            print(f"  {i+1}/{len(paths)}  {path.name}  "
                  f"{n_sherd} sherds, covers {100*rows[-1]['sherd_coverage']:.1f}%  "
                  f"({(time.time()-t0)/(i+1):.2f}s/frame)", flush=True)

    (args.out / "masks.json").write_text(json.dumps(rows, indent=2))

    # ORPHANS. A mask whose photograph is no longer in the capture. These appear whenever a
    # file is removed and the masks are regenerated -- which is exactly what happened on
    # A03 when the Metashape texture atlas was taken out: 164 photographs, 165 masks left
    # over, and the count check downstream refused the whole set. Deleting the stale mask
    # is right; leaving it to be found by a later job is not. Pruned by source name, so a
    # --limit run does not touch the masks of photographs it simply did not visit.
    have = {p.name for p in paths} | {p.name for p in args.images.iterdir() if p.is_file()}
    pruned = 0
    for key in ("masks_sherds", "masks_object", "masks_measure", "masks_dial"):
        for m in dirs[key].glob("*.png"):
            if m.name[:-4] not in have:
                m.unlink()
                pruned += 1
    if pruned:
        print(f"\n  pruned {pruned} orphaned mask(s) whose photograph is no longer in "
              f"the capture")

    ns = np.array([r["sherd_instances"] for r in rows])
    cov = np.array([r["sherd_coverage"] for r in rows])
    print(f"\n=== {len(rows)} frames in {time.time()-t0:.0f}s ===")
    # INSTANCE COUNT IS NOT A SHERD COUNT, and reading it as one misleads. A pottery tree
    # is a single loading, so it holds a FIXED number of sherds in every frame -- A02 holds
    # 10. Yet the median instance count there is 11 and the maximum 16, because a clamp jaw
    # crossing a sherd splits the visible pottery into disconnected regions and each is
    # reported separately. Measured on A02: the correlation between instance count and
    # coverage is r = -0.05, and frames reporting more than 10 average the same coverage
    # (5.07%) as those reporting 10 or fewer (5.08%) -- the extra instances carry no extra
    # pottery. Harmless for the mask, which is a union, but useless as a quality signal.
    print(f"  sherd COVERAGE (the meaningful one): min {100*cov.min():.1f}% "
          f"median {100*np.median(cov):.1f}% max {100*cov.max():.1f}%")
    print(f"  instance blobs per frame: min {ns.min()} median {int(np.median(ns))} "
          f"max {ns.max()}   <- blobs, NOT sherds: occlusion splits one sherd into several")

    # Coverage collapsing is the failure that matters; a frame finding literally nothing is
    # only its extreme case, and an average hides both.
    med = float(np.median(cov))
    thin = [r["frame"] for r in rows if r["sherd_coverage"] < 0.4 * med]
    if thin:
        print(f"\n  {len(thin)} frame(s) cover less than 40% of the median "
              f"({100*med:.1f}%) -- look at these:")
        for t in thin[:12]:
            print(f"    {t}")

    # RUNAWAY masks matter as much as thin ones, and only thin ones were being reported.
    # On A03 one frame scored 69.5% against a 2.2% median: it was A03.jpg, the Metashape
    # TEXTURE ATLAS sitting beside the photographs -- a sheet of sherd surfaces, so "clay
    # fragment" was right about it and it was not a photograph at all. Anything this far
    # above the median is either not a photograph of the tree or a mask that has escaped.
    fat = [r for r in rows if r["sherd_coverage"] > 4 * med]
    if fat:
        print(f"\n  {len(fat)} FRAME(S) COVER MORE THAN 4x THE MEDIAN ({100*med:.1f}%) --")
        print("  a mask that has run away, or a file that is not a photograph of the tree:")
        for r in sorted(fat, key=lambda x: -x["sherd_coverage"])[:12]:
            print(f"    {r['frame']}  {100*r['sherd_coverage']:.1f}%")
        print("  A texture atlas or a detail shot will land here. Remove it from the")
        print("  capture rather than masking around it: COLMAP would try to match it too.")
    bad = [r["frame"] for r in rows if r["sherd_instances"] == 0]
    if bad:
        print(f"\n  {len(bad)} FRAME(S) WITH NO SHERDS FOUND -- look at these:")
        for b in bad[:12]:
            print(f"    {b}")
    else:
        print("\n  every frame found at least one sherd")

    # THE BASE IS THE SCALE REFERENCE. If subtracting the hardware ate it, every mesh built
    # from masks_measure loses the one object that can be checked against a known size --
    # and it would go unnoticed, because the sherds would look perfectly fine.
    braw = np.array([r["base_raw_coverage"] for r in rows])
    bkept = np.array([r["base_kept_coverage"] for r in rows])
    survived = np.where(braw > 0, bkept / np.maximum(braw, 1e-9), 1.0)
    print(f"\n  BASE PLATE (the scale reference):")
    print(f"    found on {int((braw > 0.002).sum())} of {len(rows)} frames, "
          f"covering median {100*np.median(braw):.1f}% of the frame")
    print(f"    after subtracting the clamps and rod, {100*np.median(survived):.0f}% of it "
          f"survives (worst frame {100*survived.min():.0f}%)")
    lost = [r["frame"] for r, s in zip(rows, survived) if s < 0.5 and r["base_raw_coverage"] > 0.002]
    if lost:
        print(f"    {len(lost)} frame(s) lost more than half the base to the subtraction --")
        print(f"    the hardware prompts are landing on the plate itself. Look at these:")
        for f in lost[:8]:
            print(f"      {f}")
    gone = [r["frame"] for r in rows if r["base_kept_coverage"] < 0.002]
    if gone:
        print(f"    {len(gone)} FRAME(S) HAVE NO BASE AT ALL in masks_measure -- a mesh from")
        print(f"    these cannot be checked against the 190 x 130 mm plate.")

    mcov = np.array([r["measure_coverage"] for r in rows])
    ocov = np.array([r["object_coverage"] for r in rows])
    print(f"\n  what each set keeps (median over {len(rows)} frames):")
    print(f"    masks_object  {100*np.median(ocov):5.1f}%   sherds + rig      -> solving the cameras")
    dcov = np.array([r["dial_coverage"] for r in rows])
    print(f"    masks_measure {100*np.median(mcov):5.1f}%   sherds + base     -> building the surface")
    print(f"    masks_dial    {100*np.median(dcov):5.1f}%   + turntable dial  -> same, with depth support")
    print(f"    masks_sherds  {100*np.median(cov):5.1f}%   sherds only       -> variant, NO base")

    print(f"\nLOOK AT {dirs['overlays']} before using these.")
    print("RED = sherds and GREEN = base are kept in the mesh; BLUE = clamps, rod and dial")
    print("are dropped. The question is whether green stops at the clamp instead of")
    print("swallowing it -- they are painted the same blue, which is why it can fail.")


if __name__ == "__main__":
    main()
