"""Ripple materials: the Material Parameter Collection + ripple-aware masters + Riverside instances.

MPC_Ripple (the one global the whole ripple reads; Sequencer keys it):
    Center (vector, world cm)   Radius (cm)   Enable (0/1)   EdgeWidth   TearAmp   TearScale
    EmberStrength   ShellFade   + EmberColor (vector)
Masters (built like materials.py, node by node):
    M_ECHO_RippleSurface  - M_ECHO_Surface + MF_RippleReveal logic inlined: masked by a world-space
                            sphere. Side=+1 -> visible INSIDE the wave (new state, B),
                            Side=-1 -> visible OUTSIDE (old state, A). The edge chars to black,
                            then burns as an emissive ember band, then tears away (noisy radius).
    M_ECHO_RippleEmissive - unlit version for neon, lit windows, the sky domes.
    M_ECHO_RippleShell    - additive Fresnel bubble: the visible wavefront.
Enable=0 disables the mask entirely (both states visible) so a failed Sequencer MPC track can
never leave the busy state invisible; ripple.py flips the MPC default to match what it built.
"""
import math

import unreal

from . import materials as M
from . import settings as S
from .util import LC, create_asset, enum, error, log, save_asset, set_prop, warn

MEL = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
MATS = {}
STATE = {"mpc": None, "surface_ok": False, "emissive_ok": False}

SCALARS = {   # name: default
    "Radius": 0.0, "Enable": 1.0, "EdgeWidth": S.RIPPLE_EDGE_WIDTH, "TearAmp": S.RIPPLE_TEAR_AMP,
    "TearScale": S.RIPPLE_TEAR_SCALE, "EmberStrength": S.RIPPLE_EMBER_STRENGTH, "ShellFade": 1.0,
    "RimStrength": S.RIPPLE_RIM_STRENGTH, "SkyRadius": 0.0,
}
VECTORS = {"Center": S.RIPPLE_CENTER + (0.0,), "EmberColor": S.RIPPLE_EMBER_COLOR + (1.0,),
           "RimColor": S.RIPPLE_RIM_COLOR + (1.0,)}


# --------------------------------------------------------------------------- MPC
def build_mpc():
    mpc, _ = create_asset(S.RIPPLE_MPC_NAME, S.RIPPLE_MAT_DIR, unreal.MaterialParameterCollection,
                          unreal.MaterialParameterCollectionFactoryNew())
    sc = []
    for n, v in SCALARS.items():
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", n)
        p.set_editor_property("default_value", float(v))
        sc.append(p)
    vc = []
    for n, v in VECTORS.items():
        p = unreal.CollectionVectorParameter()
        p.set_editor_property("parameter_name", n)
        p.set_editor_property("default_value", LC(*v))
        vc.append(p)
    # only rewrite the arrays when the names changed (keeps parameter GUIDs stable on re-runs,
    # so materials compiled last time keep resolving)
    try:
        have = [str(n) for n in mpc.get_scalar_parameter_names()] + [str(n) for n in mpc.get_vector_parameter_names()]
    except Exception:
        have = []
    if sorted(have) != sorted(list(SCALARS) + list(VECTORS)):
        mpc.set_editor_property("scalar_parameters", sc)
        mpc.set_editor_property("vector_parameters", vc)
    else:
        set_mpc_default(mpc, SCALARS)
        set_mpc_vector_default(mpc, VECTORS)
    save_asset(mpc)
    STATE["mpc"] = mpc
    return mpc


def _rewrite_params(mpc, attr, values, is_vector):
    arr = list(mpc.get_editor_property(attr))
    for p in arr:
        n = str(p.get_editor_property("parameter_name"))
        if n in values:
            v = values[n]
            p.set_editor_property("default_value", LC(*v) if is_vector else float(v))
    mpc.set_editor_property(attr, arr)


def set_mpc_default(mpc, values):
    """Change scalar defaults in place (same GUIDs). values: name -> float."""
    try:
        _rewrite_params(mpc, "scalar_parameters", values, False)
    except Exception as exc:
        warn("MPC default update failed: %s" % exc)


def set_mpc_vector_default(mpc, values):
    try:
        _rewrite_params(mpc, "vector_parameters", values, True)
    except Exception as exc:
        warn("MPC vector default update failed: %s" % exc)


# --------------------------------------------------------------------------- graph helpers
_expr, _vparam, _sparam, _const = M._expr, M._vparam, M._sparam, M._const
_link, _out, _binop, _unary = M._link, M._out, M._binop, M._unary


def _cp(mat, name, x, y):
    e = _expr(mat, "MaterialExpressionCollectionParameter", x, y)
    e.set_editor_property("collection", STATE["mpc"])     # collection first: name lookup needs it
    e.set_editor_property("parameter_name", name)
    return e


def _rgb(mat, src, x, y):
    return _unary(mat, "MaterialExpressionComponentMask", src, x, y, r=True, g=True, b=True, a=False)


def _ripple_terms(m, x0=-2600, y0=1200):
    """Returns (opacity_mask_expr, band_expr). band = 1 at the burning edge, 0 away from it."""
    wp = _expr(m, "MaterialExpressionWorldPosition", x0, y0)
    center = _rgb(m, _cp(m, "Center", x0, y0 + 150), x0 + 200, y0 + 150)
    dist = _binop(m, "MaterialExpressionDistance", wp, center, x0 + 400, y0 + 50)
    tscale = _cp(m, "TearScale", x0, y0 + 300)
    npos = _binop(m, "MaterialExpressionMultiply", wp, tscale, x0 + 200, y0 + 300)
    # materials.noise3: Noise node if its Position pin connects on this engine, else a math-only
    # warped-sine field (UE 5.8.4 refused Multiply -> Noise.Position in the gala build). Range 0..1.
    noise01 = M.noise3(m, npos, x0 + 400, y0 + 300, scale=1.0, levels=4, turbulence=False)
    noise = _binop(m, "MaterialExpressionSubtract", noise01, _const(m, 0.5, x0 + 400, y0 + 420), x0 + 500, y0 + 330)
    tear = _binop(m, "MaterialExpressionMultiply", noise, _cp(m, "TearAmp", x0 + 400, y0 + 450), x0 + 600, y0 + 350)
    d2 = _binop(m, "MaterialExpressionAdd", dist, tear, x0 + 800, y0 + 100)
    radius = _cp(m, "Radius", x0 + 800, y0 + 250)
    inside = _binop(m, "MaterialExpressionSubtract", radius, d2, x0 + 1000, y0 + 150)       # >0 inside the wave
    side = _sparam(m, "Side", 1.0, x0 + 1000, y0 + 300)
    signed = _binop(m, "MaterialExpressionMultiply", inside, side, x0 + 1200, y0 + 200)      # >0 = visible
    enable = _cp(m, "Enable", x0 + 1200, y0 + 400)
    off = _binop(m, "MaterialExpressionMultiply", _unary(m, "MaterialExpressionOneMinus", enable, x0 + 1400, y0 + 400),
                 _const(m, 100000.0, x0 + 1400, y0 + 500), x0 + 1600, y0 + 420)
    om = _binop(m, "MaterialExpressionAdd", _binop(m, "MaterialExpressionAdd", signed, _const(m, 0.5, x0 + 1400, y0 + 250),
                                                    x0 + 1600, y0 + 220), off, x0 + 1800, y0 + 300)
    om = _unary(m, "MaterialExpressionSaturate", om, x0 + 2000, y0 + 300)
    # ember band: 1 at the visible edge, cubic falloff over EdgeWidth, x Enable
    ratio = _binop(m, "MaterialExpressionDivide", signed, _cp(m, "EdgeWidth", x0 + 1200, y0 + 600), x0 + 1400, y0 + 620)
    band = _unary(m, "MaterialExpressionSaturate", _unary(m, "MaterialExpressionOneMinus", ratio, x0 + 1600, y0 + 620),
                  x0 + 1800, y0 + 620)
    band3 = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", band, band, x0 + 2000, y0 + 620),
                   band, x0 + 2200, y0 + 620)
    aside = _unary(m, "MaterialExpressionAbs", side, x0 + 2200, y0 + 800)    # Side 0 = rim only, never chars
    en_s = _binop(m, "MaterialExpressionMultiply", enable, aside, x0 + 2300, y0 + 800)
    band3 = _binop(m, "MaterialExpressionMultiply", band3, en_s, x0 + 2400, y0 + 620)
    band1 = _binop(m, "MaterialExpressionMultiply", band, en_s, x0 + 2400, y0 + 760)
    # the rim: a shimmering line exactly on the wave radius. It uses a *reduced* tear so the
    # glowing ring stays one coherent shell; the opacity mask still gets the full paper-tear.
    d2_rim = _binop(m, "MaterialExpressionAdd", dist, M._mulc(m, tear, 0.28, x0 + 1000, y0 + 850),
                    x0 + 1100, y0 + 850)
    inside_rim = _binop(m, "MaterialExpressionSubtract", radius, d2_rim, x0 + 1250, y0 + 850)
    absd = _unary(m, "MaterialExpressionAbs", inside_rim, x0 + 1200, y0 + 900)
    width = _binop(m, "MaterialExpressionAdd", M._mulc(m, _cp(m, "EdgeWidth", x0 + 800, y0 + 950), 0.9, x0 + 1000, y0 + 950),
                   M._mulc(m, dist, S.RIPPLE_RIM_ANGULAR, x0 + 1000, y0 + 1050), x0 + 1200, y0 + 1000)
    r = _unary(m, "MaterialExpressionSaturate", _unary(m, "MaterialExpressionOneMinus",
               _binop(m, "MaterialExpressionDivide", absd, width, x0 + 1400, y0 + 950), x0 + 1600, y0 + 950),
               x0 + 1800, y0 + 950)
    r2 = _binop(m, "MaterialExpressionMultiply", r, r, x0 + 2000, y0 + 950)
    r4 = _binop(m, "MaterialExpressionMultiply", r2, r2, x0 + 2200, y0 + 950)
    t = _expr(m, "MaterialExpressionTime", x0 + 1400, y0 + 1150)
    ph = _binop(m, "MaterialExpressionAdd", M._mulc(m, t, 31.0, x0 + 1600, y0 + 1150),
                M._mulc(m, dist, 0.045, x0 + 1600, y0 + 1250), x0 + 1800, y0 + 1200)
    shimmer = M._addc(m, M._mulc(m, M._sin(m, ph, x0 + 2000, y0 + 1200), 0.35, x0 + 2150, y0 + 1200), 0.65,
                      x0 + 2300, y0 + 1200)
    rim = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", r4, shimmer, x0 + 2400, y0 + 1000),
                 enable, x0 + 2600, y0 + 1000)
    col = _rgb(m, _cp(m, "RimColor", x0 + 2400, y0 + 1300), x0 + 2600, y0 + 1300)
    k = _binop(m, "MaterialExpressionMultiply", rim, _cp(m, "RimStrength", x0 + 2400, y0 + 1450), x0 + 2800, y0 + 1100)
    STATE["_rim"] = _binop(m, "MaterialExpressionMultiply", col, k, x0 + 3000, y0 + 1200)
    return om, band3, band1


def _rim_emissive(m):
    """Emissive of the rim built by the last _ripple_terms call on this material."""
    return STATE.pop("_rim")


def _ember(m, band3, x, y):
    col = _rgb(m, _cp(m, "EmberColor", x - 400, y), x - 200, y)
    k = _binop(m, "MaterialExpressionMultiply", band3, _cp(m, "EmberStrength", x - 400, y + 150), x - 200, y + 120)
    return _binop(m, "MaterialExpressionMultiply", col, k, x, y + 50)


def _masked(m):
    set_prop(m, "blend_mode", unreal.BlendMode.BLEND_MASKED)
    set_prop(m, "used_with_skeletal_mesh", True, quiet=True)
    set_prop(m, "used_with_instanced_static_meshes", True, quiet=True)


# --------------------------------------------------------------------------- masters
def build_surface_master():
    m = M._new_master("M_ECHO_RippleSurface")
    _masked(m)
    base = _vparam(m, "BaseColor", (0.5, 0.5, 0.5), -1100, -300)
    vein = _vparam(m, "VeinColor", (0.1, 0.1, 0.1), -1100, -100)
    vstr = _sparam(m, "VeinStrength", 0.0, -1100, 100)
    vscl = _sparam(m, "VeinScale", 0.004, -1600, 0)
    wp = _expr(m, "MaterialExpressionWorldPosition", -1600, -200)
    pos = _binop(m, "MaterialExpressionMultiply", wp, vscl, -1400, -100)
    noise = M.noise3(m, pos, -1200, 300, scale=1.0, levels=5, turbulence=True)
    vmask = _unary(m, "MaterialExpressionSaturate", _binop(m, "MaterialExpressionMultiply", noise, vstr, -900, 100),
                   -800, 100)
    lerp = _expr(m, "MaterialExpressionLinearInterpolate", -650, -200)
    _link(base, "", lerp, "A")
    _link(vein, "", lerp, "B")
    _link(vmask, "", lerp, "Alpha")
    om, band3, band1 = _ripple_terms(m)
    # char toward black just before the tear (burnt paper)
    char = _expr(m, "MaterialExpressionLinearInterpolate", -400, -200)
    _link(lerp, "", char, "A")
    _link(_const(m, 0.0, -600, -50), "", char, "B")
    _link(band1, "", char, "Alpha")
    _out(char, "", MP.MP_BASE_COLOR)
    rough = _sparam(m, "Roughness", 0.5, -1100, 400)
    rvar = _sparam(m, "RoughnessVariation", 0.0, -1100, 500)
    radd = _binop(m, "MaterialExpressionAdd", rough, _binop(m, "MaterialExpressionMultiply", noise, rvar, -900, 450),
                  -700, 420)
    _out(_unary(m, "MaterialExpressionSaturate", radd, -550, 420), "", MP.MP_ROUGHNESS)
    _out(_sparam(m, "Metallic", 0.0, -550, 600), "", MP.MP_METALLIC)
    _out(_sparam(m, "Specular", 0.5, -550, 700), "", MP.MP_SPECULAR)
    ecol = _vparam(m, "EmissiveColor", (0, 0, 0), -900, 850)
    estr = _sparam(m, "EmissiveStrength", 0.0, -900, 1000)
    em = _binop(m, "MaterialExpressionMultiply", ecol, estr, -700, 900)
    em = _binop(m, "MaterialExpressionAdd", em, _ember(m, band3, -500, 1100), -300, 950)
    em = _binop(m, "MaterialExpressionAdd", em, _rim_emissive(m), -150, 1000)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    _out(om, "", MP.MP_OPACITY_MASK)
    return M._finish(m)


def build_emissive_master(name="M_ECHO_RippleEmissive", is_sky=False):
    """Unlit masked: neon, lit windows, lightboxes. The sky variant (Is Sky, so the real-time
    SkyLight captures it) draws the two dome gradients (Sky=1)."""
    m = M._new_master(name)
    if is_sky:
        set_prop(m, "is_sky", True, quiet=True)
    unlit = enum("MaterialShadingModel", "MSM_UNLIT")
    if unlit is not None:
        set_prop(m, "shading_model", unlit)
    _masked(m)
    set_prop(m, "two_sided", True)
    # gradient: lerp(Color, Zenith, saturate(normal.z * 1.6) * Sky) - Sky=0 gives a flat colour
    nrm = _expr(m, "MaterialExpressionVertexNormalWS", -1300, 0)
    nz = _unary(m, "MaterialExpressionComponentMask", nrm, -1150, 0, r=False, g=False, b=True, a=False)
    k = _unary(m, "MaterialExpressionSaturate", _binop(m, "MaterialExpressionMultiply", nz, _const(m, 1.6, -1150, 100),
                                                       -1000, 0), -850, 0)
    k = _binop(m, "MaterialExpressionMultiply", k, _sparam(m, "Sky", 0.0, -850, 120), -700, 30)
    colr = M._mask_rgb(m, _vparam(m, "Color", (1, 0.6, 0.3), -1000, -300), -850, -300)
    if is_sky:
        # horizon -> mid band -> zenith, then a cloud field multiplies the sky by CloudTint
        mid = M._mask_rgb(m, _vparam(m, "Mid", (0.5, 0.3, 0.4), -1000, -220), -850, -220)
        zen = M._mask_rgb(m, _vparam(m, "Zenith", (0.1, 0.15, 0.4), -1000, -150), -850, -150)
        k2 = _unary(m, "MaterialExpressionSaturate", M._mulc(m, k, 2.0, -700, 150), -600, 150)
        k3 = _unary(m, "MaterialExpressionSaturate", M._addc(m, M._mulc(m, k, 2.0, -700, 250), -1.0, -650, 250), -600, 250)
        grad = M._lerp(m, M._lerp(m, colr, mid, k2, -500, -250), zen, k3, -400, -200)
        cpos = _binop(m, "MaterialExpressionMultiply", nrm,
                      M._mask_rgb(m, _vparam(m, "CloudStretch", (1.0, 1.0, 3.2), -1300, 400), -1150, 400), -1000, 400)
        cpos = _binop(m, "MaterialExpressionMultiply", cpos, _sparam(m, "CloudScale", 2.2, -1150, 500), -900, 450)
        cloud = M.noise3(m, cpos, -800, 500, scale=1.0, levels=4, turbulence=False)
        cm = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, cloud, -0.42, -600, 500), 3.0, -500, 500),
                    -400, 500)
        cm = _binop(m, "MaterialExpressionMultiply", cm, _sparam(m, "CloudAmount", 0.8, -500, 600), -300, 550)
        tint = M._lerp(m, _const(m, 1.0, -400, 650), M._mask_rgb(m, _vparam(m, "CloudTint", (0.7, 0.7, 0.75), -600, 700),
                                                                   -450, 700), cm, -250, 650)
        lerp = _binop(m, "MaterialExpressionMultiply", grad, tint, -250, -150)
    else:
        lerp = _expr(m, "MaterialExpressionLinearInterpolate", -550, -100)
        _link(colr, "", lerp, "A")
        _link(M._mask_rgb(m, _vparam(m, "Zenith", (0.1, 0.15, 0.4), -1000, -150), -850, -150), "", lerp, "B")
        _link(k, "", lerp, "Alpha")
    em = _binop(m, "MaterialExpressionMultiply", lerp, _sparam(m, "Strength", 10.0, -550, 100), -150, 0)
    om, band3, _band1 = _ripple_terms(m)
    em = _binop(m, "MaterialExpressionAdd", em, _ember(m, band3, -400, 300), -100, 100)
    em = _binop(m, "MaterialExpressionAdd", em, _rim_emissive(m), -50, 200)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    _out(om, "", MP.MP_OPACITY_MASK)
    return M._finish(m)


def build_shell_master():
    """The visible wavefront: a translucent bubble with a bright emissive rim, a soft inner
    skin, and a time-varying refraction (heat-haze). Falls back to additive if translucent fails."""
    m = M._new_master("M_ECHO_RippleShell")
    translucent = set_prop(m, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT, quiet=True)
    if not translucent:
        set_prop(m, "blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    unlit = enum("MaterialShadingModel", "MSM_UNLIT")
    if unlit is not None:
        set_prop(m, "shading_model", unlit)
    set_prop(m, "two_sided", True)
    set_prop(m, "used_with_instanced_static_meshes", True, quiet=True)
    fres_lo = _expr(m, "MaterialExpressionFresnel", -1100, 50, exponent=1.15, base_reflect_fraction=0.0)
    fres_hi = _expr(m, "MaterialExpressionFresnel", -1100, 200, exponent=float(S.RIPPLE_SHELL_FRESNEL),
                    base_reflect_fraction=0.0)
    t = _expr(m, "MaterialExpressionTime", -1500, 500)
    wp = _expr(m, "MaterialExpressionWorldPosition", -1500, 650)
    wx = M._mask(m, wp, "r", -1350, 650)
    wy = M._mask(m, wp, "g", -1350, 750)
    wz = M._mask(m, wp, "b", -1350, 850)
    ph = _binop(m, "MaterialExpressionAdd",
                _binop(m, "MaterialExpressionAdd", M._mulc(m, t, 18.0, -1200, 500), M._mulc(m, wx, 0.03, -1200, 650),
                       -1050, 550),
                _binop(m, "MaterialExpressionAdd", M._mulc(m, wy, 0.025, -1200, 750), M._mulc(m, wz, 0.04, -1200, 850),
                       -1050, 750),
                -900, 600)
    shimmer = M._addc(m, M._mulc(m, M._sin(m, ph, -750, 550), 0.25, -600, 550), 0.75, -450, 550)
    ph2 = _binop(m, "MaterialExpressionAdd", M._mulc(m, t, 27.0, -1200, 950),
                 _binop(m, "MaterialExpressionAdd", M._mulc(m, wz, 0.11, -1200, 1050),
                        M._mulc(m, wx, 0.04, -1200, 1150), -1050, 1050), -900, 1000)
    haze = M._addc(m, M._mulc(m, M._sin(m, ph2, -750, 1000), 0.45, -600, 1000), 0.55, -450, 1000)
    fade = _cp(m, "ShellFade", -900, 350)
    # mid fresnel: a slightly wider ring than the core, used as the chromatic halo
    fres_mid = _expr(m, "MaterialExpressionFresnel", -1100, 350, exponent=1.45, base_reflect_fraction=0.0)
    # center of the shell stays almost clear (v4's 0.32*fres_lo fill read as a dark wall)
    fill = M._mulc(m, fres_lo, 0.04, -800, 50)
    core = _binop(m, "MaterialExpressionMultiply", fres_hi, shimmer, -650, 200)
    # halo = mid minus core -> a band just outside the tight white edge, not a filled disc
    halo = _unary(m, "MaterialExpressionSaturate",
                  _binop(m, "MaterialExpressionAdd", fres_mid, M._mulc(m, fres_hi, -1.0, -800, 350), -650, 350),
                  -500, 350)
    halo = _binop(m, "MaterialExpressionMultiply", halo, haze, -350, 350)
    st = _sparam(m, "Strength", S.RIPPLE_SHELL_STRENGTH, -900, 0)
    core_col = _vparam(m, "Color", (0.72, 0.95, 1.25), -900, -100)          # cyan-white leading edge
    halo_col = _vparam(m, "HaloColor", (1.25, 0.28, 0.55), -900, -250)      # magenta / warm outer band
    em_core = _binop(m, "MaterialExpressionMultiply",
                     _binop(m, "MaterialExpressionMultiply", core_col, st, -700, -50), core, -200, 40)
    em_halo = _binop(m, "MaterialExpressionMultiply",
                     _binop(m, "MaterialExpressionMultiply", halo_col, M._mulc(m, st, 0.55, -700, -200), -500, -200),
                     halo, -200, -150)
    em = _binop(m, "MaterialExpressionMultiply",
                _binop(m, "MaterialExpressionAdd", em_core, em_halo, -80, 0), fade, 40, 0)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    if translucent:
        # opacity lives only on the band so the street can refract through the interior
        band = _binop(m, "MaterialExpressionAdd",
                      _binop(m, "MaterialExpressionAdd", M._mulc(m, core, 0.95, -200, 280),
                             M._mulc(m, halo, 0.45, -200, 360), -50, 300),
                      M._mulc(m, fill, 0.08, -200, 420), 80, 300)
        _out(_unary(m, "MaterialExpressionSaturate",
                    _binop(m, "MaterialExpressionMultiply", band, fade, 200, 300), 320, 300), "", MP.MP_OPACITY)
        try:
            # IOR on the chromatic band + a small oscillating offset = heat-haze shimmer
            bend = M._mulc(m, band, float(S.RIPPLE_SHELL_IOR) - 1.0, -200, 450)
            wob = _binop(m, "MaterialExpressionMultiply", M._addc(m, haze, -0.55, -350, 520),
                         M._mulc(m, band, 0.12, -200, 560), -80, 520)
            ior = M._addc(m, _binop(m, "MaterialExpressionAdd", bend, wob, -20, 480), 1.0, 120, 480)
            _out(ior, "", MP.MP_REFRACTION)
        except Exception as exc:
            warn("shell refraction unavailable (%s) - rim only" % exc)
    return M._finish(m)


def build_scrap_master():
    """Burnt paper scrap: cream paper charring to black toward its edges, with a flickering ember
    line on the very edge. Edge distance comes from the BasicShape UVs (0..1 per face)."""
    m = M._new_master("M_ECHO_RippleScrap")
    set_prop(m, "two_sided", True)
    set_prop(m, "used_with_instanced_static_meshes", True, quiet=True)
    uv = _expr(m, "MaterialExpressionTextureCoordinate", -1600, 0)
    u = _unary(m, "MaterialExpressionAbs", M._addc(m, M._mask(m, uv, "r", -1450, 0), -0.5, -1300, 0), -1150, 0)
    v = _unary(m, "MaterialExpressionAbs", M._addc(m, M._mask(m, uv, "g", -1450, 150), -0.5, -1300, 150), -1150, 150)
    e = M._mulc(m, _binop(m, "MaterialExpressionMax", u, v, -1000, 50), 2.0, -850, 50)        # 0 centre .. 1 edge
    wob = M._mulc(m, M._sin(m, _add2(m, M._mulc(m, M._mask(m, uv, "r", -1450, 300), 23.0, -1300, 300),
                                     M._mulc(m, M._mask(m, uv, "g", -1450, 400), 17.0, -1300, 400), -1150, 350),
                            -1000, 350), 0.12, -850, 350)                                       # ragged burn line
    e = _binop(m, "MaterialExpressionAdd", e, wob, -700, 150)
    char = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, e, -0.45, -550, 150), 2.6, -450, 150), -350, 150)
    rimb = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, e, -0.82, -550, 300), 7.0, -450, 300), -350, 300)
    base = M._lerp(m, M._mask_rgb(m, _vparam(m, "PaperColor", (0.55, 0.5, 0.4), -600, -300), -450, -300),
                   M._mask_rgb(m, _vparam(m, "CharColor", (0.012, 0.01, 0.008), -600, -150), -450, -150), char, -200, -200)
    _out(base, "", MP.MP_BASE_COLOR)
    _out(_sparam(m, "Roughness", 0.85, -200, 0), "", MP.MP_ROUGHNESS)
    t = _expr(m, "MaterialExpressionTime", -900, 600)
    flick = M._addc(m, M._mulc(m, M._sin(m, M._mulc(m, t, 19.0, -750, 600), -600, 600), 0.35, -450, 600), 0.65, -300, 600)
    em = _binop(m, "MaterialExpressionMultiply", M._mask_rgb(m, _vparam(m, "EmberColor", S.RIPPLE_EMBER_COLOR, -600, 450),
                                                             -450, 450),
                _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", rimb, flick, -200, 400),
                       _sparam(m, "EmberStrength", 120.0, -300, 500), -100, 450), 0, 450)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    return M._finish(m)


def build_skydome_master():
    """ONE opaque, unlit, two-sided Is-Sky dome that draws both skies and blends them by the wave
    (v2 used two masked Is-Sky domes; masked + Is Sky is not a combination UE's sky path is built
    for, and a dome whose material fails to compile renders the cream default material).
    Is Sky also keeps height fog off the dome and lets the real-time SkyLight capture it."""
    m = M._new_master("M_ECHO_RippleSkyDome")
    set_prop(m, "is_sky", True, quiet=True)
    unlit = enum("MaterialShadingModel", "MSM_UNLIT")
    if unlit is not None:
        set_prop(m, "shading_model", unlit)
    set_prop(m, "blend_mode", unreal.BlendMode.BLEND_OPAQUE, quiet=True)
    set_prop(m, "two_sided", True)
    nrm = _expr(m, "MaterialExpressionVertexNormalWS", -2600, 0)
    nz = M._mask(m, nrm, "b", -2450, 0)
    # a full-dome gradient (v3 used nz*3, so everything above ~18 deg was already zenith - a flat sky)
    k2 = _unary(m, "MaterialExpressionSaturate", M._mulc(m, nz, 1.7, -2300, 0), -2150, 0)        # mid by ~36 deg
    k3 = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, nz, -0.35, -2300, 120), 1.5, -2150, 120),
                -2000, 120)                                                                     # zenith from ~20 deg up
    stretch = M._mask_rgb(m, _vparam(m, "CloudStretch", (1.0, 1.0, 3.2), -2600, 400), -2450, 400)
    cscale = _sparam(m, "CloudScale", 2.4, -2450, 500)
    cpos = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", nrm, stretch, -2300, 400),
                  cscale, -2150, 450)
    cloud = M.noise3(m, cpos, -2000, 450, scale=1.0, levels=4, turbulence=False)
    # a second, finer layer so the clouds have edges the camera can actually read
    cpos2 = _binop(m, "MaterialExpressionMultiply", cpos, _const(m, 3.2, -2150, 620), -2000, 620)
    cloud2 = M.noise3(m, cpos2, -1850, 620, scale=1.0, levels=3, turbulence=False)
    big = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, cloud, -0.38, -1800, 450), 3.4, -1700, 450),
                 -1600, 450)
    fine = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, cloud2, -0.52, -1800, 620), 4.0, -1700, 620),
                  -1600, 620)
    cmask = _unary(m, "MaterialExpressionSaturate",
                   _binop(m, "MaterialExpressionAdd", M._mulc(m, big, 0.78, -1500, 500),
                          M._mulc(m, fine, 0.45, -1500, 620), -1400, 540), -1300, 540)

    def state(p, y):
        hor = M._mask_rgb(m, _vparam(m, p + "Horizon", (0.4, 0.45, 0.5), -1600, y), -1450, y)
        mid = M._mask_rgb(m, _vparam(m, p + "Mid", (0.3, 0.35, 0.4), -1600, y + 100), -1450, y + 100)
        zen = M._mask_rgb(m, _vparam(m, p + "Zenith", (0.15, 0.2, 0.3), -1600, y + 200), -1450, y + 200)
        grad = M._lerp(m, M._lerp(m, hor, mid, k2, -1300, y), zen, k3, -1150, y + 50)
        cm = _binop(m, "MaterialExpressionMultiply", cmask, _sparam(m, p + "CloudAmount", 0.8, -1450, y + 300),
                    -1300, y + 300)
        tint = M._lerp(m, _const(m, 1.0, -1300, y + 400),
                       M._mask_rgb(m, _vparam(m, p + "CloudTint", (0.7, 0.7, 0.75), -1450, y + 450), -1300, y + 450),
                       cm, -1150, y + 350)
        c = _binop(m, "MaterialExpressionMultiply", grad, tint, -1000, y + 100)
        return _binop(m, "MaterialExpressionMultiply", c, _sparam(m, p + "Strength", 10.0, -1000, y + 250), -850, y + 150)

    col_a = state("A_", -900)
    col_b = state("B_", -300)
    # State A moon: a soft disc + halo in the direction the moonlight comes from (matches A_SUN_ROT)
    pr, yr = math.radians(S.A_SUN_ROT[0]), math.radians(S.A_SUN_ROT[1])
    moon_dir = (-math.cos(pr) * math.cos(yr), -math.cos(pr) * math.sin(yr), -math.sin(pr))
    mdir = M._mask_rgb(m, _vparam(m, "MoonDir", moon_dir, -1600, -50), -1450, -50)
    mdot = _binop(m, "MaterialExpressionDotProduct", nrm, mdir, -1300, -50)
    disc = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, mdot, -(1.0 - 0.012), -1150, -80),
                                                           1.0 / 0.012, -1000, -80), -850, -80)
    disc2 = _binop(m, "MaterialExpressionMultiply", disc, disc, -700, -80)
    halo = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, mdot, -(1.0 - 0.08), -1150, 20),
                                                           1.0 / 0.08, -1000, 20), -850, 20)
    halo2 = _binop(m, "MaterialExpressionMultiply", halo, halo, -700, 20)
    mamt = _binop(m, "MaterialExpressionAdd", M._mulc(m, disc2, 12.0, -550, -80), M._mulc(m, halo2, 0.55, -550, 20),
                  -400, -20)
    mcol = M._mask_rgb(m, _vparam(m, "MoonColor", (0.85, 0.90, 1.0), -700, 80), -550, 80)
    moon = _binop(m, "MaterialExpressionMultiply",
                  _binop(m, "MaterialExpressionMultiply", mcol, mamt, -250, 0),
                  _sparam(m, "MoonStrength", 6.0, -400, 80), -100, 20)
    col_a = _binop(m, "MaterialExpressionAdd", col_a, moon, -850, -600)
    # State B: a warm sun glow just above the horizon in the dusk-sun direction
    bpr, byr = math.radians(S.B_SUN_ROT[0]), math.radians(S.B_SUN_ROT[1])
    sun_dir = (-math.cos(bpr) * math.cos(byr), -math.cos(bpr) * math.sin(byr), -math.sin(bpr))
    sdir = M._mask_rgb(m, _vparam(m, "SunDir", sun_dir, -1600, 250), -1450, 250)
    sdot = _unary(m, "MaterialExpressionSaturate", _binop(m, "MaterialExpressionDotProduct", nrm, sdir, -1300, 250),
                  -1150, 250)
    s4 = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", sdot, sdot, -1000, 250),
                _binop(m, "MaterialExpressionMultiply", sdot, sdot, -1000, 330), -850, 250)
    # tighter toward the horizon so it does not wash the zenith
    hz = _unary(m, "MaterialExpressionSaturate", M._mulc(m, _unary(m, "MaterialExpressionOneMinus",
                _unary(m, "MaterialExpressionAbs", nz, -1300, 350), -1150, 350), 3.5, -1000, 350), -850, 350)
    sglow = _binop(m, "MaterialExpressionMultiply",
                   _binop(m, "MaterialExpressionMultiply", s4, hz, -700, 280),
                   M._mask_rgb(m, _vparam(m, "SunGlow", (1.4, 0.55, 0.18), -700, 380), -550, 380), -400, 300)
    sglow = _binop(m, "MaterialExpressionMultiply", sglow, _sparam(m, "SunGlowStrength", 2.8, -400, 400), -250, 300)
    col_b = _binop(m, "MaterialExpressionAdd", col_b, sglow, -850, -250)
    # wave mask on the dome: ragged along the clouds (the sky tears cloud by cloud)
    wp = _expr(m, "MaterialExpressionWorldPosition", -1600, 900)
    center = _rgb(m, _cp(m, "Center", -1600, 1000), -1450, 1000)
    dist = _binop(m, "MaterialExpressionDistance", wp, center, -1300, 950)
    tear = M._mulc(m, M._addc(m, cloud, -0.5, -1450, 1150), 1.0, -1300, 1150)
    tear = _binop(m, "MaterialExpressionMultiply", tear, _sparam(m, "SkyTear", 18000.0, -1450, 1250), -1150, 1150)
    d2 = _binop(m, "MaterialExpressionAdd", dist, tear, -1000, 1000)
    # SkyRadius (MPC) compresses the 1.5 km dome onto the S2 crane-up; falls back to Radius if unset
    sky_r = _cp(m, "SkyRadius", -1150, 900)
    inside = _binop(m, "MaterialExpressionSubtract", sky_r, d2, -850, 950)
    edge = _sparam(m, "SkyEdge", 10000.0, -1000, 1300)
    enable = _cp(m, "Enable", -1000, 1400)
    alpha = _unary(m, "MaterialExpressionSaturate",
                   M._addc(m, _binop(m, "MaterialExpressionDivide", inside, edge, -700, 1000), 0.5, -600, 1000), -500, 1000)
    alpha = _binop(m, "MaterialExpressionMultiply", alpha, enable, -400, 1050)
    col = M._lerp(m, col_a, col_b, alpha, -300, -400)
    # burning edge + cyan rim on the sky
    absd = _unary(m, "MaterialExpressionAbs", inside, -700, 1500)
    band = _unary(m, "MaterialExpressionSaturate", _unary(m, "MaterialExpressionOneMinus",
                  _binop(m, "MaterialExpressionDivide", absd, M._mulc(m, edge, 1.5, -700, 1650), -550, 1550),
                  -450, 1550), -350, 1550)
    b3 = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", band, band, -250, 1550), band,
                -150, 1550)
    b3 = _binop(m, "MaterialExpressionMultiply", b3, enable, -50, 1550)
    ember = _ember(m, M._mulc(m, b3, 0.15, 50, 1550), 300, 1500)
    rim = _unary(m, "MaterialExpressionSaturate", _unary(m, "MaterialExpressionOneMinus",
                 _binop(m, "MaterialExpressionDivide", absd, _sparam(m, "SkyRimWidth", 4000.0, -700, 1850), -550, 1800),
                 -450, 1800), -350, 1800)
    r2 = _binop(m, "MaterialExpressionMultiply", rim, rim, -250, 1800)
    r4 = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", r2, r2, -150, 1800), enable,
                -50, 1800)
    rk = _binop(m, "MaterialExpressionMultiply", r4, M._mulc(m, _cp(m, "RimStrength", -250, 1950), 0.25, -100, 1950),
                50, 1850)
    rimc = _binop(m, "MaterialExpressionMultiply", _rgb(m, _cp(m, "RimColor", 50, 2000), 200, 2000), rk, 300, 1850)
    em = _binop(m, "MaterialExpressionAdd", _binop(m, "MaterialExpressionAdd", col, ember, 400, 0), rimc, 550, 100)
    _out(em, "", MP.MP_EMISSIVE_COLOR)
    return M._finish(m)


def build_brick_master():
    """Opaque masonry: procedural running bond in world space (Floor/Frac), recessed-looking mortar,
    per-brick tone (hash), per-instance hue shift (PerInstanceRandom), a large-scale weathering
    field and a wet grime gradient at the base. Carries the ripple rim so the ring crosses walls."""
    m = M._new_master("M_ECHO_RippleBrick")
    M._usage(m)
    wp = _expr(m, "MaterialExpressionWorldPosition", -3000, -600)
    nrm = _expr(m, "MaterialExpressionVertexNormalWS", -3000, -400)
    ax = _unary(m, "MaterialExpressionAbs", M._mask(m, nrm, "r", -2850, -450), -2700, -450)
    ay = _unary(m, "MaterialExpressionAbs", M._mask(m, nrm, "g", -2850, -350), -2700, -350)
    sel = _unary(m, "MaterialExpressionSaturate", M._mulc(m, _binop(m, "MaterialExpressionSubtract", ax, ay, -2550, -400),
                                                           20.0, -2450, -400), -2350, -400)
    wx = M._mask(m, wp, "r", -2850, -700)
    wy = M._mask(m, wp, "g", -2850, -600)
    wz = M._mask(m, wp, "b", -2850, -500)
    h = M._lerp(m, wx, wy, sel, -2200, -650)           # wall facing X -> courses run along Y
    bw = _sparam(m, "BrickW", 21.0, -2200, -500)
    bh = _sparam(m, "BrickH", 7.6, -2200, -400)
    vz = _binop(m, "MaterialExpressionDivide", wz, bh, -2050, -450)
    row = _unary(m, "MaterialExpressionFloor", vz, -1900, -450)
    fv = _unary(m, "MaterialExpressionFrac", vz, -1900, -350)
    hh = _binop(m, "MaterialExpressionAdd", _binop(m, "MaterialExpressionDivide", h, bw, -2050, -650),
                M._mulc(m, row, 0.5, -1900, -550), -1750, -600)
    col = _unary(m, "MaterialExpressionFloor", hh, -1600, -650)
    fu = _unary(m, "MaterialExpressionFrac", hh, -1600, -550)
    mw = _sparam(m, "MortarW", 0.06, -1600, -450)
    mh = _sparam(m, "MortarH", 0.14, -1600, -350)
    bu = _unary(m, "MaterialExpressionSaturate", M._mulc(m, _binop(m, "MaterialExpressionSubtract", fu, mw, -1450, -550),
                                                          30.0, -1350, -550), -1250, -550)
    bv = _unary(m, "MaterialExpressionSaturate", M._mulc(m, _binop(m, "MaterialExpressionSubtract", fv, mh, -1450, -400),
                                                          14.0, -1350, -400), -1250, -400)
    brick = _binop(m, "MaterialExpressionMultiply", bu, bv, -1100, -480)
    rnd = M._hash2(m, col, row, -1450, -150)
    pir = _expr(m, "MaterialExpressionPerInstanceRandom", -1450, 50)
    huevar = _sparam(m, "HueVar", 0.35, -1450, 150)
    t = _unary(m, "MaterialExpressionSaturate", _binop(m, "MaterialExpressionAdd",
               _binop(m, "MaterialExpressionMultiply", pir, huevar, -1250, 100), M._mulc(m, rnd, 0.4, -1250, -100),
               -1100, 0), -1000, 0)
    c1 = M._mask_rgb(m, _vparam(m, "BrickColor", (0.23, 0.075, 0.05), -1250, -300), -1100, -300)
    c2 = M._mask_rgb(m, _vparam(m, "BrickColor2", (0.15, 0.06, 0.045), -1250, -200), -1100, -200)
    tone = M._lerp(m, c1, c2, t, -900, -250)
    tone = _binop(m, "MaterialExpressionMultiply", tone, M._addc(m, M._mulc(m, rnd, 0.45, -1000, -100), 0.75, -900, -100),
                  -800, -200)
    # weathering patches (large-scale field): darkens / desaturates whole areas of wall
    wpos = M._mulc(m, wp, 0.0025, -2850, 300)
    wf = M.noise3(m, wpos, -2700, 300, scale=1.0, levels=3, turbulence=False)
    weather = _unary(m, "MaterialExpressionSaturate", M._mulc(m, M._addc(m, wf, -0.45, -2500, 300), 2.0, -2400, 300),
                     -2300, 300)
    weather = _binop(m, "MaterialExpressionMultiply", weather, _sparam(m, "Weathering", 0.35, -2400, 400), -2200, 350)
    tone = M._lerp(m, tone, M._mulc(m, tone, 0.6, -900, 100), weather, -700, -100)
    mortar = M._mask_rgb(m, _vparam(m, "MortarColor", (0.2, 0.19, 0.17), -1100, 250), -950, 250)
    mortar = M._lerp(m, mortar, M._mulc(m, mortar, 0.55, -900, 350), weather, -750, 300)
    base = M._lerp(m, mortar, tone, brick, -550, -100)
    # grime: dark, damp band rising from the pavement
    gz = _binop(m, "MaterialExpressionDivide", M._addc(m, wz, -15.0, -2700, 600),
                _sparam(m, "GrimeHeight", 220.0, -2700, 700), -2550, 650)
    g = _unary(m, "MaterialExpressionSaturate", _unary(m, "MaterialExpressionOneMinus", gz, -2400, 650), -2300, 650)
    g = _binop(m, "MaterialExpressionMultiply", _binop(m, "MaterialExpressionMultiply", g, g, -2200, 650),
               _sparam(m, "GrimeAmount", 0.7, -2300, 750), -2100, 700)
    g = _binop(m, "MaterialExpressionMultiply", g, M._addc(m, M._mulc(m, wf, 0.6, -2200, 850), 0.7, -2100, 850),
               -1950, 750)
    base = M._lerp(m, base, M._mask_rgb(m, _vparam(m, "GrimeColor", (0.03, 0.028, 0.026), -700, 600), -550, 600), g,
                   -350, 0)
    _out(base, "", MP.MP_BASE_COLOR)
    rough = M._lerp(m, _const(m, 0.95, -700, 800), _sparam(m, "Roughness", 0.82, -700, 900), brick, -500, 850)
    rough = _binop(m, "MaterialExpressionSubtract", rough, M._mulc(m, g, 0.35, -500, 950), -350, 900)
    _out(_unary(m, "MaterialExpressionSaturate", rough, -200, 900), "", MP.MP_ROUGHNESS)
    _out(_sparam(m, "Specular", 0.4, -200, 1000), "", MP.MP_SPECULAR)
    _out(M._lerp(m, _const(m, 0.55, -400, 1100), _const(m, 1.0, -400, 1200), brick, -200, 1150), "",
         MP.MP_AMBIENT_OCCLUSION)
    _ripple_terms(m, -3200, 1500)
    _out(_rim_emissive(m), "", MP.MP_EMISSIVE_COLOR)
    return M._finish(m)


def _add2(m, a, b, x, y):
    return _binop(m, "MaterialExpressionAdd", a, b, x, y)


# --------------------------------------------------------------------------- instances
def _rs(name, side, base, rough, metal=0.0, spec=0.5, vein=None, vstr=0.0, vscale=0.004, rvar=0.0,
        emis=None, estr=0.0):
    sc = {"Roughness": rough, "Metallic": metal, "Specular": spec, "VeinStrength": vstr, "VeinScale": vscale,
          "RoughnessVariation": rvar, "EmissiveStrength": estr, "Side": float(side)}
    vc = {"BaseColor": base, "VeinColor": vein or base}
    if emis:
        vc["EmissiveColor"] = emis
    mi = M._mi(name, STATE.get("surface"), sc, vc)
    MATS[name] = mi
    return mi


def _re(name, side, color, strength, zenith=None, sky=0.0):
    vc = {"Color": color}
    if zenith:
        vc["Zenith"] = zenith
    mi = M._mi(name, STATE.get("sky" if sky else "emissive"), {"Strength": strength, "Side": float(side), "Sky": sky}, vc)
    MATS[name] = mi
    return mi


def _skydome(name):
    """Single sky dome instance carrying both skies (A_* outside the wave, B_* inside)."""
    if STATE.get("skydome") is None:
        warn("sky dome master missing - %s falls back to a flat Vacant-grey unlit sky (no B sky)" % name)
        mi = _pe(name, S.A_SKY["Mid"], S.A_SKY["Strength"])
        MATS[name] = mi
        return mi
    sc, vc = {}, {}
    for p, d in (("A_", S.A_SKY), ("B_", S.B_SKY)):
        sc[p + "Strength"] = d["Strength"]
        sc[p + "CloudAmount"] = d.get("CloudAmount", 0.8)
        vc[p + "Horizon"] = d["Horizon"]
        vc[p + "Mid"] = d.get("Mid", d["Horizon"])
        vc[p + "Zenith"] = d["Zenith"]
        vc[p + "CloudTint"] = d.get("CloudTint", (0.7, 0.7, 0.75))
    sc["CloudScale"] = 0.5 * (S.A_SKY.get("CloudScale", 2.2) + S.B_SKY.get("CloudScale", 2.6))
    mi = M._mi(name, STATE["skydome"], sc, vc)
    MATS[name] = mi
    log("sky dome material %s -> parent M_ECHO_RippleSkyDome (A %s / B %s horizon)"
        % (name, S.A_SKY["Horizon"], S.B_SKY["Horizon"]))
    return mi


def _rb(name, c1, c2, mortar, rough, w=21.0, h=7.6, mw=0.06, mh=0.14, hue=0.35, weather=0.35, grime=0.7, fb=None):
    """Masonry instance on M_ECHO_RippleBrick (falls back to a flat gala surface)."""
    if STATE.get("brick") is None:
        col, r = fb or (c1, rough)
        return _ps(name, col, r, vein=mortar, vstr=0.4, vscale=0.04, rvar=-0.2)
    mi = M._mi(name, STATE["brick"], {"BrickW": w, "BrickH": h, "MortarW": mw, "MortarH": mh, "HueVar": hue,
                                      "Weathering": weather, "GrimeAmount": grime, "GrimeHeight": 220.0,
                                      "Roughness": rough, "Specular": 0.4},
               {"BrickColor": c1, "BrickColor2": c2, "MortarColor": mortar, "GrimeColor": (0.03, 0.028, 0.026)})
    MATS[name] = mi
    return mi


def _street(name, base, rough, **kw):
    """State-invariant surface that still shows the ripple RIM (Side 0 on the ripple master)."""
    if STATE.get("surface") is None:
        return _ps(name, base, rough, **kw)
    return _rs(name, 0, base, rough, **kw)


def _ps(name, base, rough, metal=0.0, spec=0.5, vein=None, vstr=0.0, vscale=0.004, rvar=0.0, emis=None, estr=0.0):
    """Plain (state-invariant) instance on the gala's M_ECHO_Surface."""
    s = M.load_master("M_ECHO_Surface")
    return M._surf(s, name, base, rough, metal, spec, vein, vstr, vscale, rvar, emis, estr)


def _pe(name, color, strength):
    return M._mi(name, M.load_master("M_ECHO_Emissive"), {"Strength": strength}, {"Color": color})


def build_all():
    with_mpc = False
    try:
        build_mpc()
        with_mpc = True
        log("MPC ready: %s/%s" % (S.RIPPLE_MAT_DIR, S.RIPPLE_MPC_NAME))
    except Exception as exc:
        error("MPC_Ripple failed (%s) - ripple falls back to transform swaps only" % exc)
    for key, fn in (("surface", build_surface_master), ("emissive", build_emissive_master),
                    ("skydome", build_skydome_master), ("brick", build_brick_master),
                    ("shell", build_shell_master), ("scrap", build_scrap_master)):
        if not with_mpc:
            STATE[key] = None
            continue
        try:
            STATE[key] = fn()
            STATE[key + "_ok"] = True
            log("ripple master ok: " + key)
        except Exception as exc:
            error("ripple master '%s' failed (%s) - its instances use the default material" % (key, exc))
            STATE[key] = None

    # the gala masters now also feed instanced static meshes (ISM usage must be compiled in,
    # -game renders can't auto-add it)
    for nm in ("M_ECHO_Surface", "M_ECHO_Emissive"):
        mm = M.load_master(nm)
        if mm is not None:
            try:
                if not mm.get_editor_property("used_with_instanced_static_meshes"):
                    mm.set_editor_property("used_with_instanced_static_meshes", True)
                    MEL.recompile_material(mm)
                    save_asset(mm)
            except Exception as exc:
                warn("ISM usage flag on %s: %s" % (nm, exc))

    # ---------------- state-invariant Riverside surfaces (gala master)
    # masonry: procedural bond (M_ECHO_RippleBrick) - red, brown, painted, soot, grey stone, cream, ironspot
    _rb("MI_Brick_Red", (0.30, 0.09, 0.055), (0.20, 0.07, 0.05), (0.26, 0.24, 0.21), 0.82)
    _rb("MI_Brick_Brown", (0.17, 0.09, 0.055), (0.11, 0.07, 0.05), (0.21, 0.19, 0.16), 0.85)
    _rb("MI_Brick_Painted", (0.34, 0.33, 0.30), (0.27, 0.28, 0.27), (0.30, 0.29, 0.27), 0.7, hue=0.15, weather=0.55,
        fb=((0.36, 0.34, 0.30), 0.7))
    _rb("MI_Brick_Soot", (0.06, 0.05, 0.045), (0.04, 0.035, 0.032), (0.09, 0.085, 0.08), 0.9, weather=0.2)
    _rb("MI_Stone_Grey", (0.30, 0.30, 0.29), (0.23, 0.235, 0.245), (0.36, 0.35, 0.33), 0.75, w=92.0, h=46.0,
        mw=0.015, mh=0.03, hue=0.5, fb=((0.28, 0.28, 0.28), 0.75))
    _rb("MI_Brick_Cream", (0.52, 0.46, 0.34), (0.44, 0.39, 0.29), (0.60, 0.58, 0.52), 0.8, hue=0.4,
        fb=((0.5, 0.45, 0.34), 0.8))
    _rb("MI_Brick_Dark", (0.09, 0.05, 0.045), (0.06, 0.045, 0.045), (0.26, 0.25, 0.23), 0.78,
        fb=((0.08, 0.05, 0.045), 0.8))
    _street("MI_Trim_Cream", (0.55, 0.5, 0.42), 0.6)
    _ps("MI_Trim_Dark", (0.07, 0.075, 0.08), 0.45, metal=0.3)
    # El: dark, oily, riveted steel (was a green that the low sun turned into an orange slab)
    _street("MI_Steel_ElGreen", (0.018, 0.03, 0.026), 0.6, metal=0.55, vein=(0.05, 0.03, 0.02), vstr=0.35, vscale=0.01)
    _ps("MI_Steel_Rivet", (0.035, 0.045, 0.04), 0.4, metal=0.8)
    _ps("MI_Rust", (0.16, 0.06, 0.025), 0.8, metal=0.4, vein=(0.05, 0.03, 0.02), vstr=0.6, vscale=0.03)
    _ps("MI_Iron_Black", (0.02, 0.02, 0.022), 0.5, metal=0.85)
    _ps("MI_Glass_Window", (0.01, 0.012, 0.015), 0.04, spec=0.9)
    _street("MI_Asphalt_Puddles", (0.024, 0.024, 0.026), 0.22, vein=(0.010, 0.010, 0.011), vstr=0.7, vscale=0.006,
            rvar=-0.42, spec=0.7)                 # wetter night street: moonlight and sodium have a mirror to sit in
    _street("MI_Sidewalk", (0.2, 0.2, 0.205), 0.6, vein=(0.1, 0.1, 0.1), vstr=0.45, vscale=0.008, rvar=-0.4)
    _street("MI_Paint_White", (0.6, 0.6, 0.58), 0.55, vein=(0.3, 0.3, 0.3), vstr=0.3, vscale=0.05)
    _ps("MI_Paint_Yellow", (0.65, 0.45, 0.02), 0.55)
    _ps("MI_Wood_Pole", (0.09, 0.06, 0.04), 0.8, vein=(0.04, 0.03, 0.02), vstr=0.5, vscale=0.05)
    _ps("MI_Cable", (0.01, 0.01, 0.01), 0.5)
    _ps("MI_WaterTower_Wood", (0.16, 0.11, 0.07), 0.85, vein=(0.07, 0.05, 0.03), vstr=0.6, vscale=0.08)
    _ps("MI_Awning_Green", (0.04, 0.16, 0.07), 0.75, vein=(0.10, 0.22, 0.08), vstr=0.55, vscale=0.04)
    _ps("MI_Awning_Burgundy", (0.22, 0.03, 0.05), 0.75, vein=(0.32, 0.06, 0.07), vstr=0.55, vscale=0.04)
    _ps("MI_Awning_Cream", (0.48, 0.40, 0.28), 0.75, vein=(0.58, 0.50, 0.34), vstr=0.45, vscale=0.04)
    _ps("MI_Hydrant_Red", (0.35, 0.03, 0.02), 0.4)
    _ps("MI_Box_Blue", (0.02, 0.07, 0.22), 0.45)
    _ps("MI_Box_Red", (0.30, 0.03, 0.03), 0.45)
    _ps("MI_Rail_Steel", (0.5, 0.5, 0.52), 0.25, metal=1.0)
    _ps("MI_Tie_Wood", (0.022, 0.018, 0.015), 0.92)    # creosote
    _ps("MI_Rubber", (0.015, 0.015, 0.015), 0.85)
    _ps("MI_Chrome_Dull", (0.6, 0.6, 0.62), 0.25, metal=1.0)
    _ps("MI_Puddle", (0.006, 0.006, 0.007), 0.015, spec=0.85)
    _ps("MI_Box_Green", (0.01, 0.14, 0.06), 0.4)
    _ps("MI_Cloth_Josh", (0.09, 0.095, 0.1), 0.85)
    wm = M.load_master("M_ECHO_Windows")
    M._mi("MI_Rowhouse_Far", wm, {"WindowStrength": S.E_WINDOW_LIT * 0.22, "LitBias": -0.15, "FloorHeight": 330,
                                  "BayWidth": 170, "Roughness": 0.7, "Metallic": 0.0},
          {"WindowColor": (1.0, 0.66, 0.4), "FacadeColor": (0.09, 0.05, 0.035)})
    M._mi("MI_Rowhouse_Far_Grey", wm, {"WindowStrength": S.E_WINDOW_LIT * 0.22, "LitBias": -0.15, "FloorHeight": 330,
                                       "BayWidth": 170, "Roughness": 0.7, "Metallic": 0.0},
          {"WindowColor": (1.0, 0.7, 0.45), "FacadeColor": (0.075, 0.075, 0.078)})
    M._mi("MI_Tower_Far", wm, {"WindowStrength": S.E_WINDOW_LIT * 0.22, "LitBias": -0.18, "FloorHeight": 360,
                               "BayWidth": 150, "Roughness": 0.35, "Metallic": 0.2},
          {"WindowColor": (0.95, 0.85, 0.7), "FacadeColor": (0.05, 0.055, 0.065)})
    _pe("MI_E_TrafficRed", (1.0, 0.05, 0.02), 20.0)
    _pe("MI_E_Window_Dim", (1.0, 0.7, 0.45), 9.0)
    _pe("MI_E_Steam", (0.6, 0.65, 0.7), 0.6)

    # ---------------- State A 'Vacant' (Side -1: visible outside the wave)
    A, B = -1, 1
    _rs("MIR_A_Plywood", A, (0.24, 0.17, 0.10), 0.85, vein=(0.12, 0.08, 0.05), vstr=0.6, vscale=0.03)
    _rs("MIR_A_PlywoodGrey", A, (0.16, 0.15, 0.13), 0.9, vein=(0.08, 0.075, 0.07), vstr=0.55, vscale=0.03)
    _rs("MIR_A_Shutter", A, (0.18, 0.19, 0.2), 0.45, metal=0.8, vein=(0.1, 0.07, 0.05), vstr=0.5, vscale=0.02)
    _rs("MIR_A_Graffiti_Pink", A, (0.6, 0.05, 0.3), 0.6)
    _rs("MIR_A_Graffiti_Teal", A, (0.02, 0.4, 0.35), 0.6)
    _rs("MIR_A_Graffiti_Yellow", A, (0.7, 0.55, 0.02), 0.6)
    _rs("MIR_A_TrashBag", A, (0.008, 0.008, 0.01), 0.18, spec=0.6)
    _rs("MIR_A_Cardboard", A, (0.28, 0.19, 0.11), 0.9)
    _rs("MIR_A_Newsprint", A, (0.42, 0.41, 0.38), 0.85)
    _rs("MIR_A_SignFaded", A, (0.25, 0.22, 0.18), 0.8, vein=(0.1, 0.09, 0.08), vstr=0.6, vscale=0.02)
    _rs("MIR_A_CarDusty", A, (0.12, 0.12, 0.11), 0.75, metal=0.4, vein=(0.2, 0.18, 0.15), vstr=0.5, vscale=0.01)
    _rs("MIR_A_Rust", A, (0.16, 0.06, 0.025), 0.8, metal=0.4, vein=(0.05, 0.03, 0.02), vstr=0.6, vscale=0.03)
    _rs("MIR_A_Cinder", A, (0.2, 0.2, 0.2), 0.9, vein=(0.1, 0.1, 0.1), vstr=0.4, vscale=0.02)
    _rs("MIR_A_Flowers_Dead", A, (0.12, 0.08, 0.05), 0.9)
    _rs("MIR_A_Brick_Cortaz", A, (0.2, 0.09, 0.06), 0.85, vein=(0.09, 0.04, 0.03), vstr=0.5, vscale=0.05)
    _rs("MIR_A_Candle_Out", A, (0.5, 0.45, 0.4), 0.6)
    _re("MIR_A_Window_Lit", A, (0.75, 0.85, 1.0), E_WINDOW_A())
    _re("MIR_A_Fluoro", A, (0.8, 0.95, 1.0), 12.0)
    _re("MIR_A_Lamp_Sodium", A, (1.0, 0.50, 0.14), 5.0)
    _re("MIR_A_Leak", A, (1.0, 0.82, 0.52), 5.5)

    # ---------------- State B 'Busy' (Side +1: visible inside the wave)
    _rs("MIR_B_Awning_Red", B, (0.32, 0.02, 0.02), 0.7)
    _rs("MIR_B_Awning_Cream", B, (0.62, 0.56, 0.45), 0.7)
    _rs("MIR_B_Awning_Green", B, (0.02, 0.16, 0.06), 0.7)
    _rs("MIR_B_Crate", B, (0.3, 0.2, 0.11), 0.8, vein=(0.15, 0.1, 0.05), vstr=0.5, vscale=0.05)
    _rs("MIR_B_Orange", B, (0.75, 0.25, 0.01), 0.45)
    _rs("MIR_B_Apple", B, (0.45, 0.02, 0.02), 0.3)
    _rs("MIR_B_Lime", B, (0.12, 0.4, 0.03), 0.4)
    _rs("MIR_B_Banana", B, (0.75, 0.55, 0.05), 0.5)
    _rs("MIR_B_Shelf", B, (0.6, 0.6, 0.6), 0.4, metal=0.6)
    _rs("MIR_B_Products_A", B, (0.55, 0.08, 0.05), 0.4)
    _rs("MIR_B_Products_B", B, (0.05, 0.2, 0.5), 0.4)
    _rs("MIR_B_Products_C", B, (0.7, 0.6, 0.1), 0.4)
    _rs("MIR_B_Counter", B, (0.12, 0.07, 0.04), 0.35, vein=(0.05, 0.03, 0.02), vstr=0.5, vscale=0.03)
    _rs("MIR_B_Paint_Teal", B, (0.02, 0.22, 0.2), 0.3, metal=0.5)
    _rs("MIR_B_Paint_Cherry", B, (0.3, 0.01, 0.02), 0.2, metal=0.6)
    _rs("MIR_B_Paint_Cab", B, (0.75, 0.5, 0.02), 0.25, metal=0.5)
    _rs("MIR_B_Paint_Navy", B, (0.01, 0.02, 0.07), 0.2, metal=0.6)
    _rs("MIR_B_CarGlass", B, (0.004, 0.004, 0.006), 0.03, spec=1.0)
    _rs("MIR_B_Tire", B, (0.02, 0.02, 0.02), 0.85)
    _rs("MIR_B_Chrome", B, (0.85, 0.85, 0.87), 0.1, metal=1.0)
    _rs("MIR_B_Flowers", B, (0.6, 0.1, 0.25), 0.6)
    _rs("MIR_B_Leaves", B, (0.05, 0.2, 0.04), 0.7)
    _rs("MIR_B_Soot", B, (0.02, 0.018, 0.016), 0.95, vein=(0.06, 0.04, 0.03), vstr=0.6, vscale=0.02)
    _rs("MIR_B_Train", B, (0.42, 0.44, 0.46), 0.3, metal=0.9, vein=(0.3, 0.3, 0.3), vstr=0.3, vscale=0.01)
    _rs("MIR_B_ChainLink", B, (0.3, 0.3, 0.3), 0.4, metal=0.9)
    # pedestrians' clothes
    for i, (nm, col, r) in enumerate((("Denim", (0.04, 0.07, 0.15), 0.8), ("Hoodie_Red", (0.3, 0.03, 0.03), 0.85),
                                      ("Coat_Camel", (0.35, 0.22, 0.1), 0.8), ("Jacket_Black", (0.02, 0.02, 0.02), 0.55),
                                      ("Puffer_Olive", (0.1, 0.12, 0.05), 0.6), ("Sweater_Cream", (0.55, 0.5, 0.42), 0.9),
                                      ("Track_Teal", (0.02, 0.2, 0.2), 0.5), ("Coat_Plum", (0.15, 0.03, 0.12), 0.8))):
        _rs("MIR_B_Cloth_" + nm, B, col, r)
    _re("MIR_B_Neon_Red", B, (1.0, 0.06, 0.08), S.E_NEON)
    _re("MIR_B_Neon_Blue", B, (0.1, 0.45, 1.0), S.E_NEON)
    _re("MIR_B_Neon_Pink", B, (1.0, 0.15, 0.7), S.E_NEON)
    _re("MIR_B_Neon_Green", B, (0.2, 1.0, 0.35), S.E_NEON * 0.8)
    _re("MIR_B_Lightbox", B, (1.0, 0.92, 0.75), S.E_LIGHTBOX)
    _re("MIR_B_Interior", B, (1.0, 0.86, 0.62), 16.0)
    _re("MIR_B_Window_Lit", B, (1.0, 0.68, 0.38), S.E_WINDOW_LIT)
    _re("MIR_B_Bulb", B, (1.0, 0.7, 0.35), 30.0)
    _re("MIR_B_Lamp_Sodium", B, (1.0, 0.55, 0.2), S.E_LAMP_LENS)
    _re("MIR_B_Headlight", B, (0.9, 0.95, 1.0), 60.0)
    _re("MIR_B_Taillight", B, (1.0, 0.03, 0.02), 25.0)
    _re("MIR_B_TrainWindow", B, (0.85, 0.95, 1.0), 35.0)     # the train stays clearly lit
    _re("MIR_B_SunDisc", B, (1.0, 0.62, 0.3), S.E_SUN_DISC)
    _skydome("MIR_SkyDome")
    # ---------------- effects (paper shreds, embers, the wavefront shell)
    if STATE.get("scrap") is not None:      # burnt paper: cream centre, black ragged edge, ember line
        MATS["MI_Paper_Ember"] = M._mi("MI_Paper_Ember", STATE["scrap"], {"Roughness": 0.85, "EmberStrength": 140.0},
                                       {"PaperColor": (0.5, 0.45, 0.35), "CharColor": (0.012, 0.01, 0.008),
                                        "EmberColor": (1.0, 0.32, 0.06)})
    else:
        _ps("MI_Paper_Ember", (0.05, 0.04, 0.03), 0.85, emis=(1.0, 0.3, 0.05), estr=6.0)
    _pe("MI_E_Ember", (1.0, 0.26, 0.03), 900.0)       # tiny, so it must be hot to read
    if STATE.get("shell") is not None:
        MATS["MI_RippleShell"] = M._mi("MI_RippleShell", STATE["shell"], {"Strength": S.RIPPLE_SHELL_STRENGTH},
                                       {"Color": S.RIPPLE_SHELL_COLOR})
        MATS["MI_RippleHaze"] = M._mi("MI_RippleHaze", STATE["shell"],
                                      {"Strength": S.RIPPLE_SHELL_STRENGTH * 0.32},
                                      {"Color": (0.55, 0.75, 0.95)})
    log("ripple materials ready: %d ripple instances" % len(MATS))
    return MATS


def E_WINDOW_A():
    return max(10.0, S.E_WINDOW_LIT * 0.85)     # State A night: cold TV-blue, but actually visible


def get(name):
    """Ripple or Riverside instance by name (built this run or loaded from disk)."""
    if name in MATS and MATS[name] is not None:
        return MATS[name]
    for folder in (S.MAT_DIR,):
        path = folder + "/" + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            MATS[name] = unreal.EditorAssetLibrary.load_asset(path)
            return MATS[name]
    return M.get(name)


def load_mpc():
    if STATE.get("mpc") is None:
        p = S.RIPPLE_MAT_DIR + "/" + S.RIPPLE_MPC_NAME
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            STATE["mpc"] = unreal.EditorAssetLibrary.load_asset(p)
    return STATE.get("mpc")
