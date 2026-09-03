# ADR 0001 — When a mesh cannot say what units it is in, refuse rather than degrade

**Status:** accepted, 2026-09-03 · **Applies to:** `scripts/compare_meshes.py`, and any
script that reports a measurement in millimetres · **From:** `.scratch/scale-provenance/spec.md` Q2

## The decision

A comparison that cannot establish the units of both meshes **stops with a non-zero exit
status** and prints no millimetre figure at all. It does not fall back to a default, does
not print a warning and continue, and does not guess from the meshes' sizes.

Running anyway is still possible, but only when asked for by name: `--shape-only` runs the
one measure that does not depend on units — outline agreement against held-out photographs
— and suppresses every millimetre figure, including the render's scale bar.

## Why not the obvious alternative

The obvious alternative is to warn and continue, which is friendlier and does not break
anybody's pipeline. It was rejected because it has already failed here, in this repository,
in a way that cost real time:

- `check_turntable.py` printed a correct and complete page of disagreeing camera frames
  while returning 0, and was called with `|| true`. The gate was dead. The dense
  reconstruction stage ran on a bent solve anyway, and the frame count in the log looked
  exactly like a working check.
- A tool adopted without checking scored a *better* reprojection error while duplicating
  every sherd, and was caught only when the conservator opened the mesh.

The common shape is that a printed warning does not stop anything, and a number printed
beside it is read as a result. A scale error is the worst case for this: a sherd 8 % too
large is not visibly a mistake, and every downstream figure is wrong by a constant factor
while looking entirely plausible.

## What it costs

Jobs that used to produce a comparison now fail on captures whose meshes were never
scaled — including, today, every derived mesh, because cropping and sherd extraction drop
the sidecar. That is the point: those comparisons were never in millimetres. The cost is
paid down by ticket 03 (crops carry their scale) and ticket 02 (every capture states its
scale source).

`--shape-only` exists so that the 59 captures with no marker are not lost for the questions
that do not need millimetres.

## How it is held in place

`compare_meshes.py --self-test` builds synthetic meshes and sidecars and asserts the **exit
status** for each case against an answer fixed in advance. It needs no capture, no COLMAP
model and no GPU, because the scale decision is taken before any of those are touched — a
refusal that only fires on a compute node would not be a gate.
