"""Fetch just the photographs of one tree from Mediaflux, not the raws.

`unimelb-mf-download` has no extension filter -- it takes whole namespaces or explicit
asset paths, and nothing in between. For tree A02 the split is:

    163 photographs  A02/*.JPG        1.43 GB   <- wanted
    162 raws         A02/*.NEF        4.16 GB   <- not wanted, never used
     32 project      A02.files/...    0.18 GB   <- the Metashape reconstruction and its
                                                   masks, worth having as a reference

So this enumerates the namespace, keeps what was asked for, and passes those assets
explicitly. Downloading the namespace and deleting afterwards would move 4 GB to throw it
away.

Usage:
    python mediaflux_fetch_tree.py --capture 17062025/A02 --dest <dir> [--with-project]
    python mediaflux_fetch_tree.py --capture 17062025/A02 --dest <dir> --dry-run
"""
import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path

ALLOC = "/projects/proj-1000_rbt23photogrammetry-1128.4.1250"
ROOT = f"{ALLOC}/Rabati2025"
TOKEN = Path.home() / ".Arcitecta" / "mflux-token.cfg"


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def load_inventory(capture, inventory):
    """Asset paths and sizes, from the CSV that `mediaflux_fetch.sh --list` writes.

    NOT via aterm. mediaflux_fetch.sh records why, and it is worth not rediscovering:
    the project role is not granted ACCESS to asset.namespace.list, so the namespace
    cannot be enumerated that way. unimelb-mf-check can, and writes this CSV as a
    side effect of comparing remote against local.
    """
    date = capture.split("/", 1)[0]
    csv_path = Path(inventory) if inventory else         Path(f"/data/gpfs/projects/punim2657/MILo/logs/mediaflux/list_{date}.csv")
    if not csv_path.exists():
        script = Path(__file__).resolve().parent / "mediaflux_fetch.sh"
        if not script.exists():
            script = Path("/data/gpfs/projects/punim2657/MILo/repo/scripts/mediaflux_fetch.sh")
        print(f"no inventory at {csv_path}; running {script.name} --list {date} ...",
              flush=True)
        r = subprocess.run([str(script), "--list", date], text=True)
        if r.returncode != 0 or not csv_path.exists():
            sys.exit(f"could not build an inventory for {date}")
    rows = []
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            path = (row.get("SRC_PATH") or "").strip().strip('"')
            if not path.startswith("asset:"):
                continue
            try:
                size = int(row.get("SRC_LENGTH") or 0)
            except ValueError:
                size = 0
            rows.append((path[len("asset:"):], size))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True, help="e.g. 17062025/A02")
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--with-project", action="store_true",
                    help="also fetch the Metashape project stored alongside (its .obj "
                         "model and its masks are a useful reference)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--inventory", default=None,
                    help="CSV from mediaflux_fetch.sh --list; found automatically if absent")
    args = ap.parse_args()

    if not TOKEN.exists():
        sys.exit(f"no Mediaflux token at {TOKEN} -- run scripts/mediaflux_token.sh")

    tree = args.capture.rsplit("/", 1)[-1]
    assets = [(p, n) for p, n in load_inventory(args.capture, args.inventory)
              if f"/{args.capture}/" in p or f"/{tree}.files/" in p]
    if not assets:
        sys.exit(f"nothing found for {args.capture} in the inventory")

    photos, project, skipped, atlas = [], [], [], []
    for path, size in assets:
        rel = path.split(f"/{tree}/", 1)[-1] if f"/{tree}/" in path else os.path.basename(path)
        if f"/{tree}.files/" in path or f"{tree}.files" in rel:
            project.append((path, size))
        elif "/" not in rel and Path(rel).stem.lower().startswith(tree.lower()):
            # "A03.jpg" beside the photographs is the Metashape TEXTURE ATLAS -- a UV map
            # of sherd surfaces, not a picture of the tree. It has to be kept out on both
            # counts: COLMAP would try to match a texture sheet against the capture, and
            # SAM 3 reads it as almost solid pottery. On A03 it scored 69.5% sherd
            # coverage against a 2.2% median, because it genuinely IS all clay fragment.
            # A02's copy was noticed and moved aside by hand; this stops that being
            # something to remember per tree.
            #
            # STARTSWITH, not equality: N01 also carries "N01 model densefirst.jpg",
            # "N01 model tiff.jpg" and five more like them -- Metashape SCREENSHOTS of the
            # finished reconstruction, sitting in the same namespace as the photographs.
            # They are the whole of the 126-vs-119 gap that the scanning record shows for
            # this capture, and they are renders of the answer, not pictures of the object.
            # Handing them to COLMAP is the atlas mistake wearing a different name.
            atlas.append((path, size))
        elif "/" not in rel and rel.lower().endswith((".jpg", ".jpeg")):
            photos.append((path, size))
        else:
            skipped.append((path, size))

    gb = lambda items: sum(s for _, s in items) / 1e9
    print(f"  photographs : {len(photos):4d}  {gb(photos):6.2f} GB   <- fetching")
    if atlas:
        for a, _ in atlas:
            print(f"  texture atlas: {os.path.basename(a)}  <- SKIPPED, not a photograph")
    print(f"  project     : {len(project):4d}  {gb(project):6.2f} GB   "
          f"<- {'fetching' if args.with_project else 'skipped'}")
    print(f"  other/raws  : {len(skipped):4d}  {gb(skipped):6.2f} GB   <- skipped")

    wanted = photos + (project if args.with_project else [])
    if not wanted:
        sys.exit("nothing selected")
    if args.dry_run:
        print("\n(dry run) first few:")
        for p, _ in wanted[:5]:
            print("   ", p)
        return 0

    args.dest.mkdir(parents=True, exist_ok=True)
    cmd = ["unimelb-mf-download", "--mf.config", str(TOKEN),
           "--out", str(args.dest), "--nb-workers", "8", "--nb-queriers", "4",
           "--overwrite", "--csum-check"] + [p for p, _ in wanted]
    print(f"\ndownloading {len(wanted)} assets to {args.dest} ...", flush=True)
    r = subprocess.run(cmd, text=True)
    got = len(list(args.dest.rglob("*.JPG"))) + len(list(args.dest.rglob("*.jpg")))
    print(f"\n  exit {r.returncode};  {got} JPG on disk under {args.dest}")
    if got < len(photos):
        print(f"  WARNING: expected {len(photos)} photographs, found {got}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
