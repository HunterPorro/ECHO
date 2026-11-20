"""Trial 1 offline checks (run via:  python3 tools/camera_clearance.py trial1).

1. cameras: every LS_Trial1_Flythrough camera path (and the walking trio) against every primitive
   the level builds (instanced dressing + group parts), 15 cm margin; glass, puddles, decals, the
   sky dome and the invisible bounds are allowed.
2. route walk: a Third Person capsule (radius 34, half-height 96, step 45) along trial1_beats.ROUTE,
   sampled every 10 cm against the collidable boxes (trial1.SOLIDS): it must always stand on something,
   never step up more than 45 cm, and never touch a wall / ceiling (DOOR_Cortaz counts as open).
3. climb: every climb foothold exists at its height and each hop is <= 100 cm (jump apex ~143 cm).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mock_run  # noqa: E402

if "unreal" not in sys.modules:
    sys.modules["unreal"] = mock_run.make_unreal()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ECHO", "Content", "Python"))
import echo_kit.util as U  # noqa: E402
import echo_kit.settings as S  # noqa: E402
import echo_kit.trial1 as T  # noqa: E402
import echo_kit.trial1_beats as TB  # noqa: E402
import echo_kit.trial1_materials as TM  # noqa: E402
import echo_kit.trial1_sequence as TS  # noqa: E402

PRIMS = []          # (mn, mx, name)
SKIP = ("SkyDome", "Puddle", "Glass", "T1_Ground", "InvisibleWall")      # see-through / flat / not rendered
RADIUS, HALF, STEP = 34.0, 96.0, 45.0


def _rec_box(c, sc, name):
    h = [50.0 * v for v in sc]
    PRIMS.append(((c[0] - h[0], c[1] - h[1], c[2] - h[2]), (c[0] + h[0], c[1] + h[1], c[2] + h[2]), name))


_orig_add = T.T1Buckets.add


def _add(self, shape_name, center, scale, mat_name, rot=(0, 0, 0), shadows=True, collision=False, core=False):
    if not any(rot):
        _rec_box(center, scale, str(mat_name))
    return _orig_add(self, shape_name, center, scale, mat_name, rot=rot, shadows=shadows, collision=collision, core=core)


T.T1Buckets.add = _add
_orig_sm = U.spawn_mesh


def _sm(shape_name, loc, scale, mat=None, rot=(0, 0, 0), label=None, folder=None, **kw):
    a = _orig_sm(shape_name, loc, scale, mat, rot=rot, label=label, folder=folder, **kw)
    if not any(rot) and (folder or "").find("StateB") < 0:
        _rec_box(loc, scale, "%s|%s" % (label or "", folder or ""))
    return a


T.spawn_mesh = _sm


def _skip(name):
    return any(k in name for k in SKIP)


def check_cameras():
    hits = 0
    paths = dict(TS.CAM_PATHS)
    n = 0
    for label, keys in paths.items():
        for (f0, a), (f1, b) in zip(keys, keys[1:]):
            for i in range(9):
                t = i / 8.0
                p = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
                n += 1
                for mn, mx, name in PRIMS:
                    if _skip(name):
                        continue
                    if all(mn[j] - 15 <= p[j] <= mx[j] + 15 for j in range(3)):
                        hits += 1
                        print("  camera %s ~f%d at %s inside %s" % (label, f0 + (f1 - f0) * t,
                                                                    tuple(round(v) for v in p), name))
                        break
    trio_hits = 0
    for label, keys in TS.TRIO_PATHS.items():
        for (f0, a), (f1, b) in zip(keys, keys[1:]):
            if math.dist(a, b) > 200:          # a cut: the double teleports
                continue
            p = b
            for mn, mx, kind_name in PRIMS:
                if _skip(kind_name) or mx[2] - mn[2] < 30 or mx[2] < p[2] + 25 or mn[2] > p[2] + 170:
                    continue
                if all(mn[j] - 25 <= p[j] <= mx[j] + 25 for j in range(2)):
                    trio_hits += 1
                    print("  trio %s f%d at %s inside %s" % (label, f1, tuple(round(v) for v in p), kind_name))
                    break
    print("trial1 cameras: %d cameras, %d samples vs %d primitives, %d hits; trio walk %d hits" % (
        len(paths), n, len(PRIMS), hits, trio_hits))
    return hits + trio_hits


def _xy_dist(p, mn, mx):
    dx = max(mn[0] - p[0], 0.0, p[0] - mx[0])
    dy = max(mn[1] - p[1], 0.0, p[1] - mx[1])
    return math.hypot(dx, dy)


def check_route():
    solids = [s for s in T.SOLIDS if s[3] not in ("door", "bounds")]
    bad, n, max_up, max_at = 0, 0, 0.0, None
    z = None
    pts = TB.ROUTE
    for (a, b) in zip(pts, pts[1:]):
        d = math.dist(a, b)
        steps = max(1, int(d // 10))
        for i in range(steps + 1):
            t = i / float(steps)
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            n += 1
            under = [s for s in solids if s[0][0] <= p[0] <= s[1][0] and s[0][1] <= p[1] <= s[1][1]]
            reach = (z + STEP) if z is not None else 1e9
            tops = [s[1][2] for s in under if s[1][2] <= reach + 0.01]
            if z is None:
                tops = [t2 for t2 in tops if t2 < 100]
            if not tops:
                bad += 1
                print("  route: nothing to stand on at %s (feet %.0f)" % (tuple(round(v) for v in p), z or 0))
                continue
            nz = max(tops)
            if z is not None and nz - z > max_up:
                max_up, max_at = nz - z, p
            z = nz
            lo, hi = z + STEP + 0.5, z + 2 * HALF
            for s in solids:
                if s[1][2] <= lo or s[0][2] >= hi:
                    continue
                if _xy_dist(p, s[0], s[1]) < RADIUS:
                    bad += 1
                    print("  route: capsule at %s (feet %.0f) touches %s %s-%s" % (
                        tuple(round(v) for v in p), z, s[2], tuple(round(v) for v in s[0]), tuple(round(v) for v in s[1])))
                    break
    print("trial1 route: %d waypoints, %d samples, %d problems, max step up %.1f cm at %s, ends at feet z %.0f" % (
        len(pts), n, bad, max_up, tuple(round(v) for v in max_at) if max_at else "-", z or 0))
    if max_up > STEP:
        bad += 1
    return bad


def check_climb():
    bad = 0
    marks = T.MARKERS["climb"]
    prev = TB.CURB
    for (label, loc, kind) in marks:
        ok = any(abs(s[1][2] - loc[2]) < 1.0 and s[0][0] - 1 <= loc[0] <= s[1][0] + 1 and s[0][1] - 1 <= loc[1] <= s[1][1] + 1
                 for s in T.SOLIDS)
        if not ok:
            bad += 1
            print("  climb: no foothold under %s at %s" % (label, loc))
        if loc[2] - prev > 100.0:
            bad += 1
            print("  climb: %s is %.0f cm above the last foothold" % (label, loc[2] - prev))
        prev = loc[2]
    hops = [b - a for (_l, a), (_m, b) in zip([("floor", TB.CURB)] + TB.CLIMB_STACK, TB.CLIMB_STACK)]
    if max(hops) > 100.0:
        bad += 1
        print("  climb: CLIMB_STACK hop %.0f cm > 100" % max(hops))
    print("trial1 climb: %d footholds (%s), hops %s cm, %d problems" % (
        len(marks), ", ".join(m[0] for m in marks), "/".join("%.0f" % h for h in hops), bad))
    return bad


def main():
    mock_run.Assets.EXIST = True            # 'existing assets': the pixel-mode shift path
    TM.build_all()
    T.build()
    TS.build()
    total = check_cameras() + check_route() + check_climb()
    print("trial1 clearance: %s" % ("OK" if not total else "%d problems" % total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
