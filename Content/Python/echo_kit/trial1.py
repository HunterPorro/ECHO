"""Builds L_Trial1_Riverside2008: chapter 6 'Trial 1' as a playable, art-directed blockout.

    Lakemont, Riverside, Tuesday January 22, 2008 - the same Delancey x Cutler corner as the ripple
    demo, two years before the robbery. You are Dr. Rivers (the Third Person template character);
    Tyler and John are with you. The route (trial1_beats.BEATS, ~150 m, 11 beats):

      B01 the arrival alley (portal dies; hide the suits)    B02 down the alley (optional fire-escape climb)
      B03-B04 blend in along Cutler, past the Lucky Star     B05-B06 the Cortaz building; pick the side door
      B07-B10 stealth through the 2-floor apartment          B11 snap-back: the history edit (State A -> B)

Art direction (how the player is led without a HUD arrow): cool moonlight + wet asphalt everywhere,
warm practicals ONLY where the player should go next - the caged bulb over the dumpster, the red
DELI blade sign framed by the alley mouth, the Lucky Star's neon and lit produce, one bare bulb over
the Cortaz side door, the TV-blue window upstairs, the hall nightlight, the candle. Every beat's
destination is the brightest warm thing in view.

Reuse: riverside.py's row houses / El / street furniture (same materials, same grid), gala.People
for the cast (legs always get MI_Fabric_Trouser), the ripple MPC + masters for the shift.
Only what the shift changes lives in state groups (T1Group): A 'Before' is visible in the saved
level; B 'Burning' is saved parked below the world and LS_Trial1_Shift brings it in at the burn
front while the ripple materials tear A away pixel by pixel.

Offline checks read SOLIDS (every collidable axis-aligned box) and the cameras' paths
(tools/camera_clearance.py trial1): camera clearance + a capsule walk along trial1_beats.ROUTE.
"""
import math
import random

import unreal

from . import gala as G
from . import riverside as RV
from . import settings as S
from . import trial1_beats as TB
from . import trial1_materials as TM
from .util import (LC, V, R, V4, attach, box_from_min_max, clear_generated_actors, component, cylinder,
                   editor_world, enable_volumetric_fog, find_asset_by_name, instanced, level_sub, log,
                   pivot, set_prop, spawn, spawn_mesh, sphere, step, warn, error)

ACTORS = {}
GROUPS = {"A": [], "B": []}            # T1Group instances (trial1_sequence.py swaps these)
LIGHTS = {"A": [], "B": [], "blast": [], "base": []}   # (actor, component, on-candelas, loc, kind)
SOLIDS = []                            # (mn, mx, label, kind) kind: solid | door | glass
TRIGGERS = {}                          # trigger id -> actor
MARKERS = {"cover": [], "climb": []}   # (label, loc, kind)
CINE = {}                              # flythrough doubles (parked under the world outside the sequence)
HIDE_Z = -100000.0
CINE_PARK = (-6000.0, -6000.0, -5000.0)
_rng = random.Random(S.T1_SEED)

CURB = TB.CURB
RX, SX, RY, SY = 700.0, 1150.0, 450.0, 800.0
L1, L2 = TB.L1, TB.L2
ALLEY_X0, ALLEY_X1, ALLEY_Y0, ALLEY_Y1 = -2850.0, -2250.0, 800.0, 4200.0
CZ_X0, CZ_X1, CZ_Y0, CZ_Y1 = 1150.0, 2250.0, -1500.0, -800.0       # the Cortaz building
CZ_H = 1110.0
WALL = 30.0
BOD_X0, BOD_X1, BOD_Y0, BOD_Y1 = 1150.0, 2350.0, 800.0, 1700.0     # the Lucky Star Deli
CORTAZ_RECLINE_ROLL = -68.0            # lean Cortaz back against the headboard (flip the sign if he leans forward)


def look():
    return S.T1_LOOKS.get(S.T1_LOOK, S.T1_LOOKS["night"])


def mat(name):
    return TM.get(name)


def col(r, g, b):
    return unreal.Color(r=int(r), g=int(g), b=int(b), a=255)


def _pm(practical_cd):
    return float(practical_cd) * float(look().get("practical_mult", 1.0))


# =========================================================================== registry + batching
def reg(mn, mx, label, kind="solid"):
    a = (min(mn[0], mx[0]), min(mn[1], mx[1]), min(mn[2], mx[2]))
    b = (max(mn[0], mx[0]), max(mn[1], mx[1]), max(mn[2], mx[2]))
    SOLIDS.append((a, b, label, kind))


class T1Buckets(RV.Buckets):
    """riverside's instancer, but every collidable axis-aligned cube is also registered in SOLIDS
    (riverside.house / build_el write through riverside.BK, which build() points at this)."""

    def add(self, shape_name, center, scale, mat_name, rot=(0, 0, 0), shadows=True, collision=False, core=False):
        if collision and not any(rot):
            h = (50.0 * scale[0], 50.0 * scale[1], 50.0 * scale[2])
            reg((center[0] - h[0], center[1] - h[1], center[2] - h[2]),
                (center[0] + h[0], center[1] + h[1], center[2] + h[2]), "BK_" + str(mat_name))
        RV.Buckets.add(self, shape_name, center, scale, mat_name, rot=rot, shadows=shadows, collision=collision,
                       core=core)

    def flush(self):
        """Same batching as riverside's, but materials resolve through trial1_materials (MIT1_* first)."""
        total = self.count()
        n_ism = 0
        for (shape_name, mat_name, shadows, collision, core), items in sorted(self.items.items()):
            cap = None if core else max(12, int(1400 * len(items) / max(1, total)))
            instanced(shape_name, items, mat(mat_name), label="ISM_T1_%s_%s" % (shape_name, mat_name),
                      folder="Trial1/Base/Instanced", movable=False, shadows=shadows, collision=collision,
                      fallback_cap=cap)
            n_ism += 1
        log("trial1 base dressing: %d primitives in %d instanced batches" % (total, n_ism))
        self.items.clear()
        return total, n_ism


BK = T1Buckets()


def solid(mn, mx, mat_name, kind="solid", shadows=True):
    """Collidable, never capped by the ISM fallback (walls, floors, steps, cover)."""
    BK.box(mn, mx, mat_name, collision=True, core=True, shadows=shadows)
    if kind != "solid":
        SOLIDS[-1] = SOLIDS[-1][:3] + (kind,)


def deco(mn, mx, mat_name, shadows=True):
    BK.box(mn, mx, mat_name, shadows=shadows)


def deco_add(shape_name, center, size_cm, mat_name, rot=(0, 0, 0), shadows=True):
    BK.add(shape_name, center, (size_cm[0] / 100.0, size_cm[1] / 100.0, size_cm[2] / 100.0), mat_name, rot=rot,
           shadows=shadows)


def rect_sub(r, h):
    """2D rectangle r minus hole h -> list of rectangles. r, h = (a0, a1, b0, b1)."""
    a0, a1, b0, b1 = r
    h0, h1, k0, k1 = max(h[0], a0), min(h[1], a1), max(h[2], b0), min(h[3], b1)
    if h0 >= h1 or k0 >= k1:
        return [r]
    out = []
    if h0 > a0:
        out.append((a0, h0, b0, b1))
    if h1 < a1:
        out.append((h1, a1, b0, b1))
    if k0 > b0:
        out.append((h0, h1, b0, k0))
    if k1 < b1:
        out.append((h0, h1, k1, b1))
    return out


def rects_minus(r, holes):
    parts = [r]
    for h in holes:
        nxt = []
        for p in parts:
            nxt += rect_sub(p, h)
        parts = nxt
    return [p for p in parts if p[1] - p[0] > 0.5 and p[3] - p[2] > 0.5]


def wall_x(x0, x1, y0, y1, z0, z1, openings, mat_name):
    """A wall slab spanning Y (thin in X) with openings [(y0, y1, z0, z1)]."""
    for (a0, a1, b0, b1) in rects_minus((y0, y1, z0, z1), openings):
        solid((x0, a0, b0), (x1, a1, b1), mat_name)


def wall_y(y0, y1, x0, x1, z0, z1, openings, mat_name):
    """A wall slab spanning X (thin in Y) with openings [(x0, x1, z0, z1)]."""
    for (a0, a1, b0, b1) in rects_minus((x0, x1, z0, z1), openings):
        solid((a0, y0, b0), (a1, y1, b1), mat_name)


def slab(x0, x1, y0, y1, z0, z1, holes, mat_name, top_mat=None):
    for (a0, a1, b0, b1) in rects_minus((x0, x1, y0, y1), holes):
        solid((a0, b0, z0), (a1, b1, z1 - (1.0 if top_mat else 0.0)), mat_name)
        if top_mat:
            deco((a0, b0, z1 - 1.0), (a1, b1, z1), top_mat, shadows=False)


# =========================================================================== state groups
class T1Group:
    """A swappable set: a movable pivot with its parts attached (KEEP_WORLD). State A is saved in
    place; State B is parked HIDE_Z below the world until LS_Trial1_Shift keys it in."""

    def __init__(self, state, name, center, folder=None, when="wave"):
        self.state, self.name, self.when = state, name, when     # when: 'wave' (burn front) | 'blast'
        self.folder = "Trial1/State%s/%s" % (state, folder or name)
        self.root = pivot(center, "T1%s_%s" % (state, name), self.folder, movable=True)
        _tags(self.root, ["T1", "T1.State.%s" % state, "T1.Group.%s" % name])
        self.center = tuple(center)
        self.mn, self.mx = list(center), list(center)
        self.parts = 0
        self.actors = []
        GROUPS[state].append(self)

    def _grow(self, mn, mx):
        for i in range(3):
            self.mn[i] = min(self.mn[i], mn[i], mx[i])
            self.mx[i] = max(self.mx[i], mn[i], mx[i])

    def _own(self, a):
        attach(a, self.root)
        self.parts += 1
        self.actors.append(a)
        return a

    def box(self, mn, mx, mat_name, shadows=True, rot=(0, 0, 0), collision=False):
        self._grow(mn, mx)
        c = ((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, (mn[2] + mx[2]) / 2.0)
        s = (abs(mx[0] - mn[0]) / 100.0, abs(mx[1] - mn[1]) / 100.0, abs(mx[2] - mn[2]) / 100.0)
        return self._own(spawn_mesh("cube", c, s, mat(mat_name), rot=rot, folder=self.folder, movable=True,
                                    shadows=shadows, collision=collision))

    def shape(self, shape_name, c, size, mat_name, rot=(0, 0, 0), shadows=False):
        h = max(size) / 2.0
        self._grow((c[0] - h, c[1] - h, c[2] - h), (c[0] + h, c[1] + h, c[2] + h))
        return self._own(spawn_mesh(shape_name, c, (size[0] / 100.0, size[1] / 100.0, size[2] / 100.0), mat(mat_name),
                                    rot=rot, folder=self.folder, movable=True, shadows=shadows, collision=False))

    def flame(self, base, w, h, lean=0.0):
        """A licking flame: an outer fire cone + a hot inner core, base at `base`."""
        self.shape("cone", (base[0], base[1], base[2] + h / 2.0), (w, w * 0.8, h), "MIRT1_B_Fire", rot=(lean, 0, 0))
        self.shape("cone", (base[0], base[1], base[2] + h * 0.32), (w * 0.5, w * 0.4, h * 0.6), "MIRT1_B_FireCore",
                   rot=(lean, 0, 0))

    def ism(self, shape_name, items, mat_name, shadows=False):
        if not items:
            return None
        for (c, sc, _r) in items:
            h = (sc[0] * 50.0, sc[1] * 50.0, sc[2] * 50.0)
            self._grow((c[0] - h[0], c[1] - h[1], c[2] - h[2]), (c[0] + h[0], c[1] + h[1], c[2] + h[2]))
        a = instanced(shape_name, items, mat(mat_name), label="T1%s_%s_ISM" % (self.state, self.name),
                      folder=self.folder, movable=True, shadows=shadows, collision=False, fallback_cap=60)
        return self._own(a) if a else None

    def text(self, txt, loc, size, color, yaw=180.0):
        a = G._text(txt, loc, size, color, folder=self.folder, yaw=yaw)
        try:
            a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        except Exception:
            pass
        self._grow((loc[0] - 10, loc[1] - 10, loc[2] - 10), (loc[0] + 10, loc[1] + 10, loc[2] + 10))
        return self._own(a)

    def aabb(self):
        return tuple(self.mn), tuple(self.mx)


def light(state, kind, label, loc, cd, kelvin_temp=2800, radius=1800.0, target=None, inner=30, outer=60,
          shadows=False, volumetric=0.3, source_radius=8.0, saved_on=None, folder="Trial1/Lights"):
    """Lights are never parented to groups: the shift keys their intensity. State A lights are saved
    on (unless saved_on=False), B / blast lights are saved at 0."""
    volumetric = min(float(volumetric), float(S.T1_LOCAL_VOLUMETRIC))
    if kind == "spot":
        a = G.spot(label, loc, target or (loc[0], loc[1], 0), 0.0, kelvin_temp=kelvin_temp, inner=inner, outer=outer,
                   shadows=shadows, volumetric=volumetric, radius=radius, folder=folder)
        comp = component(a, unreal.SpotLightComponent)
    else:
        a = G.point(label, loc, 0.0, kelvin_temp=kelvin_temp, radius=radius, shadows=shadows, volumetric=volumetric,
                    source_radius=source_radius, folder=folder)
        comp = component(a, unreal.PointLightComponent)
    on = (state == "base" or state == "A") if saved_on is None else bool(saved_on)
    if comp is not None and on:
        set_prop(comp, "intensity", float(cd))
    _tags(a, ["T1", "T1.Light.%s" % state])
    if state in LIGHTS:
        LIGHTS[state].append((a, comp, float(cd), tuple(loc), label))
    return a


def _tags(actor, extra):
    try:
        t = list(actor.get_editor_property("tags") or [])
        for e in extra:
            t.append(unreal.Name(e))
        actor.set_editor_property("tags", t)
    except Exception as exc:
        warn("tags on %s: %s" % (actor, exc))
    return actor


# =========================================================================== level
def open_or_create_level():
    path = S.T1_MAP_PATH
    ls = level_sub()
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        log("loading existing level " + path)
        if not ls.load_level(path):
            raise RuntimeError("load_level failed: " + path)
        clear_generated_actors()
    else:
        log("creating level " + path)
        unreal.EditorAssetLibrary.make_directory(S.MAP_DIR)
        try:
            ok = ls.new_level(path, False)
        except TypeError:
            ok = ls.new_level(path)
        if not ok:
            raise RuntimeError("new_level failed: " + path)


# =========================================================================== environment + grade
def build_environment():
    F = "Trial1/Environment"
    lk = look()
    dm = mat("MIT1_SkyDome")
    d = spawn_mesh("sphere", (0, 0, 0), (6000.0, 6000.0, 6000.0), dm, label="SkyDome_2008", folder=F,
                   shadows=False, collision=False)
    smc = d.static_mesh_component
    for prop in ("affect_distance_field_lighting", "affect_dynamic_indirect_lighting", "cast_shadow"):
        set_prop(smc, prop, False, quiet=True)
    try:
        got = smc.get_material(0)
        log("trial1 sky dome: material slot 0 = %s" % (got.get_path_name() if got else "NONE"))
    except Exception:
        pass
    ACTORS["dome"] = d
    moon = spawn(unreal.DirectionalLight, (0, 0, 4000), (lk["moon_rot"][0], lk["moon_rot"][1], 0), "Moon_2008", F)
    mc = component(moon, unreal.DirectionalLightComponent)
    mc.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(mc, "intensity", float(lk["moon_lux"]))
    set_prop(mc, "use_temperature", True)
    set_prop(mc, "temperature", float(lk["moon_k"]))
    set_prop(mc, "volumetric_scattering_intensity", 0.8)
    set_prop(mc, "light_source_angle", float(lk["moon_angle"]), quiet=True)
    set_prop(mc, "cast_volumetric_shadow", True, quiet=True)
    set_prop(mc, "atmosphere_sun_light", False, quiet=True)
    ACTORS["moon"] = moon
    sky = spawn(unreal.SkyLight, (0, 0, 2500), (0, 0, 0), "SkyLight_2008", F)
    kc = component(sky, unreal.SkyLightComponent)
    kc.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(kc, "real_time_capture", True, quiet=True)
    set_prop(kc, "intensity", float(lk["skylight"]))
    set_prop(kc, "lower_hemisphere_is_black", False, quiet=True)
    set_prop(kc, "sky_distance_threshold", 400000.0, quiet=True)
    ACTORS["skylight"] = sky
    fog = spawn(unreal.ExponentialHeightFog, (0, 0, -50), (0, 0, 0), "HeightFog_2008", F)
    fc = component(fog, unreal.ExponentialHeightFogComponent)
    set_prop(fc, "fog_density", float(lk["fog_density"]))
    set_prop(fc, "fog_height_falloff", float(lk["fog_falloff"]))
    set_prop(fc, ["fog_inscattering_luminance", "fog_inscattering_color"], LC(*lk["fog_color"]))
    set_prop(fc, "fog_max_opacity", 0.6)
    set_prop(fc, "start_distance", 400.0, quiet=True)
    set_prop(fc, "fog_cutoff_distance", 120000.0, quiet=True)      # never fog the dome flat
    enable_volumetric_fog(fc, True)
    set_prop(fc, ["volumetric_fog_scattering_distribution", "VolumetricFogScatteringDistribution"], 0.45)
    set_prop(fc, ["volumetric_fog_extinction_scale", "VolumetricFogExtinctionScale"], float(lk["fog_extinction"]))
    set_prop(fc, ["volumetric_fog_distance", "VolumetricFogDistance"], 7000.0)
    set_prop(fc, ["volumetric_fog_albedo", "VolumetricFogAlbedo"], unreal.Color(r=205, g=212, b=228, a=255), quiet=True)
    ACTORS["fog"] = fog


GRADES = {}


def _ppv(label, priority, weight, grade):
    ppv = spawn(unreal.PostProcessVolume, (0, 0, 500), (0, 0, 0), label, "Trial1/Environment/Grade")
    set_prop(ppv, "unbound", True)
    set_prop(ppv, "priority", float(priority), quiet=True)
    set_prop(ppv, "blend_weight", float(weight), quiet=True)
    s = ppv.get_editor_property("settings")
    bad = []
    for k, v in grade.items():
        try:
            s.set_editor_property(k, v)
            s.set_editor_property("override_" + k, True)
        except Exception:
            bad.append(k)
    ppv.set_editor_property("settings", s)
    _tags(ppv, ["T1", "T1.Grade.%s" % label])
    log("grade %s: %d fields, priority %.0f, weight %.2f%s" % (label, len(grade) - len(bad), priority, weight,
                                                             (" (skipped %s)" % ", ".join(bad)) if bad else ""))
    return ppv


def build_post_process():
    lk = look()
    base = {
        "dynamic_global_illumination_method": unreal.DynamicGlobalIlluminationMethod.LUMEN,
        "reflection_method": unreal.ReflectionMethod.LUMEN,
        "lumen_scene_lighting_quality": 1.0, "lumen_final_gather_quality": 1.0, "lumen_reflection_quality": 1.0,
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_HISTOGRAM,
        "auto_exposure_min_brightness": float(lk["ev"][0]), "auto_exposure_max_brightness": float(lk["ev"][1]),
        "auto_exposure_speed_up": 2.0, "auto_exposure_speed_down": 1.2,
        "film_slope": 0.86, "film_toe": 0.56, "film_shoulder": 0.26, "film_black_clip": 0.0, "film_white_clip": 0.04,
        # 2008 anchor: cold cyan shadows, sodium-amber highlights, a touch of bleach bypass + grain
        "white_temp": float(lk["white_temp"]), "white_tint": -0.03,
        "color_saturation": V4(0.95, 1.0, 1.0, float(lk["saturation"])),
        "color_contrast": V4(1.0, 1.0, 1.0, 1.08),
        "color_gain_shadows": V4(0.88, 0.97, 1.08, 1.0), "color_offset_shadows": V4(0.004, 0.008, 0.012, 0.0),
        "color_gain_highlights": V4(1.08, 1.0, 0.88, 1.0),
        "bloom_intensity": 0.26, "bloom_threshold": 1.0, "vignette_intensity": 0.42,
        "film_grain_intensity": float(S.T1_GRAIN), "scene_fringe_intensity": 0.14,
        "motion_blur_amount": 0.35, "ambient_occlusion_intensity": 0.6, "ambient_occlusion_radius": 110.0,
    }
    headache = {   # the snap-back: ringing, the world smears, a red-black vignette (nosebleed)
        "scene_fringe_intensity": 5.0, "vignette_intensity": 1.3, "film_grain_intensity": 0.8,
        "color_saturation": V4(1.0, 1.0, 1.0, 0.35), "color_gain": V4(1.15, 0.92, 0.9, 1.0),
        "bloom_intensity": 0.9, "auto_exposure_bias": 0.6,
    }
    blast = {"bloom_intensity": 2.4, "auto_exposure_bias": -0.6, "scene_fringe_intensity": 2.5,
             "color_gain": V4(1.2, 1.0, 0.8, 1.0)}
    GRADES.clear()
    GRADES.update({"base": base, "headache": headache, "blast": blast})
    ACTORS["ppv"] = _ppv("PPV_T1_2008", 1.0, 1.0, base)
    ACTORS["ppv_headache"] = _ppv("PPV_T1_Headache", 3.0, 0.0, headache)
    ACTORS["ppv_blast"] = _ppv("PPV_T1_Blast", 4.0, 0.0, blast)


# =========================================================================== streets
def build_streets():
    F = "Trial1/Base/Street"
    L = 9000.0
    asphalt, walk = mat("MI_Asphalt_Puddles"), mat("MI_Sidewalk")
    # world floor under everything (dirt + backstop so nothing falls forever)
    box_from_min_max((-14000, -14000, -80), (14000, 14000, -2), mat("MIT1_Concrete"), label="T1_Ground", folder=F)
    reg((-14000, -14000, -80), (14000, 14000, -2), "ground")
    box_from_min_max((-RX, -L, -30), (RX, L, 0), asphalt, label="Road_Delancey_2008", folder=F)
    reg((-RX, -L, -30), (RX, L, 0), "road")
    for x0, x1 in ((-L, -RX), (RX, L)):
        box_from_min_max((x0, -RY, -30), (x1, RY, 0), asphalt, label="Road_Cutler_2008", folder=F)
        reg((x0, -RY, -30), (x1, RY, 0), "road")
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = sorted((sx * RX, sx * SX))
            y0, y1 = sorted((sy * RY, sy * L))
            box_from_min_max((x0, y0, -30), (x1, y1, CURB), walk, label="Sidewalk_Main", folder=F)
            reg((x0, y0, -30), (x1, y1, CURB), "sidewalk")
            x0, x1 = sorted((sx * SX, sx * L))
            y0, y1 = sorted((sy * RY, sy * SY))
            box_from_min_max((x0, y0, -30), (x1, y1, CURB), walk, label="Sidewalk_Cross", folder=F)
            reg((x0, y0, -30), (x1, y1, CURB), "sidewalk")
            deco((sx * RX - 6, min(sy * RY, sy * L), 0), (sx * RX + 6, max(sy * RY, sy * L), CURB + 1), "MI_Trim_Cream",
                 shadows=False)
            deco((min(sx * SX, sx * L), sy * RY - 6, 0), (max(sx * SX, sx * L), sy * RY + 6, CURB + 1), "MI_Trim_Cream",
                 shadows=False)
    # the alley: cracked concrete, a centre gutter, an apron where it meets the Cutler sidewalk
    box_from_min_max((ALLEY_X0, ALLEY_Y0, -30), (ALLEY_X1, ALLEY_Y1, CURB), mat("MI_Asphalt_Puddles"),
                     label="Alley_Floor", folder=F)
    reg((ALLEY_X0, ALLEY_Y0, -30), (ALLEY_X1, ALLEY_Y1, CURB), "alley")
    deco((-2580, ALLEY_Y0, CURB), (-2520, ALLEY_Y1, CURB + 0.4), "MI_Iron_Black", shadows=False)
    for y in range(int(ALLEY_Y0) + 200, int(ALLEY_Y1), 400):           # patched concrete seams
        deco((ALLEY_X0, y - 3, CURB), (ALLEY_X1, y + 3, CURB + 0.4), "MI_Trim_Dark", shadows=False)
    for y in range(-4000, 4001, 150):                                    # sidewalk joints
        if abs(y) > RY + 50:
            for sx in (-1, 1):
                deco((min(sx * RX, sx * SX), y - 1, CURB), (max(sx * RX, sx * SX), y + 1, CURB + 0.4), "MI_Trim_Dark",
                     shadows=False)
    for sy in (-1, 1):                                                   # zebras across Delancey
        for k in range(9):
            x = -RX + 60 + k * 155
            y0, y1 = sorted((sy * (RY + 40), sy * (RY + 330)))
            deco((x, y0, 0), (x + 70, y1, 0.8), "MI_Paint_White", shadows=False)
    for sx in (-1, 1):                                                   # zebras across Cutler
        for k in range(6):
            y = -RY + 50 + k * 150
            x0, x1 = sorted((sx * (RX + 40), sx * (RX + 330)))
            deco((x0, y, 0), (x1, y + 70, 0.8), "MI_Paint_White", shadows=False)
    for y0, y1 in ((-L, -RY - 400), (RY + 400, L)):
        for dx in (-9, 9):
            deco((dx - 5, y0, 0), (dx + 5, y1, 0.6), "MI_Paint_Yellow", shadows=False)
    for x0, x1 in ((-L, -RX - 400), (RX + 400, L)):
        for k in range(int((x1 - x0) // 600)):
            xs = x0 + k * 600
            deco((xs, -6, 0), (xs + 300, 6, 0.6), "MI_Paint_White", shadows=False)
    # standing water: where the light lands (sodium, neon, the El tube) so every practical doubles
    for (cx, cy, w, d, yaw) in ((-2560, 3300, 260, 120, 8), (-2480, 2300, 340, 110, -4), (-2600, 1300, 220, 90, 12),
                                (-2400, 700, 380, 120, 0), (-1600, 640, 300, 90, 2), (-300, 560, 520, 120, -3),
                                (400, 680, 440, 100, 4), (980, 560, 260, 140, 0), (880, -200, 300, 160, 88),
                                (1500, -640, 360, 110, 1), (2050, -560, 240, 90, -6), (-300, -1500, 600, 140, 90),
                                (250, 1900, 520, 120, 90), (-200, 3200, 400, 110, 92)):
        BK.add("cylinder", (cx, cy, CURB + 0.35 if (abs(cx) > RX or abs(cy) > RY) else 0.35),
               (w / 100.0, d / 100.0, 0.006), "MI_Puddle", rot=(0, yaw, 0), shadows=False)
    for i in range(22):
        cx, cy = _rng.uniform(-RX + 60, RX - 60), _rng.uniform(-3000, 3000)
        BK.add("cylinder", (cx, cy, 0.35), (_rng.uniform(80, 380) / 100.0, _rng.uniform(60, 220) / 100.0, 0.006),
               "MI_Puddle", rot=(0, _rng.uniform(0, 180), 0), shadows=False)
    ACTORS["steam_spots"] = [(-2600, 2050), (-260, 1900), (300, -300)]
    for (x, y) in ACTORS["steam_spots"] + [(2600, 120)]:
        z = CURB if (abs(x) > RX and abs(y) > RY) or (ALLEY_X0 < x < ALLEY_X1) else 0.0
        BK.cyl((x, y, z), 70, 1.6, "MI_Iron_Black", shadows=False)
        BK.cyl((x, y, z), 78, 0.8, "MI_Rust", shadows=False)


def build_steam():
    cls = getattr(unreal, "LocalFogVolume", None)
    if cls is None:
        warn("LocalFogVolume not in this engine - no steam")
        return
    for i, (x, y) in enumerate(ACTORS.get("steam_spots", [])):
        a = spawn(cls, (x, y, 200), (0, 0, 0), "T1_Steam_%d" % i, "Trial1/Base/Steam", scale=(0.12, 0.12, 0.5))
        c = component(a, getattr(unreal, "LocalFogVolumeComponent", unreal.ActorComponent))
        if c:
            set_prop(c, "radial_fog_extinction", 0.55, quiet=True)
            set_prop(c, "height_fog_extinction", 0.6, quiet=True)
            set_prop(c, "height_fog_falloff", 1200.0, quiet=True)
            set_prop(c, "fog_phase_g", 0.3, quiet=True)
            set_prop(c, "fog_albedo", LC(0.55, 0.56, 0.58), quiet=True)


# =========================================================================== the El (riverside's, same steel)
def build_el():
    RV.build_el()           # writes through riverside.BK (pointed at our T1Buckets for this build)
    # one fluorescent tube under the deck over the north crosswalk: cool light on the crossing
    deco((-120, 632, 628), (120, 642, 634), "MIT1_E_Fluoro", shadows=False)
    light("base", "point", "T1_El_Fluoro", (0, 640, 600), _pm(S.T1_EL_FLUORO_CD), kelvin_temp=5600, radius=1500,
          volumetric=0.3, source_radius=60)


# =========================================================================== row-house blocks
def _windows_from(key, warm="MIT1_E_Window_Warm"):
    for (mn, mx) in RV.WINDOWS_LIT.get(key, {}).get("B", []):
        m = "MIT1_E_Window_TV" if _rng.random() < 0.18 else warm
        BK.box(mn, mx, m, shadows=False)


def _face(key, F, u_start, count, floors_rng=(3, 4), widths=(480, 620), depth=1100.0, back=None, back_key=None,
          fill=None):
    """A block face of riverside row houses. back=(Facade) pairs each house with a matching rear
    elevation (no stoop, same height) so alleys get real backs. fill=cm rescales the widths so the
    face ends exactly there (no gap / no overlap with the next mass)."""
    u = u_start
    bricks = ["MI_Brick_Red", "MI_Brick_Red", "MI_Brick_Brown", "MI_Brick_Painted", "MI_Brick_Dark"]
    ws = [float(_rng.randint(int(widths[0] / 10), int(widths[1] / 10)) * 10) for _i in range(count)]
    if fill:
        k = fill / sum(ws)
        ws = [round(w * k / 10.0) * 10.0 for w in ws]
        ws[-1] += fill - sum(ws)
    for i in range(count):
        W = ws[i]
        floors = _rng.randint(*floors_rng)
        brick = _rng.choice(RV.BRICK_VARIANTS.get(_rng.choice(bricks), ["MI_Brick_Red"]))
        H = RV.house(F, key, u, W, floors, brick, fire_escape=_rng.random() < 0.4, water_tower=_rng.random() < 0.3,
                     depth=depth)
        if back is not None:
            RV.house(back, back_key, u, W, floors, brick, fire_escape=False, water_tower=False, stoop=False, depth=depth)
        u += W
    return u


def build_blocks():
    RV.WINDOWS_LIT.clear()
    Fc = RV.Facade
    # NW block (front on Delancey, back on the alley): 550 + 550 deep so the two elevations never coplane
    _face("W_N", Fc((-SX, SY, 0), (0, 1, 0), (-1, 0, 0)), 0, S.T1_HOUSES_PER_FACE + 1, depth=550.0,
          back=Fc((ALLEY_X1, SY, 0), (0, 1, 0), (1, 0, 0)), back_key="W_N_back", fill=ALLEY_Y1 - SY)
    _face("E_N", Fc((SX, BOD_Y1, 0), (0, 1, 0), (1, 0, 0)), 0, S.T1_HOUSES_PER_FACE)
    _face("E_S", Fc((SX, CZ_Y0, 0), (0, -1, 0), (1, 0, 0)), 0, S.T1_HOUSES_PER_FACE)
    _face("W_S", Fc((-SX, -SY, 0), (0, -1, 0), (-1, 0, 0)), 0, S.T1_HOUSES_PER_FACE)
    _face("N_W", Fc((ALLEY_X0, SY, 0), (-1, 0, 0), (0, 1, 0)), 0, 4)                  # west of the alley mouth
    _face("S_W", Fc((-SX, -SY, 0), (-1, 0, 0), (0, -1, 0)), 1100, 4)
    _face("N_E", Fc((SX, SY, 0), (1, 0, 0), (0, 1, 0)), BOD_X1 - SX, 4)
    _face("S_E", Fc((SX, -SY, 0), (1, 0, 0), (0, -1, 0)), CZ_X1 - SX, 4)
    for key in list(RV.WINDOWS_LIT.keys()):
        _windows_from(key)
    # the warehouse across the alley (its loading dock is the dumpster corner)
    solid((-3950, 1900, 0), (ALLEY_X0, ALLEY_Y1, 980), "MI_Brick_Brown")
    deco((ALLEY_X0 - 2, 1900, 960), (ALLEY_X0 + 25, ALLEY_Y1, 990), "MI_Trim_Dark")
    for y0 in (2250, 3500):                                              # roll-up doors, a concrete dock
        deco((ALLEY_X0 - 1, y0, CURB), (ALLEY_X0 + 6, y0 + 380, 360), "MIT1_Shutter")
        deco((ALLEY_X0 + 6, y0 - 20, 360), (ALLEY_X0 + 14, y0 + 400, 380), "MI_Iron_Black")
    solid((ALLEY_X0, 2150, CURB), (ALLEY_X0 + 70, 2750, 95), "MIT1_Concrete")          # dock (low cover)
    for k in range(6):                                                   # high windows, a few lit
        y = 2050 + k * 360
        deco((ALLEY_X0 - 1, y, 620), (ALLEY_X0 + 4, y + 170, 840), "MI_Glass_Window")
        if k in (1, 4):
            deco((ALLEY_X0 + 4.5, y + 6, 626), (ALLEY_X0 + 5.5, y + 164, 834), "MIT1_E_Window_Warm", shadows=False)
    # the dead end: a tall brick back with a faded painted ghost sign
    solid((-3950, ALLEY_Y1, 0), (-1160, ALLEY_Y1 + 900, 1500), "MI_Brick_Red")      # (recessed 10 cm: no z-fight)
    deco((-3950, ALLEY_Y1 - 2, 1470), (-1160, ALLEY_Y1 + 900, 1510), "MI_Trim_Dark")
    # a painted wall ad on the NW block's blank Cutler end - the first thing you see leaving the alley
    G._text("HAAS BROS.  FURNITURE  -  EST. 1921", (-1700, SY - 3, 1000), 46.0, col(150, 128, 92),
            folder="Trial1/Base/Signage", yaw=-90)
    G._text("CREDIT  -  DELIVERY", (-1700, SY - 3, 920), 30.0, col(125, 108, 80), folder="Trial1/Base/Signage",
            yaw=-90)
    G._text("LAKEMONT LEDGER", (-2550, ALLEY_Y1 - 3, 1050), 90.0, col(150, 140, 110), folder="Trial1/Base/Signage",
            yaw=-90)
    G._text("THE CITY'S PAPER SINCE 1886", (-2550, ALLEY_Y1 - 3, 950), 34.0, col(130, 120, 95),
            folder="Trial1/Base/Signage", yaw=-90)
    # far masses + skyline (state-invariant; closes every vista)
    for (mn, mx) in (((-2300, 5100, 0), (-1150, 9000, 1500)), ((1150, 4600, 0), (2400, 9000, 1700)),
                     ((-2300, -9000, 0), (-1150, -3800, 1400)), ((1150, -9000, 0), (2400, -4300, 1600)),
                     ((-9000, -2000, 0), (-5200, -800, 1300)), ((-9000, 800, 0), (-5200, 2000, 1200)),
                     ((4400, 800, 0), (9000, 2200, 1500)), ((4400, -2200, 0), (9000, -800, 1400))):
        RV.far_mass(mn, mx)
    for i, (x, y, w, h) in enumerate(((-3000, 11500, 1800, 9000), (1500, 12500, 2200, 12500), (5200, 10500, 1500, 7000),
                                      (-6500, 13000, 2600, 15000), (9000, 14000, 2000, 10000), (-1500, -12000, 2400, 8000),
                                      (4000, -13500, 2000, 11000), (-8000, -11000, 1800, 6500), (13000, 2500, 2400, 9000),
                                      (-13000, -2500, 2200, 7500))):
        BK.box((x - w / 2, y - w / 2, 0), (x + w / 2, y + w / 2, h), "MI_Tower_Far", core=True, shadows=False)
        BK.box((x - w / 2 - 20, y - w / 2 - 20, h), (x + w / 2 + 20, y + w / 2 + 20, h + 60), "MI_Trim_Dark",
               shadows=False)
        if i in (1, 3, 4):                                               # aircraft warning lights
            deco_add("sphere", (x, y, h + 120), (60, 60, 60), "MIT1_E_Neon_Red", shadows=False)


# =========================================================================== the arrival alley
def _caged_bulb(x, y, z, face_x, idx):
    deco((x - 8 * face_x - 6, y - 10, z - 4), (x - 8 * face_x + 6, y + 10, z + 10), "MI_Iron_Black", shadows=False)
    deco_add("sphere", (x, y, z), (14, 14, 18), "MIT1_E_Bulb", shadows=False)
    for k in range(4):
        deco((x - 9, y - 9 + k * 6, z - 9), (x + 9, y - 8 + k * 6, z + 9), "MI_Iron_Black", shadows=False)
    light("base", "point", "T1_AlleyBulb_%d" % idx, (x + 25 * face_x, y, z - 10), _pm(S.T1_ALLEY_BULB_CD),
          kelvin_temp=2500, radius=1300, shadows=(idx == 0), volumetric=0.35, source_radius=6)


def _dumpster(x0, y0, w, d, h, m, label, lid_open=False):
    solid((x0, y0, CURB), (x0 + w, y0 + d, CURB + h - 12), m)
    deco((x0 - 4, y0 - 4, CURB + h - 22), (x0 + w + 4, y0 + d + 4, CURB + h - 12), "MI_Iron_Black")
    if lid_open:
        deco_add("cube", (x0 + 6, y0 + d / 2, CURB + h + 50), (6, d, 110), "MI_Rubber")      # lid up against the wall
    else:
        solid((x0 - 2, y0, CURB + h - 12), (x0 + w + 2, y0 + d, CURB + h), "MI_Rubber")
    for yy in (y0 + 15, y0 + d - 25):
        BK.cyl((x0 + w / 2, yy, CURB), 12, 10, "MI_Rubber", shadows=False)
    MARKERS["cover"].append((label, (x0 + w / 2, y0 - 50, CURB), "low"))


def build_alley():
    F = "Trial1/Alley"
    ax = -2550.0
    # --- the portal: a ring that dies as the level starts (the director / flythrough scale it to 0)
    pc = TB.MARKS["PortalCenter"]
    root = pivot(pc[:3], "T1_Portal", F, movable=True)
    _tags(root, ["T1", "T1.Portal"])
    n, rr = 40, 165.0
    for i in range(n):
        a = 2 * math.pi * i / n
        x, z = pc[0] + rr * math.cos(a), pc[2] + rr * math.sin(a)
        attach(spawn_mesh("cube", (x, pc[1], z), (0.3, 0.16, 0.12), mat("MIT1_E_Portal"), rot=(math.degrees(a) + 90, 0, 0),
                          folder=F, movable=True, shadows=False, collision=False), root)
        if i % 4 == 0:
            attach(spawn_mesh("cube", (pc[0] + (rr + 18) * math.cos(a), pc[1] + 8, pc[2] + (rr + 18) * math.sin(a)),
                              (0.22, 0.1, 0.1), mat("MIT1_Portal_Ring"), rot=(math.degrees(a) + 90, 0, 0), folder=F,
                              movable=True, shadows=False, collision=False), root)
    attach(spawn_mesh("cylinder", pc[:3], (2.9, 2.9, 0.02), mat("MIT1_E_PortalCore"), rot=(0, 0, 90), folder=F,
                      movable=True, shadows=False, collision=False), root)
    ACTORS["portal"] = root
    ACTORS["portal_light"] = light("base", "point", "T1_PortalLight", (pc[0], pc[1] - 120, pc[2]),
                                   S.T1_PORTAL_CD, kelvin_temp=11000, radius=2600, volumetric=0.35, source_radius=120)
    # scorch ring on the concrete where it opened
    BK.add("cylinder", (pc[0], pc[1], CURB + 0.3), (3.6, 3.6, 0.006), "MI_Trim_Dark", shadows=False)
    # --- the newspaper (fictional masthead): the date sells the jump
    nx, ny = -2470.0, 3330.0
    deco((nx - 28, ny - 38, CURB + 0.2), (nx + 28, ny + 38, CURB + 0.9), "MIT1_Paper", shadows=False)
    deco_add("cube", (nx + 22, ny - 30, CURB + 0.6), (40, 52, 0.6), "MIT1_Paper", rot=(0, 24, 0), shadows=False)
    for txt, dy, sz in (("LAKEMONT LEDGER", 26, 8.5), ("TUESDAY, JANUARY 22, 2008", 15, 4.2),
                        ("COUNCIL OKs RIVERSIDE REZONING", 4, 4.6), ("Echo who? Rivers Labs posts record year", -10, 3.0)):
        t = G._text(txt, (nx, ny + dy, CURB + 1.2), sz, col(25, 25, 25), folder=F + "/Newspaper", yaw=-90)
        try:
            t.set_actor_rotation(R(pitch=90, yaw=-90, roll=0), False)
        except Exception:
            pass
    ACTORS["newspaper"] = pivot((nx, ny, CURB + 2), "Focus_Newspaper", F, movable=True)
    # --- dumpsters (hide-suits spot = the lit green one), pallets, bags, wet cardboard
    _dumpster(-2840, 3050, 180, 200, 150, "MIT1_Dumpster_Green", "Cover_Dumpster_Suits", lid_open=True)
    for k in range(3):                                                    # the silver suits, stuffed in
        deco_add("cube", (-2770 + k * 25, 3150 + (k - 1) * 30, CURB + 140), (50, 60, 30), "MIT1_Suit_Silver",
                 rot=(8 * k, 20 * k, 10))
    _caged_bulb(ALLEY_X0 + 4, 3150, 400, 1, 0)                            # B01 breadcrumb
    _dumpster(-2840, 1950, 170, 180, 140, "MIT1_Dumpster_Blue", "Cover_Dumpster_Blue")
    for (x, y, yaw) in ((-2800, 3420, 8), (-2290, 3520, -6), (-2300, 1200, 4), (-2810, 2900, 80)):
        deco_add("cube", (x, y, CURB + 7), (120, 100, 14), "MIT1_Wood_Pallet", rot=(0, yaw, 0))
        deco_add("cube", (x, y, CURB + 21), (120, 100, 14), "MIT1_Wood_Pallet", rot=(0, yaw + 5, 0))
    for i in range(16):                                                   # trash bags against both walls
        side = -1 if i % 2 else 1
        x = (ALLEY_X0 + 50) if side < 0 else (ALLEY_X1 - 60)
        y = _rng.uniform(1000, 3900)
        if side > 0 and (2350 < y < 2750 or 2850 < y < 3250):
            continue                                                      # keep the climb stack + S1 lens clear
        BK.add("sphere", (x + _rng.uniform(-15, 15), y, CURB + 28), (_rng.uniform(0.55, 0.8), _rng.uniform(0.5, 0.7),
                                                                      _rng.uniform(0.45, 0.6)), "MIT1_TrashBag")
    for i in range(8):
        x, y = _rng.uniform(ALLEY_X0 + 40, ALLEY_X1 - 60), _rng.uniform(900, 3900)
        deco_add("cube", (x, y, CURB + 1), (_rng.uniform(40, 80), _rng.uniform(30, 60), 2), "MIT1_Cardboard_Wet",
                 rot=(0, _rng.uniform(0, 180), 0), shadows=False)
    # --- chain-link gate, half open (the gap is the path)
    gy = 1600.0
    for (x0, x1) in ((ALLEY_X0, -2565), (-2415, ALLEY_X1)):
        solid((x0, gy - 3, CURB), (x1, gy + 3, CURB + 240), "MIT1_Chainlink", kind="glass")   # see-through: 'glass'
        for xx in range(int(x0), int(x1) + 1, 150):
            BK.cyl((xx, gy, CURB), 7, 250, "MI_Iron_Black")
        deco((x0, gy - 4, CURB + 236), (x1, gy + 4, CURB + 244), "MI_Iron_Black")
    deco_add("cube", (-2430, gy - 60, CURB + 120), (4, 150, 230), "MIT1_Chainlink", rot=(0, 60, 0))     # the swung leaf
    MARKERS["cover"].append(("Cover_Gate_Post", (-2600, gy + 40, CURB), "high"))
    # --- back doors + caged bulbs + AC units + downpipes on the NW block's rear wall
    for i, y in enumerate((3600, 2860, 1300)):
        deco((ALLEY_X1 - 4, y - 50, CURB), (ALLEY_X1, y + 50, CURB + 225), "MIT1_Door_Steel")
        deco((ALLEY_X1 - 6, y - 60, CURB + 225), (ALLEY_X1, y + 60, CURB + 240), "MI_Trim_Dark")
        if i < 2:
            _caged_bulb(ALLEY_X1 - 4, y + 90, 290, -1, i + 1)
    for y in (3300, 2950, 1050):
        deco((ALLEY_X1 - 60, y - 34, 520), (ALLEY_X1, y + 34, 570), "MI_Chrome_Dull")
        BK.cyl((ALLEY_X1 - 8, y + 300, CURB), 12, 1050, "MI_Iron_Black", shadows=False)
    # --- the optional high route: crate -> dumpster lid -> fire escape -> upper landing (clipping)
    _climb_route()


def _climb_paint(mn, mx):
    if S.T1_SHOW_CLIMB_PAINT:
        deco(mn, mx, "MIT1_Climb_Paint", shadows=False)


def _climb_route():
    xw = ALLEY_X1                                   # the NW block's rear wall (alley side)
    solid((xw - 100, 2620, CURB), (xw - 20, 2720, 85), "MIT1_Wood_Pallet")                       # crate, top 85
    _climb_paint((xw - 101, 2620, 83), (xw - 99, 2720, 85))
    MARKERS["climb"].append(("Climb_Crate", (xw - 60, 2670, 85), "jump"))
    _dumpster(xw - 120, 2420, 115, 190, 150, "MIT1_Dumpster_Green", "Cover_Dumpster_Climb")      # lid top 165
    _climb_paint((xw - 122, 2420, 163), (xw - 118, 2610, 165.5))
    MARKERS["climb"].append(("Climb_DumpsterLid", (xw - 60, 2515, 165), "jump"))
    # lower fire-escape landing, top 250 (iron grate), then iron steps to the upper landing at 580
    solid((xw - 110, 1900, 240), (xw, 2410, 250), "MI_Iron_Black")
    _climb_paint((xw - 111, 2380, 247), (xw - 109, 2410, 250.5))
    MARKERS["climb"].append(("Climb_FireEscape_Lower", (xw - 55, 2380, 250), "grab"))
    for i in range(1, 12):
        y1 = 2350 - 36 * (i - 1)
        top = 250 + 30 * i
        solid((xw - 105, y1 - 36, top - 10), (xw - 15, y1, top), "MI_Iron_Black", shadows=False)
    solid((xw - 110, 1780, 570), (xw, 1960, 580), "MI_Iron_Black")
    for z0 in (250, 580):                                                # rails (visual, so you can still drop)
        deco((xw - 112, 1780 if z0 > 300 else 1900, z0 + 92), (xw - 108, 2410 if z0 < 300 else 1960, z0 + 96),
             "MI_Iron_Black", shadows=False)
        for y in range(1780 if z0 > 300 else 1900, 2411 if z0 < 300 else 1961, 60):
            deco((xw - 112, y - 1.5, z0), (xw - 108, y + 1.5, z0 + 94), "MI_Iron_Black", shadows=False)
    for y in range(1900, 2411, 14):                                      # grate slats read as a fire escape
        deco((xw - 110, y, 250), (xw, y + 2, 251), "MI_Trim_Dark", shadows=False)
    # the clipping on the upper landing (collectible C01): a folded newspaper under a brick
    deco((xw - 66, 1866, 581), (xw - 46, 1876, 588), "MI_Brick_Red")
    ACTORS["clipping"] = (xw - 55, 1880, 581)          # build_gameplay spawns T1_Clipping here (pick-up)
    # a second, decorative fire escape stack higher up (not reachable - reads as 'more city')
    for zp in (737, 1067):
        deco((xw - 110, 3350, zp - 6), (xw, 3800, zp), "MI_Iron_Black")
        deco((xw - 112, 3350, zp + 90), (xw - 108, 3800, zp + 94), "MI_Iron_Black", shadows=False)


# =========================================================================== the Lucky Star Deli (2008: open)
def build_bodega():
    F = "Trial1/LuckyStar"
    x0, x1, y0, y1 = BOD_X0, BOD_X1, BOD_Y0, BOD_Y1
    H = CURB + 3 * RV.FLOOR_H + 70.0
    brick = "MI_Brick_Painted"
    solid((x0, y0, 330), (x1, y1, H), brick)                                   # upper floors (solid mass)
    solid((x0, y0, 0), (x1, y0 + 30, 330), brick)                              # ground-floor shell
    solid((x0, y1 - 30, 0), (x1, y1, 330), brick)
    solid((1700, y0, 0), (x1, y1, 330), brick)                                 # back of house (storeroom)
    slab(x0, 1700, y0 + 30, y1 - 30, 0, CURB, [], "MIT1_Concrete", top_mat="MIT1_Linoleum")
    solid((x0 - 2, y0, 0), (x0 + 6, y0 + 100, 330), "MI_Trim_Dark")           # piers either side of the glass
    solid((x0 - 2, y1 - 100, 0), (x0 + 6, y1, 330), "MI_Trim_Dark")
    solid((x0, y0 + 100, 0), (x0 + 6, y1 - 100, 60), "MI_Trim_Dark")          # kick plate
    solid((x0 - 1, y0 + 100, 60), (x0 + 3, y1 - 100, 300), "MIT1_Glass_Shop", kind="glass")
    deco((x0 - 4, y0 + 100, 300), (x0 + 6, y1 - 100, 330), "MI_Trim_Dark")
    for y in (y0 + 380, y0 + 650):                                             # mullions
        deco((x0 - 4, y - 4, 60), (x0 + 2, y + 4, 300), "MI_Trim_Dark")
    # interior: fluorescent ceiling, aisles of product, a counter + lotto lightbox
    deco((x0 + 6, y0 + 30, 325), (1700, y1 - 30, 330), "MIT1_Plaster", shadows=False)
    for y in (1000, 1250, 1500):
        deco((1250, y - 6, 318), (1650, y + 6, 324), "MIT1_E_Fluoro_Shop", shadows=False)
    for k, y in enumerate((980, 1180, 1380)):
        solid((1300, y, CURB), (1620, y + 60, CURB + 170), "MIT1_Shelf")
        for zz in (40, 85, 130, 175):
            for j in range(8):
                deco((1305 + j * 39, y - 4, CURB + zz - 30), (1338 + j * 39, y + 64, CURB + zz),
                     ("MIT1_Products_A", "MIT1_Products_B", "MIT1_Products_C")[(j + k + zz // 45) % 3], shadows=False)
    solid((1200, 1560, CURB), (1420, 1640, CURB + 105), "MIT1_Counter")
    deco((1250, 1636, 180), (1400, 1650, 260), "MIT1_E_Lightbox", shadows=False)
    light("base", "point", "T1_LuckyStar_Interior", (1450, 1250, 290), _pm(S.T1_BODEGA_CD), kelvin_temp=5200,
          radius=1400, volumetric=0.2, source_radius=80)
    light("base", "spot", "T1_LuckyStar_Spill", (1180, 1250, 310), _pm(S.T1_BODEGA_CD) * 0.6, kelvin_temp=5000,
          radius=1500, target=(700, 1150, 0), inner=45, outer=75, volumetric=0.3)
    # the neon: LUCKY STAR DELI, red over blue, the street's anchor colour
    deco((x0 - 30, y0 + 120, 345), (x0 - 4, y1 - 120, 440), "MI_Trim_Dark")
    G._text("LUCKY STAR", (x0 - 33, (y0 + y1) / 2.0, 395), 52.0, col(255, 40, 30), folder=F + "/Neon", yaw=180)
    G._text("DELI  GROCERY  LOTTO", (x0 - 33, (y0 + y1) / 2.0, 352), 24.0, col(60, 120, 255), folder=F + "/Neon",
            yaw=180)
    for z in (338, 446):
        deco((x0 - 34, y0 + 120, z), (x0 - 30, y1 - 120, z + 4), "MIT1_E_Neon_Blue", shadows=False)
    deco((x0 - 34, y0 + 120, 444), (x0 - 30, y0 + 230, 448), "MIT1_E_Neon_Red", shadows=False)
    deco((x0 + 4, y0 + 160, 230), (x0 + 7, y0 + 330, 280), "MIT1_E_Neon_Open", shadows=False)   # OPEN in the glass
    G._text("OPEN", (x0 + 3, y0 + 245, 245), 22.0, col(255, 120, 30), folder=F + "/Neon", yaw=180)
    light("base", "point", "T1_LuckyStar_NeonRed", (x0 - 90, (y0 + y1) / 2.0, 400), _pm(S.T1_NEON_CD),
          kelvin_temp=1700, radius=900, volumetric=0.35, source_radius=200)
    light("base", "point", "T1_LuckyStar_NeonBlue", (x0 - 80, (y0 + y1) / 2.0, 340), _pm(S.T1_NEON_CD) * 0.7,
          kelvin_temp=12000, radius=700, volumetric=0.3, source_radius=200)
    # the blade sign on the Cutler side: framed by the alley mouth from 3.5 km/h away (B02's guide)
    bx = 1300.0
    deco((bx - 12, y0 - 170, 450), (bx + 12, y0, 720), "MI_Trim_Dark")
    for sx, yaw in ((-1, 180), (1, 0)):
        deco((bx + sx * 12, y0 - 160, 465), (bx + sx * 15, y0 - 10, 705), "MIT1_E_Neon_Red", shadows=False)
        G._text("DELI", (bx + sx * 17, y0 - 85, 560), 46.0, col(255, 235, 220), folder=F + "/Neon", yaw=yaw)
    for k in range(4):
        deco((bx - 25, y0 - 150, 460 + k * 2), (bx + 25, y0 - 20, 462 + k * 2), "MI_Iron_Black", shadows=False)
    light("base", "point", "T1_DeliBlade", (bx - 80, y0 - 85, 590), _pm(S.T1_NEON_CD) * 1.2, kelvin_temp=1600,
          radius=1100, volumetric=0.35, source_radius=120)
    # awning (striped green), produce stand under it: low cover + the warmest colour on the corner
    deco_add("cube", (x0 - 80, (y0 + y1) / 2.0, 312), (165, 720, 5), "MIT1_Awning_Green", rot=(14, 0, 0))
    deco((x0 - 162, y0 + 90, 288), (x0 - 158, y1 - 90, 306), "MIT1_Awning_Green")
    solid((1030, 1080, CURB), (1125, 1420, CURB + 75), "MIT1_Crate")
    MARKERS["cover"].append(("Cover_ProduceStand", (1000, 1250, CURB), "low"))
    fruit = ("MIT1_Orange", "MIT1_Apple", "MIT1_Lime", "MIT1_Banana")
    for k in range(4):
        yk = 1090 + k * 82
        deco_add("cube", (1078, yk + 38, CURB + 85), (88, 76, 18), "MIT1_Crate", rot=(-12, 0, 0))
        for i in range(10):
            BK.add("sphere", (1045 + (i % 5) * 16, yk + 15 + (i // 5) * 40, CURB + 98 + (i % 2) * 4),
                   (0.11, 0.11, 0.11), fruit[k], shadows=False)
    light("base", "spot", "T1_Produce_Lamp", (1100, 1250, 285), _pm(S.T1_BODEGA_CD) * 0.35, kelvin_temp=3000,
          radius=600, target=(1078, 1250, 100), inner=35, outer=60, volumetric=0.2)
    # upper-floor windows (the owner lives above the shop): two lit
    for k, y in enumerate((950, 1250, 1550)):
        for f in (1, 2):
            z = CURB + f * RV.FLOOR_H + 70
            deco((x0 - 1, y - 55, z), (x0 + 1, y + 55, z + 175), "MI_Glass_Window")
            deco((x0 - 8, y - 63, z - 10), (x0, y + 63, z), "MI_Trim_Cream")
            deco((x0 - 8, y - 67, z + 175), (x0, y + 67, z + 197), "MI_Trim_Cream")
            if (k + f) % 3 == 0:
                deco((x0 - 1.8, y - 51, z + 4), (x0 - 1.2, y + 51, z + 171), "MIT1_E_Window_Warm", shadows=False)
    deco((x0 - 45, y0 - 10, H - 70), (x0, y1 + 10, H - 30), "MI_Trim_Dark")
    deco((x0 - 50, y0 - 12, H - 30), (x0, y1 + 12, H - 14), "MI_Trim_Cream")


# =========================================================================== the Cortaz building (the target)
def _liner_x(x0, x1, y0, y1, z0, z1, openings, m):
    for (a0, a1, b0, b1) in rects_minus((y0, y1, z0, z1), openings):
        deco((x0, a0, b0), (x1, a1, b1), m, shadows=False)


def _liner_y(y0, y1, x0, x1, z0, z1, openings, m):
    for (a0, a1, b0, b1) in rects_minus((x0, x1, z0, z1), openings):
        deco((a0, y0, b0), (a1, y1, b1), m, shadows=False)


CZ_WIN_W = 110.0
CZ_N_WIN = {"L1": (1350, 1650, 1950), "L2": (1350, 1650, 2050)}     # north (Cutler) face, window centres X
CZ_W_WIN = (-1380, -1150, -920)                                     # west (Delancey) face, window centres Y
CZ_WZ = {"L1": (L1 + 90, L1 + 280), "L2": (L2 + 90, L2 + 280)}
CZ_DOOR = (1960.0, 2060.0, CURB, CURB + 220.0)


def _cz_openings():
    north = [(CZ_DOOR[0], CZ_DOOR[1], CZ_DOOR[2], CZ_DOOR[3])]
    for lv in ("L1", "L2"):
        z0, z1 = CZ_WZ[lv]
        north += [(c - CZ_WIN_W / 2, c + CZ_WIN_W / 2, z0, z1) for c in CZ_N_WIN[lv]]
    west = [(-1420, -880, CURB, 330.0)]
    for lv in ("L1", "L2"):
        z0, z1 = CZ_WZ[lv]
        west += [(c - CZ_WIN_W / 2, c + CZ_WIN_W / 2, z0, z1) for c in CZ_W_WIN]
    return north, west


def _stair(axis, a0, sign, b0, b1, z0, rise, tread, n, m="MIT1_Floor_Wood"):
    """n steps; step i (1..n) top = z0 + i*rise. axis 'x': steps advance along X (sign), span Y b0..b1."""
    for i in range(1, n + 1):
        p, q = a0 + sign * tread * (i - 1), a0 + sign * tread * i
        lo, hi = min(p, q), max(p, q)
        top = z0 + rise * i
        if axis == "x":
            solid((lo, b0, z0), (hi, b1, top), m)
        else:
            solid((b0, lo, z0), (b1, hi, top), m)


def build_cortaz():
    F = "Trial1/Cortaz"
    x0, x1, y0, y1, W = CZ_X0, CZ_X1, CZ_Y0, CZ_Y1, WALL
    ix0, ix1, iy0, iy1 = x0 + W, x1 - W, y0 + W, y1 - W           # interior 1180..2220 x -1470..-830
    north, west = _cz_openings()
    brick = "MI_Brick_Dark"
    # ---- shell
    wall_y(y1 - W, y1, x0, x1, 0, CZ_H, north, brick)
    wall_x(x0, x0 + W, y0, y1 - W, 0, CZ_H, [(a0, a1, b0, b1) for (a0, a1, b0, b1) in west], brick)
    solid((x0, y0, 0), (x1, y0 + W, CZ_H), brick)
    solid((x1 - W, y0 + W, 0), (x1, y1 - W, CZ_H), brick)
    # ---- floors (plaster ceilings below, finished tops)
    slab(ix0, ix1, iy0, iy1, 0, CURB, [], "MIT1_Concrete", top_mat="MIT1_Linoleum")
    slab(ix0, ix1, iy0, iy1, L1 - 20, L1, [(2080, 2220, -1412, -880)], "MIT1_Plaster", top_mat="MIT1_Floor_Wood")
    slab(ix0, ix1, iy0, iy1, L2 - 20, L2, [(1280, 1766, -1470, -1335)], "MIT1_Plaster", top_mat="MIT1_Floor_Wood")
    slab(ix0, ix1, iy0, iy1, 1020, 1040, [], "MIT1_Plaster", top_mat="MI_Trim_Dark")
    # ---- stairs: GF -> L1 along -Y on the east wall; L1 -> L2 along +X on the south wall
    _stair("y", -880.0, -1, 2080.0, 2220.0, CURB, (L1 - CURB) / 19.0, 28.0, 19)
    _stair("x", 1290.0, 1, -1470.0, -1340.0, L1, (L2 - L1) / 17.0, 28.0, 17)
    solid((2078, -1300, L1), (2082, -880, L1 + 100), "MI_Iron_Black")                 # L1 stair rail
    solid((1280, -1337, L2), (1700, -1333, L2 + 100), "MI_Iron_Black")                # L2 hole rail
    solid((1278, -1470, L2), (1282, -1335, L2 + 100), "MI_Iron_Black")
    # ---- partitions
    solid((1800, iy0, CURB), (1830, iy1, L1 - 20), "MIT1_Plaster")                     # GF: closed shop | entry hall
    wall_x(1800, 1820, iy0, iy1, L1, L2 - 20, [(-1150, -1030, L1, L1 + 210)], "MIT1_Wallpaper")   # living | kitchen
    wall_y(-1300, -1290, ix0, ix1, L2, 1020, [(1760, 1860, L2, L2 + 210), (2000, 2090, L2, L2 + 210)], "MIT1_Plaster")
    solid((1900, -1290, L2), (1910, iy1, 1020), "MIT1_Plaster")                         # bedroom | bath
    wall_x(1950, 1960, iy0, -1350, L1, L2 - 20, [(-1450, -1370, L1, L1 + 200)], "MIT1_Wallpaper")  # pantry
    solid((1830, -1360, L1), (1960, -1350, L2 - 20), "MIT1_Wallpaper")
    # ---- interior liners (so the rooms read as rooms through the windows)
    for lv, z0, z1, m in (("L1", L1, L2 - 20, "MIT1_Wallpaper"), ("L2", L2, 1020, "MIT1_Plaster")):
        wz0, wz1 = CZ_WZ[lv]
        _liner_y(iy1 - 1, iy1, ix0, ix1, z0, z1,
                 [(c - CZ_WIN_W / 2, c + CZ_WIN_W / 2, wz0, wz1) for c in CZ_N_WIN[lv]], m)
        _liner_x(ix0, ix0 + 1, iy0, iy1, z0, z1, [(c - CZ_WIN_W / 2, c + CZ_WIN_W / 2, wz0, wz1) for c in CZ_W_WIN], m)
        _liner_y(iy0, iy0 + 1, ix0, ix1, z0, z1, [], m)
    # ---- facade: window trim, sills, lintels; cornice + parapet; storefront shutter; signage
    for lv in ("L1", "L2"):
        z0, z1 = CZ_WZ[lv]
        for c in CZ_N_WIN[lv]:
            deco((c - 67, y1, z1), (c + 67, y1 + 8, z1 + 22), "MI_Trim_Cream")
            deco((c - 63, y1, z0 - 10), (c + 63, y1 + 10, z0), "MI_Trim_Cream")
        for c in CZ_W_WIN:
            deco((x0 - 8, c - 67, z1), (x0, c + 67, z1 + 22), "MI_Trim_Cream")
            deco((x0 - 10, c - 63, z0 - 10), (x0, c + 63, z0), "MI_Trim_Cream")
    for (mn, mx) in (((x0 - 42, y0, CZ_H - 72), (x0, y1 + 42, CZ_H - 40)), ((x0, y1, CZ_H - 72), (x1, y1 + 42, CZ_H - 40)),
                     ((x0 - 50, y0, CZ_H - 40), (x0, y1 + 50, CZ_H - 26)), ((x0, y1, CZ_H - 40), (x1, y1 + 50, CZ_H - 26))):
        deco(mn, mx, "MI_Trim_Dark" if mx[2] < CZ_H - 39 else "MI_Trim_Cream")
    deco((x0 - 4, y0, 0), (x0, y1, 90), "MI_Trim_Cream")
    solid((x0 - 6, -1420, CURB), (x0 + 2, -880, 330), "MIT1_Shutter")
    deco((x0 - 18, -1440, 330), (x0, -860, 380), "MI_Trim_Dark")
    G._text("R. CORTAZ  -  SHOE REPAIR", (x0 - 20, -1150, 345), 26.0, col(120, 110, 90), folder=F + "/Signage", yaw=180)
    G._text("CLOSED", (x0 - 7, -1150, 200), 30.0, col(150, 40, 30), folder=F + "/Signage", yaw=180)
    G._text("1418", (2100, y1 + 9, 200), 18.0, col(200, 190, 160), folder=F + "/Signage", yaw=90)
    deco((CZ_DOOR[0] - 8, y1, CZ_DOOR[3]), (CZ_DOOR[1] + 8, y1 + 10, CZ_DOOR[3] + 14), "MI_Trim_Dark")
    deco((CZ_DOOR[0] - 30, y1, CURB), (CZ_DOOR[1] + 30, y1 + 40, CURB + 15), "MIT1_Concrete")     # step
    # ---- the side door (DOOR_Cortaz): closed leaf collides; the open leaf is saved hidden
    dz0, dz1 = CZ_DOOR[2], CZ_DOOR[3]
    door = spawn_mesh("cube", ((CZ_DOOR[0] + CZ_DOOR[1]) / 2.0, y1 - 15, (dz0 + dz1) / 2.0),
                      ((CZ_DOOR[1] - CZ_DOOR[0] - 4) / 100.0, 0.06, (dz1 - dz0 - 2) / 100.0), mat("MIT1_Door_Steel"),
                      label="DOOR_Cortaz", folder=F + "/Door", movable=True, shadows=True, collision=True)
    _tags(door, ["T1", "T1.Door", "T1.Door.Cortaz", "T1.Id.DOOR_Cortaz"])
    reg((CZ_DOOR[0], y1 - 18, dz0), (CZ_DOOR[1], y1 - 12, dz1), "DOOR_Cortaz", "door")
    knob = spawn_mesh("sphere", (CZ_DOOR[1] - 15, y1 - 10, CURB + 100), (0.06, 0.06, 0.06), mat("MI_Chrome_Dull"),
                      folder=F + "/Door", movable=True, shadows=False, collision=False)
    attach(knob, door)
    op = spawn_mesh("cube", (CZ_DOOR[0] + 5, y1 - 15 - (CZ_DOOR[1] - CZ_DOOR[0]) / 2.0, (dz0 + dz1) / 2.0),
                    (0.06, (CZ_DOOR[1] - CZ_DOOR[0] - 4) / 100.0, (dz1 - dz0 - 2) / 100.0), mat("MIT1_Door_Steel"),
                    label="DOOR_Cortaz_Open", folder=F + "/Door", movable=True, shadows=True, collision=False)
    _tags(op, ["T1", "T1.DoorOpen", "T1.DoorOpen.Cortaz"])
    try:
        op.set_actor_hidden_in_game(True)
        op.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass
    ACTORS["door"], ACTORS["door_open"] = door, op
    # ---- furniture (base = survives as charred shapes in B? no: lived-in pieces are State A)
    # GF entry hall: mailboxes, a radiator; the closed shop: dusty counter + boxes behind the shutter
    deco((2190, -1000, CURB + 110), (2220, -900, CURB + 170), "MI_Box_Blue")
    deco((1840, -840, CURB), (1950, -834, CURB + 80), "MI_Iron_Black")
    solid((1300, -1300, CURB), (1650, -1240, CURB + 100), "MIT1_Wood_Dark")
    for k in range(6):
        deco((1220 + k * 90, -1440, CURB), (1290 + k * 90, -1380, CURB + 40 + (k % 3) * 30), "MIT1_Crate")
    # L1 kitchen (the stove = the shift's epicentre)
    solid((1840, -900, L1), (2070, -836, L1 + 90), "MIT1_Counter")
    solid((1895, -900, L1), (1965, -836, L1 + 92), "MIT1_Appliance")                 # stove
    for (bx, by) in ((1912, -885), (1948, -885), (1912, -852), (1948, -852)):
        BK.cyl((bx, by, L1 + 92), 18, 1.2, "MI_Iron_Black", shadows=False)
    solid((2010, -1000, L1), (2075, -930, L1 + 175), "MIT1_Appliance")               # fridge
    solid((1880, -1010, L1), (1980, -930, L1 + 75), "MIT1_Wood_Dark")                # table
    for (cx, cy) in ((1860, -970), (2050, -1100)):
        solid((cx - 20, cy - 20, L1), (cx + 20, cy + 20, L1 + 45), "MIT1_Wood_Dark")
    ACTORS["candle_loc"] = (1930.0, -970.0, L1 + 75)
    deco((1840, -1470, L1), (1950, -1440, L1 + 200), "MIT1_Shelf")                    # pantry shelves
    # L1 living: TV + stand, rug, coffee table, the glass on the floor (noise), a standing lamp
    solid((1190, -1100, L1), (1240, -1000, L1 + 70), "MIT1_Wood_Dark")
    solid((1195, -1090, L1 + 70), (1245, -1010, L1 + 130), "MIT1_CRT")
    deco((1300, -1150, L1), (1560, -960, L1 + 0.6), "MIT1_Carpet", shadows=False)
    solid((1330, -1080, L1), (1410, -1000, L1 + 42), "MIT1_Wood_Dark")
    for i in range(9):
        deco_add("cube", (1530 + _rng.uniform(0, 60), -1300 + _rng.uniform(-30, 30), L1 + 0.8),
                 (_rng.uniform(4, 12), _rng.uniform(3, 9), 0.6), "MIT1_Glass_Shop", rot=(0, _rng.uniform(0, 180), 0),
                 shadows=False)
    BK.cyl((1250, -880, L1), 30, 3, "MI_Iron_Black")
    BK.cyl((1250, -880, L1), 4, 150, "MI_Iron_Black", shadows=False)
    # L2 bedroom + bath
    solid((1185, -1190, L2), (1198, -920, L2 + 140), "MIT1_Wood_Dark")                # headboard
    solid((1820, -1120, L2), (1890, -1020, L2 + 90), "MIT1_Wood_Dark")                 # dresser
    solid((1830, -1110, L2 + 90), (1885, -1030, L2 + 145), "MIT1_CRT")
    deco((2100, -1000, L2), (2210, -840, L2 + 55), "MIT1_Appliance")
    deco((1930, -860, L2 + 75), (1990, -840, L2 + 90), "MIT1_Appliance")
    # hall nightlight (L2) + stair bulb: B07/B08's breadcrumbs (base: they burn out at the blast via A lights)
    deco((2200, -1420, L2 + 30), (2208, -1405, L2 + 42), "MIT1_E_Bulb", shadows=False)
    deco((2140, -1460, L1 + 230), (2160, -1440, L1 + 240), "MIT1_E_Bulb", shadows=False)
    _build_cortaz_state_a()
    _build_cortaz_state_b()


def _window_boxes(inset=0.0):
    """(mn, mx, face) for every Cortaz window pane (north face: thin in Y; west face: thin in X)."""
    out = []
    for lv in ("L1", "L2"):
        z0, z1 = CZ_WZ[lv]
        for c in CZ_N_WIN[lv]:
            out.append(((c - CZ_WIN_W / 2 + inset, CZ_Y1 - 16, z0 + inset), (c + CZ_WIN_W / 2 - inset, CZ_Y1 - 13, z1 - inset), "N", lv, c))
        for c in CZ_W_WIN:
            out.append(((CZ_X0 + 13, c - CZ_WIN_W / 2 + inset, z0 + inset), (CZ_X0 + 16, c + CZ_WIN_W / 2 - inset, z1 - inset), "W", lv, c))
    return out


def _build_cortaz_state_a():
    """State A 'Before' - the apartment as it is at 11:02 PM / AM: glass in the frames, curtains,
    a TV on upstairs, lamps on, the plants on the sills. Torn out by the burn front (ripple
    materials) or swapped (fallback)."""
    glass = T1Group("A", "Cortaz_Glass", (1700, -1150, 700), when="blast")
    for (mn, mx, face, lv, c) in _window_boxes():
        glass.box(mn, mx, "MIT1_Glass_Dirty", shadows=False, collision=True)
        reg(mn, mx, "Cortaz_Glass", "glass")
    cur = T1Group("A", "Cortaz_Curtains", (1700, -1150, 700))
    for (mn, mx, face, lv, c) in _window_boxes():
        if face == "N":
            cur.box((mn[0] - 10, mn[1] - 20, mn[2] - 5), (mn[0] + 28, mn[1] - 16, mx[2] + 20), "MIRT1_A_Curtain")
            cur.box((mx[0] - 28, mn[1] - 20, mn[2] - 5), (mx[0] + 10, mn[1] - 16, mx[2] + 20), "MIRT1_A_Curtain")
        else:
            cur.box((mx[0] + 16, mn[1] - 10, mn[2] - 5), (mx[0] + 20, mn[1] + 28, mx[2] + 20), "MIRT1_A_Curtain")
            cur.box((mx[0] + 16, mx[1] - 28, mn[2] - 5), (mx[0] + 20, mx[1] + 10, mx[2] + 20), "MIRT1_A_Curtain")
    plants = T1Group("A", "Cortaz_Plants", (1650, -800, 480))
    for c in (1350, 1650):
        plants.shape("cylinder", (c, -822, L1 + 100), (22, 22, 20), "MIRT1_A_Wood")
        plants.shape("sphere", (c, -822, L1 + 128), (40, 34, 36), "MIRT1_A_Plant")
    living = T1Group("A", "Cortaz_Lived", (1500, -1100, 500))
    living.box((1450, -1140, L1), (1530, -920, L1 + 45), "MIRT1_A_Couch", collision=True)
    reg((1450, -1140, L1), (1530, -920, L1 + 45), "Couch")
    living.box((1500, -1140, L1 + 45), (1530, -920, L1 + 95), "MIRT1_A_Couch", collision=True)   # back (hide behind)
    reg((1500, -1140, L1 + 45), (1530, -920, L1 + 95), "CouchBack")
    living.box((1190, -1190, L2), (1400, -920, L2 + 55), "MIRT1_A_Bedding", collision=True)
    reg((1190, -1190, L2), (1400, -920, L2 + 55), "Bed")
    living.box((1200, -1180, L2 + 55), (1250, -1090, L2 + 75), "MIRT1_A_Bedding")
    living.box((1245, -1085, L1 + 75), (1246, -1015, L1 + 125), "MIRT1_A_TV", shadows=False)       # living TV (off-ish)
    tv = T1Group("A", "Cortaz_TV", (1830, -1070, L2 + 118))
    tv.box((1828, -1100, L2 + 96), (1829, -1040, L2 + 140), "MIRT1_A_TV", shadows=False)
    lamps = T1Group("A", "Cortaz_Lamps", (1600, -1000, 600))
    lamps.shape("cone", (1250, -880, L1 + 165), (42, 42, 32), "MIRT1_A_Window_Warm")
    lamps.shape("sphere", (1930, -970, L1 + 260), (26, 26, 26), "MIRT1_A_Bulb")
    lamps.box((1928, -972, L1 + 270), (1932, -968, L2 - 20), "MI_Iron_Black")
    candle = T1Group("A", "Cortaz_Candle", ACTORS["candle_loc"])
    cx, cy, cz = ACTORS["candle_loc"]
    candle.shape("cylinder", (cx, cy, cz + 9), (6, 6, 18), "MIT1_Paper")
    candle.shape("cone", (cx, cy, cz + 21), (3, 3, 6), "MIRT1_A_Candle")
    ACTORS["candle"] = candle.root
    for a in [candle.root] + candle.actors:                        # John lights it at B10 (the director)
        _tags(a, ["T1.Candle"])
        try:
            a.set_actor_hidden_in_game(True)
        except Exception:
            pass
    # State A lights (the shift fades them as the front passes)
    light("A", "point", "T1A_Kitchen_Pendant", (1930, -970, L1 + 245), _pm(S.T1_INTERIOR_CD), kelvin_temp=2700,
          radius=650, shadows=True, source_radius=6)
    light("A", "point", "T1A_Living_Lamp", (1250, -880, L1 + 150), _pm(S.T1_INTERIOR_CD) * 0.7, kelvin_temp=2500,
          radius=600, source_radius=10)
    light("A", "point", "T1A_Bedroom_TV", (1790, -1070, L2 + 120), _pm(S.T1_TV_CD), kelvin_temp=9500, radius=700,
          source_radius=25)
    light("A", "point", "T1A_Hall_Nightlight", (2190, -1412, L2 + 40), _pm(S.T1_INTERIOR_CD) * 0.25, kelvin_temp=2400,
          radius=420, source_radius=3)
    light("A", "point", "T1A_Stair_Bulb", (2150, -1450, L1 + 220), _pm(S.T1_INTERIOR_CD) * 0.45, kelvin_temp=2600,
          radius=520, source_radius=4)
    light("A", "point", "T1A_Candle", (cx, cy, cz + 30), _pm(S.T1_INTERIOR_CD) * 0.6, kelvin_temp=1850, radius=260, source_radius=2,
          saved_on=False)
    ACTORS["candle_light"] = LIGHTS["A"][-1]
    _tags(LIGHTS["A"][-1][0], ["T1.CandleLight"])
    # the bare bulb over the side door (B05/B06's beacon)
    deco((CZ_DOOR[0] + 40, CZ_Y1, CZ_DOOR[3] + 40), (CZ_DOOR[0] + 60, CZ_Y1 + 18, CZ_DOOR[3] + 48), "MI_Iron_Black")
    db = T1Group("A", "Cortaz_DoorBulb", (CZ_DOOR[0] + 50, CZ_Y1 + 22, CZ_DOOR[3] + 34))
    db.shape("sphere", (CZ_DOOR[0] + 50, CZ_Y1 + 22, CZ_DOOR[3] + 34), (13, 13, 16), "MIRT1_A_Bulb")
    light("A", "point", "T1A_DoorBulb", (CZ_DOOR[0] + 50, CZ_Y1 + 40, CZ_DOOR[3] + 25), _pm(S.T1_DOOR_BULB_CD),
          kelvin_temp=2400, radius=900, shadows=True, volumetric=0.35, source_radius=4)


def _build_cortaz_state_b():
    """State B 'Burning' - parked below the world until the shift. 'wave' groups arrive with the
    burn front; 'blast' groups appear on the explosion frame (shattered glass, the door, debris)."""
    fire = T1Group("B", "Cortaz_Fire", (1700, -1150, 600))
    for (mn, mx, face, lv, c) in _window_boxes(inset=6.0):
        z = mn[2]
        if face == "N":
            fire.flame((c, CZ_Y1 + 6, z), 70, 150, lean=-10)              # licking out of the frame
            fire.box((c - 50, CZ_Y1, mx[2] + 4), (c + 50, CZ_Y1 + 2, mx[2] + 220), "MIRT1_B_Scorch", shadows=False)
        else:
            fire.flame((CZ_X0 - 6, c, z), 70, 150, lean=10)
            fire.box((CZ_X0 - 2, c - 50, mx[2] + 4), (CZ_X0, c + 50, mx[2] + 220), "MIRT1_B_Scorch", shadows=False)
    for (x, y, z, w, h) in ((1930, -900, L1 + 92, 120, 220), (1600, -1100, L1, 160, 260), (1300, -1050, L2, 170, 260),
                            (1800, -1200, L2, 130, 230), (2100, -1100, L1, 110, 200), (1450, -1350, CURB, 140, 240)):
        fire.flame((x, y, z), w, h)
    smoke = T1Group("B", "Cortaz_Smoke", (1700, -1000, 1400))
    for i in range(14):
        t = i / 13.0
        smoke.shape("sphere", (1700 + _rng.uniform(-420, 420), -1000 + _rng.uniform(-300, 400), 1080 + t * 1400),
                    (260 + 300 * t, 240 + 300 * t, 200 + 220 * t), "MIRT1_B_SmokeLit" if t < 0.3 else "MIRT1_B_Smoke")
    char = T1Group("B", "Cortaz_Charred", (1500, -1100, 500))
    char.box((1450, -1140, L1), (1530, -920, L1 + 30), "MIRT1_B_Charred")
    char.box((1190, -1190, L2), (1400, -920, L2 + 30), "MIRT1_B_Charred")
    char.box((1300, -1150, L1 + 0.7), (1560, -960, L1 + 1.4), "MIRT1_B_Scorch", shadows=False)
    blast = T1Group("B", "Cortaz_Blast", (1900, -700, 200), when="blast")
    blast.box((1990, -560, CURB), (2090, -554, CURB + 220), "MIRT1_B_Charred", rot=(0, 18, 82))   # the door, blown out
    for i in range(46):                                                # glass + brick + lath across Cutler
        x, y = _rng.uniform(1250, 2250), _rng.uniform(-780, -150)
        blast.box((x, y, CURB), (x + _rng.uniform(6, 30), y + _rng.uniform(5, 22), CURB + _rng.uniform(1, 8)),
                  "MIRT1_B_Debris" if i % 3 else "MIT1_Glass_Shop", rot=(0, _rng.uniform(0, 180), 0), shadows=False)
    for i in range(24):
        x, y, z = _rng.uniform(1300, 2200), _rng.uniform(-760, -300), _rng.uniform(60, 900)
        blast.shape("sphere", (x, y, z), (5, 5, 5), "MIRT1_B_Ember")
    # fire lights (saved at 0; the shift flickers them in) + the blast flash
    for k, (x, y, z) in enumerate(((1950, -760, L1 + 140), (1650, -760, L1 + 140), (1350, -760, L2 + 140),
                                   (2050, -760, L2 + 140), (1100, -1150, L1 + 140), (1100, -920, L2 + 140),
                                   (1700, -1150, L1 + 120), (1500, -1150, L2 + 120))):
        light("B", "point", "T1B_Fire_%d" % k, (x, y, z), _pm(S.T1_FIRE_CD) * (0.6 + 0.4 * (k % 2)), kelvin_temp=1800,
              radius=1600 if k < 6 else 900, shadows=(k == 0), volumetric=0.35, source_radius=60)
    light("blast", "point", "T1_Blast", (S.T1_SHIFT_CENTER[0], S.T1_SHIFT_CENTER[1] + 200, S.T1_SHIFT_CENTER[2]), S.T1_BLAST_CD,
          kelvin_temp=2400, radius=4000, volumetric=0.35, source_radius=200, saved_on=False)
    for g in GROUPS["B"]:
        if True:
            try:
                g.root.set_actor_location(V(g.center[0], g.center[1], g.center[2] + HIDE_Z), False, False)
            except Exception as exc:
                warn("park %s: %s" % (g.name, exc))


# =========================================================================== street furniture + cars
def _lamp(x, y, ax, ay, idx):
    """Cobra-head sodium lamp (no state group: trial1's lamps never change)."""
    BK.cyl((x, y, CURB), 26, 30, "MI_Iron_Black")
    BK.cyl((x, y, CURB), 14, 820, "MI_Iron_Black")
    hx, hy = x + ax * 200, y + ay * 200
    BK.box((min(x, hx) - 5 * abs(ay), min(y, hy) - 5 * abs(ax), 820), (max(x, hx) + 5 * abs(ay), max(y, hy) + 5 * abs(ax), 832),
           "MI_Iron_Black")
    BK.box((hx - 30, hy - 30, 806), (hx + 30, hy + 30, 836), "MI_Chrome_Dull")
    deco((hx - 22, hy - 14, 801), (hx + 22, hy + 14, 806), "MIT1_E_Sodium", shadows=False)
    light("base", "spot", "T1_Sodium_%d" % idx, (hx, hy, 795), _pm(S.T1_SODIUM_CD), kelvin_temp=2000, radius=2300,
          target=(hx, hy, 0), inner=42, outer=70, shadows=(idx in (1, 3)), volumetric=0.3)


def _car(x, y, yaw, paint, label, cop=False):
    """A 2008 sedan as solid cover: body, cabin, glass, wheels. yaw 0 = along X, 90 = along Y."""
    along_y = abs(math.sin(math.radians(yaw))) > 0.5
    L, Wd = 470.0, 182.0
    hx, hy = (Wd / 2, L / 2) if along_y else (L / 2, Wd / 2)
    solid((x - hx, y - hy, 22), (x + hx, y + hy, 100), paint)
    cx, cy = (hx - 10, hy * 0.5) if along_y else (hx * 0.5, hy - 10)
    deco((x - cx, y - cy, 100), (x + cx, y + cy, 148), "MIT1_Car_Glass")
    deco((x - cx + 5, y - cy + 5, 148), (x + cx - 5, y + cy - 5, 152), paint)
    for sx in (-1, 1):
        for sy in (-1, 1):
            wx = x + sx * (hx - 2 if along_y else hx * 0.62)
            wy = y + sy * (hy * 0.62 if along_y else hy - 2)
            BK.add("cylinder", (wx, wy, 34), (0.66, 0.66, 0.24), "MI_Rubber", rot=(0, 0, 90) if not along_y else (90, 0, 0))
    lx, ly = (0, hy + 1) if along_y else (hx + 1, 0)
    for s in (-1, 1):
        deco((x + s * lx - (40 if along_y else 1), y + s * ly - (1 if along_y else 40), 70),
             (x + s * lx + (40 if along_y else 1), y + s * ly + (1 if along_y else 40), 82),
             "MIT1_E_Neon_Red" if s < 0 else "MIT1_E_Lightbox", shadows=False)
    if cop:
        deco((x - 25 - (0 if along_y else 30), y - 25 - (30 if along_y else 0), 152),
             (x + 25 + (0 if along_y else 30), y + 25 + (30 if along_y else 0), 162), "MI_Trim_Dark")
        deco((x - 20, y - 20 - (25 if along_y else 0), 162), (x, y + 20, 170), "MIT1_E_Neon_Red", shadows=False)
        deco((x, y - 20, 162), (x + 20, y + 20 + (25 if along_y else 0), 170), "MIT1_E_Neon_Blue", shadows=False)
        for s in (-1, 1):
            if along_y:
                deco((x + s * (hx + 0.5) - 0.5, y - 120, 45), (x + s * (hx + 0.5) + 0.5, y + 120, 75), "MIT1_Paper",
                     shadows=False)
            else:
                deco((x - 120, y + s * (hy + 0.5) - 0.5, 45), (x + 120, y + s * (hy + 0.5) + 0.5, 75), "MIT1_Paper",
                     shadows=False)
    MARKERS["cover"].append((label, (x, y, 0), "low"))


def build_furniture():
    for i, (x, y, ax, ay) in enumerate(((-1950, 760, 0, -1), (-1080, 1700, 1, 0), (-1080, -1500, 1, 0),
                                        (1700, -770, 0, 1), (1080, 2400, -1, 0), (1080, -2300, -1, 0),
                                        (2900, 770, 0, -1), (-3300, -770, 0, 1))):
        _lamp(x, y, ax, ay, i)
    RV.hydrant(-1300, 760)
    RV.hydrant(1250, -765)
    RV.mailbox(-1000, 1050)
    RV.newspaper_box(-2150, 765, 90, "MI_Box_Red", "LEDGER", 0)
    RV.newspaper_box(-2060, 765, 90, "MI_Box_Blue", "METRO", 1)
    poles = [(-2650, -770), (-1450, -770), (2650, -770), (-1400, 775), (2700, 775)]
    tops = [RV.utility_pole(x, y) for (x, y) in poles]
    for a, b in ((0, 1), (3, 4)):
        for k in range(min(len(tops[a]), len(tops[b]))):
            RV.wire(tops[a][k], tops[b][k], sag=55)
    for y in (1400, 2900, 3700):                                           # alley wires: the sky is a net
        RV.wire((ALLEY_X1, y, 820), (ALLEY_X0, y + 140, 760), sag=70, segments=10)
        RV.wire((ALLEY_X1, y + 60, 900), (ALLEY_X0, y - 80, 880), sag=50, segments=10)
    for (x, y, yaw) in ((-760, 520, -90), (760, 520, 180), (760, -520, 90), (-760, -520, 0)):
        RV.traffic_signal(x, y, yaw)
    RV.street_sign(-760, 520, 470, "CUTLER ST", 180)
    RV.street_sign(-760, 520, 445, "DELANCEY AV", 90)
    RV.street_sign(760, -520, 470, "CUTLER ST", 0)
    # parked cars (2008): cover along the curbs, never on the crossings
    cars = ((-590, 1700, 90, "MIT1_Car_Maroon"), (-590, 2600, 90, "MIT1_Car_Silver"), (-590, -1600, 90, "MIT1_Car_Navy"),
            (590, 2100, 90, "MIT1_Car_Black"), (590, -1900, 90, "MIT1_Car_Green"), (-1900, 350, 0, "MIT1_Car_Silver"),
            (-2900, 350, 0, "MIT1_Car_Cab"), (1600, -350, 0, "MIT1_Car_Maroon"), (2500, 350, 0, "MIT1_Car_Navy"))
    for i, (x, y, yaw, paint) in enumerate(cars[:int(S.T1_PARKED_CARS)]):
        _car(x, y, yaw, paint, "Cover_Car_%d" % i)
    _car(-1500, -350, 0, "MIT1_Car_Black", "Cover_PoliceCar", cop=True)   # the beat cop's cruiser
    G._text("LPD", (-1500, -350 - 92, 60), 14.0, col(240, 240, 240), folder="Trial1/Base/Signage", yaw=-90)


# =========================================================================== people
CAST = {}


def _cap(actor, loc):
    if not S.T1_CAPS or actor is None:
        return
    c = spawn_mesh("sphere", (loc[0], loc[1], loc[2] + 176), (0.22, 0.22, 0.1), mat("MIT1_Cap"), folder="Trial1/Cast",
                   movable=True, shadows=True, collision=False)
    try:
        c.attach_to_component(actor.skeletal_mesh_component, unreal.Name("head"),
                              unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)
    except Exception:
        attach(c, actor)


def _person(people, loc, yaw, female, outfit, label, folder, tags=(), scale=None, collide=False, rot_extra=None):
    a = people.place(loc, yaw, female, outfit, label, folder)
    if a is None:
        return None
    try:
        a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception:
        pass
    if scale:
        try:
            a.set_actor_scale3d(V(scale, scale, scale))
        except Exception:
            pass
    if rot_extra:
        try:
            a.set_actor_rotation(R(*rot_extra), False)
        except Exception:
            pass
    if not collide:
        try:
            a.set_actor_enable_collision(False)
        except Exception:
            pass
    _tags(a, ["T1"] + list(tags))
    CAST[label] = a
    return a


def build_people():
    CAST.clear()
    people = G.People()
    b1 = TB.BEATS[0]["companions"]
    for name, outfit in (("Tyler", "MIT1_Cloth_TylerJacket"), ("John", "MIT1_Cloth_JohnHoodie")):
        x, y, z, yaw = b1[name]
        a = _person(people, (x, y, z), yaw, False, outfit, "T1_" + name, "Trial1/Cast", ["T1.NPC", "T1.NPC." + name])
        _cap(a, (x, y, z))
    ox, oy, oz, oyaw = TB.MARKS["Owner"]
    _person(people, (ox, oy, oz), oyaw, False, "MIT1_Cloth_Owner", "T1_BodegaOwner", "Trial1/Cast",
            ["T1.NPC", "T1.NPC.Owner"], collide=True)
    sx, sy, sz, syaw = TB.MARKS["OwnersSon"]
    _person(people, (sx, sy, sz), syaw, False, "MIT1_Cloth_Kid", "T1_OwnersSon", "Trial1/Cast",
            ["T1.NPC", "T1.NPC.Son"], scale=0.72)
    cx, cy, cz, cyaw = TB.MARKS["Cortaz"]
    _person(people, (cx + 85, cy, cz), cyaw, False, "MIT1_Cloth_Grey", "T1_Cortaz", "Trial1/Cast",
            ["T1.NPC", "T1.NPC.Cortaz"], rot_extra=(0.0, cyaw - 90.0, CORTAZ_RECLINE_ROLL))
    px, py, pz, pyaw = TB.MARKS["Officer"]
    a = _person(people, (px, py, pz), pyaw, False, "MIT1_Cloth_Cop", "T1_Officer", "Trial1/Cast",
                ["T1.NPC", "T1.NPC.Officer"], collide=True)
    _cap(a, (px, py, pz))
    outfits = ("MIT1_Cloth_Camel", "MIT1_Cloth_Grey", "MIT1_Cloth_Puffer", "MIT1_Cloth_Burgundy", "MIT1_Cloth_Olive",
               "MIT1_Cloth_Denim")
    spots = ((-1000, 2300, -90), (1000, 2700, 180), (-1040, -2200, 30), (900, -1700, 160), (3000, 620, -150),
             (-3400, -620, 90), (2700, -620, 120), (-1000, 1400, 0), (1060, 2000, 200), (-300, -2500, 90))
    for i, (x, y, yaw) in enumerate(spots[:int(S.T1_PEDESTRIANS)]):
        z = CURB if (abs(x) > RX or abs(y) > RY) else 0.0
        _person(people, (x, y, z), yaw + _rng.uniform(-20, 20), bool(i % 2), outfits[i % len(outfits)],
                "T1_Ped_%02d" % i, "Trial1/Cast/Pedestrians", ["T1.NPC", "T1.NPC.Ped"], collide=True)
    # flythrough doubles (walk cycle), parked off-world until the sequence keys them in
    walk = RV._find_walk()
    if walk is None:
        warn("trial1: no walk animation found - the flythrough trio will glide")
    for name, outfit in (("Rivers", "MIT1_Cloth_RiversCoat"), ("Tyler", "MIT1_Cloth_TylerJacket"),
                         ("John", "MIT1_Cloth_JohnHoodie")):
        a = _person(people, CINE_PARK, 0.0, False, outfit, "CINE_" + name, "Trial1/Cinematic", ["T1.Cine"])
        RV._play(a, walk, 1.05)
        _cap(a, CINE_PARK)
        CINE[name] = a


# =========================================================================== gameplay (Blueprint-free)
def _trigger(tid, kind, c, size, beat, text, extra):
    a = spawn(unreal.TriggerBox, c, (0, 0, 0), tid, "Trial1/Gameplay/Triggers")
    comp = component(a, unreal.BoxComponent)
    try:
        comp.set_box_extent(V(size[0] / 2.0, size[1] / 2.0, size[2] / 2.0), True)
    except Exception:
        set_prop(comp, "box_extent", V(size[0] / 2.0, size[1] / 2.0, size[2] / 2.0), quiet=True)
    tags = ["T1", "T1.Trigger", "T1.Id.%s" % tid, "T1.Kind.%s" % kind]
    if beat:
        tags.append("T1.Beat.%s" % beat)
    for k, v in (extra or {}).items():
        tags.append("T1.%s.%s" % (k.capitalize(), v if not isinstance(v, (tuple, list)) else "_".join(str(int(q)) for q in v)))
    _tags(a, tags)
    TRIGGERS[tid] = a
    return a


def build_gameplay():
    F = "Trial1/Gameplay"
    ps = spawn(unreal.PlayerStart, (-2550, 3650, CURB + TB.CAPSULE_Z), (0, -90, 0), "PlayerStart_Trial1", F)
    _tags(ps, ["T1", "T1.PlayerStart"])
    ACTORS["player_start"] = ps
    for tid, (kind, c, size, beat, text, extra) in TB.TRIGGERS.items():
        _trigger(tid, kind, c, size, beat, text, extra)
    for name, m in TB.MARKS.items():
        tp = spawn(unreal.TargetPoint, (m[0], m[1], m[2] + TB.CAPSULE_Z), (0, m[3], 0), "MARK_" + name, F + "/Marks")
        _tags(tp, ["T1", "T1.Mark", "T1.Mark.%s" % name])
    for b in TB.BEATS:
        x, y, z, yaw = b["checkpoint"]
        tp = spawn(unreal.TargetPoint, (x, y, z + TB.CAPSULE_Z), (0, yaw, 0), "CHECKPOINT_%s" % b["id"], F + "/Checkpoints")
        _tags(tp, ["T1", "T1.Checkpoint", "T1.Checkpoint.%s" % b["id"]])
    for kind in ("cover", "climb"):
        for (label, loc, sub) in MARKERS[kind]:
            tp = spawn(unreal.TargetPoint, loc, (0, 0, 0), label, F + "/" + kind.capitalize())
            _tags(tp, ["T1", "T1.%s" % kind.capitalize(), "T1.%s.%s" % (kind.capitalize(), sub)])
    # the collectible (the director hides it on pick-up)
    cl = spawn_mesh("cube", ACTORS["clipping"], (0.3, 0.4, 0.012), mat("MIT1_Paper"), label="T1_Clipping",
                    folder=F + "/Collectibles", movable=True, shadows=False, collision=False)
    _tags(cl, ["T1", "T1.Collectible", "T1.Id.T1_Clipping"])
    # level-design notes: what each beat is, standing where it happens
    if S.T1_NOTES:
        for b in TB.BEATS:
            k = TB.TRIGGERS.get(b["trigger"])
            if not k:
                continue
            try:
                n = spawn(unreal.Note, (k[1][0], k[1][1], k[1][2] + 160), (0, 0, 0), "NOTE_%s" % b["id"], F + "/Notes")
                set_prop(n, "text", "%s %s\nObjective: %s\nMechanic: %s\nLight: %s" % (
                    b["id"], b["name"], b["objective"], b["mechanic"], b["light_guide"]), quiet=True)
            except Exception:
                pass
    # soft bounds: keep the player on the slice
    for i, (mn, mx) in enumerate((((-1150, 3300, -50), (1150, 3340, 900)), ((-1150, -2640, -50), (1150, -2600, 900)),
                                  ((-3140, -800, -50), (-3100, 800, 900)), ((3300, -800, -50), (3340, 800, 900)))):
        w = box_from_min_max(mn, mx, None, label="T1_InvisibleWall_%d" % i, folder=F, shadows=False)
        try:
            w.set_actor_hidden_in_game(True)
            w.static_mesh_component.set_visibility(False, False)
        except Exception:
            pass
        reg(mn, mx, "T1_InvisibleWall_%d" % i, "bounds")
    # game mode override + kill Z (same as the gala)
    gm_path = find_asset_by_name("BP_ThirdPersonGameMode")
    if not gm_path:
        warn("BP_ThirdPersonGameMode not found - trial1 uses the default GameMode (fly-cam pawn)")
        return
    try:
        gm = unreal.EditorAssetLibrary.load_blueprint_class(gm_path.split(".")[0])
        ws = editor_world().get_world_settings()
        set_prop(ws, "default_game_mode", gm)
        set_prop(ws, "kill_z", -1500.0, quiet=True)
        log("trial1 GameMode override: " + gm_path)
    except Exception as exc:
        warn("trial1 game mode override: %s" % exc)


# =========================================================================== layout export (offline tools / director)
def export_layout():
    data = {
        "solids": [[list(a), list(b), l, k] for (a, b, l, k) in SOLIDS],
        "groups": {s: [[g.name, g.when, list(g.mn), list(g.mx), g.parts] for g in GROUPS[s]] for s in GROUPS},
        "lights": {s: [[l[4], list(l[3]), l[2]] for l in LIGHTS[s]] for s in LIGHTS},
        "triggers": sorted(TRIGGERS.keys()),
        "cover": [[l, list(p), k] for (l, p, k) in MARKERS["cover"]],
        "climb": [[l, list(p), k] for (l, p, k) in MARKERS["climb"]],
    }
    try:
        import json
        import os
        saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        p = os.path.join(saved, "ECHO_trial1_layout.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        log("trial1 layout -> %s" % p)
    except Exception as exc:
        warn("trial1 layout export: %s" % exc)
    return data


# =========================================================================== entry
def _reset():
    for k in GROUPS:
        del GROUPS[k][:]
    for k in LIGHTS:
        del LIGHTS[k][:]
    del SOLIDS[:]
    TRIGGERS.clear()
    for k in MARKERS:
        del MARKERS[k][:]
    CINE.clear()
    ACTORS.clear()
    BK.items.clear()
    _rng.seed(S.T1_SEED)


def build():
    _reset()
    saved = (RV.BK, RV._rng.getstate(), RV._rng_mat.getstate(), dict(RV.WINDOWS_LIT), dict(RV.ACTORS))
    RV.BK = BK
    RV._rng.seed(S.T1_SEED)
    RV._rng_mat.seed(S.T1_SEED + 101)
    try:
        with step("open/create trial1 level", critical=True):
            open_or_create_level()
        with step("trial1: moon, sky, volumetric fog"):
            build_environment()
        with step("trial1: 2008 grade + headache/blast volumes"):
            build_post_process()
        with step("trial1: streets, alley floor, puddles"):
            build_streets()
        with step("trial1: steam"):
            build_steam()
        with step("trial1: the El"):
            build_el()
        with step("trial1: row-house blocks, warehouse, skyline"):
            build_blocks()
        with step("trial1: the arrival alley + climb route"):
            build_alley()
        with step("trial1: the Lucky Star Deli"):
            build_bodega()
        with step("trial1: the Cortaz building (A + B)"):
            build_cortaz()
        with step("trial1: street furniture + parked cars"):
            build_furniture()
        with step("trial1: flush instanced base dressing"):
            BK.flush()
        with step("trial1: cast"):
            build_people()
        with step("trial1: gameplay (PlayerStart, triggers, marks, bounds, game mode)"):
            build_gameplay()
    finally:
        RV.BK = saved[0]
        RV._rng.setstate(saved[1])
        RV._rng_mat.setstate(saved[2])
        RV.WINDOWS_LIT.clear()
        RV.WINDOWS_LIT.update(saved[3])
        RV.ACTORS.clear()
        RV.ACTORS.update(saved[4])
    export_layout()
    log("trial1: %d solids, %d A groups, %d B groups, %d A / %d B / %d base lights, %d triggers, %d cover, %d climb" % (
        len(SOLIDS), len(GROUPS["A"]), len(GROUPS["B"]), len(LIGHTS["A"]), len(LIGHTS["B"]), len(LIGHTS["base"]),
        len(TRIGGERS), len(MARKERS["cover"]), len(MARKERS["climb"])))
    with step("save trial1 level"):
        G.save_level()
    ACTORS["cine"] = CINE
    return ACTORS
