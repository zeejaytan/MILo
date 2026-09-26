"""Instrument GOR-IS training loop ops without touching its tree.

Wraps GaussianModel.{build_bvh,trace,reflect_trace} with CUDA-event timing
plus allocated/reserved memory, printed every 50 iters, then runs train.py.
Answers: does per-iter time climb while points/memory stay flat (compute
pathology) or does device memory climb (leak)? Faulthandler repeat-dumps
preserved from goris_diag_train.py.

Usage:
  python -u scripts/goris_diag_timing.py ./train.py [train.py argv...]
"""
import faulthandler
import runpy
import sys
import time

import torch

faulthandler.dump_traceback_later(600, repeat=True)

from scene.gaussian_model import GaussianModel  # noqa: E402

_wrapped = {}


def _timed(name, fn):
    def inner(self, *a, **k):
        t0 = time.perf_counter()
        out = fn(self, *a, **k)
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        self._diag_n = getattr(self, "_diag_n", 0) + 1
        if self._diag_n % 50 == 0:
            al = torch.cuda.memory_allocated() / 1e9
            rs = torch.cuda.memory_reserved() / 1e9
            n = self.get_xyz.shape[0]
            print(f"DIAG iter~{self._diag_n} {name} {dt * 1000:.0f}ms "
                  f"alloc={al:.2f}G reserved={rs:.2f}G points={n}",
                  flush=True)
        return out
    return inner


for _name in ("build_bvh", "trace", "reflect_trace"):
    _fn = getattr(GaussianModel, _name)
    setattr(GaussianModel, _name, _timed(_name, _fn))

train_py = sys.argv[1]
sys.argv = ["train.py"] + sys.argv[2:]
runpy.run_path(train_py, run_name="__main__")
