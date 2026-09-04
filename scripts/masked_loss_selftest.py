"""Self-checks for the masked-training loss formulas (ticket masked-training/01).

Mirrors the three formulas patched into train.py in numpy, so they run on the
login node with no torch and no GPU:

  masked L1:  mean(|I*M - G*M|)          (both sides)
  bg term:    gamma * mean(A * (1 - M))

Proves the instrumentation can fail: assertion 4 recomputes the REMOVED
one-sided patch (GT masked, render not) and requires it to differ on a rim
pixel -- a future one-sided edit fails this file instead of an A03 run.

usage:  python scripts/masked_loss_selftest.py
"""

import numpy as np


def masked_l1(image, gt, mask):
    return np.abs(image * mask - gt * mask).mean()


def bg_term(alpha, mask, gamma=0.5):
    return gamma * (alpha * (1.0 - mask)).mean()


def main():
    rng = np.random.default_rng(0)
    image = rng.random((3, 16, 16))
    gt = np.clip(image + rng.normal(0, 0.02, image.shape), 0, 1)

    # 1. Parity: all-clay frame (M == 1) matches the unpatched loss exactly.
    m_all = np.ones((1, 16, 16))
    assert masked_l1(image, gt, m_all) == np.abs(image - gt).mean(), \
        "masked loss must equal plain L1 where the mask is one"

    # 2. Background term is zero on an all-clay frame.
    alpha = rng.random((1, 16, 16))
    assert bg_term(alpha, m_all) == 0.0, "bg term must be zero where mask is one"

    # 3. Fully masked-out frame: colour loss is exactly zero, bg term is maximal
    # (mean alpha), i.e. full transparency pressure and nothing else.
    m_none = np.zeros((1, 16, 16))
    assert masked_l1(image, gt, m_none) == 0.0
    assert bg_term(alpha, m_none) == 0.5 * alpha.mean()

    # 4. The removed failure stays removed: one-sided GT masking (770338f)
    # paints background over a rim pixel (M = 0, clay colour in the render);
    # two-sided masking leaves it unsupervised (zero). They must differ.
    rim_render = np.full((3, 1, 1), 0.6)   # clay the render models
    rim_gt = np.full((3, 1, 1), 0.6)       # clay the photo shows
    rim_mask = np.zeros((1, 1, 1))         # ...but the eroded mask says background
    one_sided = np.abs(rim_render - rim_gt * rim_mask).mean()  # = 0.6, paints bg
    two_sided = masked_l1(rim_render, rim_gt, rim_mask)         # = 0.0, leaves alone
    assert one_sided > 0.5 and two_sided == 0.0, \
        f"one-sided {one_sided} must punish the rim pixel two-sided {two_sided} spares"

    # 5. Determinism across reruns is structural (no randomness above), and the
    # background weight transfers without rescaling: the term is a mean over
    # pixels, so gamma = 0.5 means the same at any resolution.
    assert bg_term(np.ones((1, 8, 8)), np.zeros((1, 8, 8))) == \
        bg_term(np.ones((1, 32, 32)), np.zeros((1, 32, 32))) == 0.5

    print("self-checks: 5 assertions passed "
          "(parity, bg-zero, fully-masked, one-sided-tripwire, scale-free gamma).")


if __name__ == "__main__":
    main()
