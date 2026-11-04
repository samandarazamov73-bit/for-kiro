"""Generates the interior texture sets into soviet_building/textures.

    python texgen_interior.py [--out ../../textures] [--only NAME_SUBSTRING]

Uses numpy + Pillow only (both ship with the `bpy` wheel environment)."""
import argparse
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sanatorium import texgen_surfaces, texgen_atlas  # noqa: E402


def all_jobs(out):
    return texgen_surfaces.generate_surfaces(out) + texgen_atlas.generate_atlases(out)


def run(args):
    i, out = args
    t = time.time()
    try:
        all_jobs(out)[i]()
        return i, round(time.time() - t, 1), None
    except Exception:
        return i, round(time.time() - t, 1), traceback.format_exc()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "textures"))
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("-j", type=int, default=os.cpu_count())
    a = ap.parse_args()
    n = len(all_jobs(a.out))
    idx = a.only if a.only else list(range(n))
    bad = 0
    with ProcessPoolExecutor(a.j) as ex:
        for i, dt, err in ex.map(run, [(i, a.out) for i in idx]):
            print(f"job {i:2d}: {dt:6.1f}s {'FAILED' if err else 'ok'}", flush=True)
            if err:
                bad += 1
                print(err)
    sys.exit(1 if bad else 0)
