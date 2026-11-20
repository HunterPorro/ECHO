"""Builds L_Prologue_Gala: exterior plaza -> glass facade -> marble hall -> stage.

Art pass (look-dev, 'The Unveiling'): a black-tie Rivers Industries gala in Lakemont.
Layout (cm): street at X<-2800, plaza -2800..0, glass facade at X=0, hall 0..6000
(Y -2000..2000, 14 m ceiling), stage X 4700..6000 at +110 cm. Rivers at a lit podium
(stage left of centre), the draped Echo on a turntable stage right, a branded teal-black LED
wall behind them. Depth layers front to back: bar islands by the entrance, side balconies
with guests, cocktail tables with candles + florals, a press pit, floral urns, stage, curtains.
Lighting budget for the Radeon 880M: 6 shadow-casting lights (Rivers key + rim, follow spot,
2 car spots, 1 chandelier); everything else (candles, sweeps, rims, practicals) is
shadowless. Repeated dressing goes through util.instanced (ISM) with an actor fallback.
Every actor is tagged ECHO_GEN and filed under World Outliner folders ECHO/*.
"""
import math
import random

import unreal

from . import materials as M
from . import settings as S
from . import util as U
from .util import (LC, V, V4, attach, box, box_from_min_max, clear_generated_actors, component,
                   cylinder, editor_world, enum, find_asset_by_name, kelvin, level_sub, local_to_world,
                   log, look_at, set_prop, spawn, spawn_mesh, sphere, step, warn)

ACTORS = {}    # named actors the sequence script needs (cameras bind to these)
CAR_PARTS = []  # every primitive of the Echo (for the build log)
_rng = random.Random(S.RANDOM_SEED)


def _cfg(name, default):
    """Art-pass tunables live in settings.py; tolerate an older settings file."""
    return getattr(S, name, default)


# =========================================================================== level
def open_or_create_level():
    path = S.MAP_PATH
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
            ok = ls.new_level(path, False)          # 5.5: (asset_path, is_partitioned_world=False)
        except TypeError:
            ok = ls.new_level(path)
        if not ok:
            raise RuntimeError("new_level failed: " + path)


def save_level():
    try:
        level_sub().save_current_level()
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


# =========================================================================== instancing helper
def _ism(shape_name, items, mat, label=None, folder=None, shadows=True, collision=False):
    """items: [(center, size, rot)] with size in cm - (x,y,z) for cubes/spheres, or
    (diameter, height) for cylinders (center = middle of the cylinder). One ISM draw call via
    util.instanced when available, else separate StaticMeshActors (identical look)."""
    conv = []
    for it in items:
        c, size = it[0], it[1]
        rot = it[2] if len(it) > 2 and it[2] is not None else (0.0, 0.0, 0.0)
        if shape_name == "cylinder" and len(size) == 2:
            sc = (size[0] / 100.0, size[0] / 100.0, size[1] / 100.0)
        else:
            if not isinstance(size, (tuple, list)):
                size = (size, size, size)
            sc = (size[0] / 100.0, size[1] / 100.0, size[2] / 100.0)
        conv.append((tuple(c), sc, tuple(rot)))
    if not conv:
        return None
    if _cfg("GALA_USE_ISM", True) and hasattr(U, "instanced"):
        try:
            return U.instanced(shape_name, conv, mat, label=label, folder=folder, shadows=shadows,
                               collision=collision)
        except Exception as exc:
            warn("instanced(%s) failed (%s) - separate actors" % (label, exc))
    out = None
    for c, sc, rot in conv:
        out = spawn_mesh(shape_name, c, sc, mat, rot=rot, label=label, folder=folder, shadows=shadows,
                         collision=collision)
    return out


# =========================================================================== lights
def _light_common(comp, cd, kelvin_temp=None, color=None, shadows=True, volumetric=1.0,
                  radius=None, source_radius=None):
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(comp, "intensity_units", unreal.LightUnits.CANDELAS, quiet=True)
    set_prop(comp, "intensity", float(cd))
    if kelvin_temp:
        set_prop(comp, "use_temperature", True)
        set_prop(comp, "temperature", float(kelvin_temp))
    if color is not None:
        try:
            comp.set_light_color(color)
        except Exception:
            set_prop(comp, "light_color", color.to_rgbe() if hasattr(color, "to_rgbe") else color, quiet=True)
    set_prop(comp, "cast_shadows", bool(shadows))
    set_prop(comp, "volumetric_scattering_intensity", float(volumetric))
    set_prop(comp, "cast_volumetric_shadow", bool(shadows and volumetric > 0.5), quiet=True)
    if radius:
        set_prop(comp, "attenuation_radius", float(radius))
    if source_radius is not None:
        set_prop(comp, "source_radius", float(source_radius), quiet=True)
        set_prop(comp, "soft_source_radius", float(source_radius) * 0.5, quiet=True)


def spot(label, loc, target, cd, kelvin_temp=4000, inner=10.0, outer=20.0, shadows=True,
         volumetric=2.0, radius=6000.0, folder="Lights/Spots", color=None):
    pitch, yaw = look_at(loc, target)
    a = spawn(unreal.SpotLight, loc, (pitch, yaw, 0), label, folder)
    c = component(a, unreal.SpotLightComponent)
    _light_common(c, cd, kelvin_temp, color, shadows, volumetric, radius, source_radius=4.0)
    set_prop(c, "inner_cone_angle", float(inner))
    set_prop(c, "outer_cone_angle", float(outer))
    return a


def point(label, loc, cd, kelvin_temp=2800, radius=2500.0, shadows=False, volumetric=1.0,
          source_radius=20.0, folder="Lights/Points", color=None):
    a = spawn(unreal.PointLight, loc, (0, 0, 0), label, folder)
    c = component(a, unreal.PointLightComponent)
    _light_common(c, cd, kelvin_temp, color, shadows, volumetric, radius, source_radius)
    return a


# =========================================================================== environment
def build_environment():
    # --- sky dome (unlit 'Is Sky' gradient). 3 km radius so it is past the SkyLight capture distance.
    dome = spawn_mesh("sphere", (0, 0, 0), (6000.0, 6000.0, 6000.0), M.get("MI_SkyDome"),
                      label="SkyDome_BlueHour", folder="Environment", shadows=False, collision=False)
    dc = dome.static_mesh_component
    for prop in ("affect_distance_field_lighting", "affect_dynamic_indirect_lighting", "cast_shadow"):
        set_prop(dc, prop, False, quiet=True)

    # --- moonlight / city bounce (cool rim through the facade)
    moon = spawn(unreal.DirectionalLight, (0, 0, 3000), (-38.0, 35.0, 0), "Moonlight", "Environment")
    mc = component(moon, unreal.DirectionalLightComponent)
    mc.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(mc, "intensity", float(S.MOON_LUX))
    set_prop(mc, "use_temperature", True)
    set_prop(mc, "temperature", 9000.0)
    set_prop(mc, "volumetric_scattering_intensity", 0.6)
    set_prop(mc, "atmosphere_sun_light", False, quiet=True)

    # --- skylight (cool ambient from the dome)
    sky = spawn(unreal.SkyLight, (0, 0, 1500), (0, 0, 0), "SkyLight", "Environment")
    sc = component(sky, unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    set_prop(sc, "real_time_capture", True, quiet=True)
    set_prop(sc, "intensity", float(S.SKYLIGHT_INTENSITY))
    set_prop(sc, "lower_hemisphere_is_black", True, quiet=True)
    set_prop(sc, "sky_distance_threshold", 150000.0, quiet=True)
    set_prop(sc, "volumetric_scattering_intensity", 0.3, quiet=True)
    try:
        sc.recapture_sky()
    except Exception:
        pass

    # --- exponential height fog + volumetric fog: the haze the beams cut through
    fog = spawn(unreal.ExponentialHeightFog, (0, 0, -50), (0, 0, 0), "HeightFog_Volumetric", "Environment")
    fc = component(fog, unreal.ExponentialHeightFogComponent)
    set_prop(fc, "fog_density", float(S.FOG_DENSITY))
    set_prop(fc, "fog_height_falloff", float(S.FOG_HEIGHT_FALLOFF))
    set_prop(fc, ["fog_inscattering_luminance", "fog_inscattering_color"], LC(*S.FOG_INSCATTER))
    set_prop(fc, "fog_max_opacity", float(_cfg("FOG_MAX_OPACITY", 0.85)))
    set_prop(fc, "start_distance", float(_cfg("FOG_START_DISTANCE", 150.0)), quiet=True)
    set_prop(fc, "fog_cutoff_distance", 200000.0)   # keep the 3 km sky dome out of the fog
    # bEnableVolumetricFog: the Python name is enable_volumetric_fog (5.x); the setter is the safe route
    ok_vol = U.call(fc, "set_volumetric_fog", True)[0]
    if set_prop(fc, ["enable_volumetric_fog", "volumetric_fog", "b_enable_volumetric_fog"], True,
                quiet=ok_vol) is None and not ok_vol:
        warn("volumetric fog could NOT be enabled - beams will not read")
    set_prop(fc, "volumetric_fog_scattering_distribution", float(S.VOLFOG_SCATTER_DIST))
    set_prop(fc, "volumetric_fog_extinction_scale", float(S.VOLFOG_EXTINCTION))
    set_prop(fc, "volumetric_fog_distance", float(S.VOLFOG_DISTANCE))
    set_prop(fc, "volumetric_fog_start_distance", 0.0, quiet=True)
    set_prop(fc, "volumetric_fog_albedo", unreal.Color(r=235, g=230, b=222, a=255), quiet=True)
    set_prop(fc, "volumetric_fog_emissive", LC(0.0, 0.0, 0.0), quiet=True)
    ACTORS["fog"] = fog


def build_post_process():
    ppv = spawn(unreal.PostProcessVolume, (2000, 0, 500), (0, 0, 0), "PPV_Gala_CinematicGrade", "Environment")
    set_prop(ppv, "unbound", True)
    set_prop(ppv, "priority", 1.0, quiet=True)
    s = ppv.get_editor_property("settings")

    def pp(name, value, quiet=False):
        try:
            s.set_editor_property(name, value)
            s.set_editor_property("override_" + name, True)
        except Exception as exc:
            if not quiet:
                warn("post-process field %s: %s" % (name, exc))

    # GI / reflections (Lumen software RT; the polished floor needs reflections)
    pp("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN)
    pp("reflection_method", unreal.ReflectionMethod.LUMEN)
    pp("lumen_scene_lighting_quality", 1.0)
    pp("lumen_final_gather_quality", 1.0)
    pp("lumen_reflection_quality", 1.0)
    pp("lumen_scene_detail", 1.0)
    pp("lumen_front_layer_translucency_reflections", True)
    pp("lumen_max_roughness_to_trace_reflections", 0.45, quiet=True)
    # exposure: histogram, tightly clamped + slow so cuts never 'pump'
    pp("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM)
    pp("auto_exposure_min_brightness", float(S.EXPOSURE_MIN_EV))
    pp("auto_exposure_max_brightness", float(S.EXPOSURE_MAX_EV))
    pp("auto_exposure_bias", float(S.EXPOSURE_BIAS))
    pp("auto_exposure_speed_up", 1.5)
    pp("auto_exposure_speed_down", 1.0)
    pp("auto_exposure_low_percent", 70.0, quiet=True)     # meter the mid/highs, let shadows go deep
    pp("auto_exposure_high_percent", 97.0, quiet=True)
    # local exposure (5.1+): keep the bright screen and the deep crowd both readable
    pp("local_exposure_highlight_contrast_scale", 0.8, quiet=True)
    pp("local_exposure_shadow_contrast_scale", 0.95, quiet=True)
    # ---- grade: warm gold practicals vs deep teal-leaning shadows, filmic shoulder
    pp("white_temp", float(_cfg("GRADE_WHITE_TEMP", 6800.0)))
    pp("white_tint", 0.0)
    pp("color_saturation", V4(1.0, 1.0, 1.0, 0.95))
    pp("color_contrast", V4(1.0, 1.0, 1.0, 1.12))
    pp("color_gamma", V4(1.0, 1.0, 1.0, 0.98))
    pp("color_saturation_shadows", V4(0.88, 1.0, 1.05, 0.92))
    pp("color_contrast_shadows", V4(1.0, 1.0, 1.0, 1.08))
    pp("color_gain_shadows", V4(0.90, 1.0, 1.05, 1.0))              # teal: pull red out of the darks
    pp("color_offset_shadows", V4(0.0, 0.0025, 0.0035, 0.0))
    pp("color_saturation_midtones", V4(1.0, 1.0, 1.0, 1.0))
    pp("color_gain_midtones", V4(1.02, 1.0, 0.97, 1.0))
    pp("color_gain_highlights", V4(1.07, 1.0, 0.88, 1.0))           # gold highlights
    pp("color_saturation_highlights", V4(1.0, 1.0, 1.0, 0.9))
    pp("color_correction_shadows_max", 0.09, quiet=True)
    pp("color_correction_highlights_min", 0.5, quiet=True)
    pp("film_slope", 0.88)
    pp("film_toe", 0.58)
    pp("film_shoulder", 0.24)
    pp("film_black_clip", 0.0)
    pp("film_white_clip", 0.04)
    # ---- lens
    pp("bloom_method", enum("BloomMethod", "BM_SOG"), quiet=True)
    pp("bloom_intensity", 0.55)
    pp("bloom_threshold", -1.0, quiet=True)
    pp("lens_flare_intensity", 0.12)
    pp("lens_flare_bokeh_size", 2.0, quiet=True)
    pp("vignette_intensity", 0.38)
    pp("film_grain_intensity", 0.08)
    pp("film_grain_intensity_shadows", 0.6, quiet=True)
    pp("film_grain_texel_size", 1.2, quiet=True)
    pp("scene_fringe_intensity", 0.3)              # chromatic aberration, edges only
    pp("chromatic_aberration_start_offset", 0.45, quiet=True)
    pp("motion_blur_amount", 0.3)
    pp("motion_blur_max", 3.0, quiet=True)
    pp("ambient_occlusion_intensity", 0.6)
    pp("ambient_occlusion_radius", 120.0, quiet=True)
    ppv.set_editor_property("settings", s)
    ACTORS["ppv"] = ppv


# =========================================================================== architecture
def build_exterior():
    F = "Exterior"
    # ground: wet plaza + wet street, big enough to fill the reverse shots through the glass
    box_from_min_max((-2800, -6000, -20), (0, 6000, 0), M.get("MI_Concrete_Wet"), label="Plaza_Wet", folder=F)
    box_from_min_max((-5200, -9000, -30), (-2800, 9000, -5), M.get("MI_Asphalt_Wet"), label="Street_Wet", folder=F)
    box_from_min_max((-2830, -9000, -5), (-2800, 9000, 15), M.get("MI_Building_Stone"), label="Curb", folder=F)
    # red carpet + stanchions with velvet ropes
    box_from_min_max((-2600, -170, 0), (0, 170, 2), M.get("MI_RedCarpet"), label="RedCarpet", folder=F)
    posts, knobs, ropes = [], [], []
    for i in range(10):
        x = -2500 + i * 260
        for side in (-1, 1):
            y = side * 220
            posts.append(((x, y, 50), (8, 100)))
            knobs.append(((x, y, 104), (12, 12, 12)))
            if i < 9:
                ropes.append(((x + 130, y, 88), (250, 5, 5)))
    _ism("cylinder", posts, M.get("MI_Gold"), "Stanchions", F + "/Carpet", collision=True)
    _ism("sphere", knobs, M.get("MI_Gold"), "Stanchion_Knobs", F + "/Carpet")
    _ism("cube", ropes, M.get("MI_VelvetRope"), "Velvet_Ropes", F + "/Carpet")
    # entrance canopy with a warm underside strip and a name plate
    box_from_min_max((-700, -900, 470), (0, 900, 500), M.get("MI_DarkMetal"), label="Canopy", folder=F)
    box_from_min_max((-690, -880, 462), (-10, 880, 470), M.get("MI_E_Warm"), label="Canopy_Glow",
                     folder=F, shadows=False, collision=False)
    _text("RIVERS INDUSTRIES  \u00b7  THE UNVEILING", (-705, 0, 485), 34, unreal.Color(r=255, g=226, b=180, a=255),
          folder=F)
    # street lamps (sodium) - shadowless: the cinematic stays inside, budget goes to the stage
    for i, y in enumerate((-4200, -2400, -600, 1200, 3000, 4800)):
        x = -2950
        cylinder((x, y, 0), 18, 650, M.get("MI_DarkMetal"), label="LampPost_%d" % i, folder=F + "/Lamps")
        sphere((x + 60, y, 640), (40, 40, 22), M.get("MI_E_Street"), folder=F + "/Lamps", shadows=False,
               collision=False)
        point("Lamp_%d" % i, (x + 60, y, 615), S.STREET_LAMP_CD, kelvin_temp=2000, radius=2600,
              shadows=False, volumetric=2.0, source_radius=15, folder="Lights/Exterior")
    # facade uplights washing the building frame
    for y in (-1900, -1000, 1000, 1900):
        spot("FacadeWash_%d" % int(y), (-150, y, 20), (0, y, 1300), 9000, kelvin_temp=3200, inner=8, outer=22,
             shadows=False, volumetric=0.8, radius=2500, folder="Lights/Exterior")
    # skyline: towers across the street and flanking the hall (Midtown glass + stone)
    towers = [(-7000, -5200, 1500, 1800, 9000, "A"), (-7600, -1400, 2000, 1600, 15000, "B"),
              (-7200, 2600, 1600, 2200, 11000, "A"), (-8200, 6400, 2400, 1800, 18000, "B"),
              (-6500, 9800, 1400, 1400, 7000, "A"), (2500, -7200, 3000, 2400, 13000, "B"),
              (3500, 7400, 2600, 2600, 10000, "A"), (9000, -2500, 3000, 3000, 21000, "B"),
              (9500, 3500, 2600, 2600, 16000, "A"), (-9500, -9000, 3000, 2000, 24000, "B")]
    for i, (x, y, sx, sy, h, kind) in enumerate(towers):
        box((x, y, h / 2.0), (sx, sy, h), M.get("MI_Tower_" + kind), label="Tower_%02d" % i, folder=F + "/Skyline",
            shadows=False)
    # hall exterior shell: roof slab and outer stone skin
    box_from_min_max((-40, -2100, S.HALL_H), (S.HALL_LEN + 100, 2100, S.HALL_H + 160), M.get("MI_Building_Stone"),
                     label="Roof", folder="Hall/Shell")
    box_from_min_max((-60, -2100, 0), (0, -2000, S.HALL_H + 160), M.get("MI_Building_Stone"), folder="Hall/Shell")
    box_from_min_max((-60, 2000, 0), (0, 2100, S.HALL_H + 160), M.get("MI_Building_Stone"), folder="Hall/Shell")


def _text(text, loc, size, color, folder="Signage", yaw=180.0, label=None):
    """TextRender faces +X; yaw 180 makes it read correctly for a viewer looking down +X."""
    a = spawn(unreal.TextRenderActor, loc, (0, yaw, 0), label or ("Text_" + text[:12]), folder)
    c = component(a, unreal.TextRenderComponent)
    if c:
        try:
            c.set_text(text)
            c.set_world_size(float(size))
            c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
            c.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
            c.set_text_render_color(color)
        except Exception as exc:
            warn("text render setup: %s" % exc)
        set_prop(c, "cast_shadow", False, quiet=True)
    return a


def build_facade():
    F = "Hall/Facade"
    glass, metal = M.get("MI_Glass_Facade"), M.get("MI_DarkMetal")
    H, W, DW = S.HALL_H, S.HALL_HALF_W, S.DOOR_HALF_W
    bay = 500.0
    y = -W
    while y < W - 1:
        y2 = y + bay
        if y2 <= -DW or y >= DW:
            box_from_min_max((-3, y, 0), (3, y2, H), glass, folder=F, label="Glass_Pane", shadows=False)
        else:
            if y < -DW:
                box_from_min_max((-3, y, 0), (3, -DW, H), glass, folder=F, shadows=False)
            if y2 > DW:
                box_from_min_max((-3, DW, 0), (3, y2, H), glass, folder=F, shadows=False)
        if abs(y) >= DW:      # no mullion inside the doorway
            box_from_min_max((-14, y - 6, 0), (14, y + 6, H), metal, folder=F, label="Mullion")
        y = y2
    box_from_min_max((-14, W - 6, 0), (14, W + 6, H), metal, folder=F)
    box_from_min_max((-3, -DW, S.DOOR_H + 6), (3, DW, H), glass, folder=F, label="Glass_Transom",
                     shadows=False, collision=False)
    box_from_min_max((-12, -DW, S.DOOR_H - 6), (12, DW, S.DOOR_H + 6), metal, folder=F, label="Door_Header")
    for side in (-1, 1):
        box_from_min_max((-14, side * DW - 6, 0), (14, side * DW + 6, S.DOOR_H), metal, folder=F, label="Door_Jamb")
    for z in (S.TRANSOM_Z, 920.0, H - 10):
        box_from_min_max((-14, -W, z - 6), (14, W, z + 6), metal, folder=F, label="Transom")


def build_hall():
    F = "Hall"
    L, W, H, T = S.HALL_LEN, S.HALL_HALF_W, S.HALL_H, S.WALL_T
    floor = M.get("MI_Floor_BlackMarble")
    box_from_min_max((0, -W, -20), (L, W, 0), floor, label="Floor_BlackMarble", folder=F)
    # walls: walnut panels, marble back wall
    box_from_min_max((0, -W - T, 0), (L, -W, H), M.get("MI_Wall_Walnut"), label="Wall_Left", folder=F)
    box_from_min_max((0, W, 0), (L, W + T, H), M.get("MI_Wall_Walnut"), label="Wall_Right", folder=F)
    box_from_min_max((L, -W - T, 0), (L + T, W + T, H), M.get("MI_Marble_White"), label="Wall_Back", folder=F)
    # walnut wall: vertical gold reveals every 200 cm (scale cue + speculars that sparkle in the haze)
    reveals = []
    for side in (-1, 1):
        x = 100.0
        while x < L - 80:
            reveals.append(((x, side * (W - 2), H / 2.0), (3, 4, H)))
            x += 200.0
    _ism("cube", reveals, M.get("MI_Gold"), "Wall_GoldReveals", F + "/Walls", shadows=False)
    # ceiling + coffers (depth cues for the push-in)
    box_from_min_max((0, -W, H - 10), (L, W, H), M.get("MI_Ceiling_Dark"), label="Ceiling", folder=F)
    beams, trims = [], []
    x = 300.0
    while x < L - 200:
        beams.append(((x, 0, H - 50), (30, 2 * W, 80)))
        trims.append(((x, 0, H - 92), (32, 2 * W, 4)))
        x += 600.0
    for yy in (-1200.0, 0.0, 1200.0):
        beams.append(((L / 2.0, yy, H - 50), (L, 30, 80)))
    _ism("cube", beams, M.get("MI_Ceiling_Dark"), "Coffer_Beams", F + "/Coffers")
    _ism("cube", trims, M.get("MI_Gold"), "Coffer_GoldTrim", F + "/Coffers", shadows=False)
    # warm cove light strips along both walls at the ceiling line
    for side in (-1, 1):
        yy = side * (W - 25)
        box_from_min_max((50, yy - 8, H - 130), (L - 50, yy + 8, H - 120), M.get("MI_E_Warm"),
                         folder=F + "/Cove", shadows=False, collision=False)
    # marble columns with gold bases/capitals + uplights; sconces between them
    xs = [600.0 + i * 800.0 for i in range(7)]
    shafts, bases, caps, sconces = [], [], [], []
    for side in (-1, 1):
        yy = side * (W - 220)
        for i, cx in enumerate(xs):
            shafts.append(((cx, yy, H / 2.0), (90, H)))
            bases.append(((cx, yy, 20), (120, 40)))
            caps.append(((cx, yy, H - 125), (120, 30)))
            spot("Uplight_%s%d" % ("L" if side < 0 else "R", i), (cx - 120, yy - side * 60, 15), (cx, yy, H - 200),
                 S.UPLIGHT_CD, kelvin_temp=3000, inner=10, outer=26, shadows=False, volumetric=1.0, radius=1800,
                 folder="Lights/Uplights")
            sx = cx + 400.0
            if sx < L - 200:
                sconces.append(((sx, side * (W - 6), 520), (60, 10, 160)))
    _ism("cylinder", shafts, M.get("MI_Marble_White"), "Columns", F + "/Columns", collision=True)
    _ism("cylinder", bases, M.get("MI_Gold"), "Column_Bases", F + "/Columns")
    _ism("cylinder", caps, M.get("MI_Gold"), "Column_Capitals", F + "/Columns")
    _ism("cube", sconces, M.get("MI_E_Warm"), "Wall_Sconces", F + "/Sconces", shadows=False)
    # leading lines: two faint cool LED strips set into the floor along the aisle
    for side in (-1, 1):
        box_from_min_max((300, side * S.AISLE_HALF_W - 2, 0), (S.STAGE_X0 - 300, side * S.AISLE_HALF_W + 2, 0.6),
                         M.get("MI_E_CoolStrip_Dim"), label="Aisle_LEDLine", folder=F + "/Aisle",
                         shadows=False, collision=False)
    build_balconies()
    build_chandeliers()


def build_balconies():
    """Side mezzanines behind the colonnade: a second layer of light + people in every wide."""
    F = "Hall/Balconies"
    W = S.HALL_HALF_W
    x0, x1 = _cfg("BALCONY_X", (400.0, 4400.0))
    z = _cfg("BALCONY_Z", 650.0)
    inner = W - 150.0                     # 1850: just behind the column line (columns end at 1825)
    posts = []
    for side in (-1, 1):
        y_in, y_out = side * inner, side * W
        lo, hi = min(y_in, y_out), max(y_in, y_out)
        box_from_min_max((x0, lo, z - 25), (x1, hi, z), M.get("MI_Wall_Walnut"), label="Balcony_Slab", folder=F)
        box_from_min_max((x0, side * (inner - 2) - 3, z - 34), (x1, side * (inner - 2) + 3, z - 25),
                         M.get("MI_E_Warm"), label="Balcony_UnderGlow", folder=F, shadows=False, collision=False)
        box_from_min_max((x0, side * inner - 3, z + 100), (x1, side * inner + 3, z + 106), M.get("MI_Gold"),
                         label="Balcony_Rail", folder=F)
        box_from_min_max((x0, side * inner - 2, z), (x1, side * inner + 2, z + 8), M.get("MI_Gold"), folder=F)
        x = x0 + 20
        while x < x1:
            posts.append(((x, side * inner, z + 50), (4, 100)))
            x += 45.0
    _ism("cylinder", posts, M.get("MI_Gold"), "Balcony_Balusters", F, shadows=False, collision=True)


def build_chandeliers():
    F = "Hall/Chandeliers"
    crystals = []
    for n, cx in enumerate((1500.0, 2900.0, 4100.0)):
        cz = S.HALL_H - 420.0
        cylinder((cx, 0, cz + 110), 3, 300, M.get("MI_Gold"), folder=F, shadows=False, collision=False)
        cylinder((cx, 0, cz + 60), 260, 12, M.get("MI_Gold"), label="Chandelier_%d_Ring" % n, folder=F,
                 shadows=False, collision=False)
        cylinder((cx, 0, cz - 20), 170, 10, M.get("MI_Gold"), folder=F, shadows=False, collision=False)
        sphere((cx, 0, cz + 40), 70, M.get("MI_E_Crystal"), folder=F, shadows=False, collision=False)
        for ring, (radius, count, z, size) in enumerate(((130.0, 18, cz + 30, 16.0), (85.0, 12, cz - 45, 13.0),
                                                         (40.0, 6, cz - 110, 11.0))):
            for k in range(count):
                a = 2 * math.pi * k / count
                px, py = cx + radius * math.cos(a), radius * math.sin(a)
                crystals.append(((px, py, z), (size, size, size * 1.6)))
                crystals.append(((px, py, z - size * 1.6), (size * 0.5, size * 0.5, size * 0.9)))
        point("Chandelier_%d_Light" % n, (cx, 0, cz - 10), S.CHANDELIER_CD, kelvin_temp=2700, radius=3200,
              shadows=(n == 1), volumetric=1.2, source_radius=60, folder="Lights/Chandeliers")
    # a nearer drop of crystals for CAM_01 (camera flies y>=300, this hangs at y=160 so it stays in the
    # upper-left of the crane as an out-of-focus foreground, never on the flight path)
    hx, hy, hz = 680.0, 160.0, 1040.0
    cylinder((hx, hy, hz + 90), 2, 180, M.get("MI_Gold"), folder=F, shadows=False, collision=False,
             label="Chandelier_FG_Rod")
    for k, (rad, zoff, size) in enumerate(((28.0, 0.0, 14.0), (16.0, -40.0, 11.0), (0.0, -70.0, 13.0))):
        if rad <= 0:
            crystals.append(((hx, hy, hz + zoff), (size, size, size * 1.5)))
            continue
        for j in range(6):
            a = 2 * math.pi * j / 6.0
            crystals.append(((hx + rad * math.cos(a), hy + rad * math.sin(a), hz + zoff),
                             (size, size, size * 1.5)))
    _ism("sphere", crystals, M.get("MI_E_Crystal"), "Chandelier_Crystals", F, shadows=False)


def _florals(center, radius, height, count, folder, label, rng=None, palette=("MI_Flower_White", "MI_Flower_Red"),
             bloom=24.0):
    """A domed arrangement: blooms on a hemisphere + leaves underneath. Returns item dicts by material."""
    rng = rng or _rng
    out = {}
    cx, cy, cz = center
    for i in range(count):
        # golden-angle spiral over a dome
        t = (i + 0.5) / count
        phi = math.acos(1 - t)            # 0..90 deg
        th = i * 2.39996
        r = radius * math.sin(phi)
        p = (cx + r * math.cos(th), cy + r * math.sin(th), cz + height * math.cos(phi))
        mat = palette[0] if rng.random() < 0.72 else palette[-1]
        s = bloom * rng.uniform(0.8, 1.2)
        out.setdefault(mat, []).append((p, (s, s, s * 0.8)))
    for i in range(max(4, count // 3)):
        th = i * 2.39996
        p = (cx + radius * 1.05 * math.cos(th), cy + radius * 1.05 * math.sin(th), cz + rng.uniform(-5, 10))
        out.setdefault("MI_Leaf", []).append((p, (bloom * 1.8, bloom * 0.9, bloom * 0.35), (rng.uniform(-25, 25),
                                                                                           math.degrees(th), 0)))
    return out


def _merge(dst, src):
    for k, v in src.items():
        dst.setdefault(k, []).extend(v)
    return dst


def build_stage():
    F = "Stage"
    L, W = S.HALL_LEN, S.HALL_HALF_W
    x0, h = S.STAGE_X0, S.STAGE_H
    box_from_min_max((x0, -W + 150, 0), (L, W - 150, h), M.get("MI_StageGloss"), label="Stage_Deck", folder=F)
    # 3 steps (each < 45 cm so the Third Person character can climb them)
    for i in range(3):
        sh = h * (i + 1) / 3.0
        box_from_min_max((x0 - 150 + i * 50, -500, 0), (x0 - 100 + i * 50, 500, sh), M.get("MI_StageGloss"),
                         folder=F + "/Steps")
    # cool LED lip along the stage front + under each step nose
    box_from_min_max((x0 - 4, -W + 150, h - 14), (x0 + 2, W - 150, h - 6), M.get("MI_E_CoolStrip"),
                     label="Stage_LEDLip", folder=F, shadows=False, collision=False)
    for i in range(3):
        sh = h * (i + 1) / 3.0
        box_from_min_max((x0 - 152 + i * 50, -500, sh - 5), (x0 - 150 + i * 50, 500, sh - 2),
                         M.get("MI_E_CoolStrip_Dim"), folder=F + "/Steps", shadows=False, collision=False)
    # LED wall: branded teal-black screen in a dark-metal bezel
    box_from_min_max((L - 60, -1600, h + 60), (L - 40, 1600, h + 960), M.get("MI_LED_Screen") or M.get("MI_E_LEDWall"),
                     label="LED_Wall", folder=F, shadows=False)
    for (a, b) in (((L - 64, -1640, h + 40), (L - 38, 1640, h + 60)), ((L - 64, -1640, h + 960), (L - 38, 1640, h + 980)),
                   ((L - 64, -1640, h + 40), (L - 38, -1600, h + 980)), ((L - 64, 1600, h + 40), (L - 38, 1640, h + 980))):
        box_from_min_max(a, b, M.get("MI_DarkMetal"), folder=F + "/Screen")
    # brand lock-up on the screen (TextRender is lit: a shadowless kicker in build_stage_lights reads it)
    _text("RIVERS  INDUSTRIES", (L - 70, 0, h + 860), 54, unreal.Color(r=214, g=226, b=228, a=255),
          folder=F + "/Screen", label="Brand_Backdrop")
    _text("E  C  H  O", (L - 70, 0, h + 560), 250, unreal.Color(r=236, g=242, b=244, a=255),
          folder=F + "/Screen", label="Brand_ECHO")
    _text("THE FUTURE DRIVES ITSELF", (L - 70, 0, h + 330), 40, unreal.Color(r=120, g=196, b=206, a=255),
          folder=F + "/Screen", label="Tagline")
    box_from_min_max((L - 66, -260, h + 395), (L - 64, 260, h + 398), M.get("MI_E_CoolStrip"), folder=F + "/Screen",
                     shadows=False, collision=False, label="Brand_Rule")
    # lighting truss
    for tx in (4450.0, 5450.0):
        box_from_min_max((tx - 20, -1800, 1180), (tx + 20, 1800, 1220), M.get("MI_DarkMetal"), folder=F + "/Truss",
                         label="Truss")
    build_curtains()
    build_podium()
    # floral urns: flanking the steps and the stage corners (frame every wide)
    items = {}
    for (ux, uy) in ((x0 - 80, -620), (x0 - 80, 620), (x0 - 80, -1720), (x0 - 80, 1720)):
        cylinder((ux, uy, 0), 46, 70, M.get("MI_DarkMetal"), folder=F + "/Florals", label="Urn")
        cylinder((ux, uy, 70), 64, 16, M.get("MI_Gold"), folder=F + "/Florals")
        _merge(items, _florals((ux, uy, 92), 48, 52, 34, F + "/Florals", "Urn_Blooms"))
    for mat, it in items.items():
        _ism("sphere", it, M.get(mat), "Urn_" + mat[3:], F + "/Florals", shadows=False)


def build_curtains():
    """Velvet proscenium legs either side of the screen: rows of fat cylinders = folds."""
    F = "Stage/Curtains"
    L, W, H, h = S.HALL_LEN, S.HALL_HALF_W, S.HALL_H, S.STAGE_H
    folds = []
    for side in (-1, 1):
        y = side * 1660.0
        k = 0
        while abs(y) < W - 25:
            x = L - 90 + (14 if k % 2 else -10) + _rng.uniform(-4, 4)
            d = 58 + _rng.uniform(-8, 8)
            folds.append(((x, y, (h + H) / 2.0 - 40), (d, H - h - 80)))
            y += side * 34.0
            k += 1
        # a pooled hem on the deck
        box_from_min_max((L - 140, min(side * 1650, side * (W - 20)), h), (L - 40, max(side * 1650, side * (W - 20)),
                         h + 6), M.get("MI_Velvet_Curtain"), folder=F)
    _ism("cylinder", folds, M.get("MI_Velvet_Curtain"), "Curtain_Folds", F)
    # a short swagged header across the top of the stage (hides the truss line in the wides)
    hdr = []
    y = -W + 160
    k = 0
    while y < W - 160:
        hdr.append(((L - 150 + (8 if k % 2 else -6), y, H - 120), (52, 52, 200)))
        y += 40.0
        k += 1
    _ism("sphere", hdr, M.get("MI_Velvet_Curtain"), "Curtain_Header", F, shadows=False)


def build_podium():
    F = "Stage/Podium"
    h = S.STAGE_H
    px, py = S.PODIUM_POS
    # tapered dark-metal lectern: wider top, brushed steel crown, glass front with a cool logo bar
    box_from_min_max((px - 30, py - 38, h), (px + 30, py + 38, h + 100), M.get("MI_DarkMetal"), label="Podium",
                     folder=F)
    box_from_min_max((px - 40, py - 50, h + 100), (px + 36, py + 50, h + 112),
                     M.get("MI_Podium_Gunmetal") or M.get("MI_DarkMetal"), folder=F, label="Podium_Top",
                     rot=(0, 0, 0))
    box_from_min_max((px - 44, py - 52, h + 10), (px - 40, py + 52, h + 98),
                     M.get("MI_Glass_Smoked") or M.get("MI_Glass_Podium"),
                     folder=F, shadows=False)
    box_from_min_max((px - 45, py - 30, h + 66), (px - 43, py + 30, h + 69), M.get("MI_E_CoolStrip"),
                     folder=F, shadows=False, collision=False, label="Podium_LogoBar")
    box_from_min_max((px - 34, py - 40, h), (px + 34, py + 40, h + 3), M.get("MI_E_CoolStrip_Dim"),
                     folder=F, shadows=False, collision=False, label="Podium_FootGlow")
    # gooseneck mic, offset away from the medium-shot eyeline
    mx, my = px + 20, py - 18
    cylinder((mx, my, h + 112), 1.6, 36, M.get("MI_Chrome"), folder=F, shadows=False, collision=False)
    sphere((mx + 2, my, h + 150), (5, 4, 4), M.get("MI_DarkMetal"), folder=F, shadows=False, collision=False)
    # reading light glow on the lectern top
    box_from_min_max((px - 20, py - 30, h + 112), (px + 10, py + 30, h + 113), M.get("MI_E_Warm"), folder=F,
                     shadows=False, collision=False, label="Podium_ReadingGlow")


def build_dressing():
    """Bar islands by the entrance + the cocktail tables (skirted, candle, florals, glasses)."""
    F = "Dressing"
    # ---- two bar islands flanking the entrance aisle (seen behind Isabella in the reverse shot)
    shelves, amber, green = [], [], []
    ACTORS["bar_staff"] = []
    for side in (-1, 1):
        y0, y1 = sorted((side * 700.0, side * 1500.0))
        box_from_min_max((640, y0, 0), (720, y1, 108), M.get("MI_Wall_Walnut"), label="Bar_Counter", folder=F + "/Bar")
        box_from_min_max((632, y0 - 8, 108), (728, y1 + 8, 114), M.get("MI_Floor_BlackMarble"), folder=F + "/Bar",
                         label="Bar_Top")
        box_from_min_max((722, y0, 8), (724, y1, 12), M.get("MI_E_Warm"), folder=F + "/Bar", shadows=False,
                         collision=False, label="Bar_KickGlow")
        box_from_min_max((380, y0, 0), (430, y1, 250), M.get("MI_DarkMetal"), label="Bar_BackShelf", folder=F + "/Bar")
        for z in (120.0, 170.0, 220.0):
            shelves.append((((436 + 438) / 2.0, (y0 + y1) / 2.0, z - 3), (4, y1 - y0, 2)))
            yy = y0 + 20
            while yy < y1 - 20:
                d = _rng.uniform(7, 9)
                hgt = _rng.uniform(26, 34)
                (amber if _rng.random() < 0.6 else green).append(((448, yy, z + hgt / 2.0), (d, hgt)))
                yy += _rng.uniform(12, 18)
    _ism("cube", shelves, M.get("MI_E_BarShelf"), "Bar_ShelfGlow", F + "/Bar", shadows=False)
    _ism("cylinder", amber, M.get("MI_Bottle_Amber"), "Bar_Bottles_Amber", F + "/Bar", shadows=False)
    _ism("cylinder", green, M.get("MI_Bottle_Green"), "Bar_Bottles_Green", F + "/Bar", shadows=False)
    for side in (-1, 1):
        point("Bar_Glow_%s" % ("L" if side < 0 else "R"), (560, side * 1100, 230), 900.0, kelvin_temp=2600,
              radius=700, shadows=False, volumetric=0.4, source_radius=30, folder="Lights/Practicals")

    # ---- cocktail tables
    ACTORS["tables"] = []
    tops, skirts, glasses, bowls, candles = [], [], [], [], []
    flor = {}
    for ti, tx in enumerate(S.TABLE_ROWS_X):
        for tj, ty in enumerate(S.TABLE_COLS_Y):
            ACTORS["tables"].append((tx, ty))
            skirts.append(((tx, ty, 50), (72, 100)))
            tops.append(((tx, ty, 102), (92, 4)))
            bowls.append(((tx, ty, 107), (22, 6)))
            _merge(flor, _florals((tx, ty, 112), 11, 9, 9, F + "/Tables", "TableBlooms", bloom=8.0))
            for k in range(2):
                a = _rng.uniform(0, 2 * math.pi)
                cxp, cyp = tx + 24 * math.cos(a), ty + 24 * math.sin(a)
                candles.append(((cxp, cyp, 110), (4.5, 12)))
                # v5: table lamps carry the practical; candle meshes stay as dressing, their points go off
                if k == 0 and _cfg("CANDLE_LIGHTS", True) and not _cfg("TABLE_LAMPS", True):
                    point("Candle_%d_%d" % (ti, tj), (cxp, cyp, 124), float(_cfg("CANDLE_CD", 30.0)),
                          kelvin_temp=1900, radius=float(_cfg("CANDLE_RADIUS", 240.0)), shadows=False,
                          volumetric=0.0, source_radius=2, folder="Lights/Candles")
            for k in range(3):
                a = _rng.uniform(0, 2 * math.pi)
                glasses.append(((tx + 34 * math.cos(a), ty + 34 * math.sin(a), 113), (6, 18)))
    _ism("cylinder", skirts, M.get("MI_Tablecloth_Black"), "Table_Skirts", F + "/Tables", collision=True)
    _ism("cylinder", tops, M.get("MI_Tablecloth"), "Table_Tops", F + "/Tables")
    _ism("cylinder", bowls, M.get("MI_Gold"), "Table_Bowls", F + "/Tables", shadows=False)
    _ism("cylinder", candles, M.get("MI_E_Candle"), "Table_Candles", F + "/Tables", shadows=False)
    _ism("cylinder", glasses, M.get("MI_Glass_Champagne"), "Table_Champagne", F + "/Tables", shadows=False)
    for mat, it in flor.items():
        _ism("sphere", it, M.get(mat), "Table_" + mat[3:], F + "/Tables", shadows=False)
    if _cfg("TABLE_LAMPS", True):
        _build_table_lamps()
    _build_wide_foreground()


def _build_table_lamps():
    """One warm practical per cocktail table: dark stem, glowing shade, shadowless point in the shade.
    These pool gold on the polished floor and fill the lower half of the chandelier crane."""
    F = "Dressing/Tables"
    bases, stems, shades = [], [], []
    cd = float(_cfg("TABLE_LAMP_CD", 110.0))
    radius = float(_cfg("TABLE_LAMP_RADIUS", 520.0))
    for ti, tx in enumerate(S.TABLE_ROWS_X):
        for tj, ty in enumerate(S.TABLE_COLS_Y):
            lx, ly = tx + 22.0, ty - 16.0
            bases.append(((lx, ly, 105), (10, 3)))
            stems.append(((lx, ly, 120), (2.2, 28)))
            shades.append(((lx, ly, 142), (16, 14)))
            point("TableLamp_%d_%d" % (ti, tj), (lx, ly, 142), cd, kelvin_temp=2300, radius=radius,
                  shadows=False, volumetric=0.2, source_radius=6, folder="Lights/TableLamps")
    _ism("cylinder", bases, M.get("MI_DarkMetal"), "Table_LampBases", F, shadows=False)
    _ism("cylinder", stems, M.get("MI_BrushedSteel") or M.get("MI_Chrome") or M.get("MI_DarkMetal"),
         "Table_LampStems", F, shadows=False)
    _ism("cylinder", shades, M.get("MI_E_LampShade") or M.get("MI_E_Warm"), "Table_LampShades", F, shadows=False)


def _build_wide_foreground():
    """A waiter-height champagne stand just off CAM_06's lens (lower-right bokeh, not on the path)."""
    F = "Dressing/Foreground"
    fx, fy = 2775.0, -215.0
    cylinder((fx, fy, 0), 10, 4, M.get("MI_DarkMetal"), label="FG_Stand_Foot", folder=F, shadows=False)
    cylinder((fx, fy, 4), 2.2, 118, M.get("MI_BrushedSteel") or M.get("MI_Chrome") or M.get("MI_DarkMetal"),
             label="FG_Stand_Stem", folder=F, shadows=False, collision=False)
    cylinder((fx, fy, 122), 22, 2, M.get("MI_DarkMetal"), label="FG_Stand_Tray", folder=F, shadows=False,
             collision=False)
    glasses = []
    for k in range(5):
        a = 2 * math.pi * k / 5.0
        glasses.append(((fx + 9.0 * math.cos(a), fy + 9.0 * math.sin(a), 132), (5.0, 16.0)))
    _ism("cylinder", glasses, M.get("MI_Glass_Champagne"), "FG_Champagne", F, shadows=False)


# =========================================================================== the Echo
def build_car():
    """Turntable + the Echo (sleek low silhouette from scaled primitives, faux-lacquer paint,
    light-line signature) + a draped satin cover that the sequence pulls into the rig."""
    F = "Stage/Echo"
    cx, cy = S.CAR_POS
    h = S.STAGE_H
    yaw = S.CAR_YAW
    # The turntable ROOT is a scale-1 pivot. (v2 bug: the root was the 7.2 x 7.2 x 0.14 cylinder itself;
    # the sequence keyed its scale back to 1, collapsing the plinth to a 1 m drum and stretching every
    # attached car part 7x tall / 7x thin. A non-uniformly scaled parent also shears pitched/rolled children.)
    table = U.pivot((cx, cy, h), "Echo_Turntable_Pivot", F, movable=True) if hasattr(U, "pivot") else \
        spawn(unreal.StaticMeshActor, (cx, cy, h), (0, 0, 0), "Echo_Turntable_Pivot", F)
    try:
        table.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception:
        pass
    # dark glossy plinth; the only light is a thin band on its edge (a 724 cm disc 1.5 cm thick buried
    # inside the 720 cm plinth: only its 2 mm rim shows). v2/v3 had a full 730 cm emissive disc flush
    # with the top + a 520 cm inner disc + an underglow pool = the pale-blue glowing table.
    plinth = cylinder((cx, cy, h), 720, 14, M.get("MI_Turntable_Top") or M.get("MI_StageGloss"),
                      label="Echo_Turntable", folder=F, movable=True)
    attach(plinth, table)
    ring = cylinder((cx, cy, h + 10.5), 724, 1.5, M.get("MI_E_CoolStrip"), folder=F, movable=True, shadows=False,
                    collision=False, label="Echo_Turntable_EdgeRing")
    attach(ring, table)
    CAR_PARTS[:] = []
    origin = (cx, cy, h + 14)

    def part(shape_name, local, size, mat, label=None, rot_local=(0, 0, 0), shadows=True):
        """size in cm (engine shapes are 100 cm)."""
        wx, wy, wz = local_to_world(origin, yaw, local)
        a = spawn_mesh(shape_name, (wx, wy, wz), tuple(s / 100.0 for s in size), mat,
                       rot=(rot_local[0], yaw + rot_local[1], rot_local[2]),
                       label=label, folder=F + "/Car", movable=True, shadows=shadows, collision=False)
        attach(a, table)
        CAR_PARTS.append(a)
        return a

    if S.ECHO_CAR_MESH and unreal.EditorAssetLibrary.does_asset_exist(S.ECHO_CAR_MESH):
        body = _spawn_asset_mesh(S.ECHO_CAR_MESH, origin, yaw + S.ECHO_CAR_MESH_YAW_OFFSET, S.ECHO_CAR_MESH_SCALE,
                                 "Echo_Car", F + "/Car")
        if body is not None:
            attach(body, table)
            _finish_car(table, body, cx, cy, h, yaw)
            return
        warn("ECHO_CAR_MESH failed to spawn - using primitives")

    paint, trim = M.get("MI_CarPaint_Pearl"), M.get("MI_CarPaint_Trim") or M.get("MI_DarkMetal")
    glass, chrome, tire = M.get("MI_CarGlass_Dark"), M.get("MI_Chrome"), M.get("MI_Tire")
    rim = M.get("MI_Rim_Gunmetal") or M.get("MI_DarkMetal")
    # v4 proportions: 500 L x 198 W x ~103 H (lower + longer than v3's 480 x 122), long hood,
    # raked windshield, cab-rearward low greenhouse under a painted roof, tapered tail, wide haunches.
    # Body core ellipsoid: a=250, b=99, c=24 centred at z=46 (local, above the turntable top).
    body = part("sphere", (0, 0, 46), (500, 198, 48), paint, "Echo_Body")
    part("sphere", (0, 0, 32), (490, 196, 28), paint, "Echo_LowerBody")                 # fuller lower flank
    part("cube", (0, 0, 20), (420, 178, 12), trim, "Echo_Skirt")                        # dark sill / diffuser
    part("sphere", (112, 0, 58), (290, 182, 26), paint, "Echo_Hood", rot_local=(-3.5, 0, 0))   # long, low hood
    part("sphere", (30, 0, 72), (150, 132, 22), glass, "Echo_Windshield", rot_local=(-16.0, 0, 0))  # raked screen
    part("sphere", (-55, 0, 80), (220, 128, 38), glass, "Echo_Greenhouse", rot_local=(-4.0, 0, 0))
    part("sphere", (-62, 0, 95), (150, 104, 14), paint, "Echo_Roof")                    # painted roof cap
    part("sphere", (-135, 0, 58), (250, 172, 30), paint, "Echo_RearDeck", rot_local=(4.0, 0, 0))   # tapers aft
    for sy in (-1, 1):
        part("sphere", (-120, sy * 74, 50), (180, 58, 44), paint, "Echo_Haunch")         # rear shoulders
        part("sphere", (158, sy * 78, 46), (128, 50, 40), paint, "Echo_FrontFender")
        part("sphere", (-10, sy * 93, 34), (250, 14, 14), trim, "Echo_SideBlade")        # dark side intake blade
    # beltline: a 1 cm chrome crease that sits ~1.5 cm proud of the body section at z=52
    part("sphere", (0, 0, 52), (487, 195, 1.0), chrome, "Echo_BeltLine", shadows=False)
    # wheels: dark rubber, a recessed dark well, gunmetal face, a hairline bright lip (not a glowing disc)
    for lx in (160.0, -160.0):
        for sy in (-1, 1):
            part("cylinder", (lx, sy * 86, 35), (70, 70, 30), tire, rot_local=(0, 0, 90))
            part("cylinder", (lx, sy * 92, 35), (44, 44, 16), M.get("MI_DarkMetal") or rim,
                 rot_local=(0, 0, 90), shadows=False)
            part("cylinder", (lx, sy * 101.0, 35), (52, 52, 2.4), rim, rot_local=(0, 0, 90), shadows=False)
            # 4 mm larger than the face, 7 mm thick: only the outer lip catches the light
            part("cylinder", (lx, sy * 101.2, 35), (52.8, 52.8, 0.7),
                 M.get("MI_E_RimAccent") or M.get("MI_E_WheelGlow"),
                 rot_local=(0, 0, 90), shadows=False)
            part("cylinder", (lx, sy * 102.2, 35), (10, 10, 0.8), chrome, rot_local=(0, 0, 90), shadows=False)
    # light signature (halo ellipsoids hugging the body section so only the intended arc shows):
    #   two stacked white headlight strips across the nose (~140 cm wide, 3 + 1.5 cm tall),
    #   a red deck-lip tail light + a full-width lower red tail bar.
    part("sphere", (10, 0, 50), (484, 190, 3.0), M.get("MI_E_CarLight"), "Echo_Headlight_Upper", shadows=False)
    part("sphere", (10, 0, 44), (486, 192, 1.5), M.get("MI_E_CarLight"), "Echo_Headlight_Lower", shadows=False)
    part("sphere", (-14, 0, 54), (492, 190, 2.5), M.get("MI_E_CarTail"), "Echo_Taillight_Deck", shadows=False)
    part("sphere", (-4, 0, 40), (492, 188, 2.0), M.get("MI_E_CarTail"), "Echo_Taillight_Bar", shadows=False)
    _finish_car(table, body, cx, cy, h, yaw)


def _spawn_asset_mesh(path, loc, yaw, scale, label, folder):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        return None
    if isinstance(asset, unreal.SkeletalMesh):
        a = spawn(unreal.SkeletalMeshActor, loc, (0, yaw, 0), label, folder, (scale, scale, scale))
        c = a.skeletal_mesh_component
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        try:
            c.set_skeletal_mesh_asset(asset)
        except Exception:
            set_prop(c, ["skeletal_mesh_asset", "skeletal_mesh"], asset)
        return a
    if isinstance(asset, unreal.StaticMesh):
        a = spawn(unreal.StaticMeshActor, loc, (0, yaw, 0), label, folder, (scale, scale, scale))
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(asset)
        return a
    try:
        cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
        return spawn(cls, loc, (0, yaw, 0), label, folder, (scale, scale, scale))
    except Exception as exc:
        warn("cannot spawn %s: %s" % (path, exc))
        return None


def _finish_car(table, body, cx, cy, h, yaw):
    F = "Stage/Echo"
    # the drape: an oversized satin shell + a flared hem skirt (attached, so they lift together)
    cover = spawn_mesh("sphere", (cx, cy, h + 14 + 62), (5.9, 2.9, 1.4), M.get("MI_CarCover_Satin"),
                       rot=(0, yaw, 0), label="Echo_Cover", folder=F, movable=True, collision=False)
    skirt = spawn_mesh("cylinder", (cx, cy, h + 14), (5.8, 2.9, 0.9), M.get("MI_CarCover_Satin"),
                       rot=(0, yaw, 0), label="Echo_Cover_Skirt", folder=F, movable=True, collision=False)
    attach(skirt, cover)
    # "little light on it": a faint cool glow leaking under the cover hem
    hem = cylinder((cx, cy, h + 14), 520, 2, M.get("MI_E_CoolStrip"), label="Echo_Cover_HemGlow", folder=F,
                   movable=True, shadows=False, collision=False)
    hem.set_actor_scale3d(V(5.92, 3.02, 0.02))
    hem.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=float(yaw)), False)
    ACTORS.update(turntable=table, car_body=body, cover=cover, cover_hem=hem)
    _log_car(table, body, cover)


def _bounds(actor):
    try:
        o, e = actor.get_actor_bounds(False)
        return "centre (%.0f, %.0f, %.0f) extent (%.0f, %.0f, %.0f)" % (o.x, o.y, o.z, e.x, e.y, e.z)
    except Exception as exc:
        return "bounds n/a (%s)" % exc


def _log_car(table, body, cover):
    """Build-log evidence that the Echo exists where the cameras expect it."""
    try:
        sc = table.get_actor_scale3d()
        log("Echo: %d car parts attached to %s (pivot scale %.2f %.2f %.2f)"
            % (len(CAR_PARTS), table.get_actor_label() if hasattr(table, "get_actor_label") else "pivot",
               sc.x, sc.y, sc.z))
        if body is not None:
            l = body.get_actor_location()
            log("Echo body at (%.0f, %.0f, %.0f), %s" % (l.x, l.y, l.z, _bounds(body)))
        if cover is not None:
            log("Echo drape %s" % _bounds(cover))
        if body is not None:
            o, e = body.get_actor_bounds(False)
            if e.z < 10 or e.x < 50:
                warn("Echo body bounds look collapsed - check scale / attachment")
    except Exception as exc:
        warn("car log: %s" % exc)


# =========================================================================== stage lighting
def build_stage_lights():
    h = S.STAGE_H
    rx, ry = S.RIVERS_POS
    cx, cy = S.CAR_POS
    head = (rx, ry, h + 165)
    # ---- Rivers: high 3/4 key (shadows), cool back rim (shadows), warm low practical rim, lectern bounce
    ACTORS["key_rivers"] = spot("Key_Rivers", (4450, -950, 1150), head, S.KEY_RIVERS_CD, kelvin_temp=4300,
                                inner=7, outer=13, shadows=True, volumetric=4.0, radius=5000)
    ACTORS["rim_rivers"] = spot("Rim_Rivers", (5450, -150, 1150), head, _cfg("RIM_RIVERS_CD", S.KEY_RIVERS_CD * 0.5),
                                kelvin_temp=6500,
                                inner=6, outer=12, shadows=True, volumetric=2.0, radius=4000)
    spot("Rim_Rivers_Practical", (5650, -780, 330), (rx, ry, h + 150), _cfg("RIVERS_PRACTICAL_RIM_CD", 9000.0),
         kelvin_temp=3000, inner=10, outer=22, shadows=False, volumetric=0.6, radius=1400, folder="Lights/Practicals")
    # lectern bounce: up near his chest, NOT 13 cm over the top (v2 blew the lectern out to a white slab)
    point("Podium_Bounce", (S.PODIUM_POS[0] + 45, S.PODIUM_POS[1], h + 150), _cfg("PODIUM_PRACTICAL_CD", 60.0),
          kelvin_temp=3200, radius=260, shadows=False, volumetric=0.0, source_radius=12, folder="Lights/Practicals")
    # follow spot from the back of the hall (starts on Rivers, swings to the car in the sequence)
    ACTORS["follow"] = spot("FollowSpot", (900, 0, 1250), head, S.FOLLOW_SPOT_CD, kelvin_temp=5600, inner=2.5,
                            outer=5.0, shadows=True, volumetric=6.0, radius=9000)
    # ---- car: two shadowed top spots (dim until the reveal) + shadowless rims and sweeps
    car_c = (cx, cy, h + 60)
    ACTORS["car_spot_a"] = spot("CarSpot_A", (4450, 300, 1150), car_c, S.CAR_SPOT_CD_PRE, kelvin_temp=6500, inner=14,
                                outer=24, shadows=True, volumetric=3.0, radius=5000)
    ACTORS["car_spot_b"] = spot("CarSpot_B", (5450, 1500, 1150), car_c, S.CAR_SPOT_CD_PRE, kelvin_temp=7500,
                                inner=14, outer=26, shadows=True, volumetric=3.0, radius=5000)
    ACTORS["car_rims"] = []
    for i, (lx, ly) in enumerate(((5800, 300), (5800, 1500))):
        # raised and aimed at the body, not the wheels, so the gun-metal rims stay dark
        ACTORS["car_rims"].append(spot("CarRim_%d" % i, (lx, ly, 420), (cx, cy, h + 95), 0.0, kelvin_temp=7500,
                                       inner=10, outer=24, shadows=False, volumetric=1.2, radius=2200))
    # sweep beams: low on the deck behind the car, they tilt from grazing the deck up through the car into the haze
    ACTORS["sweeps"] = []
    for i, ly in enumerate((cy - 560, cy - 190, cy + 190, cy + 560)):
        loc = (5820, ly, h + 12)
        a = spot("Sweep_%d" % i, loc, (cx - 200, cy + (ly - cy) * 0.3, h), 0.0, kelvin_temp=7000, inner=3, outer=7,
                 shadows=False, volumetric=5.0, radius=5000, folder="Lights/Sweeps")
        ACTORS["sweeps"].append(a)
    ACTORS["car_underglow"] = point("Echo_UnderGlow", (cx, cy, h + 22), 0.0, color=LC(0.35, 0.6, 1.0),
                                    kelvin_temp=None, radius=520, shadows=False, volumetric=0.0, source_radius=150)
    # cool blue wash beams across the stage (visible in the volumetric fog)
    for i, y in enumerate((-1500, -700, 700, 1500)):
        spot("StageWash_%d" % i, (5450, y, 1150), (4700, y * 0.6, 0), S.STAGE_WASH_CD, inner=5, outer=12,
             shadows=False, volumetric=3.5, radius=4000, color=LC(0.25, 0.55, 0.9), kelvin_temp=None)
    # lit TextRender on an unlit screen: a broad shadowless kicker only the text responds to
    spot("Screen_TextKicker", (5500, 0, 1120), (S.HALL_LEN - 70, 0, h + 560), _cfg("TEXT_KICKER_CD", 5000.0),
         kelvin_temp=6000, inner=25, outer=40, shadows=False, volumetric=0.0, radius=1600, folder="Lights/Practicals")
    # v5: cool backlight on the front of the house so crowd shoulders rim against a darker room
    for i, (lx, ly) in enumerate(((S.STAGE_X0 - 40, -700.0), (S.STAGE_X0 - 40, 700.0))):
        spot("CrowdRim_%d" % i, (lx, ly, h + 95), (lx - 1800, ly * 0.45, 140), float(_cfg("CROWD_RIM_CD", 14000.0)),
             kelvin_temp=6500, inner=16, outer=38, shadows=False, volumetric=0.7, radius=2800,
             folder="Lights/Practicals")
    spot("CrowdRim_Aisle", (S.STAGE_X0 - 80, 0, h + 80), (3100, 0, 150), float(_cfg("CROWD_RIM_CD", 14000.0)) * 0.7,
         kelvin_temp=6200, inner=12, outer=28, shadows=False, volumetric=0.5, radius=2600,
         folder="Lights/Practicals")
    # Isabella: soft warm key from the stage side (shadowless - she is a face in the crowd, but OUR face)
    ix, iy = _cfg("ISABELLA_POS", (4200.0, -1180.0))
    ACTORS["key_isabella"] = spot("Key_Isabella", (4720, -900, 430), (ix, iy, 150), _cfg("ISABELLA_KEY_CD", 2500.0),
                                  kelvin_temp=3100, inner=14, outer=34, shadows=False, volumetric=0.3, radius=1500,
                                  folder="Lights/Practicals")
    point("Isabella_Fill", (ix + 150, iy + 120, 120), 150.0, kelvin_temp=3600, radius=420, shadows=False,
          volumetric=0.0, source_radius=40, folder="Lights/Practicals")


# =========================================================================== people
_ANIM_EXCLUDE = ("Pistol", "Rifle", "Death", "Jump", "Fall", "Crouch", "Walk", "Jog", "Run", "Turn", "Land",
                 "Aim", "Reload", "Fire", "Hit", "Montage", "BlendSpace", "BS_", "Additive")


class People:
    """Mannequin crowd. Mesh lookup tries settings.MANNY/QUINN_MESH_PATHS, then short names anywhere
    under /Game; idles try settings.IDLE_ANIM(_PATHS), then any '*Idle*' AnimSequence that isn't a
    weapon/locomotion clip. Falls back to capsules / bind pose with a warning."""

    def __init__(self):
        self.manny, mp = U.find_first_asset(
            _cfg("MANNY_MESH_PATHS", ["/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple",
                                      "/Game/Characters/Mannequins/Meshes/SKM_Manny"]),
            _cfg("MANNY_MESH_NAMES", ["SKM_Manny_Simple", "SKM_Manny"]), "SkeletalMesh", "Mannequins")
        self.quinn, qp = U.find_first_asset(
            _cfg("QUINN_MESH_PATHS", ["/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple",
                                      "/Game/Characters/Mannequins/Meshes/SKM_Quinn"]),
            _cfg("QUINN_MESH_NAMES", ["SKM_Quinn_Simple", "SKM_Quinn"]), "SkeletalMesh", "Mannequins")
        log("crowd meshes: manny=%s quinn=%s" % (mp, qp))
        self.idles = self._find_idles()
        if not (self.manny or self.quinn):
            warn("Manny/Quinn not found in /Game - crowd will be capsule placeholders. "
                 "Copy the Third Person template content (setup.ps1 does this).")
        if not self.idles:
            warn("no idle animation found - mannequins will stand in bind pose (A-pose)")
        self._tints = {}

    @staticmethod
    def _anim_len(anim):
        for fn in ("get_play_length",):
            try:
                v = float(getattr(anim, fn)())
                if v > 0.1:
                    return v
            except Exception:
                pass
        for prop in ("sequence_length", "play_length"):
            try:
                v = float(anim.get_editor_property(prop))
                if v > 0.1:
                    return v
            except Exception:
                pass
        return 3.0

    def _find_idles(self):
        found, seen = [], set()
        paths = []
        if S.IDLE_ANIM:
            paths.append(S.IDLE_ANIM)
        paths += list(_cfg("IDLE_ANIM_PATHS", ["/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle"]))
        for n in ("MM_Idle", "MF_Idle", "MM_Unarmed_Idle", "Idle"):
            p = find_asset_by_name(n, prefer_substring="Mannequins")
            if p:
                paths.append(p.split(".")[0])
        paths += [p.split(".")[0] for p in U.find_assets_matching("Idle", "/Game", exclude=_ANIM_EXCLUDE, limit=12)]
        for p in paths:
            if p in seen:
                continue
            seen.add(p)
            a = U.load(p)
            if a is None or not U._is_class(a, "AnimSequence"):
                continue
            found.append((a, self._anim_len(a), p))
            if len(found) >= 3:
                break
        log("crowd idles: %s" % [f[2] for f in found])
        return found

    def _outfit(self, name, female):
        """Our sheen fabric MI when the surface master built (or wasn't rebuilt this run);
        otherwise a tinted template-mannequin MI; otherwise whatever exists."""
        mat = M.get(name)
        if mat is not None and M.MASTERS.get("surface", True) is not None:
            return mat
        key = (name, female)
        if key not in self._tints:
            rgb = _cfg("OUTFIT_TINTS", {}).get(name, (0.02, 0.02, 0.025))
            parents = (_cfg("QUINN_MATERIALS", ["/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_01"])
                       if female else
                       _cfg("MANNY_MATERIALS", ["/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New"]))
            tint = None
            for pp in parents:
                tint = M.mannequin_tint("MI_Crowd_" + name[3:] + ("_F" if female else "_M"), pp, rgb)
                if tint is not None:
                    break
            self._tints[key] = tint or mat
        return self._tints[key]

    def place(self, loc, face_yaw, female=False, outfit="MI_Fabric_Tux", label=None, folder="Crowd",
              secondary=None, play_rate=None, skin=None, inspect=False):
        bp = S.CAST_BLUEPRINTS.get(label or "", "")
        if bp:
            try:
                cls = unreal.EditorAssetLibrary.load_blueprint_class(bp)
                if cls:
                    return spawn(cls, loc, (0, face_yaw + S.CAST_BLUEPRINT_YAW_OFFSET, 0), label, folder)
            except Exception as exc:
                warn("cast blueprint %s for %s failed (%s) - using a mannequin" % (bp, label, exc))
        mesh = (self.quinn if female else self.manny) or self.manny or self.quinn
        if mesh is None:
            return self._capsule(loc, outfit, label, folder)
        # Mannequin meshes face +Y; actor yaw = desired facing - 90
        a = spawn(unreal.SkeletalMeshActor, loc, (0, face_yaw - 90.0, 0), label, folder)
        c = a.skeletal_mesh_component
        try:
            c.set_skeletal_mesh_asset(mesh)
        except Exception:
            set_prop(c, ["skeletal_mesh_asset", "skeletal_mesh"], mesh)
        if inspect:
            _log_template_materials(c, label or "mannequin")
        mat = self._outfit(outfit, female)
        mat2 = self._outfit(secondary, female) if secondary else mat
        skin_mat = M.get(skin) if skin else None
        trouser_mat = M.get("MI_Fabric_Trouser") or mat
        if mat:
            try:
                n = max(1, int(c.get_num_materials()))
                slots = _slot_names(c, n)
                for i in range(n):
                    use = mat if i == 0 else (mat2 or mat)
                    kind = _slot_kind(slots[i])
                    if kind == "legs":
                        # M_HeadLegs is one slot on the simple mannequin (skull + legs). Skin here
                        # would also paint the trousers peach, so we suit the whole slot.
                        use = trouser_mat or mat
                    elif kind == "skin" and skin_mat is not None:
                        use = skin_mat
                    c.set_material(i, use)
            except Exception as exc:
                warn("outfit material: %s" % exc)
        if self.idles:
            anim, length, _p = self.idles[_rng.randrange(len(self.idles))]
            try:
                c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                data = unreal.SingleAnimationPlayData()
                data.set_editor_property("anim_to_play", anim)
                data.set_editor_property("saved_looping", True)
                data.set_editor_property("saved_playing", True)
                data.set_editor_property("saved_position", _rng.uniform(0.0, max(0.1, length - 0.05)))
                data.set_editor_property("saved_play_rate", play_rate or _rng.uniform(0.85, 1.1))
                c.set_editor_property("animation_data", data)
            except Exception as exc:
                warn("idle anim: %s" % exc)
        set_prop(c, "cast_shadow", True, quiet=True)
        return a

    @staticmethod
    def _capsule(loc, outfit, label, folder):
        body = cylinder((loc[0], loc[1], loc[2]), 45, 150, M.get(outfit), label=label, folder=folder)
        sphere((loc[0], loc[1], loc[2] + 168), 26, M.get(outfit), folder=folder)
        return body


def _slot_names(comp, n):
    names = []
    try:
        names = [str(x) for x in (comp.get_material_slot_names() or [])]
    except Exception:
        pass
    return (names + [""] * n)[:n]


def _slot_kind(name):
    """Classify a mannequin slot. 'M_HeadLegs' must count as legs, not skin: 'head' is a substring."""
    n = (name or "").lower()
    if any(k in n for k in ("leg", "pant", "trouser")):
        return "legs"
    if any(k in n for k in ("head", "face", "skin")):
        return "skin"
    return "cloth"


def _log_template_materials(comp, who):
    """What the stock mannequin exposes (slot names + each template material's parameters), so the
    next art pass can tint it instead of replacing it if wanted."""
    try:
        n = int(comp.get_num_materials())
        slots = _slot_names(comp, n)
        for i in range(n):
            m = comp.get_material(i)
            vec, sca = [], []
            if m is not None:
                try:
                    vec = [str(x) for x in (M.MEL.get_vector_parameter_names(m) or [])]
                    sca = [str(x) for x in (M.MEL.get_scalar_parameter_names(m) or [])]
                except Exception as exc:
                    vec = ["n/a: %s" % exc]
            log("%s template slot %d '%s' = %s | vector params %s | scalar params %s"
                % (who, i, slots[i], m.get_name() if m else "None", vec, sca))
    except Exception as exc:
        warn("%s template material log: %s" % (who, exc))


def _log_materials(actor, who):
    try:
        c = actor.skeletal_mesh_component
        n = int(c.get_num_materials())
        names = []
        for i in range(n):
            m = c.get_material(i)
            names.append(m.get_name() if m else "None")
        log("%s materials per slot: %s" % (who, names))
    except Exception as exc:
        warn("%s material log: %s" % (who, exc))


GOWNS = ["MI_Gown_Red", "MI_Gown_Gold", "MI_Gown_Emerald", "MI_Gown_Midnight", "MI_Gown_Black", "MI_Gown_Black",
         "MI_Gown_Silver"]
SUITS = ["MI_Fabric_Tux", "MI_Fabric_Tux", "MI_Fabric_Tux", "MI_Fabric_Charcoal", "MI_Fabric_Navy"]


def _guest_look(female):
    if female:
        g = _rng.choice(GOWNS)
        return g, g
    return _rng.choice(SUITS), "MI_Fabric_Satin"


def build_crowd():
    people = People()
    h = S.STAGE_H
    rx, ry = S.RIVERS_POS
    ix, iy = _cfg("ISABELLA_POS", (4200.0, -1180.0))
    suit = "MI_Fabric_RiversSuit" if M.get("MI_Fabric_RiversSuit") else "MI_Fabric_Charcoal"
    ACTORS["rivers"] = people.place((rx, ry, h), 180.0, False, suit, "DrRivers", "Cast",
                                    secondary=suit, play_rate=0.9, skin="MI_Skin_Dark", inspect=True)
    # torso: near-black suit cloth; M_HeadLegs: dark trouser (not skin — that slot also covers the legs)
    _log_materials(ACTORS["rivers"], "DrRivers")
    ACTORS["assistant"] = people.place((5380, -1350, h), 165.0, True, "MI_Gown_Black", "Assistant", "Cast")
    ACTORS["isabella"] = people.place((ix, iy, 0), math.degrees(math.atan2(ry - iy, rx - ix)), True, "MI_Gown_Red",
                                      "Isabella", "Cast", play_rate=0.85)
    if not S.CROWD_ENABLED:
        ACTORS["press"] = []
        return
    stage_target = (S.STAGE_X0 + 400, -100)
    face_stage = _cfg("CROWD_FACE_STAGE", 0.8)
    for ti, tx in enumerate(S.TABLE_ROWS_X):
        for tj, ty in enumerate(S.TABLE_COLS_Y):
            n = S.GUESTS_PER_TABLE
            # open the side facing the stage so nobody stands with their back to it
            base = math.degrees(math.atan2(stage_target[1] - ty, stage_target[0] - tx)) + 180.0 - 60.0
            for k in range(n):
                ang = math.radians(base + k * (120.0 / max(1, n - 1)) + _rng.uniform(-14, 14))
                px, py = tx + 95 * math.cos(ang), ty + 95 * math.sin(ang)
                if math.hypot(px - ix, py - iy) < 110:      # keep Isabella's eyeline clear
                    continue
                to_table = math.degrees(math.atan2(ty - py, tx - px))
                to_stage = math.degrees(math.atan2(stage_target[1] - py, stage_target[0] - px))
                face = to_stage if _rng.random() < face_stage else to_table
                face += _rng.uniform(-12, 12)
                female = _rng.random() < 0.5
                outfit, sec = _guest_look(female)
                people.place((px, py, 0), face, female, outfit, "Guest_%d_%d_%d" % (ti, tj, k), "Crowd/Guests",
                             secondary=sec)
    # standing guests along the aisle edges near the front (fills the dolly's foreground)
    for i, (gx, gy) in enumerate(((3050, -470), (3700, 480), (4150, 520), (2450, 450), (3900, -560))):
        female = i % 2 == 0
        outfit, sec = _guest_look(female)
        face = math.degrees(math.atan2(stage_target[1] - gy, stage_target[0] - gx)) + _rng.uniform(-10, 10)
        people.place((gx, gy, 0), face, female, outfit, "Guest_Aisle_%d" % i, "Crowd/Guests", secondary=sec)
    # v5: a close left-shoulder silhouette for CAM_06 (camera sits at ~2720, -340, 175, looking stage-ward)
    face_fg = math.degrees(math.atan2(stage_target[1] - (-490.0), stage_target[0] - 2840.0))
    people.place((2840, -490, 0), face_fg, True, "MI_Gown_Black", "Guest_FG_Shoulder", "Crowd/Guests",
                 secondary="MI_Gown_Black")
    # balcony guests leaning on the rail, looking down at the stage
    nb = int(_cfg("BALCONY_GUESTS_PER_SIDE", 6))
    bx0, bx1 = _cfg("BALCONY_X", (400.0, 4400.0))
    bz = _cfg("BALCONY_Z", 650.0)
    for side in (-1, 1):
        for i in range(nb):
            gx = bx0 + 300 + (bx1 - bx0 - 600) * (i + _rng.uniform(0.15, 0.85)) / max(1, nb)
            gy = side * (S.HALL_HALF_W - 105)
            face = math.degrees(math.atan2(stage_target[1] - gy, stage_target[0] - gx)) + _rng.uniform(-15, 15)
            female = _rng.random() < 0.5
            outfit, sec = _guest_look(female)
            people.place((gx, gy, bz), face, female, outfit, "Balcony_%s_%d" % ("L" if side < 0 else "R", i),
                         "Crowd/Balcony", secondary=sec)
    # bartenders
    for side in (-1, 1):
        people.place((540, side * 1100, 0), 0.0 + _rng.uniform(-20, 20), False, "MI_Fabric_Tux",
                     "Bartender_%s" % ("L" if side < 0 else "R"), "Crowd/Bar", secondary="MI_Tablecloth")
    # press pit between the podium and the car (the flash lights live at their hands)
    ACTORS["press"] = []
    y0, dy = _cfg("PRESS_Y0", -600.0), _cfg("PRESS_SPACING", 300.0)
    for i in range(S.PRESS_COUNT):
        py = y0 + i * dy + _rng.uniform(-30, 30)
        px = S.STAGE_X0 - 260 + _rng.uniform(-30, 30)
        aim = (rx, ry) if py < 150 else S.CAR_POS
        face = math.degrees(math.atan2(aim[1] - py, aim[0] - px)) + _rng.uniform(-6, 6)
        people.place((px, py, 0), face, _rng.random() < 0.3, "MI_Fabric_Charcoal", "Press_%d" % i, "Crowd/Press",
                     secondary="MI_Fabric_Satin")
        ACTORS["press"].append((px, py))


def build_flash_lights():
    """Camera-flash point lights (intensity 0; the sequences key them)."""
    ACTORS["flash_cine"], ACTORS["flash_loop"] = [], []
    for i, (px, py) in enumerate(ACTORS.get("press", [])):
        a = point("Flash_Cine_%d" % i, (px + 45, py, 175), 0.0, kelvin_temp=6200, radius=2200, shadows=False,
                  volumetric=0.5, source_radius=6, folder="Lights/Flashes")
        ACTORS["flash_cine"].append(a)
    for i in range(6):   # flashes scattered in the crowd for the walkable loop
        px = _rng.uniform(1300, 4200)
        py = _rng.choice([-1, 1]) * _rng.uniform(500, 1700)
        a = point("Flash_Loop_%d" % i, (px, py, 190), 0.0, kelvin_temp=6200, radius=1800, shadows=False,
                  volumetric=0.3, source_radius=6, folder="Lights/Flashes")
        ACTORS["flash_loop"].append(a)


# =========================================================================== cinematic focus marks
def build_focus_marks():
    """Invisible TargetPoints the cine cameras track for focus on wide shots."""
    h = S.STAGE_H
    marks = {"focus_stage": (5150.0, 150.0, h + 170.0), "focus_crowd": (3400.0, -200.0, 160.0)}
    for k, loc in marks.items():
        try:
            ACTORS[k] = spawn(unreal.TargetPoint, loc, (0, 0, 0), "Focus_" + k.split("_")[1].title(), "Cinematics")
        except Exception as exc:
            warn("focus mark %s: %s" % (k, exc))


# =========================================================================== gameplay
def build_gameplay():
    ps = spawn(unreal.PlayerStart, (-2200, 0, 120), (0, 0, 0), "PlayerStart_RedCarpet", "Gameplay")
    ACTORS["player_start"] = ps
    gm_path = find_asset_by_name("BP_ThirdPersonGameMode")
    gm_class = None
    if gm_path:
        try:
            gm_class = unreal.EditorAssetLibrary.load_blueprint_class(gm_path.split(".")[0])
        except Exception as exc:
            warn("load_blueprint_class failed: %s" % exc)
    if gm_class is None:
        warn("BP_ThirdPersonGameMode not found - level will use the default GameMode (fly-cam pawn)")
        return
    world = editor_world()
    ws = None
    for fn in ("get_world_settings", "k2_get_world_settings"):
        try:
            ws = getattr(world, fn)()
            if ws:
                break
        except Exception:
            continue
    if ws is None:
        warn("could not reach WorldSettings to set the game mode override")
        return
    set_prop(ws, "default_game_mode", gm_class)
    set_prop(ws, "kill_z", -1500.0, quiet=True)
    log("GameMode override: " + gm_path)


def build_invisible_walls():
    """Collision-only walls around the plaza so the player can't walk off the set."""
    for i, (mn, mx) in enumerate((((-5300, -9100, -50), (-5200, 9100, 800)),
                                  ((-5300, -9100, -50), (0, -9000, 800)),
                                  ((-5300, 9000, -50), (0, 9100, 800)))):
        w = box_from_min_max(mn, mx, None, label="InvisibleWall_%d" % i, folder="Gameplay", shadows=False)
        w.set_actor_hidden_in_game(True)
        try:
            w.static_mesh_component.set_visibility(False, False)
        except Exception:
            pass


# =========================================================================== entry
def build():
    with step("open/create level", critical=True):
        open_or_create_level()
    with step("environment (sky dome, moon, skylight, volumetric fog)"):
        build_environment()
    with step("post-process grade"):
        build_post_process()
    with step("exterior plaza + skyline"):
        build_exterior()
    with step("glass facade"):
        build_facade()
    with step("hall (marble, walnut, coffers, columns, balconies, chandeliers)"):
        build_hall()
    with step("stage + screen + curtains + podium + florals"):
        build_stage()
    with step("dressing (bar islands, cocktail tables, candles)"):
        build_dressing()
    with step("the Echo + cover + turntable"):
        build_car()
    with step("stage lighting"):
        build_stage_lights()
    with step("cast + crowd"):
        build_crowd()
    with step("camera flash lights"):
        build_flash_lights()
    with step("cinematic focus marks"):
        build_focus_marks()
    with step("player start + game mode"):
        build_gameplay()
    with step("invisible walls"):
        build_invisible_walls()
    with step("save level"):
        save_level()
    return ACTORS
