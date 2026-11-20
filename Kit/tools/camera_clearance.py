"""Offline check: do the sequence cameras fly through any generated geometry?
Runs the build against the fake `unreal` module, records every primitive's AABB, then samples
each camera path (linear between keys) and reports hits (glass panes are allowed).

    python3 tools/camera_clearance.py          # the gala (unchanged)
    python3 tools/camera_clearance.py trial1   # Trial 1: flythrough cameras + the trio's walk vs every
                                               # primitive, a capsule walk along trial1_beats.ROUTE
                                               # (support, <= 45 cm steps, head room, 34 cm radius) and
                                               # the climb stack (each foothold exists, <= 100 cm apart)
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_run  # noqa: E402

sys.modules["unreal"] = mock_run.make_unreal()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ECHO", "Content", "Python"))
import echo_kit.util as U  # noqa: E402
import echo_kit.gala as G  # noqa: E402
import echo_kit.sequence as Q  # noqa: E402
import echo_kit.settings as S  # noqa: E402

BOXES = []
_orig = U.spawn_mesh


def rec(shape_name, loc, scale, mat=None, rot=(0, 0, 0), label=None, folder=None, **kw):
    a = _orig(shape_name, loc, scale, mat, rot=rot, label=label, folder=folder, **kw)
    if shape_name in ("cube", "cylinder", "sphere", "cone") and not any(rot) and "SkyDome" not in (label or "") \
            and "InvisibleWall" not in (label or ""):
        h = [50.0 * s for s in scale]
        BOXES.append(((loc[0] - h[0], loc[1] - h[1], loc[2] - h[2]), (loc[0] + h[0], loc[1] + h[1], loc[2] + h[2]),
                      label or folder or shape_name))
    return a


for mod in (U, G):
    mod.spawn_mesh = rec
# box/cylinder/sphere helpers resolve spawn_mesh from util's globals
U.spawn_mesh = rec

PATHS = {}
_orig_shot_tf = Q.add_transform


def rec_tf(seq, binding, start, end, keys, interp="AUTO"):
    PATHS.setdefault(len(PATHS), [(k[0], k[1]) for k in keys])
    return _orig_tf(seq, binding, start, end, keys, interp)


_orig_tf = Q.add_transform
Q.add_transform = rec_tf

if len(sys.argv) > 1 and sys.argv[1] == "trial1":
    sys.exit(__import__("camera_clearance_trial1").main())

mock_run.Assets.EXIST = False
actors = G.build()
Q.build(actors)

cams = {i: p for i, p in list(PATHS.items())[:4]}
hits = 0
for ci, keys in cams.items():
    for (f0, a), (f1, b) in zip(keys, keys[1:]):
        for t in [i / 40.0 for i in range(41)]:
            p = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
            for mn, mx, name in BOXES:
                if "Glass" in name:
                    continue
                if all(mn[j] - 15 <= p[j] <= mx[j] + 15 for j in range(3)):
                    hits += 1
                    print("camera %d frame ~%d at %s inside %s" % (ci, f0 + (f1 - f0) * t, tuple(round(v) for v in p), name))
                    break
print("checked %d boxes, %d hits" % (len(BOXES), hits))
