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
import os
import subprocess
import sys
from pathlib import Path

ALLOC = "/projects/proj-1000_rbt23photogrammetry-1128.4.1250"
ROOT = f"{ALLOC}/Rabati2025"
TOKEN = Path.home() / ".Arcitecta" / "mflux-token.cfg"


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def list_namespace(ns):
    """Asset paths and sizes directly under a namespace, via unimelb-mf-check's inventory."""
    out = run(["unimelb-mf-download", "--mf.config", str(TOKEN), "--help"])
    if out.returncode not in (0, 1):
        sys.exit("unimelb-mf-download not available -- module load unimelb-mf-clients")
    # aterm is the only thing that enumerates without downloading.
    q = f'asset.query :where "namespace>=\'{ns}\'" :action get-values ' \
        f':xpath -ename path path :xpath -ename size content/size :size infinity'
    r = run(["unimelb-mf-aterm.sh", "--mf.config", str(TOKEN), "nogui", q])
    if r.returncode != 0:
        sys.exit(f"aterm query failed:\n{r.stderr[:800]}")
    paths, cur = [], {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith(":path "):
            cur["path"] = line[6:].strip().strip('"')
        elif line.startswith(":size "):
            try:
                cur["size"] = int(line[6:].strip().strip('"'))
            except ValueError:
                cur["size"] = 0
            if "path" in cur:
                paths.append((cur["path"], cur["size"]))
            cur = {}
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True, help="e.g. 17062025/A02")
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--with-project", action="store_true",
                    help="also fetch the Metashape project stored alongside (its .obj "
                         "model and its masks are a useful reference)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not TOKEN.exists():
        sys.exit(f"no Mediaflux token at {TOKEN} -- run scripts/mediaflux_token.sh")

    ns = f"{ROOT}/{args.capture}"
    tree = args.capture.rsplit("/", 1)[-1]
    print(f"enumerating {ns} ...", flush=True)
    assets = list_namespace(ns)
    if not assets:
        sys.exit(f"nothing found under {ns}")

    photos, project, skipped = [], [], []
    for path, size in assets:
        rel = path.split(f"/{tree}/", 1)[-1] if f"/{tree}/" in path else os.path.basename(path)
        if f"/{tree}.files/" in path or f"{tree}.files" in rel:
            project.append((path, size))
        elif "/" not in rel and rel.lower().endswith((".jpg", ".jpeg")):
            photos.append((path, size))
        else:
            skipped.append((path, size))

    gb = lambda items: sum(s for _, s in items) / 1e9
    print(f"  photographs : {len(photos):4d}  {gb(photos):6.2f} GB   <- fetching")
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
