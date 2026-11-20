"""Trial 1 sequences.

LS_Trial1_Flythrough (24 fps, 480 frames = 20 s, the MRQ render target) - the slice in four shots:
    S1 arrival   0-132   low on the wet alley floor beside the newspaper (TUESDAY, JANUARY 22, 2008);
                         the portal folds shut behind the trio (scale -> 0 by f54); rack focus from the
                         date to the three of them walking past the lens
    S2 crane   132-252   crane straight up the alley past the fire escapes: roofs, water towers, the El,
                         and the red DELI blade sign at the end of Cutler (where the player goes next)
    S3 blend   252-372   follow the trio across Delancey under the El toward the Lucky Star's neon
    S4 address 372-480   from the bodega's side of Cutler: TV-blue in the Cortaz top floor, down to the
                         bare bulb on the green side door as the trio arrive
LS_Trial1_Shift (264 frames = 11 s, played by the PIE director; no camera cuts) - the history edit:
    f0-60 headache (PPV_T1_Headache) -> f60 ignition at the stove -> the burn front (MPC_Ripple,
    Center keyed to the stove) tears State A away and burns State B in -> f132 the explosion (glass +
    door + debris, the blast flash) -> f150-264 burning.
    Pixel mode = ripple masters + MPC track; swap mode (fallback) = transform swaps at the same frames.
"""
import math

import unreal

from . import ripple_materials as RM
from . import sequence as SQ
from . import settings as S
from . import trial1 as T
from .util import component, error, log, save_asset, set_prop, spawn, step, warn

FPS = S.FPS
INFO = {"fly": None, "shift_mode": None, "groups": 0, "lights": 0, "cameras": 0, "center_key": False}
CAM_PATHS = {}           # camera label -> [(frame, loc)] (tools/camera_clearance.py trial1)
TRIO_PATHS = {}          # double label -> [(frame, loc)]


# =========================================================================== helpers
def _new(name, end):
    seq = SQ._new_sequence(name)
    SQ._setup_range(seq, end)
    return seq


def _nm(a):
    try:
        return a.get_actor_label()
    except Exception:
        return str(a)


def _xf(seq, actor, keys, end, interp="AUTO"):
    try:
        b = seq.add_possessable(actor)
        SQ.add_transform(seq, b, 0, end + 1, keys, interp=interp)
        return b
    except Exception as exc:
        warn("trial1 transform track %s: %s" % (_nm(actor), exc))
        return None


def _float(seq, actor, comp_cls, prop, keys, end, interp="AUTO", binding=None, path=None):
    try:
        ab = binding or seq.add_possessable(actor)
        cb = SQ.bind_component(seq, ab, component(actor, comp_cls))
        SQ.add_float_property(seq, cb, prop, path or prop, 0, end + 1, keys, interp=interp)
        return ab
    except Exception as exc:
        warn("trial1 float track %s.%s: %s" % (_nm(actor), prop, exc))
        return binding


def _actor_float(seq, actor, prop, keys, end, interp="LINEAR"):
    try:
        b = seq.add_possessable(actor)
        tr = b.add_track(unreal.MovieSceneFloatTrack)
        tr.set_property_name_and_path(prop, prop)
        sec = tr.add_section()
        sec.set_range(0, end + 1)
        ch = SQ._channels(sec)
        for f, v in keys:
            SQ._key(ch[0], f, v, interp)
        return b
    except Exception as exc:
        warn("trial1 actor float %s.%s: %s" % (_nm(actor), prop, exc))
        return None


def _lsa(seq, label, autoplay=False, disable_cuts=False, tags=()):
    lsa = spawn(unreal.LevelSequenceActor, (0, 0, 260), (0, 0, 0), label, "Trial1/Cinematics")
    try:
        lsa.set_sequence(seq)
    except Exception:
        set_prop(lsa, "level_sequence_asset", seq)
    try:
        ps = lsa.get_editor_property("playback_settings")
        ps.set_editor_property("auto_play", bool(autoplay))
        set_prop(ps, "disable_camera_cuts", bool(disable_cuts), quiet=True)
        set_prop(ps, "pause_at_end", True, quiet=True)
        lsa.set_editor_property("playback_settings", ps)
    except Exception as exc:
        warn("%s playback settings: %s" % (label, exc))
    T._tags(lsa, ["T1"] + list(tags))
    return lsa


def _camera_grade(cam, grade, ev):
    """Base 2008 grade on the camera with exposure locked (no histogram pumping between shots)."""
    try:
        cc = cam.get_cine_camera_component()
        s = cc.get_editor_property("post_process_settings")
        g = dict(grade)
        g["auto_exposure_min_brightness"] = float(ev)
        g["auto_exposure_max_brightness"] = float(ev)
        bad = []
        for k, v in g.items():
            try:
                s.set_editor_property(k, v)
                s.set_editor_property("override_" + k, True)
            except Exception:
                bad.append(k)
        cc.set_editor_property("post_process_settings", s)
        cc.set_editor_property("post_process_blend_weight", 1.0)
        return 1
    except Exception as exc:
        warn("trial1 camera grade %s: %s" % (_nm(cam), exc))
        return 0


# =========================================================================== the flythrough
WALK_CM_F = 160.0 / FPS            # 1.6 m/s: a low-profile walk


def _walk_keys(points, f0, f1, face_yaw, every=4):
    """Straight walk from points[0] to points[1] over f0..f1 (mannequin actor yaw = face - 90)."""
    keys = []
    frames = list(range(int(f0), int(f1), every)) + [int(f1)]
    for f in frames:
        t = (f - f0) / float(max(1, f1 - f0))
        p = tuple(points[0][j] + (points[1][j] - points[0][j]) * t for j in range(3))
        keys.append((f, p, (0.0, face_yaw - 90.0, 0.0), None))
    return keys


def _trio(seq, end):
    """The flythrough doubles (CINE_*), one continuous walk per shot; jumps only on the cuts."""
    sh = S.T1_FLY_SHOTS
    c = T.CURB
    # (start, end) per shot, per character: Rivers centre, Tyler left/behind, John right/behind
    plans = {
        "Rivers": [((-2550, 3760, c), (-2550, 3760 - WALK_CM_F * 252, c), 0, 252, -90.0),
                   ((-700, 640, 0), (-700 + WALK_CM_F * 120, 640, 0), 252, 372, 0.0),
                   ((1300, -640, c), (1300 + WALK_CM_F * 108, -640, c), 372, 480, 0.0)],
        "Tyler": [((-2610, 3830, c), (-2610, 3830 - WALK_CM_F * 252, c), 0, 252, -90.0),
                  ((-800, 590, 0), (-800 + WALK_CM_F * 120, 590, 0), 252, 372, 0.0),
                  ((1220, -580, c), (1220 + WALK_CM_F * 108, -580, c), 372, 480, 0.0)],
        "John": [((-2440, 3850, c), (-2440, 3850 - WALK_CM_F * 252, c), 0, 252, -90.0),
                 ((-790, 720, 0), (-790 + WALK_CM_F * 120, 720, 0), 252, 372, 0.0),
                 ((1240, -700, c), (1240 + WALK_CM_F * 108, -700, c), 372, 480, 0.0)],
    }
    n = 0
    for name, segs in plans.items():
        a = T.CINE.get(name)
        if a is None:
            continue
        keys = []
        for (p0, p1, f0, f1, yaw) in segs:
            seg = _walk_keys((p0, p1), f0, f1 - (1 if f1 < end else 0), yaw)
            keys += seg
        TRIO_PATHS["CINE_" + name] = [(k[0], k[1]) for k in keys]
        if _xf(seq, a, keys, end, interp="LINEAR"):
            n += 1
    # the gameplay companions stand at their B01 marks in the saved level: off-stage for the film
    for k, label in enumerate(("T1_Tyler", "T1_John")):
        a = T.CAST.get(label)
        if a is not None:
            park = (T.CINE_PARK[0] - 400 * (k + 1), T.CINE_PARK[1], T.CINE_PARK[2])
            _xf(seq, a, [(0, park, (0, 0, 0), None), (end, park, (0, 0, 0), None)], end, interp="CONSTANT")
    _ = sh
    return n


def _portal(seq, end):
    root = T.ACTORS.get("portal")
    if root is not None:
        try:
            v = root.get_actor_location()
            c = (v.x, v.y, v.z)
        except Exception:
            c = T.TB.MARKS["PortalCenter"][:3]
        _xf(seq, root, [(0, c, (0, 0, 0), (1.0, 1.0, 1.0)), (26, c, (0, 0, 0), (1.06, 1.06, 1.06)),
                        (40, c, (0, 0, 0), (0.7, 0.7, 0.7)), (54, c, (0, 0, 0), (0.001, 0.001, 0.001)),
                        (end, c, (0, 0, 0), (0.001, 0.001, 0.001))], end, interp="LINEAR")
    pl = T.ACTORS.get("portal_light")
    if pl is not None:
        cd = S.T1_PORTAL_CD
        _float(seq, pl, unreal.PointLightComponent, "Intensity",
               [(0, cd), (20, cd * 1.3), (30, cd * 0.4), (34, cd), (44, cd * 0.2), (48, cd * 0.6), (54, 0.0), (end, 0.0)],
               end, interp="LINEAR")


def _shot(seq, cut, label, frames, locs, targets, focal, fstop, ease=0.6, focus=None, grade_ev=None):
    s0, s1 = frames
    keys = SQ.sample_move(s0, s1, locs, targets, ease=ease, every=2)
    cam = SQ.make_camera(label, keys[0][1], targets[0], focal[0], fstop, None)
    b = seq.add_possessable(cam)
    SQ.add_transform(seq, b, s0, s1 + 1, keys)
    CAM_PATHS[label] = [(k[0], k[1]) for k in keys]
    _float(seq, cam, unreal.CineCameraComponent, "CurrentFocalLength", [(s0, focal[0]), (s1, focal[1])], s1,
           binding=b)
    if focus:
        _float(seq, cam, unreal.CineCameraComponent, "ManualFocusDistance", focus, s1, binding=b,
               path="FocusSettings.ManualFocusDistance")
    sec = cut.add_section()
    sec.set_range(int(s0), int(s1))
    sec.set_camera_binding_id(SQ._binding_id(seq, b))
    if T.GRADES:
        _camera_grade(cam, T.GRADES["base"], grade_ev if grade_ev is not None else T.look()["cam_ev"])
    T._tags(cam, ["T1", "T1.Camera"])
    INFO["cameras"] += 1
    return cam


def build_flythrough():
    end = int(S.T1_FLY_FRAMES)
    sh = S.T1_FLY_SHOTS
    CAM_PATHS.clear()
    TRIO_PATHS.clear()
    INFO["cameras"] = 0
    seq = _new(S.T1_SEQ_NAME, end)
    cut = SQ._add_track(seq, unreal.MovieSceneCameraCutTrack)
    paper = (-2470.0, 3330.0, 16.0)
    ev = T.look()["cam_ev"]
    _shot(seq, cut, "CAM_T1_S1_Arrival", sh["arrival"],
          [(-2330, 2980, 38), (-2330, 3050, 45), (-2330, 3120, 55)],
          [paper, paper, (-2520, 3300, 120), (-2520, 3080, 160)], (32.0, 35.0), 2.0, ease=0.5,
          focus=[(0, 377.0), (60, 377.0), (96, 300.0), (131, 170.0)], grade_ev=ev)
    _shot(seq, cut, "CAM_T1_S2_Crane", sh["crane"],
          [(-2560, 3050, 170), (-2580, 2750, 900), (-2560, 2300, 2400)],
          [(-2550, 2700, 150), (-2400, 1500, 500), (1150, 800, 500)], (24.0, 28.0), 4.0, ease=0.7, grade_ev=ev - 0.2)
    _shot(seq, cut, "CAM_T1_S3_BlendIn", sh["blend"],
          [(-1250, 560, 175), (-850, 580, 170), (-450, 600, 165)],
          [(1150, 1000, 300), (1150, 1000, 280), (1150, 950, 260)], (35.0, 45.0), 2.8, ease=0.4, grade_ev=ev)
    _shot(seq, cut, "CAM_T1_S4_Address", sh["address"],
          [(1350, 600, 140), (1450, 560, 158), (1550, 520, 175)],
          [(1650, -800, 900), (1850, -800, 520), (2010, -800, 160)], (40.0, 50.0), 2.8, ease=0.6, grade_ev=ev)
    n = _trio(seq, end)
    _portal(seq, end)
    save_asset(seq)
    _lsa(seq, "LSA_Trial1_Flythrough", tags=["T1.Flythrough"])
    INFO["fly"] = "%d cameras, %d walkers" % (INFO["cameras"], n)
    log("trial1 flythrough: %s, %d frames (%s)" % (INFO["fly"], end, ", ".join(
        "%s %d-%d" % (k, v[0], v[1]) for k, v in sh.items())))
    return seq


# =========================================================================== the shift (history edit)
SHIFT_END = int(S.T1_SHIFT_FRAMES)
IGNITE, BLAST, FULL = 60, 132, 150
R_KEYS = [(0, 0.0), (IGNITE, 0.0), (IGNITE + 12, 350.0), (BLAST, 1400.0), (FULL, float(S.T1_SHIFT_RADIUS)),
          (SHIFT_END, float(S.T1_SHIFT_RADIUS))]


def radius(f):
    for (f0, r0), (f1, r1) in zip(R_KEYS, R_KEYS[1:]):
        if f0 <= f <= f1:
            return r0 + (r1 - r0) * (f - f0) / float(max(1, f1 - f0))
    return R_KEYS[-1][1]


def hit(d):
    """First frame the burn front reaches distance d (cm) from the stove."""
    if d <= 0:
        return IGNITE
    for (f0, r0), (f1, r1) in zip(R_KEYS, R_KEYS[1:]):
        if r1 > r0 and r0 <= d <= r1:
            return int(round(f0 + (f1 - f0) * (d - r0) / (r1 - r0)))
    return FULL


def dist(p):
    c = S.T1_SHIFT_CENTER
    return math.sqrt(sum((p[i] - c[i]) ** 2 for i in range(3)))


def near_far(mn, mx):
    c = S.T1_SHIFT_CENTER
    near = math.sqrt(sum((max(mn[i], min(c[i], mx[i])) - c[i]) ** 2 for i in range(3)))
    far = math.sqrt(sum(max(abs(mn[i] - c[i]), abs(mx[i] - c[i])) ** 2 for i in range(3)))
    return near, far


def _mpc(seq):
    mpc = RM.load_mpc()
    masters_ok = unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/Masters/M_ECHO_RippleSurface")
    if mpc is None or not masters_ok:
        warn("trial1 shift: MPC_Ripple / ripple masters missing - transform swaps only")
        return False
    sk = {
        "Radius": R_KEYS,
        "Enable": [(0, 1.0), (SHIFT_END, 1.0)],
        "EdgeWidth": [(0, 260.0), (BLAST, 260.0), (FULL, 520.0), (SHIFT_END, 520.0)],
        "TearAmp": [(0, 70.0), (SHIFT_END, 90.0)],
        "EmberStrength": [(0, 500.0), (BLAST, 900.0), (FULL, 500.0), (SHIFT_END, 420.0)],
        "RimStrength": [(0, 0.0), (SHIFT_END, 0.0)],          # no 'rewrite line' on the street: it's a fire
        "ShellFade": [(0, 0.0), (SHIFT_END, 0.0)],
        "SkyRadius": [(0, 0.0), (SHIFT_END, 0.0)],             # the 2008 sky doesn't change
    }
    try:
        from . import ripple as RP
        tr = RP._mpc_track(seq, mpc, sk)
    except Exception as exc:
        error("trial1 shift MPC track failed (%s) - transform swaps" % exc)
        return False
    # Center lives in the shared MPC (its default is the ripple demo's bodega door): key it in the
    # section so only this sequence moves it. The director also sets it at runtime (belt + braces).
    try:
        secs = list(tr.get_sections())
        c = S.T1_SHIFT_CENTER
        ticks = RP._tick_scale(seq)
        for f in (0, SHIFT_END):
            secs[0].add_color_parameter_key(unreal.Name("Center"), unreal.FrameNumber(int(f * ticks)),
                                            unreal.LinearColor(c[0], c[1], c[2], 0.0))
        INFO["center_key"] = True
    except Exception as exc:
        warn("trial1 shift: Center vector key unavailable (%s) - the director sets MPC Center at runtime" % exc)
    return True


def _hidden(c):
    return (c[0], c[1], c[2] + T.HIDE_Z)


def _swap_groups(seq, pixel):
    n = 0
    one, tiny = (1.0, 1.0, 1.0), (0.01, 0.01, 0.01)
    for state in ("A", "B"):
        for g in T.GROUPS[state]:
            try:
                c = g.center
                mn, mx = g.aabb()
                dn, dfar = near_far(mn, mx)
                if g.when == "blast":
                    f = BLAST
                elif pixel:
                    f = min(SHIFT_END - 1, hit(dfar) + 2) if state == "A" else max(1, hit(dn) - 1)
                else:
                    f = hit(dist(c))
                if state == "A":
                    keys = [(0, c, (0, 0, 0), one), (f, c, (0, 0, 0), one), (f + 1, _hidden(c), (0, 0, 0), tiny)]
                else:
                    keys = [(0, _hidden(c), (0, 0, 0), tiny), (f, _hidden(c), (0, 0, 0), tiny), (f + 1, c, (0, 0, 0), one)]
                keys = [k for k in keys if 0 <= k[0] <= SHIFT_END]
                if _xf(seq, g.root, keys, SHIFT_END, interp="CONSTANT"):
                    n += 1
            except Exception as exc:
                warn("trial1 swap %s: %s" % (g.name, exc))
    INFO["groups"] = n
    return n


def _lights(seq):
    n = 0
    flick = T._rng
    for state in ("A", "B", "blast"):
        for (a, comp, cd, loc, label) in T.LIGHTS[state]:
            if comp is None:
                continue
            if state == "A":
                f = max(IGNITE + 1, hit(dist(loc)))
                keys = [(0, cd), (f - 3, cd), (f - 2, cd * 0.2), (f - 1, cd * 0.9), (f, 0.0), (SHIFT_END, 0.0)]
            elif state == "B":
                f = max(IGNITE, hit(dist(loc)))
                keys = [(0, 0.0), (f, 0.0)]
                ff = f + 2
                while ff < SHIFT_END:
                    keys.append((ff, cd * flick.uniform(0.55, 1.0) * (1.6 if BLAST <= ff <= BLAST + 8 else 1.0)))
                    ff += 3
                keys.append((SHIFT_END, cd * 0.8))
            else:
                keys = [(0, 0.0), (BLAST - 1, 0.0), (BLAST, cd), (BLAST + 3, cd * 0.45), (BLAST + 10, cd * 0.12),
                        (BLAST + 24, 0.0), (SHIFT_END, 0.0)]
            keys = sorted(dict((max(0, min(SHIFT_END, int(k[0]))), k[1]) for k in keys).items())
            cls = unreal.SpotLightComponent if isinstance(comp, unreal.SpotLightComponent) else unreal.PointLightComponent
            if _float(seq, a, cls, "Intensity", keys, SHIFT_END, interp="LINEAR"):
                n += 1
    INFO["lights"] = n
    return n


def _grades(seq):
    hd, bl = T.ACTORS.get("ppv_headache"), T.ACTORS.get("ppv_blast")
    if hd is not None:
        _actor_float(seq, hd, "BlendWeight", [(0, 0.0), (30, 0.9), (44, 0.75), (60, 0.0), (BLAST - 2, 0.0),
                                              (BLAST + 4, 0.5), (BLAST + 40, 0.0), (SHIFT_END, 0.0)], SHIFT_END)
    if bl is not None:
        _actor_float(seq, bl, "BlendWeight", [(0, 0.0), (BLAST - 1, 0.0), (BLAST, 1.0), (BLAST + 12, 0.35),
                                              (BLAST + 48, 0.0), (SHIFT_END, 0.0)], SHIFT_END)


def build_shift():
    seq = _new(S.T1_SHIFT_SEQ_NAME, SHIFT_END)
    pixel = False
    with step("trial1 shift: MPC track (burn front from the stove)"):
        pixel = _mpc(seq)
    INFO["shift_mode"] = "pixel" if pixel else "swap"
    with step("trial1 shift: State A -> B swaps"):
        _swap_groups(seq, pixel)
    with step("trial1 shift: light cues (A out, fire in, blast)"):
        _lights(seq)
    with step("trial1 shift: headache + blast grades"):
        _grades(seq)
    save_asset(seq)
    _lsa(seq, "LSA_Trial1_Shift", autoplay=False, disable_cuts=True, tags=["T1.Shift"])
    log("trial1 shift: mode=%s groups=%d lights=%d center_key=%s ignite f%d blast f%d full f%d (%d frames)" % (
        INFO["shift_mode"], INFO["groups"], INFO["lights"], INFO["center_key"], IGNITE, BLAST, FULL, SHIFT_END))
    return seq


def build(actors=None):
    if not T.GROUPS["A"] and not T.GROUPS["B"]:
        warn("trial1 sequence: no trial1 groups in this session - build the trial1_level stage first")
    fly = None
    with step("trial1: LS_Trial1_Flythrough"):
        fly = build_flythrough()
    with step("trial1: LS_Trial1_Shift"):
        build_shift()
    return fly
