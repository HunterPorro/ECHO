"""LS_Ripple_Demo - the Timeline Ripple (24 fps, 480 frames = 20 s) + LS_Ripple_Live.

    S1  0-150    VACANT     crane down over the night corner, 24->30mm f/4, moonlight, sodium, fog
    S2  150-350  THE WAVE   low on the sidewalk facing the boarded door, 40->32mm f/2. The wave is
                            born at the door (frame 168), the street tears from grey to gold
                            toward us, it passes THROUGH the lens (~frame 212: shake, chromatic
                            split, flash), then we crane up and back to watch it eat the sky while
                            the first train in years rolls in overhead
    S3  350-480  BUSY       slow push-in past Josh's shoulder to Dad behind the counter, 45->60mm f/2

The wave: R(f) = R_AT_CAMERA * ((f - START) / CAMERA_FRAMES) ^ EXPONENT - slow at first (the
viewer reads it) then exponential (it outruns the eye and swallows the horizon).
Mode 'pixel' (MPC track built): ripple materials tear every surface at the wavefront; actor
transforms only clean up (A parts leave once fully outside the mask's reach, B parts arrive just
before the front). Mode 'swap' (MPC track failed): Enable=0 in the MPC and every prop tears/pops
at the moment the front crosses its centre - same timing, coarser.
"""
import math
import random

import unreal

from . import riverside as RV
from . import ripple_materials as RM
from . import sequence as SQ
from . import settings as S
from . import util as U
from .util import component, error, log, look_at, save_asset, set_prop, spawn, spawn_mesh, step, warn

MSE = unreal.MovieSceneSequenceExtensions
_rng = random.Random(S.RIPPLE_SEED + 11)
END = int(S.RIPPLE_FRAMES)
C = tuple(S.RIPPLE_CENTER)
HIDE_Z = -100000.0
SHOTS = {"vacant": (0, 150), "wave": (150, 365), "busy": (365, END)}
INFO = {"mode": None, "mpc_track": False, "groups": 0, "lights": 0, "fx": 0}


# =========================================================================== wave math
def _exp(t):
    """Two-phase growth: near-steady (EXPONENT_NEAR) until the front reaches R_AT_CAMERA, so it
    visibly walks across the street; exponential (EXPONENT) after, so it outruns the eye."""
    return getattr(S, "RIPPLE_EXPONENT_NEAR", S.RIPPLE_EXPONENT) if t <= 1.0 else S.RIPPLE_EXPONENT


def radius(f):
    t = (f - S.RIPPLE_START) / float(S.RIPPLE_CAMERA_FRAMES)
    if t <= 0:
        return 0.0
    return min(S.RIPPLE_R_MAX, S.RIPPLE_R_AT_CAMERA * t ** _exp(t))


def hit(d):
    """First frame the front reaches distance d (cm) from the centre (inverse of radius())."""
    d = max(0.0, min(d, S.RIPPLE_R_MAX))
    ratio = d / S.RIPPLE_R_AT_CAMERA
    return S.RIPPLE_START + S.RIPPLE_CAMERA_FRAMES * ratio ** (1.0 / _exp(ratio))


def log_timeline(cam_hit):
    """Radius timeline in the build log: where the ring is, frame by frame, while it is on screen."""
    frames = sorted(set([S.RIPPLE_START + k for k in range(0, 61, 6)] + [fi(cam_hit), fi(hit(149000)),
                                                                         fi(hit(451000)), fi(hit(S.RIPPLE_R_MAX))]))
    marks = {fi(hit(dist((640.0, 1010.0, 15.0)))): "east curb", fi(hit(dist((0.0, 900.0, 15.0)))): "street centre",
             fi(hit(dist((-640.0, 600.0, 15.0)))): "west curb", fi(cam_hit): "CAMERA", fi(hit(149000)): "sky (near dome)",
             fi(hit(451000)): "sky (far dome)"}
    for f in sorted(set(frames) | set(marks)):
        log("ripple radius: f%3d  %5.2fs  R=%8.0f cm  %s" % (f, f / float(S.FPS), radius(f), marks.get(f, "")))


def dist(p):
    return math.sqrt((p[0] - C[0]) ** 2 + (p[1] - C[1]) ** 2 + (p[2] - C[2]) ** 2)


def aabb_near_far(mn, mx):
    near = [min(max(C[i], mn[i]), mx[i]) for i in range(3)]
    far = [mn[i] if abs(C[i] - mn[i]) > abs(C[i] - mx[i]) else mx[i] for i in range(3)]
    return dist(near), dist(far)


def fi(x):
    return int(round(x))


# =========================================================================== sequence helpers
def _new(name):
    seq = SQ._new_sequence(name)
    SQ._setup_range(seq, END)
    return seq


def _xf(seq, actor, keys, interp="AUTO"):
    """keys: (frame, loc, rot, scale). Skips silently-failing actors with a warning."""
    try:
        b = seq.add_possessable(actor)
        SQ.add_transform(seq, b, 0, END + 1, keys, interp=interp)
        return b
    except Exception as exc:
        warn("transform track %s: %s" % (_nm(actor), exc))
        return None


def _float(seq, actor, comp_cls, prop, keys, interp="AUTO", binding=None):
    try:
        ab = binding or seq.add_possessable(actor)
        cb = SQ.bind_component(seq, ab, component(actor, comp_cls))
        SQ.add_float_property(seq, cb, prop, prop, 0, END + 1, keys, interp=interp)
        return ab
    except Exception as exc:
        warn("float track %s.%s: %s" % (_nm(actor), prop, exc))
        return binding


def _actor_float(seq, actor, prop, keys, interp="AUTO"):
    """Float property on the actor itself (PostProcessVolume.BlendWeight)."""
    try:
        b = seq.add_possessable(actor)
        tr = b.add_track(unreal.MovieSceneFloatTrack)
        tr.set_property_name_and_path(prop, prop)
        sec = tr.add_section()
        sec.set_range(0, END + 1)
        ch = SQ._channels(sec)
        for f, v in keys:
            SQ._key(ch[0], f, v, interp)
        return b
    except Exception as exc:
        warn("actor float track %s.%s: %s" % (_nm(actor), prop, exc))
        return None


def _color(seq, actor, comp_cls, prop, keys):
    """Linear-color property track (fog inscattering). Optional - logs and moves on."""
    try:
        ab = seq.add_possessable(actor)
        cb = SQ.bind_component(seq, ab, component(actor, comp_cls))
        tr = cb.add_track(unreal.MovieSceneColorTrack)
        tr.set_property_name_and_path(prop, prop)
        sec = tr.add_section()
        sec.set_range(0, END + 1)
        ch = SQ._channels(sec)
        if len(ch) < 3:
            raise RuntimeError("color section has %d channels" % len(ch))
        for f, rgb in keys:
            for i in range(3):
                SQ._key(ch[i], f, rgb[i])
            if len(ch) > 3:
                SQ._key(ch[3], f, 1.0)
    except Exception as exc:
        warn("color track %s.%s: %s" % (_nm(actor), prop, exc))


def _nm(a):
    try:
        return a.get_actor_label()
    except Exception:
        return str(a)


def _loc(a):
    v = a.get_actor_location()
    return (v.x, v.y, v.z)


def _rot(a):
    r = a.get_actor_rotation()
    return (r.pitch, r.yaw, r.roll)


def _scl(a):
    s = a.get_actor_scale3d()
    return (s.x, s.y, s.z)


# =========================================================================== the MPC track
def _tick_scale(seq):
    """Ticks per display frame (ParameterSection.add_*_parameter_key takes tick-resolution times)."""
    try:
        tr = MSE.get_tick_resolution(seq)
        dr = MSE.get_display_rate(seq)
        return (tr.numerator / float(tr.denominator)) / (dr.numerator / float(dr.denominator))
    except Exception:
        return 24000.0 / S.FPS


def _mpc_track(seq, mpc, scalar_keys):
    """scalar_keys: {param: [(frame, value), ...]}. Seeds each parameter with a tick-time key via the
    section API, then (preferred) re-keys through the scripting channels in display-rate frames."""
    tr = SQ._add_track(seq, unreal.MovieSceneMaterialParameterCollectionTrack)
    set_prop(tr, ["mpc", "MPC"], mpc)
    sec = tr.add_section()
    sec.set_range(0, END + 1)
    ticks = _tick_scale(seq)
    for name, keys in scalar_keys.items():
        f0, v0 = keys[0]
        sec.add_scalar_parameter_key(unreal.Name(name), unreal.FrameNumber(int(f0 * ticks)), float(v0))
    chans = {}
    for c in SQ._channels(sec):
        try:
            chans[str(c.get_editor_property("channel_name"))] = c
        except Exception:
            pass
    for name, keys in scalar_keys.items():
        ch = chans.get(name) or next((c for n, c in chans.items() if n.endswith(name)), None)
        if ch is not None:
            for k in list(ch.get_keys()):
                ch.remove_key(k)
            for f, v in keys:
                SQ._key(ch, f, v, "LINEAR")
        else:
            for f, v in keys[1:]:
                sec.add_scalar_parameter_key(unreal.Name(name), unreal.FrameNumber(int(f * ticks)), float(v))
    return tr


def _radius_keys():
    keys = [(0, 0.0), (S.RIPPLE_START, 0.0)]
    f = S.RIPPLE_START + 1
    while f <= END:
        r = radius(f)
        keys.append((f, r))
        if r >= S.RIPPLE_R_MAX:
            break
        f += 1 if f < S.RIPPLE_START + S.RIPPLE_CAMERA_FRAMES + 20 else 2
    keys.append((END, S.RIPPLE_R_MAX))
    return keys


def _sky_radius_keys(cam_hit):
    """The visible +X sky sits ~1.5 km out, so a world-space Radius only reaches it at f316.
    SkyRadius is a compressed distance so the dusk reveal sweeps the sky during the S2 crane-up
    (just after the wave hits the lens) and is done before the S3 push-in."""
    h = fi(cam_hit)
    return [(0, 0.0), (h + 6, 0.0), (h + 14, 40000.0), (h + 40, 149000.0),
            (h + 88, 340000.0), (h + 118, 500000.0), (END, 600000.0)]


def build_mpc_track(seq, cam_hit):
    mpc = RM.load_mpc()
    masters_ok = unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/Masters/M_ECHO_RippleSurface")
    if mpc is None or not masters_ok:
        warn("MPC_Ripple / ripple masters missing - using transform swaps only")
        return False
    sk = {
        "Radius": _radius_keys(),
        "Enable": [(0, 1.0), (END, 1.0)],
        # the tear widens as it accelerates (reads at distance), embers flare as it hits camera
        "EdgeWidth": [(0, S.RIPPLE_EDGE_WIDTH), (fi(cam_hit), S.RIPPLE_EDGE_WIDTH * 1.3),
                      (fi(cam_hit) + 80, S.RIPPLE_EDGE_WIDTH * 3.0), (END, S.RIPPLE_EDGE_WIDTH * 5.0)],
        # keep the tear a gentle wobble even at distance - v3's *10/*40 turned the ring into scribbles
        "TearAmp": [(0, S.RIPPLE_TEAR_AMP), (fi(cam_hit) + 80, S.RIPPLE_TEAR_AMP * 1.6), (END, S.RIPPLE_TEAR_AMP * 2.2)],
        "EmberStrength": [(0, S.RIPPLE_EMBER_STRENGTH), (fi(cam_hit) - 4, S.RIPPLE_EMBER_STRENGTH * 1.6),
                          (fi(cam_hit) + 40, S.RIPPLE_EMBER_STRENGTH), (END, S.RIPPLE_EMBER_STRENGTH * 0.8)],
        "ShellFade": [(0, 1.0), (fi(cam_hit) - 2, 1.0), (fi(cam_hit) + 3, 0.0), (END, 0.0)],
        # the rewrite line: bright on approach, flares on the lens, stays as a clean ring in the sky
        "RimStrength": [(0, S.RIPPLE_RIM_STRENGTH), (fi(cam_hit) - 6, S.RIPPLE_RIM_STRENGTH * 1.5),
                        (fi(cam_hit), S.RIPPLE_RIM_STRENGTH * 2.5), (fi(cam_hit) + 12, S.RIPPLE_RIM_STRENGTH),
                        (END, S.RIPPLE_RIM_STRENGTH * 1.2)],
        # the sky is 1.5 km out; a dedicated radius lets dusk start as we crane up after the lens hit
        # instead of waiting until f316-369 (end of S2), when the shot is already leaving the sky
        "SkyRadius": _sky_radius_keys(cam_hit),
    }
    try:
        _mpc_track(seq, mpc, sk)
    except Exception as exc:
        error("MPC track failed (%s) - disabling the pixel mask, using transform swaps" % exc)
        try:
            RM.set_mpc_default(mpc, {"Enable": 0.0})
        except Exception as exc2:
            warn("could not set MPC Enable=0: %s" % exc2)
        return False
    try:   # editor/PIE without the sequence: only Vacant shows (Radius 0, Enable 1)
        RM.set_mpc_default(mpc, {"Enable": 1.0, "Radius": 0.0})
    except Exception:
        pass
    return True


# =========================================================================== world tracks
GONE = (0.001, 0.001, 0.001)   # hide by scale where keys interpolate (motion blur samples sub-frames)


def _hidden(c):
    return (c[0], c[1], c[2] + HIDE_Z)


def swap_groups(seq, pixel):
    n = 0
    for state in ("A", "B"):
        for g in RV.GROUPS[state]:
            try:
                c = _loc(g.root)
                mn, mx = g.aabb()
                dn, dfar = aabb_near_far(mn, mx)
                tiny = (0.01, 0.01, 0.01)
                one = (1.0, 1.0, 1.0)
                if pixel:
                    # the mask does the visible work; transforms only remove what the mask can't (text,
                    # lights' meshes) and keep B out of the editor / pre-wave frames
                    if state == "A":
                        f = min(END, fi(hit(dfar)) + 2)
                        keys = [(0, c, (0, 0, 0), one), (f, c, (0, 0, 0), one), (f + 1, _hidden(c), (0, 0, 0), tiny)]
                    else:
                        f = max(1, fi(hit(dn)) - 1)
                        keys = [(0, _hidden(c), (0, 0, 0), tiny), (f, _hidden(c), (0, 0, 0), tiny), (f + 1, c, (0, 0, 0), one)]
                    interp = "CONSTANT"
                else:
                    f = fi(hit(dist(g.center)))
                    if state == "A":
                        if g.pop:   # torn away: lift, stretch, gone
                            keys = [(0, c, (0, 0, 0), one), (f, c, (0, 0, 0), one),
                                    (f + 2, (c[0], c[1], c[2] + 25), (0, 0, 4), (1.04, 1.04, 1.1)),
                                    (f + 4, (c[0], c[1], c[2] + 60), (0, 0, 9), GONE), (END, (c[0], c[1], c[2] + 60), (0, 0, 9), GONE)]
                        else:
                            keys = [(0, c, (0, 0, 0), one), (f, c, (0, 0, 0), one), (f + 1, _hidden(c), (0, 0, 0), tiny)]
                    else:
                        if g.pop:   # unfolds into place with a small overshoot
                            keys = [(0, c, (0, 0, 0), GONE), (f - 1, c, (0, 0, 0), GONE),
                                    (f, c, (0, 0, 0), (0.05, 0.05, 0.05)), (f + 3, c, (0, 0, 0), (1.06, 1.06, 1.06)),
                                    (f + 6, c, (0, 0, 0), one)]
                        else:
                            keys = [(0, _hidden(c), (0, 0, 0), tiny), (f, _hidden(c), (0, 0, 0), tiny), (f + 1, c, (0, 0, 0), one)]
                    interp = "CONSTANT" if not g.pop else "LINEAR"
                keys = [k for k in keys if 0 <= k[0] <= END] or keys[:1]
                if _xf(seq, g.root, keys, interp=interp):
                    n += 1
            except Exception as exc:
                warn("swap %s: %s" % (g.name, exc))
    INFO["groups"] = n
    log("ripple swaps: %d groups keyed (%s mode)" % (n, "pixel" if pixel else "swap"))


def ramp_lights(seq):
    n = 0
    for state in ("A", "B"):
        for (a, comp, cd, loc) in RV.LIGHTS[state]:
            if comp is None:
                continue
            f = fi(hit(dist(loc)))
            if state == "A":     # dies with a stutter, like a ballast giving up
                keys = [(0, cd), (f - 3, cd), (f - 2, cd * 0.15), (f - 1, cd * 0.8), (f, 0.0), (END, 0.0)]
            else:                # strikes on: two flickers, then full (neon/sodium warm-up)
                keys = [(0, 0.0), (f, 0.0), (f + 1, cd * 0.7), (f + 2, cd * 0.1), (f + 4, cd), (f + 5, cd * 0.4),
                        (f + 7, cd), (END, cd)]
            keys = sorted(set((max(0, min(END, int(k[0]))), k[1]) for k in keys))
            cls = unreal.SpotLightComponent if isinstance(comp, unreal.SpotLightComponent) else unreal.PointLightComponent
            if _float(seq, a, cls, "Intensity", keys, interp="LINEAR"):
                n += 1
    INFO["lights"] = n


def env_tracks(seq, cam_hit):
    """Sun, sky light, fog and the grade cross over while the wave is on the camera."""
    A = RV.ACTORS
    h = fi(cam_hit)
    w0, w1 = h - 3, h + 26                # the world under the camera turns over ~1 s
    sun = A.get("sun")
    if sun:
        b = _xf(seq, sun, [(0, (0, 0, 4000), (S.A_SUN_ROT[0], S.A_SUN_ROT[1], 0), None),
                           (w0, (0, 0, 4000), (S.A_SUN_ROT[0], S.A_SUN_ROT[1], 0), None),
                           (w1, (0, 0, 4000), (S.B_SUN_ROT[0], S.B_SUN_ROT[1], 0), None),
                           (END, (0, 0, 4000), (S.B_SUN_ROT[0] + 0.8, S.B_SUN_ROT[1] - 1.5, 0), None)])
        b = _float(seq, sun, unreal.DirectionalLightComponent, "Intensity",
                   [(0, S.A_SUN_LUX), (w0, S.A_SUN_LUX), (w1, S.B_SUN_LUX), (END, S.B_SUN_LUX)],
                   binding=b)
        _float(seq, sun, unreal.DirectionalLightComponent, "Temperature",
               [(0, S.A_SUN_K), (w0, S.A_SUN_K), (w1, S.B_SUN_K), (END, S.B_SUN_K)], binding=b)
    sky = A.get("skylight")
    if sky:
        ia, ib = float(getattr(S, "A_SKYLIGHT", 1.55)), float(getattr(S, "B_SKYLIGHT", 1.25))
        _float(seq, sky, unreal.SkyLightComponent, "Intensity",
               [(0, ia), (w0, ia), (w1, ib), (END, ib)])
    fog = A.get("fog")
    if fog:
        fb = _float(seq, fog, unreal.ExponentialHeightFogComponent, "FogDensity",
                    [(0, S.A_FOG_DENSITY), (w0, S.A_FOG_DENSITY), (w1, S.B_FOG_DENSITY), (END, S.B_FOG_DENSITY)])
        _float(seq, fog, unreal.ExponentialHeightFogComponent, "VolumetricFogExtinctionScale",
               [(0, S.A_FOG_EXTINCTION), (w0, S.A_FOG_EXTINCTION), (w1, S.B_FOG_EXTINCTION), (END, S.B_FOG_EXTINCTION)],
               binding=fb)
        _color(seq, fog, unreal.ExponentialHeightFogComponent, "FogInscatteringLuminance",
               [(0, S.A_FOG_COLOR), (w0, S.A_FOG_COLOR), (w1, S.B_FOG_COLOR), (END, S.B_FOG_COLOR)])
    if A.get("ppv_b"):
        _actor_float(seq, A["ppv_b"], "BlendWeight", [(0, 0.0), (w0, 0.0), (h + 14, 0.55), (h + 40, 1.0), (END, 1.0)])
    if A.get("ppv_hit"):
        _actor_float(seq, A["ppv_hit"], "BlendWeight",
                     [(0, 0.0), (h - 5, 0.0), (h - 1, 0.6), (h, 1.0), (h + 3, 0.75), (h + 16, 0.0), (END, 0.0)])


def shell_and_fx(seq, cam_hit):
    """The visible wavefront bubble + a slightly larger heat-haze shell, then paper shreds and
    embers thrown off where it tears the world. Both shells hide just as they would swallow the lens."""
    def _shell_keys(scale_mul, until):
        keys = [(0, C, (0, 0, 0), GONE), (S.RIPPLE_START, C, (0, 0, 0), GONE)]
        f = S.RIPPLE_START + 1
        while f <= min(END, until):
            s = max(0.01, 2.0 * radius(f) / 100.0 * scale_mul)
            keys.append((f, C, (0, 0, 0), (s, s, s)))
            f += 1
        keys.append((until + 1, C, (0, 0, 0), GONE))
        keys.append((END, C, (0, 0, 0), GONE))
        return keys

    until = fi(cam_hit) + 4
    shell = spawn_mesh("sphere", C, GONE, RM.get("MI_RippleShell"), label="Ripple_Shell",
                       folder="Ripple/FX", movable=True, shadows=False, collision=False)
    _xf(seq, shell, _shell_keys(1.0, until), interp="LINEAR")
    haze_mat = RM.get("MI_RippleHaze") or RM.get("MI_RippleShell")
    haze = spawn_mesh("sphere", C, GONE, haze_mat, label="Ripple_Haze",
                      folder="Ripple/FX", movable=True, shadows=False, collision=False)
    _xf(seq, haze, _shell_keys(1.08, until), interp="LINEAR")
    _fx(seq, cam_hit)


CAM = {}      # frame -> camera location (filled by build_cameras; FX keep clear of it)


def _cam_at(f):
    if not CAM:
        return (-560.0, 250.0, 162.0)
    k = min(CAM, key=lambda x: abs(x - f))
    return CAM[k]


def _front_speed(f):
    """Wavefront speed in cm/s at frame f (dR/dt)."""
    t = f - S.RIPPLE_START
    if t <= 0.5:
        return 0.0
    return _exp(t / float(S.RIPPLE_CAMERA_FRAMES)) * radius(f) / t * S.FPS


def _trajectory(kind, base, f0, life, rr):
    """Positions/rotations/scales every 2 frames: the particle is flung off the tear and rides the
    wavefront for a beat (streaking along it), then drag takes over - paper flutters down, embers
    rise and burn out."""
    d = max(1.0, dist(base))
    n = ((base[0] - C[0]) / d, (base[1] - C[1]) / d, max(-0.2, (base[2] - C[2]) / d) + 0.15)
    ride = rr.randint(10, 18) if kind == "shred" else rr.randint(8, 14)
    lo, hi = S.RIPPLE_SHRED_SIZE if kind == "shred" else S.RIPPLE_EMBER_SIZE
    size = rr.uniform(lo, hi)
    width = size * rr.uniform(0.55, 0.9)
    p = list(base)
    v = [0.0, 0.0, 0.0]
    out = []
    phase = rr.uniform(0, 6.28)
    for j in range(0, life + 1):
        f = f0 + j
        if j <= ride:          # carried by the front (a fraction of its speed, capped)
            sp = min(0.3 * _front_speed(f), 1500.0 if kind == "shred" else 2200.0)
            v = [n[0] * sp, n[1] * sp, n[2] * sp * 0.5]
        else:                  # drag, gravity (paper) / buoyancy (embers), flutter
            v = [v[0] * 0.9, v[1] * 0.9, v[2] * 0.9 + (-45.0 if kind == "shred" else 70.0) / S.FPS * 3]
        sway = math.sin(phase + j * 0.45) * (35.0 if kind == "shred" else 12.0)
        p = [p[0] + v[0] / S.FPS - n[1] * sway / S.FPS, p[1] + v[1] / S.FPS + n[0] * sway / S.FPS,
             max(3.0, p[2] + v[2] / S.FPS)]
        if j % 2 and j != life:
            continue
        spd = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
        yaw = math.degrees(math.atan2(v[1], v[0])) if spd > 1 else 0.0
        pitch = math.degrees(math.atan2(v[2], math.hypot(v[0], v[1]))) if spd > 1 else 0.0
        burn = max(0.0, 1.0 - (j / float(life)) ** 3)
        if kind == "shred":    # thin plane, edge-on to its motion while riding, then tumbling flutter
            roll = math.sin(phase + j * 0.6) * (25.0 if j <= ride else 70.0)
            sc = (max(0.001, size * burn / 100.0), max(0.001, width * burn / 100.0), 0.002)
            rot = (pitch + math.sin(phase + j * 0.35) * 20.0, yaw, roll)
        else:                  # motion streak: stretched along the velocity (a cheap trail)
            streak = min(28.0, spd / S.FPS * 0.85)
            s0 = max(0.001, size * burn / 100.0)
            sc = (max(0.001, (size + streak) * burn / 100.0), s0, s0)
            rot = (pitch, yaw, 0.0)
        out.append((f, tuple(p), rot, sc))
    return out


def _fx(seq, cam_hit):
    rr = random.Random(S.RIPPLE_SEED + 21)
    n, rejected = 0, 0
    clear = float(S.RIPPLE_FX_CLEARANCE)
    for kind, count, mname in (("shred", S.RIPPLE_SHRED_COUNT, "MI_Paper_Ember"),
                               ("ember", S.RIPPLE_EMBER_COUNT, "MI_E_Ember")):
        made = 0
        tries = 0
        while made < int(count) and tries < int(count) * 12:
            tries += 1
            # spawn where the tear is happening on screen: sidewalks + street between the door
            # and the camera, the storefront, the El columns - never on the lens
            # two bands: a dense sheet on the street between the door and the lens, plus a wider
            # sprinkling so shreds also peel off the facade and the near curb
            tight = rr.random() < 0.7
            ang = rr.uniform(-0.7, 0.7) + math.atan2(250 - C[1], -560 - C[0]) if tight else (
                rr.uniform(-2.4, 0.3) + math.atan2(260 - C[1], -520 - C[0]) + 1.2)
            r = rr.uniform(200, 2000) if tight else rr.uniform(150, 3200)
            base = (C[0] + math.cos(ang) * r, C[1] + math.sin(ang) * r,
                    rr.uniform(8, 220 if kind == "shred" else 340))
            f0 = fi(hit(dist(base)))
            if f0 >= END - 12 or f0 < S.RIPPLE_START:
                continue
            traj = _trajectory(kind, base, f0, rr.randint(30, 60) if kind == "shred" else rr.randint(18, 40), rr)
            if any(math.dist(k[1], _cam_at(k[0])) < clear for k in traj):
                rejected += 1
                continue
            a = spawn_mesh("cube" if kind == "shred" else "sphere", base, GONE, RM.get(mname),
                           label="Ripple_%s_%02d" % (kind, made), folder="Ripple/FX", movable=True, shadows=False,
                           collision=False)
            ks = [(0, base, (0, 0, 0), GONE), (f0 - 1, base, (0, 0, 0), GONE)] + traj
            last = traj[-1]
            if last[0] < END:
                ks.append((min(END, last[0] + 1), last[1], last[2], GONE))
            ks = sorted({k[0]: k for k in ks}.values(), key=lambda k: k[0])
            if _xf(seq, a, ks, interp="LINEAR"):
                n += 1
            made += 1
    INFO["fx"] = n
    INFO["fx_rejected_near_camera"] = rejected


def train_track(seq):
    tr = RV.ACTORS.get("train")
    if not tr:
        return
    c = _loc(tr)
    _xf(seq, tr, [(0, c, (0, 0, 0), None), (230, c, (0, 0, 0), None),
                  (330, (c[0], c[1] + 11500, c[2]), (0, 0, 0), None),
                  (400, (c[0], c[1] + 16500, c[2]), (0, 0, 0), None), (END, (c[0], c[1] + 16500, c[2]), (0, 0, 0), None)])


def walkers(seq):
    for (a, loc, vel) in RV.PEOPLE_B:
        if vel is None:
            continue
        try:
            f0 = max(1, fi(hit(dist(loc))) - 1)
            yaw = _rot(a)[1]
            ks = [(0, loc, (0, yaw, 0), GONE), (f0, loc, (0, yaw, 0), GONE)]
            for f in list(range(f0 + 1, END, 12)) + [END]:
                t = (f - f0) / float(S.FPS)
                ks.append((f, (loc[0] + vel[0] * t, loc[1] + vel[1] * t, loc[2]), (0, yaw, 0), (1.0, 1.0, 1.0)))
            _xf(seq, a, ks, interp="LINEAR")
        except Exception as exc:
            warn("walker: %s" % exc)


# =========================================================================== cameras
def _move(s0, s1, locs, targets, ease=0.6, shake=None):
    """Eased Catmull-Rom keys every 2 frames; every frame inside the shake window, with a decaying
    handheld jolt (the wave hitting the lens) layered on location + roll."""
    keys = []
    frames = set(range(int(s0), int(s1), 2)) | {int(s1)}
    if shake:
        frames |= set(range(max(int(s0), shake[0]), min(int(s1), shake[1]) + 1))
    jr = random.Random(S.RIPPLE_SEED + 3)
    for f in sorted(frames):
        t = (f - s0) / float(max(1, s1 - s0))
        u = SQ._soft_ease(t, ease)
        loc = list(SQ._catmull(locs, u))
        tgt = SQ._catmull(targets, u)
        roll = 0.0
        if shake and shake[0] <= f <= shake[1]:
            k = (f - shake[0]) / float(max(1, shake[1] - shake[0]))
            amp = math.exp(-4.0 * k) * (1.0 if f >= shake[2] else 0.35)
            loc = [loc[0] + jr.uniform(-9, 9) * amp, loc[1] + jr.uniform(-9, 9) * amp, loc[2] + jr.uniform(-6, 6) * amp]
            roll = jr.uniform(-2.2, 2.2) * amp
        p, y = look_at(loc, tgt)
        keys.append((f, tuple(loc), (p, y, roll), None))
    return keys


def _log_s2_clearance(keys, h, s1):
    """Sanity-check the S2 path against El bents, the west fire-escape plane, and the El deck
    *after* the hit-flash window (frames inside the flash may graze the deck as we rise)."""
    bents = getattr(RV, "EL_BENTS", (-900, 900))
    n_col = n_esc = n_deck = 0
    sky_frames = 0
    sky0 = sky1 = None
    for f, loc, rot, _sc in keys:
        x, y, z = loc
        for bx, by in ((-640.0, by) for by in bents):
            if abs(x - bx) < 80 and abs(y - by) < 80:
                n_col += 1
                break
        if x < -1042 + 60:
            n_esc += 1
        # look ray vs El deck, only after the flash
        if f >= h + 18 and rot is not None:
            pitch, yaw = rot[0], rot[1]
            # a point 4 m along the look
            import math as _m
            d = 4000.0
            pr, yr = _m.radians(pitch), _m.radians(yaw)
            tgt = (x + d * _m.cos(pr) * _m.cos(yr), y + d * _m.cos(pr) * _m.sin(yr), z + d * _m.sin(pr))
            dx, dy, dz = tgt[0] - x, tgt[1] - y, tgt[2] - z
            hit = False
            if abs(dx) > 1e-3:
                for plane in (-345.0, 345.0):
                    u = (plane - x) / dx
                    if 0 <= u <= 1 and 640 <= (z + u * dz) <= 845:
                        hit = True
            if hit:
                n_deck += 1
            if pitch >= 6.0:
                sky_frames += 1
                if sky0 is None:
                    sky0 = f
                sky1 = f
    hold_s = (0.0 if sky0 is None else (sky1 - sky0) / float(S.FPS))
    log("S2 clearance: %d keys, bent grazes %d, fire-escape grazes %d, post-flash deck crossings %d, sky-hold %.1fs (f%s-f%s)" % (
        len(keys), n_col, n_esc, n_deck, hold_s, sky0 if sky0 is not None else "-", sky1 if sky0 is not None else "-"))


def build_cameras(seq, cam_hit):
    A = RV.ACTORS
    door = A.get("focus_door")
    dad = A.get("focus_counter")
    door_p = _loc(door) if door else (1150.0, 1012.0, 150.0)
    dad_p = _loc(dad) if dad else (1500.0, 1030.0, 165.0)
    cut = SQ._add_track(seq, unreal.MovieSceneCameraCutTrack)
    h = fi(cam_hit)

    def shot(label, frames, keys, focal_keys, fstop, track_actor, offset=(0, 0, 0)):
        s0, s1 = frames
        k0 = keys[0]
        tgt = (k0[1][0] + 1000 * math.cos(math.radians(k0[2][1])), k0[1][1] + 1000 * math.sin(math.radians(k0[2][1])), k0[1][2])
        cam = SQ.make_camera(label, k0[1], tgt, focal_keys[0][1], fstop, track_actor, offset)
        b = seq.add_possessable(cam)
        SQ.add_transform(seq, b, s0, s1 + 1, keys)
        for k in keys:
            CAM[k[0]] = k[1]
        _float(seq, cam, unreal.CineCameraComponent, "CurrentFocalLength", focal_keys, binding=b)
        sec = cut.add_section()
        sec.set_range(int(s0), int(s1))
        sec.set_camera_binding_id(SQ._binding_id(seq, b))
        return cam, b

    s0, s1 = SHOTS["vacant"]       # S1: over the rooftops and water towers, drop under the El onto the door
    # frame 0 keeps the El deck in the lower third and the corner on the right third; the crane
    # sinks below the deck (the tie shadows comb the wet street) and lands low on the dead door
    c1, _b1 = shot("CAM_R1_Vacant_Crane", SHOTS["vacant"],
         _move(s0, s1, [(-3000, -250, 1000), (-2500, 0, 600), (-1900, 150, 240)],
               [(1400, 1250, 900), (1300, 1150, 420), door_p], ease=0.8),
         [(s0, 28.0), (s1, 32.0)], 4.0, door)
    s0, s1 = SHOTS["wave"]
    # v4 mid-stretch went black: the lens sat in the roadway at X=-520 (120 cm from an El
    # column) then craned into the deck underside. Wait on the WEST SIDEWALK (X~-870: 150 cm
    # from fire escapes, 200 cm from El bents, between bents at Y=-900 and 900) so the
    # shockwave has a clear lane down the street. After the hit, the rise happens during the
    # flash, then we hold a dusk-sky frame (24 mm, roofline in the lower third) for 2+ seconds.
    a = _move(s0, h + 2,
              [(-870.0, 350.0, 168.0), (-880.0, 340.0, 165.0), (-890.0, 330.0, 162.0)],
              [(1140.0, 1010.0, 148.0), (1140.0, 1010.0, 150.0), (1140.0, 1012.0, 152.0)],
              ease=0.3, shake=(h - 4, h + 18, h))
    # Rise during the hit flash so the look can snap from the door (rays duck under the
    # El) to a view over the deck without a black slab on screen. Then tilt to a 24 mm
    # dusk-sky frame (roofline in the lower third) and hold it for 2+ seconds.
    b_rise = _move(h + 2, h + 20,
                   [(-890.0, 330.0, 162.0), (-875.0, 305.0, 500.0), (-870.0, 280.0, 920.0)],
                   [(1140.0, 1012.0, 152.0), (1140.0, 1012.0, 200.0), (900.0, 1080.0, 1200.0)],
                   ease=0.4, shake=(h + 2, h + 18, h))
    b_tilt = _move(h + 20, h + 90,
                   [(-870.0, 280.0, 920.0), (-870.0, 250.0, 945.0), (-870.0, 240.0, 950.0)],
                   [(900.0, 1080.0, 1200.0), (850.0, 1140.0, 1420.0), (850.0, 1140.0, 1420.0)],
                   ease=0.55)
    b_hold = _move(h + 90, s1,
                   [(-870.0, 240.0, 950.0), (-870.0, 235.0, 952.0), (-870.0, 230.0, 955.0)],
                   [(850.0, 1140.0, 1420.0), (840.0, 1130.0, 1410.0), (830.0, 1120.0, 1400.0)],
                   ease=0.0)
    keys = sorted({k[0]: k for k in a + b_rise + b_tilt + b_hold}.values(), key=lambda k: k[0])
    c2, b2 = shot("CAM_R2_The_Wave", SHOTS["wave"], keys, [(s0, 35.0), (h, 32.0), (h + 20, 28.0), (s1, 24.0)], 2.0, door)
    _log_s2_clearance(keys, h, s1)
    s0, s1 = SHOTS["busy"]         # S3: down the west sidewalk, past Josh's shoulder, to Dad at the counter
    # the lens line threads between the El bents at Y 900 / 2500 the whole way (no pillar across
    # the storefront) and aims between Dad and the sign so LUCKY STAR DELI + OPEN sit in frame
    aim = (1350.0, 1130.0, 215.0)
    c3, _b3 = shot("CAM_R3_Busy_PushIn", SHOTS["busy"],
         _move(s0, s1, [(-950, 2000, 150), (-975, 1700, 158), (-1000, 1430, 165)],
               [(1300, 1250, 230), aim, aim], ease=0.6),
         [(s0, 40.0), (s1, 55.0)], 2.0, dad)
    # the grade lives ON THE CAMERAS (v2: both states rendered warm; the PPV_B blend track is not
    # trusted). S1 = Vacant at weight 1, S2 = Busy keyed 0 -> 1 as the world turns over, S3 = Busy.
    G = RV.GRADES
    ok = 0
    if G:
        ok += _camera_grade(c1, G["A"], 1.0)
        ok += _camera_grade(c2, G["B"], 0.0)
        ok += _camera_grade(c3, G["B"], 1.0)
        _float(seq, c2, unreal.CineCameraComponent, "PostProcessBlendWeight",
               [(0, 0.0), (h - 3, 0.0), (h + 14, 0.55), (h + 40, 1.0), (END, 1.0)], binding=b2)
    INFO["camera_grades"] = ok
    if ok == 3 and RV.ACTORS.get("ppv_b"):
        # PPV_B would double up (or, if its saved weight never took, warm the Vacant shots): off
        set_prop(RV.ACTORS["ppv_b"], "enabled", False, quiet=True)
        log("grade: Vacant/Busy grades on the 3 cameras; PPV_B_Busy disabled (LS_Ripple_Live keeps PPV_A only)")
    else:
        warn("grade: only %d/3 camera grades applied - leaving PPV_B_Busy and its BlendWeight track in charge" % ok)


def _camera_grade(cam, grade, weight):
    """Copy a riverside grade dict onto a CineCamera's own post-process settings."""
    try:
        cc = cam.get_cine_camera_component()
        s = cc.get_editor_property("post_process_settings")
        bad = []
        for k, v in grade.items():
            try:
                s.set_editor_property(k, v)
                s.set_editor_property("override_" + k, True)
            except Exception:
                bad.append(k)
        cc.set_editor_property("post_process_settings", s)
        cc.set_editor_property("post_process_blend_weight", float(weight))
        log("camera grade %s: %d fields, weight %.1f, white_temp %s%s" % (
            _nm(cam), len(grade) - len(bad), weight, grade.get("white_temp"),
            (" (skipped %s)" % ", ".join(bad)) if bad else ""))
        return 1
    except Exception as exc:
        warn("camera grade %s: %s" % (_nm(cam), exc))
        return 0


# =========================================================================== entry
def _lsa(seq, label, autoplay=False, disable_cuts=False):
    lsa = spawn(unreal.LevelSequenceActor, (0, 0, 260), (0, 0, 0), label, "Cinematics")
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
    return lsa


def _world(seq, pixel, cam_hit):
    with step("ripple: state swaps"):
        swap_groups(seq, pixel)
    with step("ripple: light cues"):
        ramp_lights(seq)
    with step("ripple: sun / sky / fog / grade crossover"):
        env_tracks(seq, cam_hit)
    with step("ripple: walkers"):
        walkers(seq)
    with step("ripple: El train"):
        train_track(seq)


def build(actors=None):
    if not RV.GROUPS["A"] and not RV.GROUPS["B"]:
        warn("ripple sequence: no riverside groups in this session - build the 'ripple' level stage first")
    cam_hit = hit(dist((-880.0, 340.0, 165.0)))  # S2 wait: west sidewalk, between fire escapes and El bents
    h = fi(cam_hit)
    log("ripple: wave born f%d, hits camera f%.1f, sky (world radius) f%.0f-%.0f, done f%.0f" % (
        S.RIPPLE_START, cam_hit, hit(149000), hit(451000), hit(S.RIPPLE_R_MAX)))
    log("ripple: SkyRadius keys  f%d=0  f%d=40m  f%d=near sky  f%d=dusk  f%d=done  (dusk reveal during S2 crane)" % (
        h + 6, h + 14, h + 40, h + 88, h + 118))
    log_timeline(cam_hit)
    seq = None
    with step("ripple: LS_Ripple_Demo", critical=False):
        seq = _new(S.RIPPLE_SEQ_NAME)
        pixel = False
        with step("ripple: MPC track (pixel tear)"):
            pixel = build_mpc_track(seq, cam_hit)
        INFO["mode"] = "pixel" if pixel else "swap"
        INFO["mpc_track"] = pixel
        _world(seq, pixel, cam_hit)
        CAM.clear()
        with step("ripple: cameras (3 shots)"):
            build_cameras(seq, cam_hit)
        with step("ripple: wavefront shell + shreds + embers"):
            shell_and_fx(seq, cam_hit)
        save_asset(seq)
        _lsa(seq, "LSA_Ripple_Demo")
    with step("ripple: LS_Ripple_Live (no cameras, for PIE)"):
        live = _new(S.RIPPLE_LIVE_SEQ_NAME)
        if INFO["mpc_track"]:
            build_mpc_track(live, cam_hit)
        _world(live, INFO["mpc_track"], cam_hit)
        save_asset(live)
        _lsa(live, "LSA_Ripple_Live", autoplay=S.RIPPLE_LIVE_AUTOPLAY, disable_cuts=True)
    log("ripple sequence: mode=%s groups=%d lights=%d fx=%d" % (INFO["mode"], INFO["groups"], INFO["lights"], INFO["fx"]))
    return seq
