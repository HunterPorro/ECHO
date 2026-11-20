"""Trial 1 materials: MIT1_* (state-invariant 2008 Riverside) + MIRT1_* (the history-edit states).

Everything is an instance of a master the gala / ripple stages already build (no new graphs):
    M_ECHO_Surface         plain PBR (+ procedural veins, tiles, Fresnel sheen)
    M_ECHO_Emissive        unlit glow (+ optional flicker: FlickerSpeed / FlickerAmount)
    M_ECHO_Glass           translucent glass (the Cortaz windows, the deli front)
    M_ECHO_RippleSurface   masked by MPC_Ripple: Side -1 = State A 'Before', +1 = State B 'Burning'
    M_ECHO_RippleEmissive  the same mask, unlit (fire, TV, candle)
    M_ECHO_RippleSkyDome   the 2008 sky (A and B halves set identical: the shift never changes the sky)
The riverside instances (MI_Brick_*, MI_Asphalt_Puddles, MI_Sidewalk, MI_Trim_*, MI_Iron_Black,
MI_Steel_ElGreen ...) are reused as-is, so 2008 Riverside and the ripple demo share one material set.
"""
import unreal

from . import materials as M
from . import ripple_materials as RM
from . import settings as S
from .util import log, warn

MATS = {}
STATE = {"ripple_masters": False}


def _look():
    return S.T1_LOOKS.get(S.T1_LOOK, S.T1_LOOKS["night"])


def _p(name, base, rough, metal=0.0, spec=0.5, vein=None, vstr=0.0, vscale=0.004, rvar=0.0, **extra):
    mi = M._surf(M.load_master("M_ECHO_Surface"), name, base, rough, metal, spec, vein, vstr, vscale, rvar, **extra)
    MATS[name] = mi
    return mi


def _e(name, color, strength, flicker=0.0, speed=9.0):
    mi = M._mi(name, M.load_master("M_ECHO_Emissive"),
               {"Strength": strength, "FlickerAmount": flicker, "FlickerSpeed": speed}, {"Color": color})
    MATS[name] = mi
    return mi


def _g(name, tint, opacity, edge, rough):
    mi = M._mi(name, M.load_master("M_ECHO_Glass"), {"Opacity": opacity, "EdgeOpacity": edge, "Roughness": rough},
               {"Tint": tint})
    MATS[name] = mi
    return mi


def _rs(name, side, base, rough, metal=0.0, vein=None, vstr=0.0, vscale=0.01, emis=None, estr=0.0):
    master = M.load_master("M_ECHO_RippleSurface")
    if master is None:      # no mask: plain surface (trial1.py keeps B hidden by transform until the shift)
        return _p(name, base, rough, metal, vein=vein, vstr=vstr, vscale=vscale)
    sc = {"Roughness": rough, "Metallic": metal, "Specular": 0.5, "VeinStrength": vstr, "VeinScale": vscale,
          "RoughnessVariation": 0.0, "EmissiveStrength": estr, "Side": float(side)}
    vc = {"BaseColor": base, "VeinColor": vein or base}
    if emis:
        vc["EmissiveColor"] = emis
    mi = M._mi(name, master, sc, vc)
    MATS[name] = mi
    return mi


def _re(name, side, color, strength):
    master = M.load_master("M_ECHO_RippleEmissive")
    if master is None:
        return _e(name, color, strength)
    mi = M._mi(name, master, {"Strength": strength, "Side": float(side), "Sky": 0.0}, {"Color": color})
    MATS[name] = mi
    return mi


def _sky(name):
    master = M.load_master("M_ECHO_RippleSkyDome")
    sky = _look()["sky"]
    if master is None:
        warn("M_ECHO_RippleSkyDome missing - %s is a flat unlit sky" % name)
        return _e(name, sky["Mid"], sky["Strength"])
    sc, vc = {"CloudScale": sky.get("CloudScale", 2.0)}, {}
    for p in ("A_", "B_"):
        sc[p + "Strength"] = sky["Strength"]
        sc[p + "CloudAmount"] = sky.get("CloudAmount", 0.8)
        vc[p + "Horizon"] = sky["Horizon"]
        vc[p + "Mid"] = sky.get("Mid", sky["Horizon"])
        vc[p + "Zenith"] = sky["Zenith"]
        vc[p + "CloudTint"] = sky.get("CloudTint", (0.6, 0.6, 0.65))
    mi = M._mi(name, master, sc, vc)
    MATS[name] = mi
    log("trial1 sky %s (%s): horizon %s zenith %s strength %.1f" % (name, S.T1_LOOK, sky["Horizon"], sky["Zenith"],
                                                                   sky["Strength"]))
    return mi


def build_all():
    STATE["ripple_masters"] = all(M.load_master(n) is not None for n in
                                  ("M_ECHO_RippleSurface", "M_ECHO_RippleEmissive"))
    if not STATE["ripple_masters"]:
        warn("trial1: ripple masters missing - the shift will hard-swap (no burning-paper tear)")
    _sky("MIT1_SkyDome")
    # ---------------- alley + street hardware
    _p("MIT1_Dumpster_Green", (0.018, 0.06, 0.035), 0.5, metal=0.55, vein=(0.12, 0.05, 0.02), vstr=0.55, vscale=0.03)
    _p("MIT1_Dumpster_Blue", (0.01, 0.03, 0.08), 0.5, metal=0.55, vein=(0.1, 0.05, 0.02), vstr=0.5, vscale=0.03)
    _p("MIT1_Wood_Pallet", (0.19, 0.13, 0.075), 0.85, vein=(0.08, 0.05, 0.03), vstr=0.6, vscale=0.06)
    _p("MIT1_Cardboard_Wet", (0.15, 0.1, 0.06), 0.9, vein=(0.08, 0.05, 0.03), vstr=0.4, vscale=0.05)
    _p("MIT1_TrashBag", (0.006, 0.006, 0.008), 0.2, spec=0.65)
    _p("MIT1_Chainlink", (0.24, 0.24, 0.25), 0.4, metal=0.9)
    _p("MIT1_Climb_Paint", (0.5, 0.38, 0.04), 0.6, vein=(0.12, 0.1, 0.08), vstr=0.55, vscale=0.05)
    _p("MIT1_Door_Steel", (0.025, 0.055, 0.045), 0.45, metal=0.6, vein=(0.12, 0.05, 0.02), vstr=0.4, vscale=0.03)
    _p("MIT1_Shutter", (0.16, 0.17, 0.18), 0.45, metal=0.8, vein=(0.09, 0.06, 0.04), vstr=0.45, vscale=0.02,
       tile=14.0, grout=0.6, grout_w=0.06, grout_col=(0.05, 0.05, 0.05))         # roll-up slats
    _p("MIT1_Concrete", (0.17, 0.17, 0.17), 0.8, vein=(0.09, 0.09, 0.09), vstr=0.45, vscale=0.01, rvar=-0.3)
    _p("MIT1_Portal_Ring", (0.10, 0.11, 0.13), 0.3, metal=0.9)
    _p("MIT1_Suit_Silver", (0.3, 0.32, 0.35), 0.35, metal=0.4, sheen=0.4, sheen_col=(0.5, 0.6, 0.7))
    _p("MIT1_Paper", (0.6, 0.58, 0.52), 0.85, vein=(0.3, 0.29, 0.27), vstr=0.3, vscale=0.08)
    # ---------------- interiors (the Cortaz apartment: 1990s, nicotine, worn)
    _p("MIT1_Plaster", (0.38, 0.34, 0.26), 0.85, vein=(0.24, 0.21, 0.15), vstr=0.35, vscale=0.01)
    _p("MIT1_Wallpaper", (0.09, 0.12, 0.085), 0.8, vein=(0.05, 0.07, 0.05), vstr=0.5, vscale=0.05,
       tile=12.0, grout=0.25, grout_w=0.08, grout_col=(0.12, 0.1, 0.06))          # faded stripe
    _p("MIT1_Floor_Wood", (0.12, 0.075, 0.045), 0.55, vein=(0.06, 0.035, 0.02), vstr=0.6, vscale=0.02,
       tile=19.0, grout=0.5, grout_w=0.02, grout_col=(0.02, 0.015, 0.01), tile_var=0.35, axis=(1.0, 0.1, 1.0))
    _p("MIT1_Linoleum", (0.3, 0.28, 0.24), 0.45, tile=30.0, grout=0.5, grout_w=0.01, grout_col=(0.1, 0.09, 0.08),
       tile_var=0.25)
    _p("MIT1_Carpet", (0.11, 0.045, 0.04), 0.95)
    _p("MIT1_Fabric_Couch", (0.15, 0.09, 0.05), 0.9, sheen=0.3, sheen_col=(0.3, 0.22, 0.16))
    _p("MIT1_Bedding", (0.3, 0.28, 0.26), 0.9, sheen=0.25, sheen_col=(0.45, 0.45, 0.45))
    _p("MIT1_Counter", (0.29, 0.27, 0.22), 0.4)
    _p("MIT1_Appliance", (0.52, 0.5, 0.45), 0.35, metal=0.2)
    _p("MIT1_CRT", (0.035, 0.035, 0.04), 0.4)
    _p("MIT1_Wood_Dark", (0.06, 0.035, 0.02), 0.5, vein=(0.03, 0.02, 0.01), vstr=0.5, vscale=0.03)
    # ---------------- the Lucky Star (2008: open, lit, stocked)
    _p("MIT1_Awning_Green", (0.02, 0.15, 0.065), 0.7, tile=60.0, grout=0.4, grout_w=0.5, grout_col=(0.55, 0.5, 0.4))
    _p("MIT1_Crate", (0.29, 0.19, 0.1), 0.8, vein=(0.14, 0.09, 0.05), vstr=0.5, vscale=0.05)
    _p("MIT1_Orange", (0.72, 0.24, 0.01), 0.45)
    _p("MIT1_Apple", (0.42, 0.02, 0.02), 0.3)
    _p("MIT1_Lime", (0.11, 0.38, 0.03), 0.4)
    _p("MIT1_Banana", (0.72, 0.52, 0.05), 0.5)
    _p("MIT1_Shelf", (0.55, 0.55, 0.56), 0.4, metal=0.6)
    _p("MIT1_Products_A", (0.52, 0.07, 0.05), 0.4)
    _p("MIT1_Products_B", (0.05, 0.18, 0.48), 0.4)
    _p("MIT1_Products_C", (0.68, 0.58, 0.1), 0.4)
    # ---------------- 2008 cars (glossy, wet)
    for nm, c in (("Maroon", (0.12, 0.012, 0.018)), ("Silver", (0.34, 0.35, 0.37)), ("Black", (0.008, 0.008, 0.01)),
                  ("Navy", (0.01, 0.018, 0.06)), ("Cab", (0.7, 0.45, 0.02)), ("Green", (0.02, 0.06, 0.04))):
        _p("MIT1_Car_" + nm, c, 0.22, metal=0.55, spec=0.6, sheen=0.35, sheen_col=(0.4, 0.42, 0.45))
    _p("MIT1_Car_Glass", (0.004, 0.005, 0.007), 0.03, spec=1.0)
    # ---------------- cast clothing (legs always get MI_Fabric_Trouser via gala.People)
    _p("MIT1_Cloth_RiversCoat", (0.016, 0.018, 0.026), 0.62, sheen=0.25, sheen_col=(0.12, 0.13, 0.16))
    _p("MIT1_Cloth_TylerJacket", (0.05, 0.055, 0.035), 0.7, sheen=0.2, sheen_col=(0.14, 0.15, 0.1))
    _p("MIT1_Cloth_JohnHoodie", (0.012, 0.012, 0.014), 0.85, sheen=0.15, sheen_col=(0.1, 0.1, 0.1))
    _p("MIT1_Cap", (0.025, 0.025, 0.03), 0.75)
    _p("MIT1_Cloth_Cop", (0.008, 0.012, 0.035), 0.55, sheen=0.25, sheen_col=(0.08, 0.1, 0.16))
    _p("MIT1_Cloth_Owner", (0.42, 0.39, 0.33), 0.85, sheen=0.2, sheen_col=(0.5, 0.48, 0.44))
    _p("MIT1_Cloth_Kid", (0.24, 0.025, 0.025), 0.85, sheen=0.2, sheen_col=(0.4, 0.12, 0.12))
    for nm, c in (("Camel", (0.28, 0.17, 0.08)), ("Grey", (0.13, 0.13, 0.135)), ("Puffer", (0.01, 0.01, 0.012)),
                  ("Burgundy", (0.12, 0.015, 0.025)), ("Olive", (0.06, 0.07, 0.035)), ("Denim", (0.04, 0.06, 0.12))):
        _p("MIT1_Cloth_" + nm, c, 0.8, sheen=0.2, sheen_col=(0.2, 0.2, 0.22))
    # ---------------- glass
    _g("MIT1_Glass_Dirty", (0.5, 0.55, 0.5), 0.24, 0.75, 0.14)
    _g("MIT1_Glass_Shop", (0.7, 0.75, 0.75), 0.1, 0.6, 0.05)
    # ---------------- emissives (the light path)
    n = float(S.E_T1_NEON)
    _e("MIT1_E_Neon_Red", (1.0, 0.04, 0.03), n)
    _e("MIT1_E_Neon_Blue", (0.07, 0.22, 1.0), n)
    _e("MIT1_E_Neon_Open", (1.0, 0.28, 0.04), n * 0.8, flicker=0.12, speed=23.0)
    _e("MIT1_E_Window_Warm", (1.0, 0.62, 0.32), S.E_T1_WINDOW)
    _e("MIT1_E_Window_TV", (0.45, 0.6, 1.0), S.E_T1_WINDOW * 0.9, flicker=0.35, speed=14.0)
    _e("MIT1_E_Bulb", (1.0, 0.76, 0.46), 70.0)
    _e("MIT1_E_Sodium", (1.0, 0.5, 0.14), 9.0)
    _e("MIT1_E_Fluoro", (0.84, 0.95, 1.0), 16.0, flicker=0.06, speed=41.0)
    _e("MIT1_E_Lightbox", (1.0, 0.94, 0.82), 20.0)
    _e("MIT1_E_Portal", (0.5, 0.78, 1.0), S.E_T1_PORTAL)
    _e("MIT1_E_PortalCore", (0.8, 0.92, 1.0), S.E_T1_PORTAL * 0.5, flicker=0.25, speed=30.0)
    _e("MIT1_E_Fluoro_Shop", (0.92, 0.98, 1.0), 26.0)
    # ---------------- State A 'Before' (Side -1: torn out by the burn front)
    A, B = -1, 1
    _rs("MIRT1_A_Curtain", A, (0.3, 0.23, 0.15), 0.9, vein=(0.2, 0.15, 0.1), vstr=0.4, vscale=0.04)
    _rs("MIRT1_A_Plant", A, (0.03, 0.08, 0.03), 0.8)
    _rs("MIRT1_A_Bedding", A, (0.3, 0.28, 0.26), 0.9)
    _rs("MIRT1_A_Couch", A, (0.15, 0.09, 0.05), 0.9)
    _rs("MIRT1_A_Wood", A, (0.06, 0.035, 0.02), 0.5, vein=(0.03, 0.02, 0.01), vstr=0.5, vscale=0.03)
    _re("MIRT1_A_TV", A, (0.5, 0.66, 1.0), 16.0)
    _re("MIRT1_A_Window_Warm", A, (1.0, 0.6, 0.3), 9.0)
    _re("MIRT1_A_Candle", A, (1.0, 0.62, 0.28), 140.0)
    _re("MIRT1_A_Bulb", A, (1.0, 0.82, 0.55), 70.0)
    # ---------------- State B 'Burning' (Side +1: burns in behind the front)
    _re("MIRT1_B_Fire", B, (1.0, 0.36, 0.05), S.E_T1_FIRE)
    _re("MIRT1_B_FireCore", B, (1.0, 0.72, 0.32), S.E_T1_FIRE * 1.7)
    _re("MIRT1_B_Ember", B, (1.0, 0.28, 0.03), S.E_T1_FIRE * 2.5)
    _rs("MIRT1_B_Smoke", B, (0.028, 0.027, 0.028), 1.0)
    _rs("MIRT1_B_SmokeLit", B, (0.08, 0.055, 0.045), 1.0, emis=(1.0, 0.32, 0.06), estr=0.9)
    _rs("MIRT1_B_Scorch", B, (0.008, 0.007, 0.006), 0.95, vein=(0.03, 0.02, 0.015), vstr=0.6, vscale=0.02)
    _rs("MIRT1_B_Debris", B, (0.06, 0.05, 0.045), 0.85, vein=(0.02, 0.018, 0.015), vstr=0.5, vscale=0.04)
    _rs("MIRT1_B_Charred", B, (0.012, 0.01, 0.009), 0.9, emis=(1.0, 0.25, 0.03), estr=0.6)
    log("trial1 materials ready: %d instances (%s look, ripple masters %s)" % (
        len(MATS), S.T1_LOOK, "ok" if STATE["ripple_masters"] else "MISSING"))
    return MATS


def get(name):
    if name in MATS and MATS[name] is not None:
        return MATS[name]
    path = S.MAT_DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        MATS[name] = unreal.EditorAssetLibrary.load_asset(path)
        return MATS[name]
    return RM.get(name)
