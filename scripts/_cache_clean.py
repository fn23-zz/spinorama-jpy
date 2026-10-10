#!/usr/bin/env python3
"""Delete probe cache files matching a glob prefix (no shell rm)."""
import glob
import os
import sys

pat = sys.argv[1]
n = 0
for p in glob.glob(pat):
    os.remove(p)
    n += 1
print("removed", n)
