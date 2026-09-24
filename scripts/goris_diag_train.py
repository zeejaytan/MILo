"""Diagnostic wrapper: run GOR-IS train.py with repeating stack dumps.

A hung job leaves no trace; faulthandler with repeat=True dumps every
interval to the log so the wedged op is named. Unbuffered output (-u at
call time) so the last logged iteration is the truth, not a buffer.

Usage (inside gor-is checkout):
  python -u /path/to/goris_diag_train.py <train.py argv...>
  e.g. python -u scripts/goris_diag_train.py -s ... --iterations 4500 ...
"""
import faulthandler
import runpy
import sys

DUMP_EVERY_S = 600

faulthandler.dump_traceback_later(DUMP_EVERY_S, repeat=True)

train_py = sys.argv[1]
sys.argv = ["train.py"] + sys.argv[2:]
runpy.run_path(train_py, run_name="__main__")
