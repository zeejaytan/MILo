"""CPU-side similarity distribution analysis (ticket alt-09).

Reads similarities.pt from the GPU query job and reports the histogram plus
a keep-count ladder, so the fusion threshold is chosen from the separation
in the data — not from the 2D training numbers the query script prespecified.
No GPU, runs on the login node.
"""

import argparse

import numpy as np
import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", required=True)
    ap.add_argument("--ladder", default="0.0,0.05,0.1,0.15,0.2,0.3,0.4,0.5,0.6,0.75")
    args = ap.parse_args()

    s = torch.load(args.sims, weights_only=True).numpy()
    print(f"n: {len(s)}")
    hist, edges = np.histogram(s, bins=16, range=(-1, 1))
    for h, e in zip(hist, edges):
        print(f"{e:+.2f}: {'#' * int(60 * h / hist.max())} {h}")
    print("ladder:")
    for t in (float(x) for x in args.ladder.split(",")):
        k = int((s > t).sum())
        print(f"  >{t:.2f}: {k:7d} ({100 * k / len(s):5.2f}%)")


if __name__ == "__main__":
    main()
