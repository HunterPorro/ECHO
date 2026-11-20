"""Level Sequences:

LS_Prologue_Unveiling (24 fps, 768 frames = 32 s) - 'The Unveiling', six deliberate shots
(frame ranges in settings.GALA_SHOTS; 2.39:1 scope filmback when settings.GALA_SCOPE):
  1 ESTABLISH  crane down + forward over the hall, chandelier + crystals in the FG, 24mm f/2.8
  2 DOLLY      slow push down the aisle between guests toward the stage, 35mm f/2.8
  3 RIVERS     medium on Dr. Rivers at the lectern, rim-lit, 50mm f/2.0 shallow DOF
  4 ISABELLA   reverse: Isabella in the crowd, warm key, city bokeh behind, 50mm f/1.8
  5 REVEAL     3/4 hero on the Echo, ECHO title above it: drape pulled into the rig, beams sweep up
  6 WIDE       over-shoulder tableau through the crowd (glasses + shoulders in the FG), 24mm f/2.8
Every camera move is sampled every 2 frames through an eased Catmull-Rom path (no shake).
LS_Gala_FlashLoop - 4 s looping flashes in the crowd, auto-plays so the walkable level feels alive.
"""
import math
import random

import unreal

from . import settings as S
from .util import (LC, V, component, create_asset, error, look_at, save_asset, set_prop, spawn, step,
                   warn, log)
from . import util as U

MSE = unreal.MovieSceneSequenceExtensions
_rng = random.Random(S.RANDOM_SEED + 7)


# =========================================================================== low-level helpers
def _new_sequence(name):
    path = S.CINE_DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        # wipe and rebuild (the referencing LevelSequenceActors were deleted with ECHO_GEN actors)
        if not unreal.EditorAssetLibrary.delete_asset(path):
            seq = unreal.EditorAssetLibrary.load_asset(path)
            _clear_sequence(seq)
            return seq
    seq, _ = create_asset(name, S.CINE_DIR, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    return seq


def _clear_sequence(seq):
    try:
        for b in list(seq.get_bindings()):
            b.remove()
        for t in list(seq.get_tracks()):
            seq.remove_track(t)
    except Exception as exc:
        warn("clearing sequence: %s" % exc)


def _setup_range(seq, end_frame):
    MSE.set_display_rate(seq, unreal.FrameRate(S.FPS, 1))
    MSE.set_playback_start(seq, 0)
    MSE.set_playback_end(seq, int(end_frame))
    try:
        MSE.set_view_range_start(seq, -0.5)
        MSE.set_view_range_end(seq, end_frame / float(S.FPS) + 0.5)
        MSE.set_work_range_start(seq, 0.0)
        MSE.set_work_range_end(seq, end_frame / float(S.FPS))
    except Exception:
        pass


def _add_track(owner, track_cls):
    """5.2+ uses add_track; older builds named it add_master_track for sequence-level tracks."""
    try:
        return owner.add_track(track_cls)
    except AttributeError:
        return owner.add_master_track(track_cls)


def _binding_id(seq, binding):
    for fn in (lambda: MSE.get_portable_binding_id(seq, seq, binding),
               lambda: MSE.get_binding_id(seq, binding),
               lambda: seq.make_binding_id(binding, unreal.MovieSceneObjectBindingSpace.LOCAL)):
        try:
            bid = fn()
            if bid is not None:
                return bid
        except Exception:
            continue
    bid = unreal.MovieSceneObjectBindingID()
    set_prop(bid, "guid", binding.get_id())
    return bid


def _channels(section):
    try:
        return list(section.get_all_channels())
    except Exception:
        return list(section.get_channels_by_type(unreal.MovieSceneScriptingDoubleChannel))


def _channel_map(section):
    """name -> channel for a 3D transform section (falls back to index order)."""
    chans = _channels(section)
    names = ["Location.X", "Location.Y", "Location.Z", "Rotation.X", "Rotation.Y", "Rotation.Z",
             "Scale.X", "Scale.Y", "Scale.Z"]
    out = {}
    for c in chans:
        try:
            out[str(c.get_editor_property("channel_name"))] = c
        except Exception:
            pass
    if not all(n in out for n in names):
        out = dict(zip(names, chans))
    return out


def _key(chan, frame, value, interp="AUTO"):
    mode = getattr(unreal.MovieSceneKeyInterpolation, interp, unreal.MovieSceneKeyInterpolation.AUTO)
    chan.add_key(unreal.FrameNumber(int(frame)), float(value), 0.0, interpolation=mode)


def add_transform(seq, binding, start, end, keys, interp="AUTO"):
    """keys: list of (frame, (x,y,z), (pitch,yaw,roll), (sx,sy,sz) or None)."""
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    sec = track.add_section()
    sec.set_range(int(start), int(end))
    ch = _channel_map(sec)
    prev_yaw = None
    for frame, loc, rot, scl in keys:
        pitch, yaw, roll = rot
        if prev_yaw is not None:                      # unwrap yaw so Sequencer never spins the long way
            while yaw - prev_yaw > 180:
                yaw -= 360
            while yaw - prev_yaw < -180:
                yaw += 360
        prev_yaw = yaw
        scl = scl or (1.0, 1.0, 1.0)
        for n, v in (("Location.X", loc[0]), ("Location.Y", loc[1]), ("Location.Z", loc[2]),
                     ("Rotation.X", roll), ("Rotation.Y", pitch), ("Rotation.Z", yaw),
                     ("Scale.X", scl[0]), ("Scale.Y", scl[1]), ("Scale.Z", scl[2])):
            if n in ch:
                _key(ch[n], frame, v, interp)
    return track


def add_float_property(seq, comp_binding, prop_name, prop_path, start, end, keys, interp="AUTO"):
    track = comp_binding.add_track(unreal.MovieSceneFloatTrack)
    track.set_property_name_and_path(prop_name, prop_path)
    sec = track.add_section()
    sec.set_range(int(start), int(end))
    chans = _channels(sec)
    if not chans:
        raise RuntimeError("no channel on float section for " + prop_name)
    for frame, value in keys:
        _key(chans[0], frame, value, interp)
    return track


def bind_component(seq, actor_binding, comp):
    cb = seq.add_possessable(comp)
    try:
        cb.set_parent(actor_binding)
    except Exception as exc:
        warn("set_parent on component binding: %s" % exc)
    return cb


def look_rot(src, dst, roll=0.0):
    p, y = look_at(src, dst)
    return (p, y, roll)


# =========================================================================== cameras
def _cfg(name, default):
    return getattr(S, name, default)


def make_camera(label, loc, target, focal, fstop, track_actor=None, track_offset=(0, 0, 0)):
    p, y = look_at(loc, target)
    cam = spawn(unreal.CineCameraActor, loc, (p, y, 0), label, "Cinematics/Cameras")
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback")
    sw, sh = _cfg("GALA_SENSOR", (36.0, 15.06)) if _cfg("GALA_SCOPE", True) else (36.0, 20.25)
    set_prop(fb, "sensor_width", float(sw))        # full-frame width -> shallow, cinematic DOF
    set_prop(fb, "sensor_height", float(sh))       # 15.06 = 2.39:1 scope (letterboxed in 16:9)
    cc.set_editor_property("filmback", fb)
    set_prop(cc, "constrain_aspect_ratio", True, quiet=True)
    set_prop(cc, "current_focal_length", float(focal))
    set_prop(cc, "current_aperture", float(fstop))
    try:
        ls = cc.get_editor_property("lens_settings")
        set_prop(ls, "min_f_stop", 1.2, quiet=True)
        set_prop(ls, "diaphragm_blade_count", 9, quiet=True)      # rounder bokeh
        cc.set_editor_property("lens_settings", ls)
    except Exception:
        pass
    fs = cc.get_editor_property("focus_settings")
    dist = math.dist(loc, target)
    if track_actor is not None:
        try:
            tfs = fs.get_editor_property("tracking_focus_settings")
            tfs.set_editor_property("actor_to_track", track_actor)
            tfs.set_editor_property("relative_offset", V(*track_offset))
            fs.set_editor_property("tracking_focus_settings", tfs)
            fs.set_editor_property("focus_method", unreal.CameraFocusMethod.TRACKING)
        except Exception as exc:
            warn("tracking focus unavailable (%s) - using manual focus %.0f cm" % (exc, dist))
            fs.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
            fs.set_editor_property("manual_focus_distance", float(dist))
    else:
        fs.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
        fs.set_editor_property("manual_focus_distance", float(dist))
    set_prop(fs, "smooth_focus_changes", True, quiet=True)
    set_prop(fs, "focus_smoothing_interp_speed", 4.0, quiet=True)
    cc.set_editor_property("focus_settings", fs)
    bias = _cfg("GALA_SHOT_EXPOSURE", {}).get(label)
    if bias is not None:
        _exposure_bias(cc, float(bias), label)
    return cam


def _exposure_bias(cc, bias, label):
    """Per-camera auto-exposure bias (histogram metering pulls the brightest subject toward mid-grey;
    a negative bias keeps a dark suit dark)."""
    try:
        pps = cc.get_editor_property("post_process_settings")
        set_prop(pps, "override_auto_exposure_bias", True)
        set_prop(pps, "auto_exposure_bias", bias)
        cc.set_editor_property("post_process_settings", pps)
        set_prop(cc, "post_process_blend_weight", 1.0, quiet=True)
        log("%s: exposure bias %+.2f EV" % (label, bias))
    except Exception as exc:
        warn("%s exposure bias unavailable (%s)" % (label, exc))


def _catmull(pts, u):
    """Uniform Catmull-Rom through pts (list of 3-tuples) at u in 0..1 (end points clamped)."""
    n = len(pts)
    if n == 1:
        return tuple(pts[0])
    if n == 2:
        return tuple(pts[0][j] + (pts[1][j] - pts[0][j]) * u for j in range(3))
    seg = min(int(u * (n - 1)), n - 2)
    t = u * (n - 1) - seg
    p0, p1, p2, p3 = pts[max(seg - 1, 0)], pts[seg], pts[seg + 1], pts[min(seg + 2, n - 1)]
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                        (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(3))


def _soft_ease(t, amount):
    """Blend of linear and smootherstep: amount 0 = constant speed, 1 = full ease in/out.
    Partial easing keeps the camera moving across a cut instead of starting from dead stop."""
    return (1.0 - amount) * t + amount * U.smootherstep(t) if hasattr(U, "smootherstep") else t


def sample_move(s0, s1, locs, targets, ease=0.6, every=2, roll=0.0):
    """Dense (frame, loc, rot, None) keys for a camera move along eased Catmull-Rom paths."""
    keys = []
    frames = list(range(int(s0), int(s1), int(every))) + [int(s1)]
    for f in frames:
        t = (f - s0) / float(max(1, s1 - s0))
        u = _soft_ease(t, ease)
        loc = _catmull(locs, u)
        tgt = _catmull(targets, u)
        p, y = look_at(loc, tgt)
        keys.append((f, loc, (p, y, roll), None))
    return keys


def _arc(center, r0, r1, a0, a1, z0, z1, n=4):
    """Points on an arc around center (angles in degrees) for orbiting moves."""
    out = []
    for i in range(n):
        t = i / float(n - 1)
        a = math.radians(a0 + (a1 - a0) * t)
        r = r0 + (r1 - r0) * t
        out.append((center[0] + r * math.cos(a), center[1] + r * math.sin(a), z0 + (z1 - z0) * t))
    return out


# =========================================================================== main sequence
def build_main(actors):
    h = S.STAGE_H
    rx, ry = S.RIVERS_POS
    cx, cy = S.CAR_POS
    ix, iy = _cfg("ISABELLA_POS", (4200.0, -1180.0))
    head = (rx, ry, h + 165)
    rivers = actors.get("rivers")
    isabella = actors.get("isabella")
    car_body = actors.get("car_body") or actors.get("turntable")
    focus_stage = actors.get("focus_stage") or rivers
    shots = _cfg("GALA_SHOTS", {"establish": (0, 168), "dolly": (168, 312), "rivers": (312, 456),
                                "isabella": (456, 552), "reveal": (552, 696), "wide": (696, 768)})

    seq = _new_sequence(S.SEQ_NAME)
    end = max(v[1] for v in shots.values())
    _setup_range(seq, end)
    cut_track = _add_track(seq, unreal.MovieSceneCameraCutTrack)

    def shot(label, frames, locs, targets, focal, fstop, track_actor, offset, ease=0.6):
        s0, s1 = frames
        cam = make_camera(label, locs[0], targets[0], focal, fstop, track_actor, offset)
        b = seq.add_possessable(cam)
        add_transform(seq, b, s0, s1 + 1, sample_move(s0, s1, locs, targets, ease=ease))
        sec = cut_track.add_section()
        sec.set_range(int(s0), int(s1))
        sec.set_camera_binding_id(_binding_id(seq, b))
        return cam, b

    # ---- 1 ESTABLISH: crane down and forward over the hall; near crystals + chandelier in the FG.
    #      Slightly steeper look-down so the polished floor and table-lamp pools fill the lower half.
    shot("CAM_01_Establish_Crane", shots["establish"],
         [(450, 420, 1120), (900, 360, 800), (1320, 280, 520)],
         [(4900, 0, 500), (4920, -80, 360), (5000, -120, 220)],
         24.0, 2.8, focus_stage, (0, 0, 0), ease=0.8)

    # ---- 2 DOLLY: low push down the aisle between guests, press silhouettes framing the lectern
    shot("CAM_02_Dolly_Aisle", shots["dolly"],
         [(2450, -240, 185), (3550, -290, 200)],
         [(rx, ry, h + 140), (rx, ry, h + 152)],
         35.0, 2.8, rivers, (0, 0, 160), ease=0.5)

    # ---- 3 RIVERS: medium shot, 50mm f/2, lectern edge in the bottom of frame, eyes on the upper third,
    #      gentle push + drift; screen glow and the cool rim separate him from the wall
    shot("CAM_03_Rivers_Medium", shots["rivers"],
         [(4690, -285, 240), (4760, -330, 243)],
         [(rx, ry, h + 138), (rx, ry, h + 140)],
         50.0, 2.0, rivers, (0, 0, 165), ease=0.5)

    # ---- 4 ISABELLA: reverse into the crowd; she watches him (city lights through the glass behind)
    shot("CAM_04_Isabella", shots["isabella"],
         [(ix + 360, iy + 170, 166), (ix + 335, iy + 125, 164)],
         [(ix, iy, 150), (ix, iy - 5, 151)],
         50.0, 1.8, isabella, (0, 0, 150), ease=0.5)

    # ---- 5 REVEAL: 3/4 front hero on the Echo with the ECHO title stacked above it.
    #      The camera sits on the line screen-centre -> car, ~8 m out, just above deck height
    #      looking slightly up: the whole car (deck to roof) fills the lower half, the title the upper.
    #      Slow arc of 16 degrees + gentle push while the drape lifts and the beams sweep up.
    title_ang = math.degrees(math.atan2(cy - 0.0, cx - (S.HALL_LEN - 70)))   # car -> away from screen centre
    shot("CAM_05_Reveal_Hero", shots["reveal"],
         _arc((cx, cy), 820, 760, title_ang - 9, title_ang + 7, h + 95, h + 82),
         # solved so deck (z 124) and title top (z ~800) both sit ~2.5 deg inside the 28mm scope frame
         [(5450, 560, 305), (5450, 560, 301), (5450, 560, 298), (5450, 560, 298)],
         28.0, 2.8, car_body, (0, 0, 40), ease=0.55)

    # ---- 6 WIDE: among the left-aisle guests, looking through out-of-focus shoulders and a champagne
    #      stand at the stage; slow pull back. f/2.8 so the room falls off and the stage pops.
    shot("CAM_06_Wide_Tableau", shots["wide"],
         [(2720, -340, 175), (2560, -360, 185)],
         [(5380, 180, 300), (5380, 180, 305)],
         24.0, 2.8, focus_stage, (0, 0, 0), ease=0.7)

    rev0 = shots["reveal"][0]
    lift0, lift1 = _cfg("COVER_LIFT", (rev0 + 14, rev0 + 64))
    car = (cx, cy, h + 75)

    # ---- follow spot: holds on Rivers, swings to the car as the drape lifts
    follow = actors.get("follow")
    if follow:
        fl = follow.get_actor_location()
        floc = (fl.x, fl.y, fl.z)
        fb = seq.add_possessable(follow)
        add_transform(seq, fb, 0, end + 1, [
            (0, floc, look_rot(floc, head), None),
            (rev0 + 2, floc, look_rot(floc, head), None),
            (rev0 + 40, floc, look_rot(floc, car), None),
            (end, floc, look_rot(floc, car), None),
        ])

    # ---- the drape: tension, then pulled straight up into the rig, out of frame, parked above the roof
    cover = actors.get("cover")
    if cover:
        cl = cover.get_actor_location()
        c0 = (cl.x, cl.y, cl.z)
        yaw = cover.get_actor_rotation().yaw
        sc = cover.get_actor_scale3d()
        s = (sc.x, sc.y, sc.z)
        cb = seq.add_possessable(cover)
        add_transform(seq, cb, 0, end + 1, [
            (0, c0, (0, yaw, 0), s),
            (lift0, c0, (0, yaw, 0), s),
            (lift0 + 8, (c0[0], c0[1], c0[2] + 25), (0, yaw, 0), (s[0] * 0.99, s[1] * 0.97, s[2] * 1.08)),
            (lift0 + 30, (c0[0] + 40, c0[1], c0[2] + 520), (4, yaw + 3, 2), (s[0] * 0.8, s[1] * 0.7, s[2] * 1.2)),
            (lift1, (c0[0] + 80, c0[1], c0[2] + 1200), (8, yaw + 6, 3), (s[0] * 0.5, s[1] * 0.45, s[2] * 0.9)),
            (lift1 + 1, (c0[0] + 80, c0[1], c0[2] + 4000), (8, yaw + 6, 3), (0.01, 0.01, 0.01)),
            (end, (c0[0] + 80, c0[1], c0[2] + 4000), (8, yaw + 6, 3), (0.01, 0.01, 0.01)),
        ])
    hem = actors.get("cover_hem")
    if hem:
        hl, hs = hem.get_actor_location(), hem.get_actor_scale3d()
        hloc, hyaw, hsc = (hl.x, hl.y, hl.z), hem.get_actor_rotation().yaw, (hs.x, hs.y, hs.z)
        hb = seq.add_possessable(hem)
        add_transform(seq, hb, 0, end + 1, [
            (0, hloc, (0, hyaw, 0), hsc), (lift0 + 6, hloc, (0, hyaw, 0), hsc),
            (lift0 + 20, hloc, (0, hyaw, 0), (0.01, 0.01, 0.01)), (end, hloc, (0, hyaw, 0), (0.01, 0.01, 0.01))])

    # ---- turntable starts turning as the drape leaves (slow, stately: ~40 degrees to the end)
    table = actors.get("turntable")
    if table:
        tl = table.get_actor_location()
        tloc = (tl.x, tl.y, tl.z)
        ty = table.get_actor_rotation().yaw
        ts = table.get_actor_scale3d()
        tsc = (ts.x, ts.y, ts.z)          # ALWAYS key the actor's own scale (None would reset it to 1)
        tb = seq.add_possessable(table)
        add_transform(seq, tb, 0, end + 1, [
            (0, tloc, (0, ty, 0), tsc), (lift0, tloc, (0, ty, 0), tsc),
            (lift0 + 40, tloc, (0, ty + 6, 0), tsc),
            (end, tloc, (0, ty + 40, 0), tsc)], interp="AUTO")

    r0 = lift0 + 20   # the light cue: everything comes up as the drape clears the roofline

    def ramp(actor, comp_cls, keys, name="Intensity"):
        if not actor:
            return
        try:
            ab = seq.add_possessable(actor)
            cb = bind_component(seq, ab, component(actor, comp_cls))
            add_float_property(seq, cb, name, name, 0, end + 1, keys)
        except Exception as exc:
            warn("light ramp %s: %s" % (actor.get_name() if hasattr(actor, "get_name") else actor, exc))

    for key in ("car_spot_a", "car_spot_b"):
        ramp(actors.get(key), unreal.SpotLightComponent, [
            (0, S.CAR_SPOT_CD_PRE), (r0, S.CAR_SPOT_CD_PRE), (r0 + 24, S.CAR_SPOT_CD_REVEAL),
            (end, S.CAR_SPOT_CD_REVEAL)])
    for i, rim in enumerate(actors.get("car_rims", [])):
        ramp(rim, unreal.SpotLightComponent, [(0, 0.0), (r0 + 4 + i * 4, 0.0),
                                              (r0 + 22 + i * 4, _cfg("CAR_RIM_CD", 40000.0)),
                                              (end, _cfg("CAR_RIM_CD", 40000.0))])
    ramp(actors.get("car_underglow"), unreal.PointLightComponent,
         [(0, 0.0), (r0, 0.0), (r0 + 30, _cfg("UNDERGLOW_CD", 1500.0)), (end, _cfg("UNDERGLOW_CD", 1500.0))])

    # sweep beams: switch on grazing the deck, tilt up through the car into the haze, settle in a fan
    sweep_cd = _cfg("SWEEP_CD", 60000.0)
    for i, sw in enumerate(actors.get("sweeps", [])):
        try:
            sl = sw.get_actor_location()
            sloc = (sl.x, sl.y, sl.z)
            yaw0 = sw.get_actor_rotation().yaw
            stagger = i * 5
            sb = seq.add_possessable(sw)
            add_transform(seq, sb, 0, end + 1, [
                (0, sloc, (-4, yaw0, 0), None),
                (r0 + stagger, sloc, (-4, yaw0, 0), None),
                (r0 + 26 + stagger, sloc, (14, yaw0, 0), None),
                (r0 + 60 + stagger, sloc, (62 + (i % 2) * 8, yaw0 + (i - 1.5) * 6, 0), None),
                (end, sloc, (66 + (i % 2) * 8, yaw0 + (i - 1.5) * 7, 0), None),
            ])
            cb = bind_component(seq, sb, component(sw, unreal.SpotLightComponent))
            add_float_property(seq, cb, "Intensity", "Intensity", 0, end + 1, [
                (0, 0.0), (r0 + stagger, 0.0), (r0 + 6 + stagger, sweep_cd), (end, sweep_cd * 0.8)])
        except Exception as exc:
            warn("sweep %d: %s" % (i, exc))

    # ---- press flashes: sparse in the establishing shot, a storm on the speech and the reveal
    flashes = actors.get("flash_cine", [])
    windows = [(shots["dolly"][0], shots["dolly"][1], 0.012), (shots["rivers"][0], shots["rivers"][1], 0.045),
               (shots["isabella"][0], shots["isabella"][1], 0.02), (shots["reveal"][0], r0, 0.01),
               (r0, end, 0.075)]
    for i, fl in enumerate(flashes):
        keys = [(0, 0.0)]
        f = 0
        for (w0, w1, rate) in windows:
            f = max(f, w0)
            while f < w1 - 4:
                if _rng.random() < rate:
                    keys += [(f, 0.0), (f + 1, S.FLASH_CD * _rng.uniform(0.6, 1.0)), (f + 3, 0.0)]
                    f += 5
                else:
                    f += 1
        keys.append((end, 0.0))
        try:
            ab = seq.add_possessable(fl)
            cb = bind_component(seq, ab, component(fl, unreal.PointLightComponent))
            add_float_property(seq, cb, "Intensity", "Intensity", 0, end + 1, keys, interp="LINEAR")
        except Exception as exc:
            warn("flash %d: %s" % (i, exc))

    save_asset(seq)
    # a LevelSequenceActor so the cinematic can also be triggered in-game / from Sequencer
    lsa = spawn(unreal.LevelSequenceActor, (0, 0, 200), (0, 0, 0), "LSA_Prologue_Unveiling", "Cinematics")
    try:
        lsa.set_sequence(seq)
    except Exception:
        set_prop(lsa, "level_sequence_asset", seq)
    log("main sequence built: %s (%d frames @ %d fps, %d shots)" % (S.SEQ_PATH, end, S.FPS, len(shots)))
    return seq


def build_flash_loop(actors):
    flashes = actors.get("flash_loop", [])
    if not flashes:
        return None
    seq = _new_sequence(S.FLASH_LOOP_NAME)
    length = 96
    _setup_range(seq, length)
    for i, fl in enumerate(flashes):
        keys = [(0, 0.0)]
        f = _rng.randint(0, 30)
        while f < length - 4:
            keys += [(f, 0.0), (f + 1, S.FLASH_CD * 0.7 * _rng.uniform(0.6, 1.0)), (f + 3, 0.0)]
            f += _rng.randint(18, 60)
        keys.append((length, 0.0))
        try:
            ab = seq.add_possessable(fl)
            cb = bind_component(seq, ab, component(fl, unreal.PointLightComponent))
            add_float_property(seq, cb, "Intensity", "Intensity", 0, length + 1, keys, interp="LINEAR")
        except Exception as exc:
            warn("loop flash %d: %s" % (i, exc))
    save_asset(seq)
    lsa = spawn(unreal.LevelSequenceActor, (0, 0, 220), (0, 0, 0), "LSA_FlashLoop_AutoPlay", "Cinematics")
    try:
        lsa.set_sequence(seq)
    except Exception:
        set_prop(lsa, "level_sequence_asset", seq)
    try:
        ps = lsa.get_editor_property("playback_settings")
        ps.set_editor_property("auto_play", True)
        lc = ps.get_editor_property("loop_count")
        lc.set_editor_property("value", -1)
        ps.set_editor_property("loop_count", lc)
        lsa.set_editor_property("playback_settings", ps)
    except Exception as exc:
        warn("flash loop autoplay: %s" % exc)
    return seq


def build(actors):
    seq = None
    with step("level sequence: opening shot + reveal"):
        seq = build_main(actors)
    with step("level sequence: looping crowd flashes"):
        build_flash_loop(actors)
    return seq
