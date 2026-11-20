"""Procedural PBR materials (no textures needed): masters + instances.

Masters (built node-by-node with MaterialEditingLibrary):
    M_ECHO_Surface  - lit opaque. Domain-warped sine 'marble' veins + cloudy tone (no Noise node:
                      its Position pin would not connect on UE 5.8), optional tile grid with grout
                      and per-tile tone, stretched-axis streaks (brushed metal), Fresnel sheen
                      (velvet / satin), roughness variation (puddles), metallic, specular, emissive.
    M_ECHO_CarPaint - clear-coat shading model: metallic base, Fresnel colour flip, glossy coat.
    M_ECHO_Screen   - unlit LED wall: teal-black radial falloff + slow flowing light lines.
    M_ECHO_Glass    - translucent, surface-forward-shaded, Fresnel opacity.
    M_ECHO_Emissive - unlit emissive (crystals, candles with optional flicker, LED strips).
    M_ECHO_Windows  - procedural tower facade with a hashed lit/unlit window grid.
    M_ECHO_SkyDome  - unlit 'Is Sky' gradient for the blue-hour sky dome.
If any graph fails to build, its instances fall back (car paint -> surface, screen -> emissive,
anything else -> engine default) so the level still builds.
"""
import math

import unreal

from . import settings as S
from .util import LC, create_asset, error, log, save_asset, set_prop, warn, enum

MEL = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty

MATS = {}      # instance name -> MaterialInstanceConstant
MASTERS = {}   # key -> master material (or None when its graph failed)
TWO_PI = 2.0 * math.pi


# --------------------------------------------------------------------------- graph helpers
def _expr(mat, cls_name, x, y, **props):
    cls = getattr(unreal, cls_name)
    e = MEL.create_material_expression(mat, cls, x, y)
    if e is None:
        raise RuntimeError("could not create " + cls_name)
    for k, v in props.items():
        set_prop(e, k, v)
    return e


def _vparam(mat, name, rgb, x, y):
    return _expr(mat, "MaterialExpressionVectorParameter", x, y,
                 parameter_name=name, default_value=LC(*rgb))


def _sparam(mat, name, value, x, y):
    return _expr(mat, "MaterialExpressionScalarParameter", x, y,
                 parameter_name=name, default_value=float(value))


def _const(mat, value, x, y):
    return _expr(mat, "MaterialExpressionConstant", x, y, r=float(value))


def _link(a, a_out, b, b_in):
    if not MEL.connect_material_expressions(a, a_out, b, b_in):
        raise RuntimeError("connect failed: %s.%s -> %s.%s" % (a.get_name(), a_out, b.get_name(), b_in))


def _out(e, out_name, prop):
    if not MEL.connect_material_property(e, out_name, prop):
        raise RuntimeError("connect to %s failed" % prop)


def _binop(mat, cls_name, a, b, x, y, a_out="", b_out=""):
    e = _expr(mat, cls_name, x, y)
    _link(a, a_out, e, "A")
    _link(b, b_out, e, "B")
    return e


def _unary(mat, cls_name, src, x, y, src_out="", **props):
    e = _expr(mat, cls_name, x, y, **props)
    _link(src, src_out, e, "")
    return e


# ---- small maths vocabulary built ONLY from node types / pins that connected on 5.8 (A/B, '')
def _mul(m, a, b, x, y):
    return _binop(m, "MaterialExpressionMultiply", a, b, x, y)


def _add(m, a, b, x, y):
    return _binop(m, "MaterialExpressionAdd", a, b, x, y)


def _sub(m, a, b, x, y):
    return _binop(m, "MaterialExpressionSubtract", a, b, x, y)


def _mulc(m, a, c, x, y):
    return _mul(m, a, _const(m, c, x - 120, y + 40), x, y)


def _addc(m, a, c, x, y):
    return _add(m, a, _const(m, c, x - 120, y + 40), x, y)


def _sin(m, a, x, y):
    """Standard sin(a) (UE's Sine node is sin(2*pi*a/Period); Period = 2*pi)."""
    return _unary(m, "MaterialExpressionSine", a, x, y, period=TWO_PI)


def _mask(m, src, ch, x, y):
    flags = {"r": ch == "r", "g": ch == "g", "b": ch == "b", "a": False}
    return _unary(m, "MaterialExpressionComponentMask", src, x, y, **flags)


def _mask_rgb(m, src, x, y):
    return _unary(m, "MaterialExpressionComponentMask", src, x, y, r=True, g=True, b=True, a=False)


def _lerp(m, a, b, alpha, x, y):
    e = _expr(m, "MaterialExpressionLinearInterpolate", x, y)
    _link(a, "", e, "A")
    _link(b, "", e, "B")
    _link(alpha, "", e, "Alpha")
    return e


def _hash2(m, a, b, x, y):
    """frac(sin(a*12.9898 + b*78.233) * 43758.5453): per-cell random 0..1 (GLSL classic)."""
    d = _add(m, _mulc(m, a, 12.9898, x, y), _mulc(m, b, 78.233, x, y + 120), x + 160, y + 60)
    s = _mulc(m, _sin(m, d, x + 300, y + 60), 43758.5453, x + 440, y + 60)
    return _unary(m, "MaterialExpressionFrac", s, x + 580, y + 60)


def _warp_field(m, p, x, y):
    """Shared domain-warped fields from a scaled position p (float3):
    returns (veins 0..1 sharp lines, cloud 0..1 soft tone)."""
    px, py, pz = _mask(m, p, "r", x, y), _mask(m, p, "g", x, y + 100), _mask(m, p, "b", x, y + 200)
    w1 = _sin(m, _add(m, _mulc(m, py, 1.7, x + 150, y + 100), _mulc(m, pz, 0.9, x + 150, y + 200),
                      x + 300, y + 150), x + 420, y + 150)
    w2 = _sin(m, _sub(m, _mulc(m, px, 0.63, x + 150, y), _mulc(m, pz, 1.3, x + 150, y + 300),
                      x + 300, y + 260), x + 420, y + 260)
    warp = _add(m, _mulc(m, w1, 1.6, x + 540, y + 150), _mulc(m, w2, 0.9, x + 540, y + 260), x + 680, y + 200)
    arg = _add(m, _add(m, px, _mulc(m, py, 0.45, x + 540, y + 40), x + 680, y + 40), warp, x + 800, y + 100)
    v = _unary(m, "MaterialExpressionAbs", _sin(m, arg, x + 920, y + 100), x + 1040, y + 100)
    vein = _unary(m, "MaterialExpressionOneMinus", v, x + 1160, y + 100)
    for i in range(3):                                   # ^8 -> thin, crisp veins
        vein = _mul(m, vein, vein, x + 1280 + i * 110, y + 100)
    carg = _add(m, _add(m, _mulc(m, px, 0.37, x + 800, y + 300), _mulc(m, pz, 0.21, x + 800, y + 400),
                        x + 920, y + 340), _mulc(m, warp, 0.5, x + 920, y + 450), x + 1040, y + 380)
    cloud = _addc(m, _mulc(m, _sin(m, carg, x + 1160, y + 380), 0.5, x + 1280, y + 380), 0.5, x + 1400, y + 380)
    return vein, cloud


def noise3(mat, pos, x, y, scale=1.0, levels=4, turbulence=True, fallback=True):
    """Drop-in for a MaterialExpressionNoise fed by `pos`. Tries the Noise node with the pin names
    UE has used ('Position', 'Position (V3)', 'position'); if none connects, returns the
    domain-warped sine 'cloud' field instead (same 0..1 range). Shared helper for other modules."""
    try:
        n = _expr(mat, "MaterialExpressionNoise", x, y, scale=float(scale), levels=int(levels), quality=1,
                  turbulence=bool(turbulence), output_min=0.0, output_max=1.0)
        for pin in ("Position", "Position (V3)", "position", "Position (Vector3)"):
            try:
                if MEL.connect_material_expressions(pos, "", n, pin):
                    return n
            except Exception:
                continue
    except Exception as exc:
        warn("noise node unavailable (%s)" % exc)
    if not fallback:
        raise RuntimeError("Noise.Position would not connect")
    _vein, cloud = _warp_field(mat, _mulc(mat, pos, float(scale), x - 200, y), x, y + 200)
    return cloud


def _new_master(name):
    mat, created = create_asset(name, S.MAT_DIR + "/Masters", unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        # rebuild the graph from scratch on every run so edits here always land
        try:
            MEL.delete_all_material_expressions(mat)
        except Exception as exc:
            warn("could not clear %s: %s" % (name, exc))
    return mat


def _finish(mat):
    MEL.recompile_material(mat)
    save_asset(mat)
    return mat


def _usage(m, skeletal=False, instanced=True):
    if skeletal:
        set_prop(m, "used_with_skeletal_mesh", True, quiet=True)
    if instanced:
        set_prop(m, "used_with_instanced_static_meshes", True, quiet=True)


# --------------------------------------------------------------------------- masters
def build_surface_master():
    m = _new_master("M_ECHO_Surface")
    _usage(m, skeletal=True)
    X = -3200
    # --- pattern space: world position * VeinScale * PatternAxisScale (stretch one axis = brushed)
    wp = _expr(m, "MaterialExpressionWorldPosition", X, 0)
    vscl = _sparam(m, "VeinScale", 0.004, X, 150)
    axis = _mask_rgb(m, _vparam(m, "PatternAxisScale", (1, 1, 1), X, 300), X + 150, 300)
    p = _mul(m, _mul(m, wp, vscl, X + 150, 50), axis, X + 300, 150)
    vein, cloud = _warp_field(m, p, X + 450, 0)
    vstr = _sparam(m, "VeinStrength", 0.0, -1400, 0)
    vmask = _add(m, _mul(m, vein, vstr, -1250, 0), _mul(m, _mulc(m, cloud, 0.25, -1400, 150), vstr, -1250, 150),
                 -1100, 60)
    vmask = _unary(m, "MaterialExpressionSaturate", vmask, -980, 60)

    # --- tiles: grout lines + per-tile tone (TileSize cm, GroutWidth fraction of a tile)
    tsize = _sparam(m, "TileSize", 120.0, X, 700)
    gw = _sparam(m, "GroutWidth", 0.004, X, 850)
    wx = _mask(m, wp, "r", X + 150, 650)
    wy = _mask(m, wp, "g", X + 150, 760)
    tx = _binop(m, "MaterialExpressionDivide", wx, tsize, X + 300, 650)
    ty = _binop(m, "MaterialExpressionDivide", wy, tsize, X + 300, 760)
    half = _sub(m, _const(m, 0.5, X + 300, 900), gw, X + 450, 880)
    mx = _unary(m, "MaterialExpressionRound",
                _add(m, _unary(m, "MaterialExpressionFrac", tx, X + 450, 650), half, X + 600, 650), X + 750, 650)
    my = _unary(m, "MaterialExpressionRound",
                _add(m, _unary(m, "MaterialExpressionFrac", ty, X + 450, 760), half, X + 600, 760), X + 750, 760)
    gstr = _sparam(m, "GroutStrength", 0.0, X + 750, 900)
    grout = _mul(m, _unary(m, "MaterialExpressionOneMinus", _mul(m, mx, my, X + 900, 700), X + 1050, 700),
                 gstr, X + 1200, 760)
    th = _hash2(m, _unary(m, "MaterialExpressionFloor", tx, X + 450, 1000),
                _unary(m, "MaterialExpressionFloor", ty, X + 450, 1100), X + 600, 1000)
    tvar = _sparam(m, "TileVariation", 0.0, X + 1200, 1100)
    tone = _addc(m, _mul(m, _addc(m, th, -0.5, X + 1350, 1000), tvar, X + 1500, 1050), 1.0, X + 1650, 1050)

    # --- base colour: veins -> tile tone -> grout -> Fresnel sheen
    base = _vparam(m, "BaseColor", (0.5, 0.5, 0.5), -1100, -400)
    veinc = _vparam(m, "VeinColor", (0.1, 0.1, 0.1), -1100, -250)
    c = _lerp(m, base, veinc, vmask, -800, -300)
    c = _mul(m, c, tone, -650, -300)
    c = _lerp(m, c, _vparam(m, "GroutColor", (0.02, 0.02, 0.02), -800, -150), grout, -500, -250)
    fres = _expr(m, "MaterialExpressionFresnel", -800, -50, exponent=3.0, base_reflect_fraction=0.0)
    sheen = _unary(m, "MaterialExpressionSaturate", _mul(m, fres, _sparam(m, "SheenStrength", 0.0, -800, 50),
                                                         -650, 0), -500, 0)
    c = _lerp(m, c, _vparam(m, "SheenColor", (0.5, 0.5, 0.5), -650, -150), sheen, -350, -200)
    _out(c, "", MP.MP_BASE_COLOR)

    # --- roughness: base + cloud variation (+ grout is matte)
    rough = _sparam(m, "Roughness", 0.5, -1100, 300)
    rvar = _sparam(m, "RoughnessVariation", 0.0, -1100, 400)
    r = _add(m, rough, _mul(m, cloud, rvar, -950, 400), -800, 350)
    r = _add(m, r, _mulc(m, grout, 0.35, -800, 480), -650, 380)
    _out(_unary(m, "MaterialExpressionSaturate", r, -500, 380), "", MP.MP_ROUGHNESS)

    _out(_sparam(m, "Metallic", 0.0, -500, 550), "", MP.MP_METALLIC)
    _out(_sparam(m, "Specular", 0.5, -500, 650), "", MP.MP_SPECULAR)
    ecol = _vparam(m, "EmissiveColor", (0, 0, 0), -700, 800)
    estr = _sparam(m, "EmissiveStrength", 0.0, -700, 950)
    _out(_mul(m, ecol, estr, -400, 850), "", MP.MP_EMISSIVE_COLOR)
    return _finish(m)


def build_carpaint_master():
    """UE 5.8's MaterialProperty enum has no clear-coat inputs (Substrate era), so the coat is faked:
    default-lit metallic base with a Fresnel colour flip, roughness that tightens toward grazing angles
    (the 'lacquer' sheen), Fresnel-boosted specular, and a faint per-cell metallic flake."""
    m = _new_master("M_ECHO_CarPaint")
    _usage(m)
    fres = _expr(m, "MaterialExpressionFresnel", -1100, 0, exponent=3.0, base_reflect_fraction=0.0)
    base = _vparam(m, "BaseColor", (0.012, 0.014, 0.018), -900, -300)
    flip = _vparam(m, "FlipColor", (0.05, 0.07, 0.10), -900, -150)
    _out(_lerp(m, base, flip, fres, -600, -200), "", MP.MP_BASE_COLOR)
    # flake: hash of a fine world grid -> 0..1 per cell
    wp = _expr(m, "MaterialExpressionWorldPosition", -1600, 600)
    fp = _mul(m, wp, _sparam(m, "FlakeScale", 0.6, -1600, 750), -1450, 650)
    flake = _hash2(m, _unary(m, "MaterialExpressionFloor", _add(m, _mask(m, fp, "r", -1300, 600),
                                                                 _mask(m, fp, "b", -1300, 700), -1180, 640),
                             -1060, 640),
                   _unary(m, "MaterialExpressionFloor", _mask(m, fp, "g", -1300, 800), -1060, 800), -950, 700)
    flake_c = _addc(m, flake, -0.5, -350, 700)
    metal = _add(m, _sparam(m, "Metallic", 0.75, -600, 50),
                 _mul(m, flake_c, _sparam(m, "FlakeMetallic", 0.12, -500, 800), -350, 800), -250, 100)
    _out(_unary(m, "MaterialExpressionSaturate", metal, -150, 100), "", MP.MP_METALLIC)
    rough = _sparam(m, "Roughness", 0.2, -900, 250)
    r_graze = _mul(m, rough, _sparam(m, "GrazingRoughnessScale", 0.35, -900, 350), -750, 300)
    r = _lerp(m, rough, r_graze, fres, -600, 280)
    r = _add(m, r, _mul(m, flake_c, _sparam(m, "FlakeRoughness", 0.05, -500, 900), -350, 900), -250, 300)
    _out(_unary(m, "MaterialExpressionSaturate", r, -150, 300), "", MP.MP_ROUGHNESS)
    spec = _add(m, _sparam(m, "Specular", 0.5, -600, 450),
                _mul(m, fres, _sparam(m, "SpecularBoost", 0.5, -750, 500), -600, 520), -450, 480)
    _out(_unary(m, "MaterialExpressionSaturate", spec, -300, 480), "", MP.MP_SPECULAR)
    ecol = _vparam(m, "EmissiveColor", (0, 0, 0), -600, 1000)
    _out(_mul(m, ecol, _sparam(m, "EmissiveStrength", 0.0, -600, 1150), -400, 1050), "", MP.MP_EMISSIVE_COLOR)
    return _finish(m)


def build_screen_master():
    """LED wall: emissive = (radial falloff edge->centre colour + flowing light lines) * Strength.
    Screen-space comes from world Y/Z so it never depends on the cube's UV layout."""
    m = _new_master("M_ECHO_Screen")
    unlit = enum("MaterialShadingModel", "MSM_UNLIT")
    if unlit is not None:
        set_prop(m, "shading_model", unlit)
    wp = _expr(m, "MaterialExpressionWorldPosition", -2600, 0)
    wy, wz = _mask(m, wp, "g", -2450, -100), _mask(m, wp, "b", -2450, 100)
    # u, v in 0..1 across the screen
    u = _binop(m, "MaterialExpressionDivide", _sub(m, wy, _sparam(m, "YMin", -1600.0, -2450, -250), -2300, -150),
               _sparam(m, "Width", 3200.0, -2300, -300), -2150, -150)
    v = _binop(m, "MaterialExpressionDivide", _sub(m, wz, _sparam(m, "ZMin", 170.0, -2450, 250), -2300, 150),
               _sparam(m, "Height", 900.0, -2300, 300), -2150, 150)
    # radial-ish falloff: sin(pi*u) * sin(pi*v)  (0 at the bezel, 1 in the middle)
    su = _sin(m, _mulc(m, u, math.pi, -2000, -150), -1850, -150)
    sv = _sin(m, _mulc(m, v, math.pi, -2000, 150), -1850, 150)
    fall = _unary(m, "MaterialExpressionSaturate", _mul(m, su, sv, -1700, 0), -1580, 0)
    # push the falloff up-screen a touch (brighter at the top like a sky)
    fall = _mul(m, fall, _addc(m, _mulc(m, v, 0.5, -1580, 150), 0.6, -1450, 150), -1350, 50)
    col = _lerp(m, _vparam(m, "EdgeColor", (0.002, 0.008, 0.010), -1350, -350),
                _vparam(m, "CenterColor", (0.010, 0.060, 0.075), -1350, -200), fall, -1100, -250)
    # flowing lines: (1-|sin(v*F + sin(u*3.1 + t)*0.8 + t*0.3)|)^16
    t = _mul(m, _expr(m, "MaterialExpressionTime", -2300, 500), _sparam(m, "FlowSpeed", 0.15, -2300, 600),
             -2150, 550)
    wob = _mulc(m, _sin(m, _add(m, _mulc(m, u, 3.1, -2000, 450), t, -1850, 500), -1700, 500), 0.8, -1580, 500)
    arg = _add(m, _add(m, _mul(m, v, _sparam(m, "LineFreq", 14.0, -2000, 700), -1850, 650), wob, -1700, 650),
               _mulc(m, t, 0.3, -1700, 780), -1580, 700)
    line = _unary(m, "MaterialExpressionOneMinus",
                  _unary(m, "MaterialExpressionAbs", _sin(m, arg, -1450, 700), -1350, 700), -1250, 700)
    for i in range(4):
        line = _mul(m, line, line, -1150 + i * 100, 700)
    line = _mul(m, _mul(m, line, fall, -700, 650), _sparam(m, "LineStrength", 0.35, -850, 800), -600, 700)
    lc = _mul(m, _vparam(m, "LineColor", (0.25, 0.75, 0.85), -700, 900), line, -500, 800)
    em = _mul(m, _add(m, col, lc, -400, 300), _sparam(m, "Strength", 8.0, -400, 450), -250, 350)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    return _finish(m)


def build_glass_master():
    m = _new_master("M_ECHO_Glass")
    set_prop(m, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    set_prop(m, "translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    set_prop(m, "two_sided", True)
    _usage(m)
    _out(_vparam(m, "Tint", (0.6, 0.7, 0.75), -500, -200), "", MP.MP_BASE_COLOR)
    _out(_sparam(m, "Roughness", 0.03, -500, 0), "", MP.MP_ROUGHNESS)
    _out(_sparam(m, "Specular", 1.0, -500, 100), "", MP.MP_SPECULAR)
    _out(_const(m, 0.0, -500, 200), "", MP.MP_METALLIC)
    op = _sparam(m, "Opacity", 0.1, -800, 300)
    edge = _sparam(m, "EdgeOpacity", 0.55, -800, 400)
    fres = _expr(m, "MaterialExpressionFresnel", -800, 500, exponent=4.0, base_reflect_fraction=0.04)
    _out(_lerp(m, op, edge, fres, -500, 400), "", MP.MP_OPACITY)
    return _finish(m)


def build_emissive_master():
    m = _new_master("M_ECHO_Emissive")
    unlit = enum("MaterialShadingModel", "MSM_UNLIT")
    if unlit is not None:
        set_prop(m, "shading_model", unlit)
    _usage(m, skeletal=True)
    col = _vparam(m, "Color", (1, 0.6, 0.3), -600, 0)
    st = _sparam(m, "Strength", 10.0, -600, 200)
    em = _mul(m, col, st, -300, 100)
    # optional flicker (candles): * (1 + FlickerAmount * sin(t*FlickerSpeed + (x+y)*0.05))
    try:
        wp = _expr(m, "MaterialExpressionWorldPosition", -1300, 400)
        ph = _mulc(m, _add(m, _mask(m, wp, "r", -1150, 350), _mask(m, wp, "g", -1150, 450), -1000, 400), 0.05,
                   -880, 400)
        t = _mul(m, _expr(m, "MaterialExpressionTime", -1150, 600), _sparam(m, "FlickerSpeed", 9.0, -1150, 700),
                 -1000, 620)
        s1 = _sin(m, _add(m, t, ph, -760, 500), -650, 500)
        s2 = _sin(m, _add(m, _mulc(m, t, 2.37, -760, 650), ph, -650, 650), -550, 650)
        wob = _mul(m, _add(m, s1, _mulc(m, s2, 0.5, -450, 650), -350, 580),
                   _sparam(m, "FlickerAmount", 0.0, -450, 750), -250, 600)
        em = _mul(m, em, _addc(m, wob, 1.0, -150, 500), -50, 300)
    except Exception as exc:
        warn("emissive flicker branch skipped: %s" % exc)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    return _finish(m)


def build_windows_master():
    m = _new_master("M_ECHO_Windows")
    _usage(m)
    wp = _expr(m, "MaterialExpressionWorldPosition", -1800, 0)
    z = _mask(m, wp, "b", -1600, -100)
    xy = _add(m, _mask(m, wp, "r", -1600, 100), _mask(m, wp, "g", -1600, 200), -1400, 150)
    fh = _sparam(m, "FloorHeight", 380.0, -1600, -250)
    bw = _sparam(m, "BayWidth", 260.0, -1600, 350)
    zf = _binop(m, "MaterialExpressionDivide", z, fh, -1300, -100)
    xf = _binop(m, "MaterialExpressionDivide", xy, bw, -1300, 150)
    # window mask: round(frac(z)+0.2) * round(frac(xy)+0.15)
    zr = _unary(m, "MaterialExpressionRound",
                _addc(m, _unary(m, "MaterialExpressionFrac", zf, -1150, -100), 0.2, -1000, -100), -850, -100)
    xr = _unary(m, "MaterialExpressionRound",
                _addc(m, _unary(m, "MaterialExpressionFrac", xf, -1150, 150), 0.15, -1000, 150), -850, 150)
    mask = _mul(m, zr, xr, -700, 0)
    # per-window random on/off: hash of the integer cell id (replaces the Noise node)
    rnd = _hash2(m, _unary(m, "MaterialExpressionFloor", xf, -1150, 400),
                 _unary(m, "MaterialExpressionFloor", zf, -1150, 500), -1000, 450)
    lit_bias = _sparam(m, "LitBias", -0.05, -750, 650)
    lit = _unary(m, "MaterialExpressionRound", _add(m, rnd, lit_bias, -350, 500), -250, 500)
    lit = _unary(m, "MaterialExpressionSaturate", lit, -150, 500)
    on = _mul(m, mask, lit, -100, 200)
    # a little per-window brightness variation so the grid doesn't read as CG
    var = _addc(m, _mulc(m, rnd, 0.8, -350, 650), 0.6, -250, 650)
    wcol = _vparam(m, "WindowColor", (1.0, 0.7, 0.45), -500, 800)
    wstr = _sparam(m, "WindowStrength", 15.0, -500, 950)
    em = _mul(m, _mul(m, _mul(m, wcol, wstr, -300, 850), on, -150, 600), var, -50, 650)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    _out(_vparam(m, "FacadeColor", (0.02, 0.025, 0.03), -300, -300), "", MP.MP_BASE_COLOR)
    _out(_sparam(m, "Roughness", 0.2, -300, -150), "", MP.MP_ROUGHNESS)
    _out(_sparam(m, "Metallic", 0.6, -300, -50), "", MP.MP_METALLIC)
    return _finish(m)


def build_sky_master():
    m = _new_master("M_ECHO_SkyDome")
    unlit = enum("MaterialShadingModel", "MSM_UNLIT")
    if unlit is not None:
        set_prop(m, "shading_model", unlit)
    set_prop(m, "two_sided", True)
    set_prop(m, "is_sky", True, quiet=True)   # lets a real-time-capture SkyLight see it
    nrm = _expr(m, "MaterialExpressionVertexNormalWS", -900, 0)
    nz = _mask(m, nrm, "b", -750, 0)
    k = _unary(m, "MaterialExpressionSaturate", _mulc(m, nz, 1.6, -600, 0), -450, 0)
    lerp = _lerp(m, _vparam(m, "Horizon", S.SKY_HORIZON, -600, -300), _vparam(m, "Zenith", S.SKY_ZENITH, -600, -150),
                 k, -300, -100)
    _out(_mul(m, lerp, _sparam(m, "Strength", S.SKY_STRENGTH, -300, 100), -150, 0), "", MP.MP_EMISSIVE_COLOR)
    return _finish(m)


# --------------------------------------------------------------------------- instances
def _mi(name, parent, scalars=None, vectors=None):
    mi, _ = create_asset(name, S.MAT_DIR, unreal.MaterialInstanceConstant,
                         unreal.MaterialInstanceConstantFactoryNew())
    if parent is not None:
        MEL.set_material_instance_parent(mi, parent)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, LC(*v))
    try:
        MEL.update_material_instance(mi)
    except Exception:
        pass
    save_asset(mi)
    MATS[name] = mi
    return mi


def _surf(parent, name, base, rough, metal=0.0, spec=0.5, vein=None, vstr=0.0, vscale=0.004,
          rvar=0.0, emis=None, estr=0.0, **extra):
    """Surface instance. Optional keyword extras (all M_ECHO_Surface params):
    tile=cm, grout=strength, grout_w=fraction, grout_col=rgb, tile_var=0..1,
    sheen=strength, sheen_col=rgb, axis=(sx,sy,sz)."""
    sc = {"Roughness": rough, "Metallic": metal, "Specular": spec, "VeinStrength": vstr,
          "VeinScale": vscale, "RoughnessVariation": rvar, "EmissiveStrength": estr}
    vc = {"BaseColor": base, "VeinColor": vein or base}
    if emis:
        vc["EmissiveColor"] = emis
    if "tile" in extra:
        sc["TileSize"] = extra["tile"]
        sc["GroutStrength"] = extra.get("grout", 1.0)
        sc["GroutWidth"] = extra.get("grout_w", 0.004)
        sc["TileVariation"] = extra.get("tile_var", 0.0)
        vc["GroutColor"] = extra.get("grout_col", (0.02, 0.02, 0.02))
    if "sheen" in extra:
        sc["SheenStrength"] = extra["sheen"]
        vc["SheenColor"] = extra.get("sheen_col", (0.5, 0.5, 0.5))
    if "axis" in extra:
        vc["PatternAxisScale"] = extra["axis"]
    return _mi(name, parent, sc, vc)


def _paint(name, base, flip, rough=0.2, metal=0.75, spec_boost=0.5, flake=0.12):
    """Car paint on the faux-lacquer master; falls back to a glossy surface instance."""
    cp = MASTERS.get("carpaint")
    if cp is not None:
        return _mi(name, cp, {"Metallic": metal, "Roughness": rough, "SpecularBoost": spec_boost,
                              "FlakeMetallic": flake, "FlakeRoughness": flake * 0.4},
                   {"BaseColor": base, "FlipColor": flip})
    return _surf(MASTERS.get("surface"), name, base, min(rough, 0.12), metal=metal, spec=0.6,
                 sheen=0.6, sheen_col=flip)


def build_all():
    for key, fn in (("surface", build_surface_master), ("carpaint", build_carpaint_master),
                    ("screen", build_screen_master), ("glass", build_glass_master),
                    ("emissive", build_emissive_master), ("windows", build_windows_master),
                    ("sky", build_sky_master)):
        try:
            MASTERS[key] = fn()
            log("master material ok: " + key)
        except Exception as exc:  # fall back so the level still builds
            error("master material '%s' failed (%s) - instances will fall back" % (key, exc))
            MASTERS[key] = None

    s, g, e, w = MASTERS["surface"], MASTERS["glass"], MASTERS["emissive"], MASTERS["windows"]

    # ---- hall surfaces
    # polished Nero Marquina floor: near-black, fine warm-white veins, 120 cm tiles, mirror gloss
    _surf(s, "MI_Floor_BlackMarble", (0.010, 0.010, 0.012), 0.018, spec=0.85, vein=(0.32, 0.30, 0.27),
          vstr=0.45, vscale=0.0035, rvar=0.02, tile=120.0, grout=0.45, grout_w=0.002,
          grout_col=(0.028, 0.025, 0.022), tile_var=0.2)
    _surf(s, "MI_Marble_White", (0.70, 0.67, 0.62), 0.14, spec=0.55, vein=(0.20, 0.19, 0.19),
          vstr=0.65, vscale=0.006, rvar=0.06)
    _surf(s, "MI_Wall_Walnut", (0.050, 0.026, 0.014), 0.36, vein=(0.016, 0.008, 0.005), vstr=0.8,
          vscale=0.035, rvar=0.12, axis=(1.0, 1.0, 0.06))
    _surf(s, "MI_Ceiling_Dark", (0.014, 0.014, 0.017), 0.7)
    _surf(s, "MI_Gold", (1.0, 0.74, 0.32), 0.24, metal=1.0, vstr=0.0, rvar=0.08, vscale=0.4,
          axis=(0.03, 1.0, 1.0))
    _surf(s, "MI_Chrome", (0.9, 0.9, 0.92), 0.06, metal=1.0)
    _surf(s, "MI_DarkMetal", (0.025, 0.025, 0.03), 0.3, metal=1.0, rvar=0.08, vscale=0.5, axis=(0.02, 1, 1))
    _surf(s, "MI_Podium_Gunmetal", (0.035, 0.036, 0.04), 0.34, metal=1.0, rvar=0.06, vscale=0.6,
          axis=(0.015, 1.0, 1.0))
    _surf(s, "MI_Fabric_RiversSuit", (0.018, 0.018, 0.021), 0.66, spec=0.3, sheen=0.12,
          sheen_col=(0.12, 0.12, 0.135))
    _surf(s, "MI_Fabric_Trouser", (0.014, 0.014, 0.016), 0.7, spec=0.28, sheen=0.1,
          sheen_col=(0.10, 0.10, 0.11))
    _surf(s, "MI_Skin_Dark", (0.06, 0.04, 0.032), 0.5, spec=0.35, sheen=0.15, sheen_col=(0.2, 0.14, 0.12))
    _surf(s, "MI_Turntable_Top", (0.004, 0.004, 0.005), 0.08, spec=0.55, rvar=0.02)
    _surf(s, "MI_Rim_Gunmetal", (0.022, 0.023, 0.026), 0.32, metal=1.0)
    _surf(s, "MI_BrushedSteel", (0.55, 0.55, 0.57), 0.26, metal=1.0, rvar=0.14, vscale=0.6,
          axis=(0.015, 1.0, 1.0))
    _surf(s, "MI_StageGloss", (0.005, 0.005, 0.007), 0.06, spec=0.6, rvar=0.03)
    _surf(s, "MI_Tablecloth", (0.62, 0.60, 0.56), 0.85, sheen=0.25, sheen_col=(0.9, 0.88, 0.84))
    _surf(s, "MI_Tablecloth_Black", (0.012, 0.012, 0.014), 0.55, spec=0.45, sheen=0.5, sheen_col=(0.12, 0.11, 0.10))
    _surf(s, "MI_RedCarpet", (0.16, 0.005, 0.01), 0.9, spec=0.3, sheen=0.4, sheen_col=(0.45, 0.06, 0.07))
    _surf(s, "MI_VelvetRope", (0.12, 0.0, 0.01), 0.7, sheen=0.7, sheen_col=(0.5, 0.05, 0.07))
    _surf(s, "MI_Velvet_Curtain", (0.045, 0.003, 0.007), 0.82, spec=0.35, sheen=0.85,
          sheen_col=(0.42, 0.07, 0.09), vstr=0.15, vein=(0.02, 0.0, 0.003), vscale=0.02, axis=(1, 1, 0.05))
    _surf(s, "MI_Leaf", (0.012, 0.05, 0.02), 0.45, sheen=0.2, sheen_col=(0.1, 0.2, 0.1))
    _surf(s, "MI_Flower_White", (0.75, 0.72, 0.68), 0.6, sheen=0.4, sheen_col=(1.0, 0.97, 0.94))
    _surf(s, "MI_Flower_Red", (0.35, 0.01, 0.025), 0.55, sheen=0.5, sheen_col=(0.7, 0.1, 0.12))
    _surf(s, "MI_Bottle_Amber", (0.12, 0.045, 0.01), 0.05, spec=0.9)
    _surf(s, "MI_Bottle_Green", (0.01, 0.04, 0.02), 0.05, spec=0.9)
    # ---- people (dress the mannequins for black tie; sheen sells fabric on a faceless mannequin)
    _surf(s, "MI_Fabric_Tux", (0.008, 0.008, 0.010), 0.5, spec=0.4, sheen=0.35, sheen_col=(0.10, 0.10, 0.12))
    _surf(s, "MI_Fabric_Charcoal", (0.035, 0.035, 0.04), 0.55, spec=0.4, sheen=0.35, sheen_col=(0.16, 0.16, 0.18))
    _surf(s, "MI_Fabric_Navy", (0.008, 0.012, 0.03), 0.5, spec=0.4, sheen=0.35, sheen_col=(0.08, 0.10, 0.18))
    _surf(s, "MI_Fabric_Satin", (0.004, 0.004, 0.005), 0.18, spec=0.6, sheen=0.25, sheen_col=(0.2, 0.2, 0.22))
    _surf(s, "MI_Gown_Red", (0.048, 0.006, 0.016), 0.22, sheen=0.75, sheen_col=(0.30, 0.06, 0.10))
    _surf(s, "MI_Gown_Gold", (0.50, 0.34, 0.11), 0.3, metal=0.5, sheen=0.4, sheen_col=(1.0, 0.8, 0.45))
    _surf(s, "MI_Gown_Emerald", (0.006, 0.09, 0.045), 0.3, sheen=0.6, sheen_col=(0.15, 0.6, 0.35))
    _surf(s, "MI_Gown_Midnight", (0.006, 0.012, 0.06), 0.3, sheen=0.6, sheen_col=(0.2, 0.3, 0.7))
    _surf(s, "MI_Gown_Silver", (0.45, 0.45, 0.47), 0.25, metal=0.6, sheen=0.4, sheen_col=(0.9, 0.9, 0.95))
    _surf(s, "MI_Gown_Black", (0.006, 0.006, 0.007), 0.3, sheen=0.5, sheen_col=(0.22, 0.2, 0.2))
    # ---- car
    _surf(s, "MI_CarCover_Satin", (0.022, 0.022, 0.028), 0.38, spec=0.5, sheen=0.75, sheen_col=(0.35, 0.38, 0.45),
          vstr=0.12, vein=(0.01, 0.01, 0.012), vscale=0.02)
    _paint("MI_CarPaint_Pearl", (0.010, 0.012, 0.016), (0.07, 0.10, 0.14), rough=0.18)   # 'Lakemont Midnight'
    _paint("MI_CarPaint_Trim", (0.004, 0.004, 0.005), (0.02, 0.02, 0.025), rough=0.45, metal=0.3,
           spec_boost=0.2, flake=0.0)
    _surf(s, "MI_CarGlass_Dark", (0.003, 0.003, 0.005), 0.015, spec=1.0, sheen=0.3, sheen_col=(0.05, 0.07, 0.1))
    _surf(s, "MI_Tire", (0.008, 0.008, 0.008), 0.9)
    # ---- exterior (wet: base rough with puddles carved out by negative variation)
    _surf(s, "MI_Asphalt_Wet", (0.03, 0.03, 0.032), 0.55, vein=(0.012, 0.012, 0.013), vstr=0.5,
          vscale=0.01, rvar=-0.5)
    _surf(s, "MI_Concrete_Wet", (0.17, 0.17, 0.18), 0.5, vein=(0.08, 0.08, 0.085), vstr=0.4,
          vscale=0.006, rvar=-0.42, tile=150.0, grout=0.6, grout_col=(0.05, 0.05, 0.05), tile_var=0.2)
    _surf(s, "MI_Building_Stone", (0.09, 0.085, 0.08), 0.6, vein=(0.05, 0.05, 0.05), vstr=0.3, vscale=0.01)

    # ---- emissives
    _mi("MI_E_Warm", e, {"Strength": S.E_WARM}, {"Color": (1.0, 0.62, 0.32)})
    _mi("MI_E_Candle", e, {"Strength": S.E_CANDLE, "FlickerAmount": 0.18, "FlickerSpeed": 11.0},
        {"Color": (1.0, 0.48, 0.16)})
    _mi("MI_E_Crystal", e, {"Strength": S.E_CRYSTAL}, {"Color": (1.0, 0.84, 0.62)})
    _mi("MI_E_LEDWall", e, {"Strength": getattr(S, "E_LED_WALL", 20.0)}, {"Color": (0.012, 0.07, 0.085)})
    _mi("MI_E_CoolStrip", e, {"Strength": S.E_COOL_STRIP}, {"Color": (0.35, 0.6, 1.0)})
    _mi("MI_E_CoolStrip_Dim", e, {"Strength": S.E_COOL_STRIP * 0.25}, {"Color": (0.35, 0.6, 1.0)})
    _mi("MI_E_CarLight", e, {"Strength": S.E_CAR_LIGHT}, {"Color": (0.8, 0.9, 1.0)})
    _mi("MI_E_CarTail", e, {"Strength": S.E_CAR_LIGHT * 0.5}, {"Color": (1.0, 0.02, 0.02)})
    _mi("MI_E_WheelGlow", e, {"Strength": getattr(S, "E_RIM_ACCENT", 6.0)}, {"Color": (0.55, 0.72, 0.9)})
    _mi("MI_E_RimAccent", e, {"Strength": getattr(S, "E_RIM_ACCENT", 6.0)}, {"Color": (0.7, 0.82, 1.0)})
    _mi("MI_E_LampShade", e, {"Strength": getattr(S, "E_LAMP_SHADE", 28.0)}, {"Color": (1.0, 0.72, 0.42)})
    _mi("MI_E_BarShelf", e, {"Strength": S.E_WARM * 0.8}, {"Color": (1.0, 0.66, 0.36)})
    _mi("MI_E_Street", e, {"Strength": S.E_STREET}, {"Color": (1.0, 0.5, 0.16)})
    _mi("MI_E_Neon", e, {"Strength": 30.0}, {"Color": (0.1, 0.8, 1.0)})
    # LED wall: branded teal-black screen (falls back to the plain emissive above)
    scr = MASTERS.get("screen")
    if scr is not None:
        _mi("MI_LED_Screen", scr, {"Strength": getattr(S, "E_LED_SCREEN", 8.0), "LineStrength": 0.35,
                                   "LineFreq": 14.0, "FlowSpeed": 0.12,
                                   "YMin": -1600.0, "Width": 3200.0, "ZMin": S.STAGE_H + 60.0, "Height": 900.0},
            {"EdgeColor": (0.002, 0.007, 0.009), "CenterColor": (0.010, 0.055, 0.07),
             "LineColor": (0.25, 0.75, 0.85)})
    else:
        MATS["MI_LED_Screen"] = MATS.get("MI_E_LEDWall")

    # ---- glass
    _mi("MI_Glass_Facade", g, {"Opacity": 0.08, "EdgeOpacity": 0.5, "Roughness": 0.02},
        {"Tint": (0.55, 0.66, 0.72)})
    _mi("MI_Glass_Podium", g, {"Opacity": 0.18, "EdgeOpacity": 0.6, "Roughness": 0.04},
        {"Tint": (0.8, 0.86, 0.92)})
    _mi("MI_Glass_Smoked", g, {"Opacity": 0.6, "EdgeOpacity": 0.9, "Roughness": 0.05},
        {"Tint": (0.02, 0.025, 0.03)})
    _mi("MI_Glass_Champagne", g, {"Opacity": 0.25, "EdgeOpacity": 0.8, "Roughness": 0.02},
        {"Tint": (1.0, 0.86, 0.55)})

    # ---- city
    _mi("MI_Tower_A", w, {"WindowStrength": S.E_WINDOWS, "LitBias": -0.05, "FloorHeight": 380, "BayWidth": 260},
        {"WindowColor": (1.0, 0.72, 0.45), "FacadeColor": (0.02, 0.025, 0.03)})
    _mi("MI_Tower_B", w, {"WindowStrength": S.E_WINDOWS * 0.8, "LitBias": -0.2, "FloorHeight": 420, "BayWidth": 180},
        {"WindowColor": (0.75, 0.85, 1.0), "FacadeColor": (0.03, 0.03, 0.035)})
    _mi("MI_SkyDome", MASTERS["sky"], {"Strength": S.SKY_STRENGTH},
        {"Horizon": S.SKY_HORIZON, "Zenith": S.SKY_ZENITH})
    log("materials ready: %d instances" % len(MATS))
    return MATS


# --------------------------------------------------------------------------- mannequin tints (fallback outfits)
_TINT_HINTS = ("tint", "color", "colour", "albedo", "base")


def mannequin_tint(name, parent_path, rgb):
    """MI parented to a template mannequin material with its colour-ish vector params set to rgb.
    Returns None if the parent is missing or exposes no colour parameter."""
    if name in MATS and MATS[name] is not None:
        return MATS[name]
    if not unreal.EditorAssetLibrary.does_asset_exist(parent_path):
        return None
    parent = unreal.EditorAssetLibrary.load_asset(parent_path)
    try:
        names = [str(n) for n in (MEL.get_vector_parameter_names(parent) or [])]
    except Exception as exc:
        warn("get_vector_parameter_names(%s): %s" % (parent_path, exc))
        return None
    hits = [n for n in names if any(h in n.lower() for h in _TINT_HINTS)]
    if not hits:
        log("mannequin material %s has no colour params (%s)" % (parent_path, names))
        return None
    mi = _mi(name, parent, None, dict((n, rgb) for n in hits))
    log("mannequin tint %s via %s" % (name, hits))
    return mi


def load_master(name):
    path = S.MAT_DIR + "/Masters/" + name
    try:
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            return unreal.EditorAssetLibrary.load_asset(path)
    except Exception as exc:
        warn("load master %s: %s" % (name, exc))
    return None


def get(name):
    """Look up an instance built this run (or load it from disk on a partial re-run).
    settings.MATERIAL_OVERRIDES wins if the override asset exists (Megascans / Fab upgrades)."""
    ov = S.MATERIAL_OVERRIDES.get(name)
    if ov:
        if unreal.EditorAssetLibrary.does_asset_exist(ov):
            return unreal.EditorAssetLibrary.load_asset(ov)
        warn("material override for %s not found: %s" % (name, ov))
    if name not in MATS:
        path = S.MAT_DIR + "/" + name
        obj = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        MATS[name] = obj
    return MATS[name]
