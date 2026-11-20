"""Builds L_Riverside_Ripple: one Riverside corner of Lakemont in two timeline states.

    State A 'Vacant'  (S0, years after the 2010 robbery): a readable night. The bodega boarded and
                      tagged, a security flood on the door, a few sodium lamps still working, litter,
                      a car on blocks, a faded memorial, moonlight and window glow, wet asphalt,
                      lifted street fog, one fluorescent tube buzzing under the El.
    State B 'Busy'    (S1, after Trial 1 rewrote 2008): the bodega lit and open with Josh's dad behind
                      the counter, awning + produce stands, neon, ~22 people, parked cars and a cab,
                      street lamps on, string lights, trees in leaf, a train on the El, golden-hour sun.
                      'Nothing changed... except': the Cortaz house across the street is a burned lot.

Everything shared by both states (street, row houses, the El, the skyline, Josh) is BASE and is
batched into instanced static meshes (one draw call per shape+material). Only what changes lives
in state groups: a movable pivot per prop with its parts attached, so ripple.py can swap a whole
prop with one transform track while the ripple materials tear it pixel by pixel.

Layout (cm): main street (Delancey Ave) along Y, roadway |X|<700, sidewalks to |X|=1150. Cross
street (Cutler St) along X, roadway |Y|<450, sidewalks to |Y|=800. Bodega = X 1150..2350,
Y 800..1700, storefront facing -X. The El runs over Delancey (deck X -330..330, top Z 760).
"""
import math
import random
from collections import defaultdict

import unreal

from . import gala as G
from . import ripple_materials as RM
from . import settings as S
from .util import (LC, V4, attach, box_from_min_max, clear_generated_actors, component, cylinder,
                   editor_world, enable_volumetric_fog, find_asset_by_name, instanced, level_sub, log,
                   pivot, set_prop, spawn, spawn_mesh, sphere, step, warn, error)

ACTORS = {}
GROUPS = {"A": [], "B": []}           # state groups (ripple.py swaps these)
LIGHTS = {"A": [], "B": []}           # (actor, component, candelas, loc) - ripple.py keys intensity
PEOPLE_B = []                         # (actor, loc, walk_dir or None)
_rng = random.Random(S.RIPPLE_SEED)
_rng_mat = random.Random(S.RIPPLE_SEED + 101)     # material variety only: never shifts the layout
BRICK_VARIANTS = {   # each layout pick is re-dealt into a family: red / ironspot / cream / grey stone
    "MI_Brick_Red": ["MI_Brick_Red", "MI_Brick_Red", "MI_Brick_Dark", "MI_Brick_Cream"],
    "MI_Brick_Brown": ["MI_Brick_Brown", "MI_Stone_Grey"],
    "MI_Brick_Painted": ["MI_Brick_Painted", "MI_Brick_Cream", "MI_Stone_Grey"],
}
LIGHT_TRIM = ("MI_Brick_Painted", "MI_Brick_Cream", "MI_Stone_Grey")
GRADES = {}         # post-process grades by state (ripple.py puts B on the cameras)

RX, SX = 700.0, 1150.0                # main street: road half-width, building line
RY, SY = 450.0, 800.0                 # cross street
CURB_H = 15.0
FLOOR_H = 330.0


def mat(name):
    return RM.get(name)


def col(r, g, b):
    return unreal.Color(r=int(r), g=int(g), b=int(b), a=255)


# =========================================================================== instanced base dressing
class Buckets:
    """Collects base (state-invariant) primitives, flushes them as one ISM per shape+material."""

    def __init__(self):
        self.items = defaultdict(list)

    def add(self, shape_name, center, scale, mat_name, rot=(0, 0, 0), shadows=True, collision=False, core=False):
        self.items[(shape_name, mat_name, bool(shadows), bool(collision), bool(core))].append(
            (tuple(center), tuple(scale), tuple(rot)))

    def box(self, mn, mx, mat_name, **kw):
        c = ((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, (mn[2] + mx[2]) / 2.0)
        s = (abs(mx[0] - mn[0]) / 100.0, abs(mx[1] - mn[1]) / 100.0, abs(mx[2] - mn[2]) / 100.0)
        self.add("cube", c, s, mat_name, **kw)

    def cyl(self, base, dia, h, mat_name, **kw):
        self.add("cylinder", (base[0], base[1], base[2] + h / 2.0), (dia / 100.0, dia / 100.0, h / 100.0), mat_name, **kw)

    def count(self):
        return sum(len(v) for v in self.items.values())

    def flush(self):
        total = self.count()
        budget = 1400        # only used if ISMs are unavailable: caps the fallback actor count
        n_ism = 0
        for (shape_name, mat_name, shadows, collision, core), items in sorted(self.items.items()):
            cap = None if core else max(12, int(budget * len(items) / max(1, total)))
            instanced(shape_name, items, mat(mat_name), label="ISM_%s_%s" % (shape_name, mat_name),
                      folder="Base/Instanced", movable=False, shadows=shadows, collision=collision,
                      fallback_cap=cap)
            n_ism += 1
        log("base dressing: %d primitives in %d instanced batches" % (total, n_ism))
        self.items.clear()
        return total, n_ism


BK = Buckets()


# =========================================================================== state groups
class Group:
    """A swappable prop: a movable pivot with parts attached (KEEP_WORLD).
    Tracks its world AABB so ripple.py can time the swap to the wavefront."""

    def __init__(self, state, name, center, folder=None):
        self.state, self.name = state, name
        self.folder = "State%s/%s" % (state, folder or name)
        self.root = pivot(center, "%s_%s" % (state, name), self.folder, movable=True)
        self.center = tuple(center)
        self.mn = list(center)
        self.mx = list(center)
        self.parts = 0
        self.pop = True               # fallback swap animates scale (False = hard cut: text, windows)
        GROUPS[state].append(self)

    def _grow(self, mn, mx):
        for i in range(3):
            self.mn[i] = min(self.mn[i], mn[i], mx[i])
            self.mx[i] = max(self.mx[i], mn[i], mx[i])

    def _own(self, a):
        attach(a, self.root)
        self.parts += 1
        return a

    def box(self, mn, mx, mat_name, shadows=True, collision=False, rot=(0, 0, 0)):
        self._grow(mn, mx)
        if any(rot):
            c = ((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, (mn[2] + mx[2]) / 2.0)
            s = (abs(mx[0] - mn[0]) / 100.0, abs(mx[1] - mn[1]) / 100.0, abs(mx[2] - mn[2]) / 100.0)
            a = spawn_mesh("cube", c, s, mat(mat_name), rot=rot, folder=self.folder, movable=True,
                           shadows=shadows, collision=collision)
        else:
            a = box_from_min_max(mn, mx, mat(mat_name), folder=self.folder, movable=True, shadows=shadows,
                                 collision=collision)
        return self._own(a)

    def cyl(self, base, dia, h, mat_name, shadows=True, rot=(0, 0, 0)):
        self._grow((base[0] - dia / 2, base[1] - dia / 2, base[2]), (base[0] + dia / 2, base[1] + dia / 2, base[2] + h))
        if any(rot):
            a = spawn_mesh("cylinder", (base[0], base[1], base[2] + h / 2.0), (dia / 100.0, dia / 100.0, h / 100.0),
                           mat(mat_name), rot=rot, folder=self.folder, movable=True, shadows=shadows, collision=False)
        else:
            a = cylinder(base, dia, h, mat(mat_name), folder=self.folder, movable=True, shadows=shadows, collision=False)
        return self._own(a)

    def sph(self, c, dia, mat_name, shadows=True):
        d = dia if isinstance(dia, (tuple, list)) else (dia, dia, dia)
        self._grow((c[0] - d[0] / 2, c[1] - d[1] / 2, c[2] - d[2] / 2), (c[0] + d[0] / 2, c[1] + d[1] / 2, c[2] + d[2] / 2))
        return self._own(sphere(c, d, mat(mat_name), folder=self.folder, movable=True, shadows=shadows, collision=False))

    def seg(self, a, b, thick, mat_name, shadows=False):
        """A thin box from point a to point b (wires, strings, struts)."""
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        ln = math.sqrt(dx * dx + dy * dy + dz * dz)
        self._grow(a, b)
        return self._own(spawn_mesh("cube", ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2),
                                    (ln / 100.0, thick / 100.0, thick / 100.0), mat(mat_name),
                                    rot=(math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)), 0),
                                    folder=self.folder, movable=True, shadows=shadows, collision=False))

    def text(self, txt, loc, size, color, yaw=180.0):
        a = G._text(txt, loc, size, color, folder=self.folder, yaw=yaw)
        try:
            a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        except Exception:
            pass
        self._grow((loc[0] - 10, loc[1] - 10, loc[2] - 10), (loc[0] + 10, loc[1] + 10, loc[2] + 10))
        return self._own(a)

    def ism(self, shape_name, items, mat_name, shadows=True):
        if not items:
            return None
        for (c, sc, _r) in items:
            h = (sc[0] * 50.0, sc[1] * 50.0, sc[2] * 50.0)
            self._grow((c[0] - h[0], c[1] - h[1], c[2] - h[2]), (c[0] + h[0], c[1] + h[1], c[2] + h[2]))
        a = instanced(shape_name, items, mat(mat_name), label="%s_%s_ISM" % (self.state, self.name),
                      folder=self.folder, movable=True, shadows=shadows, collision=False, fallback_cap=60)
        return self._own(a) if a else None

    def light(self, kind, loc, cd, kelvin_temp=2800, radius=1800.0, target=None, inner=25, outer=50,
              shadows=False, volumetric=1.5, source_radius=8.0):
        """State lights are NOT parented: ripple.py ramps their intensity at the wave.
        B lights are saved at 0 (the level opens in State A); A lights are saved on.
        Fog scattering is capped (RIPPLE_LOCAL_VOLUMETRIC): >1 grew glowing balls in the haze."""
        volumetric = min(float(volumetric), float(S.RIPPLE_LOCAL_VOLUMETRIC))
        if kind == "spot":
            a = G.spot("%s_%s_Spot" % (self.state, self.name), loc, target, 0.0, kelvin_temp=kelvin_temp, inner=inner,
                       outer=outer, shadows=shadows, volumetric=volumetric, radius=radius, folder=self.folder)
            comp = component(a, unreal.SpotLightComponent)
        else:
            a = G.point("%s_%s_Point" % (self.state, self.name), loc, 0.0, kelvin_temp=kelvin_temp, radius=radius,
                        shadows=shadows, volumetric=volumetric, source_radius=source_radius, folder=self.folder)
            comp = component(a, unreal.PointLightComponent)
        if self.state == "A" and comp is not None:
            set_prop(comp, "intensity", float(cd))
        LIGHTS[self.state].append((a, comp, float(cd), tuple(loc)))
        return a

    def aabb(self):
        return tuple(self.mn), tuple(self.mx)


# =========================================================================== facades (local frames)
class Facade:
    """Local frame for a block face: u along the street, v into the building (front at v=0,
    outside is v<0), z up. along/depth are axis unit vectors."""

    def __init__(self, origin, along, depth):
        self.o, self.a, self.d = origin, along, depth

    def w(self, u, v, z):
        return (self.o[0] + u * self.a[0] + v * self.d[0], self.o[1] + u * self.a[1] + v * self.d[1], z)

    def mm(self, u0, u1, v0, v1, z0, z1):
        p, q = self.w(u0, v0, z0), self.w(u1, v1, z1)
        return (min(p[0], q[0]), min(p[1], q[1]), min(p[2], q[2])), (max(p[0], q[0]), max(p[1], q[1]), max(p[2], q[2]))

    def tilt(self, deg):
        """Rotation that tilts a u-long box up by deg around the depth axis."""
        return (0.0, 0.0, deg) if abs(self.d[0]) > 0.5 else (deg, 0.0, 0.0)


WINDOWS_LIT = defaultdict(lambda: {"A": [], "B": []})   # facade key -> lit window overlays per state


def _bk_box(F, u0, u1, v0, v1, z0, z1, mat_name, **kw):
    mn, mx = F.mm(u0, u1, v0, v1, z0, z1)
    BK.box(mn, mx, mat_name, **kw)


def house(F, key, u0, W, floors, brick, fire_escape=False, water_tower=False, stoop=True, depth=1100.0,
          lit_bias=0.0, exposed_left=False, exposed_right=False):
    """A Philly row house: brick, a heavy cornice + dentils, recessed punched windows with
    stone frames, a stoop with iron rails, a ground-floor awning, optional NYC fire escape,
    Chicago-style rooftop water tower. Exposed side walls get punched windows too."""
    H = CURB_H + floors * FLOOR_H + 70.0
    _bk_box(F, u0, u0 + W, 0, depth, 0, H, brick, collision=True, core=True)
    _bk_box(F, u0, u0 + W, -6, 0, 0, 90, "MI_Trim_Cream" if brick not in LIGHT_TRIM else "MI_Trim_Dark")
    _bk_box(F, u0, u0 + 16, -10, 0, 0, H - 60, "MI_Brick_Brown")
    _bk_box(F, u0 + W - 16, u0 + W, -10, 0, 0, H - 60, "MI_Brick_Brown")
    # heavier, more projecting cornice so the roofline reads at night
    _bk_box(F, u0 - 12, u0 + W + 12, -58, 0, H - 80, H - 44, "MI_Trim_Dark")
    _bk_box(F, u0 - 16, u0 + W + 16, -72, 0, H - 44, H - 22, "MI_Trim_Cream")
    _bk_box(F, u0 - 8, u0 + W + 8, -36, 0, H - 22, H - 10, "MI_Trim_Dark")
    for k in range(int(W // 50)):                         # dentils under the cornice
        uu = u0 + 16 + k * 50
        _bk_box(F, uu, uu + 20, -46, 0, H - 104, H - 80, "MI_Trim_Dark", shadows=False)
    nwin = 2 if W < 560 else 3
    for f in range(1, floors):
        z0 = CURB_H + f * FLOOR_H + 70.0
        wh, ww = 175.0, 105.0
        for k in range(nwin):
            uc = u0 + W * (k + 0.5) / nwin
            # deep punch: lining, glass set 16 cm in, chunky stone frame and sill
            _bk_box(F, uc - ww / 2, uc + ww / 2, 0, 18, z0, z0 + wh, "MI_Trim_Dark")
            _bk_box(F, uc - ww / 2 + 5, uc + ww / 2 - 5, 16, 18, z0 + 6, z0 + wh - 6, "MI_Glass_Window", core=True)
            _bk_box(F, uc - ww / 2 - 16, uc + ww / 2 + 16, -16, 0, z0 + wh, z0 + wh + 28, "MI_Trim_Cream")  # lintel
            _bk_box(F, uc - ww / 2 - 18, uc + ww / 2 + 18, -22, 0, z0 - 16, z0, "MI_Trim_Cream")            # sill
            _bk_box(F, uc - ww / 2 - 16, uc - ww / 2, -14, 0, z0, z0 + wh, "MI_Trim_Cream")                 # jambs
            _bk_box(F, uc + ww / 2, uc + ww / 2 + 16, -14, 0, z0, z0 + wh, "MI_Trim_Cream")
            _bk_box(F, uc - 2, uc + 2, -4, 16, z0 + 6, z0 + wh - 6, "MI_Trim_Dark", shadows=False)           # mullion
            _bk_box(F, uc - ww / 2 + 5, uc + ww / 2 - 5, -4, 16, z0 + wh * 0.55, z0 + wh * 0.55 + 5, "MI_Trim_Dark", shadows=False)
            r = _rng.random()
            mn, mx = F.mm(uc - ww / 2 + 6, uc + ww / 2 - 6, 16.2, 17.6, z0 + 6, z0 + wh - 6)
            if r < 0.30 + lit_bias:
                WINDOWS_LIT[key]["B"].append((mn, mx))
            if r < 0.20:                                   # A night: enough lit rooms to read the facades
                WINDOWS_LIT[key]["A"].append((mn, mx))
            elif 0.20 <= r < 0.28:
                BK.box(mn, mx, "MI_E_Window_Dim", shadows=False)
            if not fire_escape and _rng.random() < 0.16:          # window AC unit
                _bk_box(F, uc - 34, uc + 34, -48, 0, z0 - 6, z0 + 40, "MI_Chrome_Dull")
    door_u = u0 + W - 100 if _rng.random() < 0.5 else u0 + 100   # ground floor: door + stoop + window
    st_h = 60.0 if stoop else 0.0
    _bk_box(F, door_u - 48, door_u + 48, -3, 0, CURB_H + st_h, CURB_H + st_h + 235, "MI_Trim_Dark", core=True)
    _bk_box(F, door_u - 60, door_u + 60, -8, 0, CURB_H + st_h + 235, CURB_H + st_h + 290, "MI_Trim_Cream")
    _bk_box(F, door_u - 44, door_u + 44, -1, 1, CURB_H + st_h + 240, CURB_H + st_h + 282, "MI_Glass_Window")
    if stoop:
        for s in range(3):
            _bk_box(F, door_u - 72, door_u + 72, -125 + 42 * s, 0, CURB_H, CURB_H + 20 * (s + 1), "MI_Sidewalk",
                    collision=True, core=True)
        for side in (-1, 1):                                   # iron stoop rails
            uu = door_u + side * 70
            _bk_box(F, uu - 2, uu + 2, -125, 0, CURB_H + 95, CURB_H + 99, "MI_Iron_Black", shadows=False)
            for vv in (-120, -60, -5):
                _bk_box(F, uu - 2, uu + 2, vv - 2, vv + 2, CURB_H, CURB_H + 97, "MI_Iron_Black", shadows=False)
    wu0, wu1 = (u0 + 40, door_u - 110) if door_u > u0 + W / 2 else (door_u + 110, u0 + W - 40)
    if wu1 - wu0 > 80:
        _bk_box(F, wu0, wu1, 0, 18, 120, 300, "MI_Trim_Dark")
        _bk_box(F, wu0 + 6, wu1 - 6, 16, 18, 126, 294, "MI_Glass_Window", core=True)
        _bk_box(F, wu0 - 14, wu1 + 14, -16, 0, 300, 328, "MI_Trim_Cream")
        _bk_box(F, wu0 - 16, wu1 + 16, -22, 0, 108, 124, "MI_Trim_Cream")
        mn, mx = F.mm(wu0 + 8, wu1 - 8, 16.2, 17.6, 130, 290)
        if _rng.random() < 0.35 + lit_bias:
            WINDOWS_LIT[key]["B"].append((mn, mx))
        # storefront awning: a sloped canvas hood on iron arms (reads at night in silhouette)
        awn = _rng_mat.choice(("MI_Awning_Green", "MI_Awning_Burgundy", "MI_Awning_Cream"))
        _bk_box(F, wu0 - 18, wu1 + 18, -80, -8, 312, 328, awn)
        _bk_box(F, wu0 - 18, wu1 + 18, -86, -76, 292, 328, awn)
        _bk_box(F, wu0 - 20, wu1 + 20, -14, -6, 300, 332, "MI_Iron_Black")
        for uu in (wu0 - 8, wu1 + 8):
            _bk_box(F, uu - 3, uu + 3, -80, -8, 250, 316, "MI_Iron_Black", shadows=False)
    if fire_escape and floors >= 3:
        for f in range(1, floors):
            zp = CURB_H + f * FLOOR_H + 62.0
            _bk_box(F, u0 + 30, u0 + W - 30, -108, -6, zp - 6, zp, "MI_Iron_Black")
            for zz in (zp + 42, zp + 92):
                _bk_box(F, u0 + 30, u0 + W - 30, -110, -104, zz, zz + 5, "MI_Iron_Black")
            for uu in (u0 + 30, u0 + W - 33):
                _bk_box(F, uu, uu + 4, -110, -6, zp + 92, zp + 97, "MI_Iron_Black")
            n = int((W - 60) // 14)
            for k in range(n + 1):
                uu = u0 + 30 + k * (W - 60) / max(1, n)
                _bk_box(F, uu - 1, uu + 1, -108, -106, zp, zp + 92, "MI_Iron_Black", shadows=False)
            for uu in (u0 + 40, u0 + W - 44):
                _bk_box(F, uu, uu + 4, -100, 0, zp - 70, zp - 64, "MI_Iron_Black", shadows=False)
            if f < floors - 1:                           # stair to the next platform
                run, rise = W * 0.45, FLOOR_H
                ang = math.degrees(math.atan2(rise, run))
                length = math.hypot(run, rise)
                for vv in (-92, -30):
                    c = F.w(u0 + W * 0.3 + run / 2, vv, zp + rise / 2)
                    sc = (length / 100.0, 0.05, 0.12) if abs(F.a[0]) > 0.5 else (0.05, length / 100.0, 0.12)
                    BK.add("cube", c, sc, "MI_Iron_Black", rot=F.tilt(ang))
        zp1 = CURB_H + FLOOR_H + 62.0                     # drop ladder
        for uu in (u0 + W * 0.7, u0 + W * 0.7 + 45):
            _bk_box(F, uu, uu + 3, -100, -97, 230, zp1, "MI_Iron_Black", shadows=False)
        for k in range(8):
            zz = 240 + k * (zp1 - 240) / 8.0
            _bk_box(F, u0 + W * 0.7, u0 + W * 0.7 + 48, -100, -97, zz, zz + 3, "MI_Iron_Black", shadows=False)
    cu = u0 + W * _rng.uniform(0.2, 0.7)                  # roof: chimney + water tower
    _bk_box(F, cu, cu + 55, depth * 0.6, depth * 0.6 + 55, H, H + 130, "MI_Brick_Brown")
    _bk_box(F, cu - 4, cu + 59, depth * 0.6 - 4, depth * 0.6 + 59, H + 130, H + 140, "MI_Trim_Dark")
    if water_tower:
        c = F.w(u0 + W / 2, depth * 0.45, H)
        for dx, dy in ((-110, -110), (110, -110), (-110, 110), (110, 110)):
            BK.cyl((c[0] + dx, c[1] + dy, H), 16, 260, "MI_Iron_Black")
        BK.cyl((c[0], c[1], H + 250), 300, 12, "MI_Iron_Black")
        BK.cyl((c[0], c[1], H + 262), 320, 340, "MI_WaterTower_Wood")
        for zz in (H + 300, H + 420, H + 540):
            BK.cyl((c[0], c[1], zz), 326, 6, "MI_Iron_Black", shadows=False)
        BK.add("cone", (c[0], c[1], H + 602 + 70), (3.5, 3.5, 1.4), "MI_Iron_Black")
    # exposed side walls (ends of a row, or a corner) get punched windows so they are not blank planes
    for exposed, uu in ((exposed_left, u0 - 2), (exposed_right, u0 + W + 2)):
        if not exposed:
            continue
        for f in range(1, floors):
            z0 = CURB_H + f * FLOOR_H + 80.0
            for k in range(2):
                vv = depth * (0.28 + k * 0.28)
                _bk_box(F, uu - 8, uu + 8, vv - 40, vv + 40, z0, z0 + 150, "MI_Trim_Dark")
                _bk_box(F, uu - 6, uu + 6, vv - 32, vv + 32, z0 + 8, z0 + 142, "MI_Glass_Window", shadows=False)
                _bk_box(F, uu - 12, uu + 12, vv - 48, vv + 48, z0 - 12, z0, "MI_Trim_Cream")
    return H


def block_face(F, key, u_start, count, floors_rng=(3, 4), widths=(480, 620)):
    u = u_start
    bricks = ["MI_Brick_Red", "MI_Brick_Red", "MI_Brick_Brown", "MI_Brick_Painted"]
    for _i in range(count):
        W = float(_rng.randint(int(widths[0] / 10), int(widths[1] / 10)) * 10)
        brick = _rng_mat.choice(BRICK_VARIANTS.get(_rng.choice(bricks), [None])) or "MI_Brick_Red"
        house(F, key, u, W, _rng.randint(*floors_rng), brick,
              fire_escape=_rng.random() < 0.75, water_tower=_rng.random() < 0.55,
              exposed_left=(_i == 0), exposed_right=(_i == count - 1))
        u += W
    return u


def far_mass(mn, mx, mat_name=None):
    """Mid-rise back mass: not a flat window-grid box. Cornice, pilasters, punched window
    recesses on the two largest faces, a parapet, and often a roof tank + fire escape."""
    mat_name = mat_name or _rng_mat.choice(("MI_Brick_Brown", "MI_Brick_Red", "MI_Brick_Painted", "MI_Brick_Soot",
                                            "MI_Stone_Grey"))
    BK.box(mn, mx, mat_name, core=True)
    x0, y0, z0 = mn
    x1, y1, z1 = mx
    # cornice + parapet
    BK.box((x0 - 28, y0 - 28, z1 - 50), (x1 + 28, y1 + 28, z1 - 18), "MI_Trim_Dark")
    BK.box((x0 - 36, y0 - 36, z1 - 18), (x1 + 36, y1 + 36, z1 + 8), "MI_Trim_Cream")
    BK.box((x0 - 12, y0 - 12, z1 + 8), (x1 + 12, y1 + 12, z1 + 42), "MI_Trim_Dark")
    dx, dy, h = x1 - x0, y1 - y0, z1 - z0
    # two largest vertical faces get punched windows and pilasters
    faces = []
    # sgn is INWARD (along the axis, into the mass) so recesses punch in and frames/escapes project out
    if dx >= dy:
        faces += [("x", x0, 1), ("x", x1, -1)] if dx > 200 else []
        if dy > 400:
            faces += [("y", y0, 1), ("y", y1, -1)]
    else:
        faces += [("y", y0, 1), ("y", y1, -1)] if dy > 200 else []
        if dx > 400:
            faces += [("x", x0, 1), ("x", x1, -1)]
    floors = max(2, int((h - 80) // 320))
    for axis, pos, sgn in faces:
        length = dy if axis == "x" else dx
        n_bays = max(2, int(length // 280))
        # pilasters
        for i in range(n_bays + 1):
            t = i / float(n_bays)
            if axis == "x":
                yy = y0 + t * dy
                BK.box((pos - 8 * sgn - 6, yy - 12, z0), (pos - 8 * sgn + 6, yy + 12, z1 - 50), "MI_Trim_Cream", shadows=False)
            else:
                xx = x0 + t * dx
                BK.box((xx - 12, pos - 8 * sgn - 6, z0), (xx + 12, pos - 8 * sgn + 6, z1 - 50), "MI_Trim_Cream", shadows=False)
        for fl in range(1, floors + 1):
            zw = z0 + 70 + fl * (h - 140) / (floors + 0.5)
            if zw + 160 > z1 - 60:
                continue
            for i in range(n_bays):
                t = (i + 0.5) / float(n_bays)
                ww, hh = 70.0, 150.0
                if axis == "x":
                    cy = y0 + t * dy
                    # punch: lining then glass 14 cm in
                    BK.box((pos, cy - ww, zw), (pos + 14 * sgn, cy + ww, zw + hh), "MI_Trim_Dark", shadows=False)
                    BK.box((pos + 14 * sgn, cy - ww + 8, zw + 8), (pos + 18 * sgn, cy + ww - 8, zw + hh - 8),
                           "MI_Glass_Window", shadows=False)
                    BK.box((pos - 16 * sgn, cy - ww - 12, zw - 14), (pos, cy + ww + 12, zw), "MI_Trim_Cream", shadows=False)
                    BK.box((pos - 14 * sgn, cy - ww - 10, zw + hh), (pos, cy + ww + 10, zw + hh + 16), "MI_Trim_Cream", shadows=False)
                else:
                    cx = x0 + t * dx
                    BK.box((cx - ww, pos, zw), (cx + ww, pos + 14 * sgn, zw + hh), "MI_Trim_Dark", shadows=False)
                    BK.box((cx - ww + 8, pos + 14 * sgn, zw + 8), (cx + ww - 8, pos + 18 * sgn, zw + hh - 8),
                           "MI_Glass_Window", shadows=False)
                    BK.box((cx - ww - 12, pos - 16 * sgn, zw - 14), (cx + ww + 12, pos, zw), "MI_Trim_Cream", shadows=False)
                    BK.box((cx - ww - 10, pos - 14 * sgn, zw + hh), (cx + ww + 10, pos, zw + hh + 16), "MI_Trim_Cream", shadows=False)
        # fire escape on the first (usually street-facing) long face
        if axis == faces[0][0] and pos == faces[0][1] and floors >= 3 and _rng.random() < 0.65:
            mid = (y0 + y1) / 2 if axis == "x" else (x0 + x1) / 2
            for fl in range(1, floors):
                zw = z0 + 70 + fl * (h - 140) / (floors + 0.5)
                if axis == "x":
                    BK.box((pos - 90 * sgn, mid - 160, zw - 6), (pos - 10 * sgn, mid + 160, zw), "MI_Iron_Black")
                    for zz in (zw + 40, zw + 90):
                        BK.box((pos - 92 * sgn, mid - 160, zz), (pos - 86 * sgn, mid + 160, zz + 4), "MI_Iron_Black")
                else:
                    BK.box((mid - 160, pos - 90 * sgn, zw - 6), (mid + 160, pos - 10 * sgn, zw), "MI_Iron_Black")
                    for zz in (zw + 40, zw + 90):
                        BK.box((mid - 160, pos - 92 * sgn, zz), (mid + 160, pos - 86 * sgn, zz + 4), "MI_Iron_Black")
    if h > 900 and _rng.random() < 0.55:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        BK.cyl((cx, cy, z1 + 42), 16, 200, "MI_Iron_Black")
        for dx, dy_ in ((-80, -80), (80, -80), (-80, 80), (80, 80)):
            BK.cyl((cx + dx, cy + dy_, z1 + 42), 12, 200, "MI_Iron_Black")
        BK.cyl((cx, cy, z1 + 230), 220, 12, "MI_Iron_Black")
        BK.cyl((cx, cy, z1 + 242), 240, 260, "MI_WaterTower_Wood")
        BK.add("cone", (cx, cy, z1 + 242 + 260 + 50), (2.6, 2.6, 1.0), "MI_Iron_Black")


# =========================================================================== level
def open_or_create_level():
    path = S.RIPPLE_MAP_PATH
    ls = level_sub()
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        log("loading existing level " + path)
        if not ls.load_level(path):
            raise RuntimeError("load_level failed: " + path)
        clear_generated_actors()
    else:
        log("creating level " + path)
        unreal.EditorAssetLibrary.make_directory(S.MAP_DIR)
        ok = False
        try:
            ok = ls.new_level(path, False)
        except TypeError:
            ok = ls.new_level(path)
        if not ok:
            raise RuntimeError("new_level failed: " + path)


# =========================================================================== environment
DOME_CENTER = (-150000.0, 0.0, 0.0)   # 1.5 km behind camera: the wave tears the sky open ahead first


def build_environment():
    F = "Environment"
    # ONE opaque unlit Is-Sky dome; its material blends Vacant -> Busy by the MPC wave radius
    dm = mat("MIR_SkyDome")
    d = spawn_mesh("sphere", DOME_CENTER, (6000.0, 6000.0, 6000.0), dm, label="SkyDome_Ripple", folder=F,
                   shadows=False, collision=False)
    smc = d.static_mesh_component
    for prop in ("affect_distance_field_lighting", "affect_dynamic_indirect_lighting", "cast_shadow"):
        set_prop(smc, prop, False, quiet=True)
    try:
        got = smc.get_material(0)
        log("sky dome: material slot 0 = %s (wanted MIR_SkyDome)" % (got.get_path_name() if got else "NONE"))
        if got is None or (dm is not None and got != dm):
            if dm is not None:
                smc.set_material(0, dm)
                log("sky dome: re-assigned MIR_SkyDome")
            else:
                error("sky dome: MIR_SkyDome missing - the sky renders the default material")
    except Exception as exc:
        warn("sky dome material check: %s" % exc)
    ACTORS["dome"] = d
    for cls_name in ("SkyAtmosphere", "VolumetricCloud"):          # nothing may paint over the dome
        cls = getattr(unreal, cls_name, None)
        if cls is not None:
            try:
                found = unreal.GameplayStatics.get_all_actors_of_class(editor_world(), cls)
                log("sky check: %d %s actor(s) in the level" % (len(found), cls_name))
            except Exception:
                pass
    sun = spawn(unreal.DirectionalLight, (0, 0, 4000), (S.A_SUN_ROT[0], S.A_SUN_ROT[1], 0), "Sun", F)
    sc = component(sun, unreal.DirectionalLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(sc, "intensity", float(S.A_SUN_LUX))
    set_prop(sc, "use_temperature", True)
    set_prop(sc, "temperature", float(S.A_SUN_K))
    set_prop(sc, "volumetric_scattering_intensity", float(S.RIPPLE_SUN_VOLUMETRIC))
    set_prop(sc, "light_source_angle", 4.0, quiet=True)          # large moon disc: soft night shadows
    set_prop(sc, "cast_volumetric_shadow", True, quiet=True)
    set_prop(sc, "atmosphere_sun_light", False, quiet=True)
    ACTORS["sun"] = sun
    sky = spawn(unreal.SkyLight, (0, 0, 2500), (0, 0, 0), "SkyLight", F)
    kc = component(sky, unreal.SkyLightComponent)
    kc.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(kc, "real_time_capture", True, quiet=True)
    set_prop(kc, "intensity", float(getattr(S, "A_SKYLIGHT", 1.55)))
    set_prop(kc, "lower_hemisphere_is_black", False, quiet=True)
    set_prop(kc, "sky_distance_threshold", 600000.0, quiet=True)
    ACTORS["skylight"] = sky
    fog = spawn(unreal.ExponentialHeightFog, (0, 0, -50), (0, 0, 0), "HeightFog", F)
    fc = component(fog, unreal.ExponentialHeightFogComponent)
    set_prop(fc, "fog_density", float(S.A_FOG_DENSITY))
    set_prop(fc, "fog_height_falloff", float(S.RIPPLE_FOG_FALLOFF))
    set_prop(fc, ["fog_inscattering_luminance", "fog_inscattering_color"], LC(*S.A_FOG_COLOR))
    set_prop(fc, "fog_max_opacity", float(S.RIPPLE_FOG_MAX_OPACITY))
    set_prop(fc, "start_distance", 600.0, quiet=True)
    # the domes sit 1.5-4.5 km out: cut the height fog off before them so the sky reads as a sky
    # (gradient + clouds), not as a flat wall of fog colour
    set_prop(fc, "fog_cutoff_distance", float(S.RIPPLE_FOG_CUTOFF))
    set_prop(fc, "directional_inscattering_exponent", 24.0, quiet=True)      # tight glow, no sun blob
    set_prop(fc, "directional_inscattering_start_distance", 3000.0, quiet=True)
    set_prop(fc, "directional_inscattering_luminance", LC(0.25, 0.14, 0.07), quiet=True)
    enable_volumetric_fog(fc, True)
    set_prop(fc, ["volumetric_fog_scattering_distribution", "VolumetricFogScatteringDistribution"],
             float(S.RIPPLE_FOG_SCATTER_G))
    set_prop(fc, ["volumetric_fog_extinction_scale", "VolumetricFogExtinctionScale"],
             float(S.A_FOG_EXTINCTION))
    set_prop(fc, ["volumetric_fog_distance", "VolumetricFogDistance"], 8000.0)
    set_prop(fc, ["volumetric_fog_albedo", "VolumetricFogAlbedo"],
             unreal.Color(r=210, g=216, b=230, a=255), quiet=True)
    ACTORS["fog"] = fog


def _ppv(label, priority, weight, grade):
    ppv = spawn(unreal.PostProcessVolume, (0, 0, 500), (0, 0, 0), label, "Environment/Grade")
    set_prop(ppv, "unbound", True)
    set_prop(ppv, "priority", float(priority), quiet=True)
    set_prop(ppv, "blend_weight", float(weight), quiet=True)
    s = ppv.get_editor_property("settings")

    def pp(name, value):
        try:
            s.set_editor_property(name, value)
            s.set_editor_property("override_" + name, True)
        except Exception as exc:
            warn("post-process field %s: %s" % (name, exc))
    for k, v in grade.items():
        pp(k, v)
    ppv.set_editor_property("settings", s)
    try:   # v2 rendered both states warm: prove the saved weights (a failed set leaves 1.0)
        log("grade %s: priority %s blend_weight %.2f (wanted %.2f) white_temp %s" % (
            label, ppv.get_editor_property("priority"), float(ppv.get_editor_property("blend_weight")), weight,
            grade.get("white_temp")))
    except Exception as exc:
        warn("grade %s readback: %s" % (label, exc))
    return ppv


def _base_grade(ev):
    return {
        "dynamic_global_illumination_method": unreal.DynamicGlobalIlluminationMethod.LUMEN,
        "reflection_method": unreal.ReflectionMethod.LUMEN,
        "lumen_scene_lighting_quality": 1.0, "lumen_final_gather_quality": 1.0,
        "lumen_reflection_quality": 1.0, "lumen_front_layer_translucency_reflections": True,
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_HISTOGRAM,
        "auto_exposure_min_brightness": float(ev[0]), "auto_exposure_max_brightness": float(ev[1]),
        "auto_exposure_speed_up": 3.0, "auto_exposure_speed_down": 1.5,
        "film_slope": 0.86, "film_toe": 0.58, "film_shoulder": 0.26, "film_black_clip": 0.0, "film_white_clip": 0.04,
        "motion_blur_amount": 0.4, "ambient_occlusion_intensity": 0.6, "ambient_occlusion_radius": 120.0,
    }


def build_post_process():
    # exposure is LOCKED per state (histogram min == max): no pumping when the sky changes, and the
    # sky/neon values in settings mean the same thing in every shot
    a = _base_grade((S.RIPPLE_EV_A, S.RIPPLE_EV_A))
    a.update({   # Vacant: cold, desaturated, deep blacks, heavy grain - grief as a palette
        "white_temp": float(S.RIPPLE_WHITE_TEMP["A"]), "white_tint": -0.02,
        "color_saturation": V4(0.9, 0.95, 1.0, float(S.RIPPLE_SATURATION["A"])),
        "color_contrast": V4(1.0, 1.0, 1.0, 1.06),
        "color_gamma_shadows": V4(1.0, 1.0, 1.0, 1.04),
        "color_gain_shadows": V4(0.90, 0.96, 1.08, 1.0), "color_offset_shadows": V4(0.006, 0.008, 0.014, 0.0),
        "color_gain_midtones": V4(0.95, 0.98, 1.05, 1.0),
        "color_gain_highlights": V4(0.9, 0.97, 1.07, 1.0),
        "bloom_intensity": float(S.RIPPLE_BLOOM["A"]), "bloom_threshold": 1.0, "lens_flare_intensity": 0.0, "vignette_intensity": 0.36,
        "film_grain_intensity": 0.18, "scene_fringe_intensity": 0.10, "auto_exposure_bias": 0.35,
        "film_toe": 0.55, "film_black_clip": 0.0,
    })
    b = _base_grade((S.RIPPLE_EV_B, S.RIPPLE_EV_B))
    b.update({   # Busy: warm highlights, teal shadows, neon bloom, a touch of flare
        "white_temp": float(S.RIPPLE_WHITE_TEMP["B"]), "white_tint": 0.02,
        "color_saturation": V4(1.0, 1.0, 1.0, float(S.RIPPLE_SATURATION["B"])),
        "color_contrast": V4(1.0, 1.0, 1.0, 1.1),
        "color_gain_shadows": V4(0.9, 1.0, 1.08, 1.0), "color_offset_shadows": V4(0.0, 0.004, 0.008, 0.0),
        "color_gain_highlights": V4(1.1, 1.0, 0.86, 1.0),
        "bloom_intensity": float(S.RIPPLE_BLOOM["B"]), "bloom_threshold": 1.0, "lens_flare_intensity": 0.2, "vignette_intensity": 0.5,
        "film_grain_intensity": 0.12, "scene_fringe_intensity": 0.22, "auto_exposure_bias": 0.2,
    })
    hit = {   # the wave passing through the lens: chromatic split, flash, headache vignette
        "scene_fringe_intensity": 4.5, "vignette_intensity": 1.1, "film_grain_intensity": 0.7,
        "bloom_intensity": float(S.RIPPLE_BLOOM["hit"]), "auto_exposure_bias": 0.5,
        "color_saturation": V4(1.0, 1.0, 1.0, 0.45), "color_gain": V4(0.9, 1.0, 1.15, 1.0),
    }
    GRADES.clear()
    GRADES.update({"A": a, "B": b, "hit": hit})
    ACTORS["ppv_a"] = _ppv("PPV_A_Vacant", 1.0, 1.0, a)
    ACTORS["ppv_b"] = _ppv("PPV_B_Busy", 2.0, 0.0, b)
    ACTORS["ppv_hit"] = _ppv("PPV_RippleHit", 3.0, 0.0, hit)


# =========================================================================== streets
def build_streets():
    F = "Base/Street"
    L = 16000.0
    asphalt, walk = mat("MI_Asphalt_Puddles"), mat("MI_Sidewalk")
    box_from_min_max((-RX, -L, -30), (RX, L, 0), asphalt, label="Road_Delancey", folder=F)
    for x0, x1 in ((-L, -RX), (RX, L)):
        box_from_min_max((x0, -RY, -30), (x1, RY, 0), asphalt, label="Road_Cutler", folder=F)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = sorted((sx * RX, sx * SX))
            y0, y1 = sorted((sy * RY, sy * L))
            box_from_min_max((x0, y0, -30), (x1, y1, CURB_H), walk, label="Sidewalk_Main", folder=F)
            x0, x1 = sorted((sx * SX, sx * L))
            y0, y1 = sorted((sy * RY, sy * SY))
            box_from_min_max((x0, y0, -30), (x1, y1, CURB_H), walk, label="Sidewalk_Cross", folder=F)
            BK.box((sx * RX - 6, min(sy * RY, sy * L), 0), (sx * RX + 6, max(sy * RY, sy * L), CURB_H + 1),
                   "MI_Trim_Cream", shadows=False)                      # granite curb edges
            BK.box((min(sx * SX, sx * L), sy * RY - 6, 0), (max(sx * SX, sx * L), sy * RY + 6, CURB_H + 1),
                   "MI_Trim_Cream", shadows=False)
    for y in range(-6000, 6001, 150):                    # sidewalk joints
        if abs(y) > RY + 50:
            for sx in (-1, 1):
                BK.box((min(sx * RX, sx * SX), y - 1, CURB_H), (max(sx * RX, sx * SX), y + 1, CURB_H + 0.4),
                       "MI_Trim_Dark", shadows=False)
    for sy in (-1, 1):                                   # zebra crosswalks
        for k in range(9):
            x = -RX + 60 + k * 155
            y0, y1 = sorted((sy * (RY + 40), sy * (RY + 330)))
            BK.box((x, y0, 0), (x + 70, y1, 0.8), "MI_Paint_White", shadows=False)
    for sx in (-1, 1):
        for k in range(6):
            y = -RY + 50 + k * 150
            x0, x1 = sorted((sx * (RX + 40), sx * (RX + 330)))
            BK.box((x0, y, 0), (x1, y + 70, 0.8), "MI_Paint_White", shadows=False)
    for y0, y1 in ((-L, -RY - 400), (RY + 400, L)):     # double yellow on Delancey
        for dx in (-9, 9):
            BK.box((dx - 5, y0, 0), (dx + 5, y1, 0.6), "MI_Paint_Yellow", shadows=False)
    for x0, x1 in ((-L, -RX - 400), (RX + 400, L)):     # dashed white on Cutler
        for k in range(int((x1 - x0) // 600)):
            xs = x0 + k * 600
            BK.box((xs, -6, 0), (xs + 300, 6, 0.6), "MI_Paint_White", shadows=False)
    for i in range(38):     # standing water: mirror-black ellipses that catch the neon and the sky
        if i % 3:
            cx, cy = _rng.uniform(-RX + 60, RX - 60), _rng.uniform(-3500, 3500)
        else:
            cx, cy = _rng.uniform(RX + 1200, 7000), _rng.uniform(-RY + 40, RY - 40)
        BK.add("cylinder", (cx, cy, 0.35), (_rng.uniform(80, 420) / 100.0, _rng.uniform(60, 260) / 100.0, 0.006),
               "MI_Puddle", rot=(0, _rng.uniform(0, 180), 0), shadows=False)
    for i in range(16):     # the opening's foreground: wet Cutler St west of the corner, long thin pools
        cx, cy = _rng.uniform(-3200, -400), _rng.uniform(-RY + 40, RY - 40)
        BK.add("cylinder", (cx, cy, 0.35), (_rng.uniform(150, 520) / 100.0, _rng.uniform(70, 200) / 100.0, 0.006),
               "MI_Puddle", rot=(0, _rng.uniform(-12, 12), 0), shadows=False)
    for i in range(10):     # long mirrors under the El / along Delancey: moonlight and sodium have somewhere to sit
        cx, cy = _rng.uniform(-RX + 80, RX - 80), _rng.uniform(-2800, 2600)
        BK.add("cylinder", (cx, cy, 0.35), (_rng.uniform(220, 680) / 100.0, _rng.uniform(50, 140) / 100.0, 0.006),
               "MI_Puddle", rot=(0, _rng.uniform(-8, 8), 0), shadows=False)
    for (x, y) in ((-260, 1900), (300, -1200), (2600, 120), (-2400, -150), (180, 4200)):
        BK.cyl((x, y, 0), 70, 1.6, "MI_Iron_Black", shadows=False)
        BK.cyl((x, y, 0), 78, 0.8, "MI_Rust", shadows=False)
    ACTORS["steam_spots"] = [(-260, 1900), (2600, 120)]


def build_steam():
    """Steam columns from two manholes - Local Fog Volumes (UE 5.3+), lit by the sun / neon."""
    cls = getattr(unreal, "LocalFogVolume", None)
    if cls is None:
        warn("LocalFogVolume not in this engine - no steam")
        return
    for i, (x, y) in enumerate(ACTORS.get("steam_spots", [])):
        # thin wisps, not lit white balloons (v2: dense sun-lit puffs read as glowing blobs)
        a = spawn(cls, (x, y, 200), (0, 0, 0), "Steam_%d" % i, "Base/Steam", scale=(0.12, 0.12, 0.45))
        c = component(a, getattr(unreal, "LocalFogVolumeComponent", unreal.ActorComponent))
        if c:
            set_prop(c, "radial_fog_extinction", 0.5, quiet=True)
            set_prop(c, "height_fog_extinction", 0.6, quiet=True)
            set_prop(c, "height_fog_falloff", 1200.0, quiet=True)
            set_prop(c, "fog_phase_g", 0.25, quiet=True)
            set_prop(c, "fog_albedo", LC(0.55, 0.56, 0.58), quiet=True)


# =========================================================================== the El
EL_Z0, EL_Z1 = 640.0, 760.0
EL_BENTS = (-7300, -5700, -4100, -2500, -900, 900, 2500, 4100, 5700, 7300)


def build_el():
    """Elevated line over Delancey: riveted girders, lattice, ties, rails, steel bents.
    The deck throws striped shadow on the street at golden hour - the single most 'Philly' image."""
    L = 9000.0
    for x in (-330, -170, 170, 330):                            # main girders
        BK.box((x - 14, -L, EL_Z0), (x + 14, L, EL_Z0 + 95), "MI_Steel_ElGreen", collision=True, core=True)
        BK.box((x - 22, -L, EL_Z0 - 6), (x + 22, L, EL_Z0), "MI_Steel_ElGreen")
        BK.box((x - 22, -L, EL_Z0 + 95), (x + 22, L, EL_Z0 + 101), "MI_Steel_ElGreen")
    for x in (-330, 330):                                       # outer lattice web
        for y in range(int(-L), int(L), 120):
            BK.add("cube", (x + (-16 if x < 0 else 16), y + 60, EL_Z0 + 48), (0.04, 1.35, 0.06), "MI_Steel_ElGreen",
                   rot=(45 if (y // 120) % 2 else -45, 0, 0), shadows=False)
    rv = "MI_Steel_Rivet"
    for x in (-330, -170, 170, 330):                            # rivet strips: the lines the eye reads as steel
        for zx0, zx1, z0, z1 in ((-19, -15, EL_Z0 - 8, EL_Z0 - 6), (15, 19, EL_Z0 - 8, EL_Z0 - 6),
                                 (-16, -14, EL_Z0 + 8, EL_Z0 + 11), (14, 16, EL_Z0 + 8, EL_Z0 + 11),
                                 (-16, -14, EL_Z0 + 84, EL_Z0 + 87), (14, 16, EL_Z0 + 84, EL_Z0 + 87)):
            BK.box((x + zx0, -L, z0), (x + zx1, L, z1), rv, shadows=False)
        for y in range(-6000, 6001, 150):                       # web stiffener plates
            BK.box((x - 19, y - 2.5, EL_Z0), (x + 19, y + 2.5, EL_Z0 + 95), "MI_Steel_ElGreen", shadows=False)
    for x in (-250, -110, 110, 250):                            # stringers under the rails: no flat slab
        BK.box((x - 9, -L, EL_Z0 + 46), (x + 9, L, EL_Z0 + 101), "MI_Steel_ElGreen")
        BK.box((x - 13, -L, EL_Z0 + 42), (x + 13, L, EL_Z0 + 46), "MI_Steel_ElGreen", shadows=False)
        BK.box((x - 12, -L, EL_Z0 + 40), (x - 9, L, EL_Z0 + 42), rv, shadows=False)
        BK.box((x + 9, -L, EL_Z0 + 40), (x + 12, L, EL_Z0 + 42), rv, shadows=False)
    for y in range(int(-L), int(L), 300):                       # cross beams
        BK.box((-330, y - 12, EL_Z0 + 10), (330, y + 12, EL_Z0 + 40), "MI_Steel_ElGreen", shadows=False)
    for y in range(int(-L), int(L), 60):                        # ties: the shadow comb
        BK.box((-300, y - 11, EL_Z0 + 101), (300, y + 11, EL_Z0 + 116), "MI_Tie_Wood")
    for x in (-250, -110, 110, 250):                            # rails
        BK.box((x - 4, -L, EL_Z0 + 116), (x + 4, L, EL_Z0 + 128), "MI_Rail_Steel", shadows=False)
    for x in (-345, 345):                                       # catwalk rails
        BK.box((x - 3, -L, EL_Z1 + 80), (x + 3, L, EL_Z1 + 85), "MI_Iron_Black", shadows=False)
        for y in range(int(-L), int(L), 240):
            BK.box((x - 3, y - 3, EL_Z1), (x + 3, y + 3, EL_Z1 + 82), "MI_Iron_Black", shadows=False)
    for y in EL_BENTS:                                          # bents: columns at the curbs
        for x in (-640, 640):
            BK.box((x - 22, y - 22, 0), (x + 22, y + 22, EL_Z0 + 30), "MI_Steel_ElGreen", collision=True, core=True)
            BK.box((x - 34, y - 34, 0), (x + 34, y + 34, 70), "MI_Steel_ElGreen")
            BK.box((x - 30, y - 30, EL_Z0 + 30), (x + 30, y + 30, EL_Z0 + 44), "MI_Steel_ElGreen")
            for sgn in (-1, 1):                                 # knee braces
                BK.add("cube", (x * 0.82, y + sgn * 55, EL_Z0 - 60), (1.5, 0.08, 0.1), "MI_Steel_ElGreen",
                       rot=(0, 0, -35 if x > 0 else 35), shadows=False)
        BK.box((-660, y - 26, EL_Z0 - 10), (660, y + 26, EL_Z0 + 50), "MI_Steel_ElGreen", collision=True, core=True)
    ACTORS["el_track_x"] = 150.0


# =========================================================================== street furniture
def lamp_post(x, y, face_x, idx):
    """Cobra-head street light. Base mesh is shared. Most lamps still work in State A (dimmer
    sodium) so the vacant night is readable; two are dead (the wave will strike them on)."""
    BK.cyl((x, y, CURB_H), 26, 30, "MI_Iron_Black")
    BK.cyl((x, y, CURB_H), 14, 820, "MI_Iron_Black")
    arm_x = x + face_x * 200
    BK.box((min(x, arm_x), y - 5, 820), (max(x, arm_x), y + 5, 832), "MI_Iron_Black")
    BK.box((arm_x - 45 * face_x - 30, y - 24, 805), (arm_x + 30, y + 24, 836), "MI_Chrome_Dull")
    # idx 0 and 5 stay dark in A (a dead head on the south block, one far east). The rest work.
    if idx not in (0, 5):
        ga = Group("A", "StreetLamp_%d" % idx, (arm_x, y, 805), folder="StreetLamps")
        ga.pop = False
        ga.box((arm_x - 34, y - 12, 801), (arm_x + 8, y + 12, 805), "MIR_A_Lamp_Sodium", shadows=False)
        ga.light("spot", (arm_x, y, 795), S.A_STREETLAMP_CD, kelvin_temp=2100, radius=2200,
                 target=(arm_x, y, 0), inner=40, outer=68, volumetric=S.A_STREETLAMP_VOLUMETRIC)
    g = Group("B", "StreetLamp_%d" % idx, (arm_x, y, 805), folder="StreetLamps")
    g.pop = False
    g.box((arm_x - 34, y - 12, 801), (arm_x + 8, y + 12, 805), "MIR_B_Lamp_Sodium", shadows=False)   # small lens
    g.light("spot", (arm_x, y, 795), S.B_STREETLAMP_CD, kelvin_temp=2100, radius=2200, target=(arm_x, y, 0),
            inner=40, outer=68, volumetric=S.B_STREETLAMP_VOLUMETRIC)


def newspaper_box(x, y, yaw, mat_name, label, idx):
    a = math.radians(yaw)
    ca, sa = math.cos(a), math.sin(a)
    BK.add("cube", (x, y, CURB_H + 55), (0.5, 0.45, 1.1), mat_name, rot=(0, yaw, 0))
    BK.add("cube", (x + ca * -23, y + sa * -23, CURB_H + 85), (0.02, 0.36, 0.3), "MI_Glass_Window", rot=(0, yaw, 0),
           shadows=False)
    BK.add("cube", (x, y, CURB_H + 111), (0.54, 0.49, 0.04), "MI_Chrome_Dull", rot=(0, yaw, 0))
    t = G._text(label, (x + ca * -26, y + sa * -26, CURB_H + 62), 7.0, col(240, 240, 235), folder="Base/Signage",
                yaw=yaw + 180)
    return t


def mailbox(x, y):
    BK.box((x - 30, y - 25, CURB_H), (x + 30, y + 25, CURB_H + 110), "MI_Box_Blue")
    BK.cyl((x, y - 25, CURB_H + 100), 60, 1, "MI_Box_Blue")
    BK.add("cylinder", (x, y, CURB_H + 112), (0.6, 0.5, 0.5), "MI_Box_Blue", rot=(0, 0, 90))
    G._text("LAKEMONT POST", (x - 31, y, CURB_H + 80), 6.0, col(230, 235, 255), folder="Base/Signage")


def hydrant(x, y):
    BK.cyl((x, y, CURB_H), 28, 62, "MI_Hydrant_Red")
    BK.add("sphere", (x, y, CURB_H + 66), (0.3, 0.3, 0.22), "MI_Hydrant_Red")
    BK.add("cylinder", (x, y, CURB_H + 42), (0.14, 0.14, 0.5), "MI_Hydrant_Red", rot=(0, 0, 90))


def utility_pole(x, y, h=1050):
    BK.cyl((x, y, CURB_H), 30, h, "MI_Wood_Pole")
    BK.box((x - 130, y - 7, h - 70), (x + 130, y + 7, h - 56), "MI_Wood_Pole")
    BK.box((x - 90, y - 6, h - 160), (x + 90, y + 6, h - 148), "MI_Wood_Pole")
    BK.cyl((x + 60, y + 25, h - 260), 48, 90, "MI_Chrome_Dull")            # transformer can
    for dx in (-110, -40, 40, 110):
        BK.cyl((x + dx, y, h - 56), 7, 12, "MI_Trim_Cream", shadows=False)    # insulators
    return [(x + dx, y, h - 50) for dx in (-110, -40, 40, 110)] + [(x - 70, y, h - 145), (x + 70, y, h - 145)]


def wire(a, b, sag=60.0, segments=8):
    """Catenary approximation: a chain of thin boxes."""
    pts = []
    for i in range(segments + 1):
        t = i / float(segments)
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - sag * 4 * t * (1 - t)))
    for p, q in zip(pts, pts[1:]):
        dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        ln = math.sqrt(dx * dx + dy * dy + dz * dz)
        BK.add("cube", ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2), (ln / 100.0, 0.025, 0.025), "MI_Cable",
               rot=(math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)), 0), shadows=False)


def traffic_signal(x, y, face_yaw):
    BK.cyl((x, y, CURB_H), 22, 430, "MI_Iron_Black")
    a = math.radians(face_yaw)
    hx, hy = x + math.cos(a) * 18, y + math.sin(a) * 18
    BK.add("cube", (hx, hy, 380), (0.36, 0.36, 1.0), "MI_Box_Green", rot=(0, face_yaw, 0))
    for k, m in enumerate(("MI_E_TrafficRed", "MI_Trim_Dark", "MI_Trim_Dark")):
        BK.add("sphere", (hx + math.cos(a) * 19, hy + math.sin(a) * 19, 412 - k * 31), (0.2, 0.2, 0.2), m, shadows=False)


def street_sign(x, y, z, txt, yaw):
    BK.add("cube", (x, y, z), (0.03, 1.1, 0.24) if abs(math.sin(math.radians(yaw))) < 0.5 else (1.1, 0.03, 0.24),
           "MI_Box_Green", shadows=False)
    G._text(txt, (x - 3 * math.cos(math.radians(yaw)), y - 3 * math.sin(math.radians(yaw)), z), 13.0,
            col(240, 240, 240), folder="Base/Signage", yaw=yaw + 180)


def tree(x, y, idx):
    """Street tree: trunk in base; bare branches in A, a full canopy in B."""
    BK.box((x - 60, y - 60, CURB_H), (x + 60, y + 60, CURB_H + 3), "MI_Iron_Black", shadows=False)
    BK.cyl((x, y, CURB_H), 24, 360, "MI_Wood_Pole")
    for k in range(4):
        a = k * 90 + 30
        BK.add("cube", (x + math.cos(math.radians(a)) * 60, y + math.sin(math.radians(a)) * 60, 430),
               (1.5, 0.08, 0.08), "MI_Wood_Pole", rot=(35, a, 0))
    g = Group("B", "TreeCanopy_%d" % idx, (x, y, 540), folder="Trees")
    for k in range(5):
        g.sph((x + _rng.uniform(-90, 90), y + _rng.uniform(-90, 90), 520 + _rng.uniform(-40, 80)),
              (_rng.uniform(200, 280), _rng.uniform(200, 280), _rng.uniform(160, 220)), "MIR_B_Leaves")


def build_furniture():
    lamps = [(-1000, -2600, 1), (-1000, 2400, 1), (1000, -1900, -1), (1000, 3200, -1), (-3300, -650, 1),
             (3600, 650, -1)]
    for i, (x, y, f) in enumerate(lamps):
        lamp_post(x, y, f, i)
    newspaper_box(-1040, 980, 0, "MI_Box_Red", "LAKEMONT LEDGER", 0)
    newspaper_box(-1040, 1060, 0, "MI_Box_Blue", "THE DAILY CIRCUIT", 1)
    mailbox(-1050, -980)
    hydrant(1030, 2050)
    hydrant(-1040, -1650)
    poles = [(-1080, -3600), (-1080, -900), (-1080, 1800), (-1080, 4500)]
    tops = [utility_pole(x, y) for (x, y) in poles]
    for t0, t1 in zip(tops, tops[1:]):
        for k in range(len(t0)):
            wire(t0[k], t1[k], sag=_rng.uniform(40, 90))
    for k in range(4):                                         # service drops across the street
        wire(tops[1][k], (SX + 5, -1700 + k * 40, 760 - k * 30), sag=80)
        wire(tops[2][k], (SX + 5, 1900 + k * 60, 800 - k * 25), sag=90)
    wire((-SX, 900, 600), (SX, 950, 620), sag=110, segments=10)      # sneakers on a wire belong here
    BK.add("cube", (0, 925, 470), (0.28, 0.1, 0.1), "MI_Rubber", rot=(0, 0, 70))
    BK.add("cube", (12, 930, 462), (0.28, 0.1, 0.1), "MI_Rubber", rot=(0, 0, 110))
    traffic_signal(-RX - 60, -RY - 60, 90)
    traffic_signal(RX + 60, RY + 60, -90)
    traffic_signal(-RX - 60, RY + 60, 0)
    street_sign(-RX - 60, RY + 60, 470, "DELANCEY AV", 0)
    street_sign(-RX - 60, RY + 120, 500, "CUTLER ST", 90)
    for i, (x, y) in enumerate(((-950, -1900), (-950, 3000), (950, 4600), (950, -3200))):
        tree(x, y, i)
    for (x, y) in ((-1080, 1350), (1060, -1400)):              # trash cans (base)
        BK.cyl((x, y, CURB_H), 60, 92, "MI_Iron_Black")
        BK.cyl((x, y, CURB_H + 92), 64, 4, "MI_Iron_Black")


# =========================================================================== city blocks + skyline
def build_blocks():
    """Eight block faces of row houses, then 3-6 storey back masses and the skyline."""
    faces = [
        ("W_N", Facade((-SX, SY, 0), (0, 1, 0), (-1, 0, 0)), SY, 7),
        ("W_S", Facade((-SX, -SY, 0), (0, -1, 0), (-1, 0, 0)), SY, 7),
        ("E_N", Facade((SX, 1700, 0), (0, 1, 0), (1, 0, 0)), 1700, 6),
        ("E_S", Facade((SX, -SY, 0), (0, -1, 0), (1, 0, 0)), SY, 7),
        ("N_W", Facade((-SX, SY, 0), (-1, 0, 0), (0, 1, 0)), SX, 6),
        ("S_W", Facade((-SX, -SY, 0), (-1, 0, 0), (0, -1, 0)), SX, 6),
        ("N_E", Facade((2350, SY, 0), (1, 0, 0), (0, 1, 0)), 2350, 5),
        ("S_E", Facade((SX, -SY, 0), (1, 0, 0), (0, -1, 0)), SX, 6),
    ]
    starts = {"N_W": 1100.0, "S_W": 1100.0, "S_E": 1100.0,   # skip the corner lot the cross face owns
              "E_S": 700.0}                                  # E_S 0..650 = the Cortaz lot (state-swapped)
    for key, F, _u0, n in faces:
        count = max(3, int(n * S.RIPPLE_HOUSES_PER_SIDE / 7.0))
        block_face(F, key, starts.get(key, 0.0), count)
    ACTORS["facades"] = dict((k, F) for (k, F, _u, _n) in faces)
    for sx in (-1, 1):                                          # back masses behind the row houses
        for sy in (-1, 1):
            for k in range(4):
                x0 = sx * (SX + 1300 + k * 1300)
                far_mass((min(x0, x0 + sx * 1100), min(sy * (SY + 1300), sy * 7000), 0),
                         (max(x0, x0 + sx * 1100), max(sy * (SY + 1300), sy * 7000), _rng.uniform(900, 2100)))


TOWERS = []


def _skyline_windows(state, frac, mat_name, seed):
    """Lit windows on the tower face that looks at the corner: one ISM per state, so downtown
    'switches on' when the wave reaches it (State B) or keeps a few cold TVs (State A)."""
    rr = random.Random(seed)
    items = []
    for (cx, cy, w, d, h) in TOWERS:
        if abs(cx) >= abs(cy):        # face toward the corner
            sgn = -1 if cx > 0 else 1
            fx, span, along = cx + sgn * (w / 2 + 6), d, "y"
        else:
            sgn = -1 if cy > 0 else 1
            fx, span, along = cy + sgn * (d / 2 + 6), w, "x"
        bays = max(3, int(span / 300))
        for fl in range(2, int(h / 330) - 1):
            z = fl * 330 + 120
            for b in range(bays):
                if rr.random() > frac:
                    continue
                off = -span / 2 + (b + 0.5) * span / bays
                if along == "y":
                    items.append(((fx, cy + off, z), (0.04, 1.9, 2.0), (0, 0, 0)))
                else:
                    items.append(((cx + off, fx, z), (1.9, 0.04, 2.0), (0, 0, 0)))
    if items:
        g = Group(state, "SkylineWindows", (6000, 0, 3000), folder="Skyline")
        g.pop = False
        g.ism("cube", items, mat_name, shadows=False)
    return len(items)


def build_skyline():
    """Downtown Lakemont on the horizon: 22 towers with setbacks, crowns, aviation lights.
    The window material gives each a random lit-window pattern; the sun + fog layer them."""
    for i in range(22):
        ang = math.radians(_rng.uniform(-70, 70) + (0 if i % 2 else 180))
        dist = _rng.uniform(18000, 42000)
        cx, cy = math.cos(ang) * dist + 6000, math.sin(ang) * dist
        if cx < -8000 and abs(cy) < 9000:
            cx += 30000
        w, d, h = _rng.uniform(1500, 3800), _rng.uniform(1500, 3800), _rng.uniform(6000, 21000)
        tmat = ("MI_Tower_Far", "MI_Rowhouse_Far_Grey", "MI_Rowhouse_Far")[i % 3]   # glass / limestone / brick
        BK.box((cx - w / 2, cy - d / 2, 0), (cx + w / 2, cy + d / 2, h), tmat, shadows=False, core=True)
        TOWERS.append((cx, cy, w, d, h))
        tz = h
        for _s in range(_rng.randint(0, 3)):                    # setbacks
            w *= 0.75
            d *= 0.75
            th = _rng.uniform(1200, 3500)
            BK.box((cx - w / 2, cy - d / 2, tz), (cx + w / 2, cy + d / 2, tz + th), tmat, shadows=False, core=True)
            tz += th
        if _rng.random() < 0.4:
            BK.add("cylinder", (cx, cy, tz + 900), (0.6, 0.6, 18.0), "MI_Iron_Black", shadows=False, core=True)
            BK.add("sphere", (cx, cy, tz + 1820), (1.4, 1.4, 1.4), "MI_E_TrafficRed", shadows=False, core=True)


# =========================================================================== the bodega (base shell)
BX0, BX1, BY0, BY1 = SX, 2350.0, SY, 1700.0
SHOP_Y0, SHOP_Y1, SHOP_Z1 = 850.0, 1650.0, 330.0
DOOR_Y0, DOOR_Y1 = 950.0, 1075.0


def build_bodega_shell():
    """Three-storey corner building; ground floor storefront facing Delancey (-X).
    The opening is filled per state: rolled-down shutters (A) / glass, awning, interior (B)."""
    H = CURB_H + 3 * FLOOR_H + 80
    BK.box((BX0, BY0, SHOP_Z1), (BX1, BY1, H), "MI_Brick_Brown", collision=True, core=True)
    BK.box((BX0 + 600, BY0, 0), (BX1, BY1, SHOP_Z1), "MI_Brick_Brown", collision=True, core=True)
    BK.box((BX0, BY0, 0), (BX0 + 600, SHOP_Y0, SHOP_Z1), "MI_Brick_Brown", collision=True, core=True)
    BK.box((BX0, SHOP_Y1, 0), (BX0 + 600, BY1, SHOP_Z1), "MI_Brick_Brown", collision=True, core=True)
    BK.box((BX0 + 20, SHOP_Y0, 0), (BX0 + 600, SHOP_Y1, CURB_H + 2), "MI_Sidewalk", core=True)       # shop floor
    BK.box((BX0 + 590, SHOP_Y0, 0), (BX0 + 600, SHOP_Y1, SHOP_Z1), "MI_Trim_Dark", core=True)        # back wall
    BK.box((BX0 + 20, SHOP_Y0, SHOP_Z1 - 10), (BX0 + 600, SHOP_Y1, SHOP_Z1), "MI_Trim_Dark", core=True)
    BK.box((BX0 - 30, BY0 - 30, SHOP_Z1), (BX0, BY1 + 30, SHOP_Z1 + 60), "MI_Trim_Dark")                # sign band
    BK.box((BX0 - 45, BY0 - 45, H - 50), (BX0 + 10, BY1 + 45, H - 20), "MI_Trim_Cream")                 # cornice
    for y in (BY0, SHOP_Y1, DOOR_Y0 - 20, DOOR_Y1):                                                     # pilasters
        BK.box((BX0 - 20, y, 0), (BX0, y + 20 if y != BY0 else y + 50, SHOP_Z1), "MI_Trim_Dark")
    F = Facade((BX0, BY0, 0), (0, 1, 0), (1, 0, 0))
    for f in (1, 2):
        z0 = CURB_H + f * FLOOR_H + 70
        for k in range(3):
            uc = 150 + k * 300
            _bk_box(F, uc - 55, uc + 55, -1, 1, z0, z0 + 170, "MI_Glass_Window", core=True)
            _bk_box(F, uc - 66, uc + 66, -8, 0, z0 + 170, z0 + 196, "MI_Trim_Cream")
            _bk_box(F, uc - 60, uc + 60, -11, 0, z0 - 10, z0, "MI_Trim_Cream")
            mn, mx = F.mm(uc - 51, uc + 51, -1.8, -1.2, z0 + 4, z0 + 166)
            WINDOWS_LIT["BODEGA"]["B"].append((mn, mx))
            if f == 2 and k == 1:
                WINDOWS_LIT["BODEGA"]["A"].append((mn, mx))      # someone still lives upstairs
    ACTORS["facades"]["BODEGA"] = F
    ACTORS["focus_door"] = pivot((BX0, (DOOR_Y0 + DOOR_Y1) / 2, 150), "Focus_BodegaDoor", "Cameras/Focus")
    ACTORS["focus_counter"] = pivot((1515, 1250, 165), "Focus_Counter", "Cameras/Focus")


# =========================================================================== State A - Vacant
def build_state_a():
    """The corner as Josh knows it: dead store, tags, the memorial nobody tends anymore."""
    g = Group("A", "Shutters", (BX0 - 12, 1250, 170), folder="Bodega")
    for (y0, y1) in ((SHOP_Y0, DOOR_Y0 - 20), (DOOR_Y1 + 20, SHOP_Y1)):
        g.box((BX0 - 14, y0, CURB_H), (BX0 - 6, y1, SHOP_Z1 - 10), "MIR_A_Shutter")
        for z in range(int(CURB_H) + 12, int(SHOP_Z1) - 10, 12):                     # slat ribs
            g.box((BX0 - 16, y0, z), (BX0 - 14, y1, z + 3), "MIR_A_Rust", shadows=False)
        g.box((BX0 - 30, y0 - 5, SHOP_Z1 - 40), (BX0 - 6, y1 + 5, SHOP_Z1 - 5), "MIR_A_Rust")          # roll box
    g.box((BX0 - 18, DOOR_Y0, CURB_H), (BX0 - 6, DOOR_Y1, 280), "MIR_A_Plywood")                    # boarded door
    g.box((BX0 - 22, DOOR_Y0 - 10, 150), (BX0 - 18, DOOR_Y1 + 10, 168), "MIR_A_PlywoodGrey", rot=(0, 0, 12))
    g.box((BX0 - 24, 1050, 120), (BX0 - 18, 1062, 136), "MIR_A_Rust")                              # padlock
    g.box((BX0 - 22, 1100, 200), (BX0 - 18, 1250, 280), "MIR_A_SignFaded")
    t = Group("A", "Signage", (BX0 - 40, 1250, 360), folder="Bodega")
    t.pop = False
    t.text("FOR LEASE  555-0142", (BX0 - 24, 1175, 240), 11.0, col(30, 30, 30))
    t.text(S.RIPPLE_BODEGA_FADED, (BX0 - 34, 1250, 360), 34.0, col(120, 105, 85))                  # missing letter
    t.box((BX0 - 33, BY0 + 20, SHOP_Z1 + 6), (BX0 - 31, BY1 - 20, SHOP_Z1 + 54), "MIR_A_SignFaded", shadows=False)
    tags = Group("A", "Graffiti", (BX0 - 10, 1250, 180), folder="Bodega")
    tags.pop = False
    for i in range(9):
        y, z = _rng.uniform(SHOP_Y0 + 20, SHOP_Y1 - 80), _rng.uniform(60, 280)
        tags.box((BX0 - 16.5, y, z), (BX0 - 16, y + _rng.uniform(40, 140), z + _rng.uniform(20, 70)),
                 _rng.choice(("MIR_A_Graffiti_Pink", "MIR_A_Graffiti_Teal", "MIR_A_Graffiti_Yellow")), shadows=False)
    for i, (txt, y, z, c) in enumerate((("RVSD", 1450, 220, (255, 80, 160)), ("KEEP OUT", 900, 150, (240, 220, 60)),
                                        ("NO HOPE ON CUTLER", 1400, 90, (80, 230, 220)),
                                        ("J+A 4EVER", 2200, 160, (250, 250, 250)))):
        x = BX0 - 17 if y < BY1 else BX0 - 20
        if y >= BY1:
            tags.text(txt, (BX0 + 400, BY0 - 5, z), 20.0, col(*c), yaw=90)
        else:
            tags.text(txt, (x, y, z), 18.0 + 4 * (i % 2), col(*c))
    m = Group("A", "Memorial", (BX0 - 50, 1010, 30), folder="Bodega")                              # 'PAPI'
    for k in range(7):
        y = 960 + k * 17
        m.cyl((BX0 - 40 - (k % 2) * 14, y, CURB_H), 7, 14 + (k % 3) * 6, "MIR_A_Candle_Out")
    for k in range(4):
        m.box((BX0 - 66, 965 + k * 26, CURB_H), (BX0 - 58, 975 + k * 26, CURB_H + 34), "MIR_A_Flowers_Dead",
              rot=(0, 0, _rng.uniform(-30, 30)))
    m.box((BX0 - 20, 990, 70), (BX0 - 18, 1030, 120), "MIR_A_Newsprint")
    m.text("PAPI", (BX0 - 22, 1010, 60), 8.0, col(60, 50, 40))
    trash = Group("A", "TrashPile", (-1000, 1450, 50), folder="Litter")
    for k in range(9):
        trash.sph((-1060 + _rng.uniform(-40, 40), 1380 + k * 25 + _rng.uniform(-10, 10), CURB_H + 30),
                  (_rng.uniform(55, 80), _rng.uniform(55, 80), _rng.uniform(45, 70)), "MIR_A_TrashBag")
    for k in range(4):
        trash.box((BX0 - 140 - k * 50, 1500 + k * 20, CURB_H), (BX0 - 80 - k * 50, 1560 + k * 20, CURB_H + 40 - k * 6),
                  "MIR_A_Cardboard", rot=(0, _rng.uniform(-20, 20), 0))
    trash.cyl((BX0 - 260, 1350, CURB_H), 60, 90, "MIR_A_Rust", rot=(0, 0, 90))                     # tipped can
    news = []
    for k in range(70):
        x, y = _rng.uniform(-1100, 1100), _rng.uniform(-1500, 2000)
        if abs(x) < RX - 30 or _rng.random() < 0.4:
            news.append(((x, y, CURB_H + 0.6 if abs(x) > RX else 0.6), (_rng.uniform(0.2, 0.42), _rng.uniform(0.16, 0.3), 0.004),
                         (0, _rng.uniform(0, 180), 0)))
    trash.ism("cube", news, "MIR_A_Newsprint", shadows=False)
    car = Group("A", "CarOnBlocks", (-480, 2100, 80), folder="Cars")
    _car(car, (-480, 2100), 0.0, "MIR_A_CarDusty", glass="MIR_A_Cinder", wheels=False)
    for dx in (-140, 140):
        for dy in (-75, 75):
            car.box((-480 + dx - 20, 2100 + dy - 20, 0), (-480 + dx + 20, 2100 + dy + 20, 32), "MIR_A_Cinder")
    tube = Group("A", "Fluorescent", (-640, 900, 600), folder="Bodega")
    tube.pop = False
    tube.box((-650, 840, 590), (-630, 960, 596), "MIR_A_Fluoro", shadows=False)
    tube.light("point", (-600, 900, 570), S.A_FLUORO_CD, kelvin_temp=6500, radius=900, volumetric=0.3, source_radius=2)
    ch = Group("A", "CortazHouse", (1700, -1150, 300), folder="Cortaz")                             # intact in A
    ch.box((1150, -1450, 0), (2250, -850, 1080), "MIR_A_Brick_Cortaz", collision=False)
    ch.box((1140, -1460, 1040), (1160, -840, 1080), "MIR_A_Cinder")
    for z in (420, 750):
        for y in (-1350, -1150, -950):
            ch.box((1148, y - 50, z), (1150, y + 50, z + 170), "MIR_A_Cinder", shadows=False)
    ch.box((1148, -1210, CURB_H), (1150, -1110, 250), "MIR_A_Shutter", shadows=False)
    for (x0, y0, y1) in ((-SX - 2, 1850, 2350), (-SX - 2, -2700, -2200)):                          # boarded neighbours
        nb = Group("A", "BoardedNeighbor_%d" % int(y0), (x0, (y0 + y1) / 2, 150), folder="Neighbors")
        nb.box((x0 - 8, y0, 40), (x0, y1, 300), "MIR_A_Plywood")
        nb.box((x0 - 9, y0 + 30, 120), (x0 - 8, y0 + 160, 170), "MIR_A_Graffiti_Teal", shadows=False)
    # a security flood and light leaks so the boarded Lucky Star is readable before the ripple hits
    sec = Group("A", "SecurityFlood", (BX0 - 80, 1010, 360), folder="Bodega")
    sec.pop = False
    sec.box((BX0 - 28, 990, 350), (BX0 - 16, 1030, 368), "MI_Iron_Black", shadows=False)
    sec.box((BX0 - 22, 998, 352), (BX0 - 14, 1022, 366), "MIR_A_Fluoro", shadows=False)
    sec.light("spot", (BX0 - 70, 1010, 355), S.A_SECURITY_CD, kelvin_temp=4200, radius=1600,
              target=(BX0 - 10, 1010, 140), inner=28, outer=62, volumetric=0.25)
    leak = Group("A", "ShutterLeaks", (BX0 - 20, 1250, 180), folder="Bodega")
    leak.pop = False
    for (y0, y1) in ((SHOP_Y0, DOOR_Y0 - 20), (DOOR_Y1 + 20, SHOP_Y1)):
        leak.box((BX0 - 17, y0 + 8, CURB_H + 4), (BX0 - 15, y0 + 18, SHOP_Z1 - 16), "MIR_A_Leak", shadows=False)
        leak.box((BX0 - 17, y1 - 18, CURB_H + 4), (BX0 - 15, y1 - 8, SHOP_Z1 - 16), "MIR_A_Leak", shadows=False)
        leak.box((BX0 - 17, y0 + 8, SHOP_Z1 - 22), (BX0 - 15, y1 - 8, SHOP_Z1 - 14), "MIR_A_Leak", shadows=False)
    leak.box((BX0 - 20, DOOR_Y0 + 4, CURB_H + 4), (BX0 - 16, DOOR_Y0 + 10, 270), "MIR_A_Leak", shadows=False)
    leak.box((BX0 - 20, DOOR_Y1 - 10, CURB_H + 4), (BX0 - 16, DOOR_Y1 - 4, 270), "MIR_A_Leak", shadows=False)
    _window_overlays("A")
    _skyline_windows("A", float(getattr(S, "RIPPLE_SKYLINE_WINDOWS_A", 0.12)), "MIR_A_Window_Lit", S.RIPPLE_SEED + 5)


def _window_overlays(state):
    """Lit windows as one ISM per state - the street 'breathes' when the wave passes."""
    items = []
    for key, d in WINDOWS_LIT.items():
        for (mn, mx) in d[state]:
            c = ((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2)
            items.append((c, (max(0.01, (mx[0] - mn[0]) / 100.0), max(0.01, (mx[1] - mn[1]) / 100.0), (mx[2] - mn[2]) / 100.0),
                          (0, 0, 0)))
    if items:
        g = Group(state, "LitWindows", (0, 0, 400), folder="Windows")
        g.pop = False
        g.ism("cube", items, "MIR_%s_Window_Lit" % state, shadows=False)


def _car(g, at, yaw, paint, glass="MIR_B_CarGlass", wheels=True, cab=False):
    """Sedan from shapes, long axis along Y (yaw 0) or X (yaw 90)."""
    x, y = at
    ax = abs(math.sin(math.radians(yaw))) > 0.5

    def bx(cx, cy, z0, lx, ly, z1, m):
        if ax:
            g.box((x + cy - ly / 2, y + cx - lx / 2, z0), (x + cy + ly / 2, y + cx + lx / 2, z1), m)
        else:
            g.box((x + cx - lx / 2, y + cy - ly / 2, z0), (x + cx + lx / 2, y + cy + ly / 2, z1), m)
    base_z = 32 if wheels else 30
    bx(0, 0, base_z, 180, 460, base_z + 70, paint)
    bx(0, -20, base_z + 70, 165, 240, base_z + 125, glass)
    bx(0, -20, base_z + 125, 160, 230, base_z + 133, paint)
    bx(0, 232, base_z + 20, 170, 6, base_z + 40, "MIR_B_Chrome" if wheels else "MIR_A_Rust")
    if wheels:
        for cx in (-82, 82):
            for cy in (-150, 150):
                if ax:
                    g.cyl((x + cy, y + cx - 10, 32), 64, 22, "MIR_B_Tire", rot=(0, 0, 90))
                else:
                    g.cyl((x + cx - 11, y + cy, 32), 64, 22, "MIR_B_Tire", rot=(90, 0, 0))
    if cab:
        bx(0, -20, base_z + 133, 50, 30, base_z + 160, "MIR_B_Lightbox")


# =========================================================================== State B - Busy
def build_state_b():
    """The corner if Dad lived: open late, loud, warm. Every light here is a choice Josh made."""
    sg = Group("B", "Signage", (BX0 - 40, 1250, 360), folder="Bodega")
    sg.pop = False
    sg.box((BX0 - 36, BY0 + 30, SHOP_Z1 + 6), (BX0 - 30, BY1 - 30, SHOP_Z1 + 56), "MIR_B_Lightbox", shadows=False)
    sg.text(S.RIPPLE_BODEGA_NAME, (BX0 - 38, 1250, SHOP_Z1 + 36), 34.0, col(200, 20, 20))
    sg.text("GROCERY \u00b7 DELI \u00b7 LOTTO \u00b7 ATM", (BX0 - 38, 1250, SHOP_Z1 + 14), 11.0, col(30, 30, 30))
    sg.light("point", (BX0 - 120, 1250, SHOP_Z1 + 30), S.B_BODEGA_CD * 0.35, kelvin_temp=5200, radius=900,
             volumetric=1.0, source_radius=60)
    aw = Group("B", "Awning", (BX0 - 110, 1250, SHOP_Z1 - 20), folder="Bodega")              # striped, tilted 18°
    stripes = ("MIR_B_Awning_Red", "MIR_B_Awning_Cream")
    n = 16
    for k in range(n):
        y0 = SHOP_Y0 - 30 + k * (SHOP_Y1 - SHOP_Y0 + 60) / n
        y1 = y0 + (SHOP_Y1 - SHOP_Y0 + 60) / n
        aw.box((BX0 - 220, y0, SHOP_Z1 - 50), (BX0, y1, SHOP_Z1 - 44), stripes[k % 2], rot=(0, 0, 0))
        aw.box((BX0 - 224, y0, SHOP_Z1 - 90), (BX0 - 218, y1, SHOP_Z1 - 44), stripes[k % 2], shadows=False)
    for (y,) in ((SHOP_Y0 - 30,), (SHOP_Y1 + 24,)):
        aw.box((BX0 - 220, y, SHOP_Z1 - 52), (BX0, y + 6, SHOP_Z1 - 42), "MIR_B_Chrome", shadows=False)
    neon = Group("B", "Neon", (BX0 - 8, 1400, 230), folder="Bodega")
    neon.pop = False
    neon.text("OPEN", (BX0 - 6, 1480, 230), 36.0, col(255, 40, 60))
    neon.box((BX0 - 5, 1420, 205), (BX0 - 4, 1540, 208), "MIR_B_Neon_Red", shadows=False)
    neon.box((BX0 - 5, 1420, 252), (BX0 - 4, 1540, 255), "MIR_B_Neon_Red", shadows=False)
    neon.text("24 HRS", (BX0 - 6, 1300, 260), 22.0, col(60, 160, 255))
    neon.box((BX0 - 5, 1250, 245), (BX0 - 4, 1350, 247), "MIR_B_Neon_Blue", shadows=False)
    neon.light("point", (BX0 - 60, 1450, 230), S.B_NEON_CD, kelvin_temp=1800, radius=650, volumetric=2.5, source_radius=30)
    po = Group("B", "Posters", (BX0 - 4, 1200, 120), folder="Bodega")
    po.pop = False
    for (txt, y, z, c, m) in (("KOLA KING", 1150, 120, (240, 240, 240), "MIR_B_Paint_Cherry"),
                              ("LAKEMONT LOTTO", 1330, 90, (20, 20, 20), "MIR_B_Products_B"),
                              ("FRESH COFFEE 99\u00a2", 1580, 120, (30, 20, 10), "MIR_B_Awning_Cream"),
                              ("WE ACCEPT EBT", 900, 200, (20, 40, 120), "MIR_B_Products_C")):
        po.box((BX0 - 3, y - 45, z - 25), (BX0 - 2, y + 45, z + 25), m, shadows=False)
        po.text(txt, (BX0 - 4, y, z), 8.0, col(*c))
    gl = Group("B", "Storefront", (BX0 - 2, 1250, 170), folder="Bodega")
    gl.pop = False
    for (y0, y1) in ((SHOP_Y0, DOOR_Y0 - 20), (DOOR_Y1 + 20, SHOP_Y1)):
        gl.box((BX0 - 2, y0, 60), (BX0, y1, SHOP_Z1 - 12), "MI_Glass_Window", shadows=False)
        gl.box((BX0 - 6, y0, CURB_H), (BX0, y1, 60), "MIR_B_Paint_Teal")
    gl.box((BX0 - 4, DOOR_Y0, CURB_H), (BX0, DOOR_Y1, 290), "MIR_B_Chrome", shadows=False)
    gl.box((BX0 - 2, DOOR_Y0 + 10, 40), (BX0 + 2, DOOR_Y1 - 10, 280), "MI_Glass_Window", shadows=False)
    inn = Group("B", "Interior", (BX0 + 300, 1250, 170), folder="Bodega")
    inn.box((BX0 + 560, SHOP_Y0 + 20, CURB_H), (BX0 + 590, SHOP_Y1 - 20, 300), "MIR_B_Interior")                 # coolers
    for k in range(6):
        y = SHOP_Y0 + 40 + k * 125
        inn.box((BX0 + 552, y, 40), (BX0 + 558, y + 110, 290), "MI_Glass_Window", shadows=False)
    for k in range(4):                                                                                           # ceiling panels
        inn.box((BX0 + 100 + k * 120, SHOP_Y0 + 100, SHOP_Z1 - 14), (BX0 + 160 + k * 120, SHOP_Y1 - 100, SHOP_Z1 - 11),
                "MIR_B_Lightbox", shadows=False)
    prods = {"MIR_B_Products_A": [], "MIR_B_Products_B": [], "MIR_B_Products_C": []}
    for s_i, x in enumerate((BX0 + 220, BX0 + 340, BX0 + 460)):                                                 # shelves
        inn.box((x - 25, SHOP_Y0 + 380, CURB_H), (x + 25, SHOP_Y1 - 60, 170), "MIR_B_Shelf")
        for z in (55, 100, 145):
            for y in range(int(SHOP_Y0 + 390), int(SHOP_Y1 - 70), 22):
                for sx in (-1, 1):
                    prods[_rng.choice(list(prods))].append(((x + sx * 30, y + 10, z + 14),
                                                            (0.12, 0.16, _rng.uniform(0.2, 0.3)), (0, 0, 0)))
    for m_name, items in prods.items():
        inn.ism("cube", items, m_name, shadows=False)
    inn.box((BX0 + 220, SHOP_Y0 + 60, CURB_H), (BX0 + 300, SHOP_Y0 + 330, 115), "MIR_B_Counter")               # counter
    inn.box((BX0 + 240, SHOP_Y0 + 230, 115), (BX0 + 280, SHOP_Y0 + 290, 140), "MIR_B_Chrome")                 # register
    inn.box((BX0 + 296, SHOP_Y0 + 70, 115), (BX0 + 300, SHOP_Y0 + 320, 180), "MI_Glass_Window", shadows=False)
    inn.light("point", (BX0 + 280, 1250, 300), S.B_BODEGA_CD, kelvin_temp=4600, radius=1400, volumetric=1.2, source_radius=90)
    inn.light("point", (BX0 + 140, SHOP_Y0 + 200, 260), S.B_BODEGA_CD * 0.6, kelvin_temp=3600, radius=1100, volumetric=1.0)
    pr = Group("B", "ProduceStands", (BX0 - 160, 1250, 60), folder="Bodega")
    fruit = {"MIR_B_Orange": [], "MIR_B_Apple": [], "MIR_B_Lime": [], "MIR_B_Banana": []}
    for k, (y0, mname) in enumerate(((SHOP_Y0 - 10, "MIR_B_Orange"), (1120, "MIR_B_Apple"), (1300, "MIR_B_Lime"),
                                     (1470, "MIR_B_Banana"))):
        y1 = y0 + 150
        pr.box((BX0 - 230, y0, CURB_H), (BX0 - 90, y1, CURB_H + 70), "MIR_B_Crate", rot=(0, 0, 0))
        for i in range(5):                                        # tilted display crates
            for j in range(4):
                fx, fy = BX0 - 215 + i * 28, y0 + 18 + j * 37
                fruit[mname].append(((fx, fy, CURB_H + 82 + i * 7), (0.17, 0.17 if mname != "MIR_B_Banana" else 0.34, 0.15),
                                     (0, 0, 0)))
    for m_name, items in fruit.items():
        pr.ism("sphere", items, m_name, shadows=False)
    fl = Group("B", "Flowers", (BX0 - 160, 900, 50), folder="Bodega")
    for k in range(5):
        fl.cyl((BX0 - 120, 870 + k * 30 - 80, CURB_H), 26, 40, "MIR_B_Paint_Navy")
        fl.sph((BX0 - 120, 870 + k * 30 - 80, CURB_H + 58), (40, 40, 36),
               _rng.choice(("MIR_B_Flowers", "MIR_B_Leaves", "MIR_B_Flowers")))
    st = Group("B", "StringLights", (0, 0, 560), folder="StringLights")                       # over Cutler
    st.pop = False
    bulbs = []
    for (a, b) in (((-SX, -SY + 60, 560), (BX0, SY - 60, 600)), ((-SX, SY - 60, 540), (BX0, -SY + 60, 580))):
        for i in range(29):
            t = i / 28.0
            bulbs.append(((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - 90 * 4 * t * (1 - t)),
                          (0.07, 0.07, 0.09), (0, 0, 0)))
        st.seg(a, b, 1.2, "MI_Cable")
    st.ism("sphere", bulbs, "MIR_B_Bulb", shadows=False)
    st.light("point", (0, 0, 470), 900.0, kelvin_temp=2400, radius=1600, volumetric=2.0, source_radius=200)
    for i, (txt, x, y, yaw, c, m) in enumerate((("LAUNDROMAT", -SX - 4, 2600, 0, (80, 200, 255), "MIR_B_Neon_Blue"),
                                                 ("PIZZA", -SX - 4, -1400, 0, (255, 120, 30), "MIR_B_Neon_Red"),
                                                 ("NAILS", SX + 4, -2600, 180, (255, 80, 200), "MIR_B_Neon_Pink"))):
        ng = Group("B", "NeighborNeon_%d" % i, (x, y, 300), folder="Neighbors")
        ng.pop = False
        off = -1 if x < 0 else 1
        ng.text(txt, (x - off * 10, y, 300), 30.0, col(*c), yaw=0 if x < 0 else 180)
        ng.box((x - off * 6 - 1, y - 120, 280), (x - off * 6 + 1, y + 120, 283), m, shadows=False)
        ng.light("point", (x - off * 80, y, 290), S.B_NEON_CD * 0.7, kelvin_temp=6500, radius=700, volumetric=2.0)
    bp = Group("B", "BarberPole", (-SX - 25, 3100, 200), folder="Neighbors")
    bp.cyl((-SX - 25, 3100, 150), 24, 110, "MIR_B_Paint_Cherry")
    bp.sph((-SX - 25, 3100, 270), 26, "MIR_B_Chrome")
    for k in range(4):
        bp.box((-SX - 38, 3088, 160 + k * 26), (-SX - 12, 3112, 168 + k * 26), "MIR_B_Awning_Cream", rot=(0, 0, 20),
               shadows=False)
    for i, (at, yaw, paint, cab) in enumerate((((-500, -1500), 0, "MIR_B_Paint_Teal", False),
                                               ((500, 2600), 0, "MIR_B_Paint_Cherry", False),
                                               ((2700, -330), 90, "MIR_B_Paint_Navy", False),
                                               ((-480, 2100), 0, "MIR_B_Paint_Cab", True))):
        cg = Group("B", "Car_%d" % i, (at[0], at[1], 80), folder="Cars")
        _car(cg, at, yaw, paint, cab=cab)
        if cab:
            cg.text("LAKEMONT CAB", (at[0] - 95, at[1], 85), 10.0, col(20, 20, 20), yaw=180)
    lot = Group("B", "BurnedLot", (1700, -1150, 60), folder="Cortaz")                        # the cost
    lot.box((1150, -1450, 0), (2250, -850, 4), "MIR_B_Soot", shadows=False)
    for k in range(12):
        lot.box((1200 + _rng.uniform(0, 1000), -1440 + _rng.uniform(0, 560), 4),
                (1260 + _rng.uniform(0, 1000), -1420 + _rng.uniform(0, 560), 4 + _rng.uniform(10, 70)), "MIR_B_Soot",
                rot=(0, _rng.uniform(0, 90), _rng.uniform(-20, 20)))
    lot.box((1160, -1450, 0), (1190, -850, 300), "MIR_B_Soot")                                # charred party wall
    lot.box((1148, -1450, CURB_H), (1152, -850, 220), "MIR_B_ChainLink", shadows=False)
    for y in range(-1450, -849, 150):
        lot.cyl((1150, y, CURB_H), 6, 230, "MIR_B_Chrome")
    lot.text("NO DUMPING", (1144, -1150, 160), 14.0, col(200, 30, 30))
    _window_overlays("B")
    _skyline_windows("B", S.RIPPLE_SKYLINE_WINDOWS_B, "MIR_B_Window_Lit", S.RIPPLE_SEED + 6)


# =========================================================================== people
JOSH_POS = (-780.0, 1320.0, CURB_H)   # west sidewalk, facing the counter
WALK_ANIMS = ("MM_Walk_Fwd", "MF_Walk_Fwd", "MF_Unarmed_Walk_Fwd", "MM_Unarmed_Walk_Fwd", "MM_Walk_InPlace")
OUTFITS = ("MIR_B_Cloth_Denim", "MIR_B_Cloth_Hoodie_Red", "MIR_B_Cloth_Coat_Camel", "MIR_B_Cloth_Jacket_Black",
           "MIR_B_Cloth_Puffer_Olive", "MIR_B_Cloth_Sweater_Cream", "MIR_B_Cloth_Track_Teal", "MIR_B_Cloth_Coat_Plum")


def _find_walk():
    for n in WALK_ANIMS:
        p = find_asset_by_name(n, prefer_substring="Mannequins")
        if p:
            try:
                a = unreal.load_asset(p.split(".")[0])
                if a is not None:
                    return a
            except Exception:
                continue
    return None


def _dress(actor, mat_name):
    m = mat(mat_name)
    if m is None or actor is None:
        return
    c = getattr(actor, "skeletal_mesh_component", None)
    if c is None:
        return
    try:
        for i in range(max(1, int(c.get_num_materials()))):
            c.set_material(i, m)
    except Exception as exc:
        warn("dress %s: %s" % (mat_name, exc))


def _play(actor, anim, rate=1.0):
    c = getattr(actor, "skeletal_mesh_component", None)
    if c is None or anim is None:
        return
    try:
        c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        data = unreal.SingleAnimationPlayData()
        data.set_editor_property("anim_to_play", anim)
        data.set_editor_property("saved_looping", True)
        data.set_editor_property("saved_playing", True)
        data.set_editor_property("saved_play_rate", float(rate))
        c.set_editor_property("animation_data", data)
    except Exception as exc:
        warn("walk anim: %s" % exc)


def build_people():
    people = G.People()
    josh = people.place(JOSH_POS, math.degrees(math.atan2(1030 - JOSH_POS[1], 1500 - JOSH_POS[0])), False,
                        "MI_Fabric_Charcoal", "Josh", "Cast")
    _dress(josh, "MI_Cloth_Josh")                       # base: Josh exists in both timelines
    ACTORS["josh"] = josh
    dad_loc = (1500, 1030, CURB_H)
    dg = Group("B", "Dad", (dad_loc[0], dad_loc[1], 100), folder="People")
    dad = people.place(dad_loc, 180.0, False, "MI_Fabric_Charcoal", "Dad", "StateB/People")
    _dress(dad, "MIR_B_Cloth_Sweater_Cream")
    dg._own(dad)
    dg._grow((dad_loc[0] - 40, dad_loc[1] - 40, 0), (dad_loc[0] + 40, dad_loc[1] + 40, 190))
    try:
        ACTORS["focus_counter"].set_actor_location(unreal.Vector(dad_loc[0], dad_loc[1], 165), False, False)
    except Exception:
        pass
    PEOPLE_B.append((dad, dad_loc, None))
    spots = [(-1040, 1200, 0), (-980, 1500, -40), (-1060, -300, 90), (BX0 - 300, 1600, 200), (BX0 - 340, 870, 160),
             (BX0 - 260, 1150, 180), (-1000, 2200, -90), (1000, 2600, 180), (2000, -600, 90), (-2200, 600, -90),
             (-2600, -620, 90), (3000, 620, -150), (-1030, -2200, 30), (900, -1600, 160), (-450, 420, 120),
             (BX0 - 420, 1350, 200)]
    n_static = max(0, int(S.RIPPLE_PEDESTRIANS) - int(S.RIPPLE_WALKERS))
    for i, (x, y, yaw) in enumerate(spots[:n_static]):
        loc = (x, y, CURB_H if (abs(x) > RX or abs(y) > RY) else 0.0)
        g = Group("B", "Ped_%02d" % i, (x, y, 100), folder="People")
        a = people.place(loc, yaw + _rng.uniform(-20, 20), bool(i % 2), "MI_Fabric_Charcoal", "Ped_%02d" % i,
                         "StateB/People")
        _dress(a, OUTFITS[i % len(OUTFITS)])
        g._own(a)
        g._grow((x - 40, y - 40, 0), (x + 40, y + 40, 190))
        PEOPLE_B.append((a, loc, None))
    walk = _find_walk()
    if walk is None:
        warn("no walk animation found (%s) - walkers will glide in idle" % ", ".join(WALK_ANIMS))
    lanes = [(-1060, -2600, 1), (-960, 2600, -1), (960, -2000, 1), (1060, 3000, -1), (-860, -900, 1), (880, 900, -1)]
    for i, (x, y, d) in enumerate(lanes[:int(S.RIPPLE_WALKERS)]):
        loc = (x, y, CURB_H)
        # walkers are NOT in a swap group: ripple.py keys their world transform directly
        # (hidden until the wave reaches them, then walking at ~1.5 m/s along the sidewalk)
        a = people.place(loc, 90.0 if d > 0 else -90.0, bool(i % 2), "MI_Fabric_Charcoal", "Walker_%d" % i,
                         "StateB/People")
        _dress(a, OUTFITS[(i + 3) % len(OUTFITS)])
        _play(a, walk, 1.0)
        try:
            a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        except Exception:
            pass
        PEOPLE_B.append((a, loc, (0.0, 150.0 * d, 0.0)))        # cm/s along the sidewalk


# =========================================================================== the train
def build_train():
    """Four-car Cutler Loop train (State B). ripple.py drives the root along Y."""
    x0, z0 = ACTORS.get("el_track_x", 150.0), EL_Z0 + 128
    root = pivot((x0, -7500, z0), "Train_Root", "StateB/Train", movable=True)
    for k in range(4):
        y = -7500 - k * 1550
        parts = [((x0 - 140, y - 740, z0 + 20), (x0 + 140, y + 740, z0 + 340), "MIR_B_Train"),
                 ((x0 - 142, y - 700, z0 + 180), (x0 + 142, y + 700, z0 + 260), "MIR_B_TrainWindow"),
                 ((x0 - 130, y - 760, z0 + 330), (x0 + 130, y + 760, z0 + 350), "MIR_B_Chrome"),
                 ((x0 - 110, y - 600, z0), (x0 + 110, y - 300, z0 + 30), "MIR_B_Tire"),
                 ((x0 - 110, y + 300, z0), (x0 + 110, y + 600, z0 + 30), "MIR_B_Tire")]
        for (mn, mx, m) in parts:
            attach(box_from_min_max(mn, mx, mat(m), folder="StateB/Train", movable=True, shadows=True, collision=False), root)
        t = G._text("CUTLER LOOP", (x0 - 145, y, z0 + 300), 22.0, col(240, 200, 60), folder="StateB/Train")
        attach(t, root)
    hl = G.point("Train_Headlight", (x0, -7500 + 780, z0 + 140), 0.0, kelvin_temp=6500, radius=2200, folder="StateB/Train")
    attach(hl, root)
    LIGHTS["B"].append((hl, component(hl, unreal.PointLightComponent), 3000.0, (x0, -7500, z0)))
    ACTORS["train"] = root


# =========================================================================== gameplay
def build_gameplay():
    ACTORS["player_start"] = spawn(unreal.PlayerStart, (-1500, 300, 120), (0, 0, 0), "PlayerStart_Riverside", "Gameplay")
    gm_path = find_asset_by_name("BP_ThirdPersonGameMode")
    if not gm_path:
        warn("BP_ThirdPersonGameMode not found - default GameMode")
        return
    try:
        gm = unreal.EditorAssetLibrary.load_blueprint_class(gm_path.split(".")[0])
        ws = editor_world().get_world_settings()
        set_prop(ws, "default_game_mode", gm)
    except Exception as exc:
        warn("game mode override: %s" % exc)


# =========================================================================== entry
def build():
    for k in GROUPS:
        GROUPS[k].clear()
        LIGHTS[k].clear()
    del PEOPLE_B[:]
    WINDOWS_LIT.clear()
    ACTORS.clear()
    del TOWERS[:]
    _rng.seed(S.RIPPLE_SEED)
    with step("open/create riverside level", critical=True):
        open_or_create_level()
    with step("riverside: sky domes, sun, skylight, volumetric fog"):
        build_environment()
    with step("riverside: post-process grades (A, B, hit)"):
        build_post_process()
    with step("riverside: streets, curbs, crosswalks, puddles"):
        build_streets()
    with step("riverside: manhole steam"):
        build_steam()
    with step("riverside: the El"):
        build_el()
    with step("riverside: street furniture, poles, wires"):
        build_furniture()
    ACTORS.setdefault("facades", {})
    with step("riverside: row-house blocks"):
        build_blocks()
    with step("riverside: skyline"):
        build_skyline()
    with step("riverside: bodega shell"):
        build_bodega_shell()
    with step("riverside: State A (vacant)"):
        build_state_a()
    with step("riverside: State B (busy)"):
        build_state_b()
    with step("riverside: flush instanced base dressing"):
        BK.flush()
    with step("riverside: people"):
        build_people()
    with step("riverside: train"):
        build_train()
    with step("riverside: player start + game mode"):
        build_gameplay()
    log("riverside: %d A groups, %d B groups, %d A lights, %d B lights, %d B people" % (
        len(GROUPS["A"]), len(GROUPS["B"]), len(LIGHTS["A"]), len(LIGHTS["B"]), len(PEOPLE_B)))
    with step("save riverside level"):
        G.save_level()
    return ACTORS
