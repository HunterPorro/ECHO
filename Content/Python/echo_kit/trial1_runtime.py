"""Trial 1 Play-In-Editor director - the slice's gameplay without a single Blueprint.

Runs as an editor Slate tick callback while you Play-In-Editor on L_Trial1_Riverside2008 (it ignores
every other map). Everything it needs is in the level as tagged actors (trial1.py) and as data
(trial1_beats.py): it reads the pawn's position against the trigger volumes itself.

    import echo_kit.trial1_runtime as D; D.start()     # Content/Python/init_unreal.py does this
    D.status()        # current beat, alert, suspicion
    D.force_shift()   # jump straight to the snap-back (State A -> B)
    D.skip()          # complete the current beat
    D.stop()

Mechanics (all tunable in settings.py, T1_*):
    hold triggers      stand inside for T1_HOLD_SECONDS[...] (hide the suits 1.5 s, pick the lock 3 s)
    objective triggers complete the current beat when entered
    blend-in zones     forced walk (max walk speed T1_WALK_SPEED); with T1_FORCE_WALK off, moving faster
                       than T1_SUSPICION_SPEED inside the officer's view raises suspicion -> checkpoint
    noise hazards      broken glass / a loose floorboard add alert (half if you walk); 100 -> checkpoint
    hiding spots       alert decays 3x faster, 'Hidden'
    companions         Tyler + John warp to their marks for each beat (trial1_beats.BEATS[...]['companions'])
    the lock           DOOR_Cortaz hides + stops colliding, the open leaf appears
    B10                John's candle (and its light) comes on
    the shift          T1_SHIFT_DELAY s after B10: plays LSA_Trial1_Shift (MPC Center set to the stove),
                       snaps the player across Cutler to watch the building go up, 'TRIAL 1 - COMPLETE'
"""
import math
import time

import unreal

from . import settings as S
from . import trial1_beats as TB

STATE = {"cb": None, "world": None, "beat": 0, "alert": 0.0, "susp": 0.0, "inside": set(), "hold": {},
         "done": set(), "shift_at": None, "shift_t0": None, "snapped": False, "complete": False,
         "collected": set(), "portal_t0": None, "msgs": {}, "errors": 0, "last_speed": None}
MAP_KEY = "L_Trial1"


# ----------------------------------------------------------------------------------- engine access
def _world():
    try:
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    except Exception:
        return None
    if w is None:
        return None
    try:
        if MAP_KEY not in w.get_name() and MAP_KEY not in str(w.get_path_name()):
            return None
    except Exception:
        return None
    return w


def _tagged(w, tag):
    try:
        return list(unreal.GameplayStatics.get_all_actors_with_tag(w, unreal.Name(tag)) or [])
    except Exception:
        return []


def _say(w, text, seconds=4.0, color=(1.0, 0.86, 0.55), key=None):
    if not text:
        return
    now = time.time()
    k = key or text
    if STATE["msgs"].get(k, 0) > now:
        return
    STATE["msgs"][k] = now + min(seconds, 2.0)
    try:
        unreal.SystemLibrary.print_string(w, text, True, False, unreal.LinearColor(*color, 1.0), float(seconds))
    except Exception:
        try:
            unreal.SystemLibrary.print_string(w, text)
        except Exception:
            unreal.log("[ECHO T1] " + text)
    unreal.log("[ECHO T1] " + text)


def _pawn(w):
    try:
        return unreal.GameplayStatics.get_player_pawn(w, 0)
    except Exception:
        return None


def _move_comp(pawn):
    for n in ("character_movement", "get_movement_component"):
        try:
            c = getattr(pawn, n)
            c = c() if callable(c) else c
            if c is not None:
                return c
        except Exception:
            continue
    return None


def _teleport(w, pawn, xyzyaw):
    x, y, z, yaw = xyzyaw
    try:
        pawn.set_actor_location_and_rotation(unreal.Vector(x, y, z + TB.CAPSULE_Z), unreal.Rotator(0, 0, yaw),
                                             False, True)
    except Exception:
        try:
            pawn.set_actor_location(unreal.Vector(x, y, z + TB.CAPSULE_Z), False, True)
        except Exception:
            pass
    try:
        ctrl = unreal.GameplayStatics.get_player_controller(w, 0)
        r = unreal.Rotator()
        r.yaw = float(yaw)
        ctrl.set_control_rotation(r)
    except Exception:
        pass


def _place(actor, x, y, z, yaw):
    try:
        r = unreal.Rotator()
        r.yaw = float(yaw) - 90.0          # mannequins face +Y
        actor.set_actor_location_and_rotation(unreal.Vector(x, y, z), r, False, True)
    except Exception:
        pass


def _show(actors, visible, collide=None):
    for a in actors:
        try:
            a.set_actor_hidden_in_game(not visible)
            if collide is not None:
                a.set_actor_enable_collision(bool(collide))
        except Exception:
            pass


def _inside(p, trig):
    _k, c, size, _b, _t, _e = trig
    return all(abs(p[i] - c[i]) <= size[i] / 2.0 for i in range(3))


# ----------------------------------------------------------------------------------- beats
def _beat():
    i = STATE["beat"]
    return TB.BEATS[i] if 0 <= i < len(TB.BEATS) else None


def _start_beat(w):
    b = _beat()
    if b is None:
        return
    for name, pos in b.get("companions", {}).items():
        for a in _tagged(w, "T1.NPC." + name):
            _place(a, *pos)
    if b.get("on_start"):
        _say(w, b["on_start"], 6.0, (0.85, 0.9, 1.0))
    _say(w, "OBJECTIVE: " + b["objective"], 6.0, key="obj")


def _complete(w, b):
    STATE["done"].add(b["id"])
    if b.get("on_done"):
        _say(w, b["on_done"], 6.0, (0.85, 0.9, 1.0))
    trig = TB.TRIGGERS.get(b["trigger"])
    extra = trig[5] if trig else {}
    if extra.get("opens"):
        _show(_tagged(w, "T1.Door.Cortaz"), False, collide=False)
        _show(_tagged(w, "T1.DoorOpen.Cortaz"), True)
    if extra.get("tyler_to"):
        for a in _tagged(w, "T1.NPC.Tyler"):
            _place(a, *extra["tyler_to"])
    if b["id"] == "B10":
        _show(_tagged(w, "T1.Candle"), True)
        for a in _tagged(w, "T1.CandleLight"):
            try:
                a.light_component.set_intensity(S.T1_INTERIOR_CD * 0.6)
            except Exception:
                pass
    STATE["beat"] += 1
    _start_beat(w)


def _fail(w, why):
    b = _beat()
    if b is None:
        return
    _say(w, why + "  (checkpoint)", 4.0, (1.0, 0.45, 0.35))
    STATE["alert"] = STATE["susp"] = 0.0
    STATE["hold"].clear()
    p = _pawn(w)
    if p is not None:
        _teleport(w, p, b["checkpoint"])


# ----------------------------------------------------------------------------------- the shift
def _play_shift(w):
    lsa = (_tagged(w, "T1.Shift") or [None])[0]
    try:
        mpc = unreal.EditorAssetLibrary.load_asset(S.RIPPLE_MAT_DIR + "/" + S.RIPPLE_MPC_NAME)
        c = S.T1_SHIFT_CENTER
        unreal.KismetMaterialLibrary.set_vector_parameter_value(w, mpc, unreal.Name("Center"),
                                                                unreal.LinearColor(c[0], c[1], c[2], 0.0))
    except Exception as exc:
        unreal.log_warning("[ECHO T1] MPC Center at runtime: %s" % exc)
    if lsa is None:
        _say(w, "LSA_Trial1_Shift not found - rebuild with -Stages trial1", 6.0, (1, 0.4, 0.3))
        return
    try:
        lsa.sequence_player.play()
    except Exception:
        try:
            lsa.get_sequence_player().play()
        except Exception as exc:
            _say(w, "could not play the shift: %s" % exc, 6.0, (1, 0.4, 0.3))
    STATE["shift_t0"] = time.time()
    for name in ("Tyler", "John"):
        for a in _tagged(w, "T1.NPC." + name):
            _place(a, *TB.BEATS[-1]["companions"][name])


def _tick_shift(w, pawn):
    t = time.time() - STATE["shift_t0"]
    if t > 0.3:
        _say(w, "Rivers: \"Ahh-\"  (the headache. A nosebleed.)", 3.0, (1.0, 0.5, 0.45), key="headache")
    if t > 1.5 and not STATE["snapped"]:
        STATE["snapped"] = True
        _teleport(w, pawn, TB.MARKS["SnapBackView"])
    if t > S.T1_SHIFT_FRAMES / float(S.FPS) and not STATE["complete"]:
        STATE["complete"] = True
        _say(w, TB.BEATS[-1]["on_done"], 12.0, (1.0, 0.9, 0.7))


# ----------------------------------------------------------------------------------- tick
def _reset(w):
    STATE.update({"world": w, "beat": 0, "alert": 0.0, "susp": 0.0, "inside": set(), "hold": {}, "done": set(),
                  "shift_at": None, "shift_t0": None, "snapped": False, "complete": False, "collected": set(),
                  "portal_t0": time.time(), "msgs": {}})
    _start_beat(w)


def _portal(w):
    t0 = STATE.get("portal_t0")
    if t0 is None:
        return
    k = (time.time() - t0) / 2.2
    s = max(0.001, 1.0 - k * k)
    for a in _tagged(w, "T1.Portal"):
        try:
            a.set_actor_scale3d(unreal.Vector(s, s, s))
        except Exception:
            pass
    if k >= 1.0:
        STATE["portal_t0"] = None


def _tick(dt):
    w = _world()
    if w is None:
        if STATE["world"] is not None:
            STATE["world"] = None
        return
    if STATE["world"] is None or STATE["world"] != w:
        _reset(w)
    pawn = _pawn(w)
    if pawn is None:
        return
    dt = max(0.0, min(float(dt), 0.1))
    _portal(w)
    if STATE["shift_t0"] is not None:
        _tick_shift(w, pawn)
        return
    v = pawn.get_actor_location()
    p = (v.x, v.y, v.z)
    try:
        vel = pawn.get_velocity()
        speed = math.hypot(vel.x, vel.y)
    except Exception:
        speed = 0.0
    now_in = set(tid for tid, trig in TB.TRIGGERS.items() if _inside(p, trig))
    entered = now_in - STATE["inside"]
    STATE["inside"] = now_in
    kinds = {tid: TB.TRIGGERS[tid][0] for tid in now_in}
    b = _beat()
    # forced walk / suspicion
    blend = any(k == "blend" for k in kinds.values())
    mc = _move_comp(pawn)
    if mc is not None and S.T1_FORCE_WALK:
        want = S.T1_WALK_SPEED if blend else S.T1_RUN_SPEED
        if STATE["last_speed"] != want:
            try:
                mc.set_editor_property("max_walk_speed", float(want))
                STATE["last_speed"] = want
            except Exception:
                pass
    watched = any(k == "watch" for k in kinds.values())
    if watched and blend and speed > S.T1_SUSPICION_SPEED:
        STATE["susp"] += S.T1_SUSPICION_RATE * dt
        _say(w, "The officer looks your way...  (suspicion %d%%)" % STATE["susp"], 1.0, (1, 0.7, 0.4), key="susp")
        if STATE["susp"] >= 100.0:
            _fail(w, "\"Hey! You three!\"")
            return
    else:
        STATE["susp"] = max(0.0, STATE["susp"] - 10.0 * dt)
    # noise / hiding
    hidden = any(k == "hide" for k in kinds.values())
    for tid in entered:
        kind, _c, _s, _bt, text, _e = TB.TRIGGERS[tid]
        if kind == "noise":
            STATE["alert"] += S.T1_NOISE_ALERT * (1.0 if speed > 250 else 0.5)
            _say(w, "%s  (alert %d%%)" % (text, STATE["alert"]), 3.0, (1, 0.6, 0.35))
        elif kind == "hide":
            _say(w, text, 2.0, (0.6, 0.9, 0.7))
        elif kind == "lore":
            _say(w, text, 7.0, (0.9, 0.9, 0.8))
        elif kind == "collectible" and tid not in STATE["collected"]:
            STATE["collected"].add(tid)
            _show(_tagged(w, "T1.Collectible"), False, collide=False)
            _say(w, "COLLECTED: " + text, 8.0, (1.0, 0.85, 0.4))
        elif kind == "blend":
            _say(w, text, 2.0, (0.8, 0.85, 1.0), key="blend")
    STATE["alert"] = max(0.0, STATE["alert"] - S.T1_ALERT_DECAY * (3.0 if hidden else 1.0) * dt)
    if STATE["alert"] >= 100.0:
        _fail(w, "Cortaz: \"...who's there?\"")
        return
    if b is None:
        return
    # the current beat
    trig_id = b["trigger"]
    trig = TB.TRIGGERS.get(trig_id)
    if trig is None:
        return
    kind = trig[0]
    if kind == "shift":
        if STATE["shift_at"] is None:
            STATE["shift_at"] = time.time() + S.T1_SHIFT_DELAY
        elif time.time() >= STATE["shift_at"]:
            _play_shift(w)
        return
    if trig_id not in now_in:
        STATE["hold"].pop(trig_id, None)
        return
    if kind == "hold":
        need = S.T1_HOLD_SECONDS.get(trig[5].get("hold", ""), 2.0)
        h = STATE["hold"].get(trig_id, 0.0) + dt
        STATE["hold"][trig_id] = h
        _say(w, "%s...  %d%%" % (trig[4], min(100, int(100 * h / need))), 0.3, key="hold")
        if h >= need:
            STATE["hold"].pop(trig_id, None)
            _complete(w, b)
    else:
        _complete(w, b)


def _safe_tick(dt):
    try:
        _tick(dt)
    except Exception as exc:
        STATE["errors"] += 1
        if STATE["errors"] <= 5:
            unreal.log_warning("[ECHO T1] director tick: %s" % exc)
        if STATE["errors"] > 200:
            stop()


# ----------------------------------------------------------------------------------- API
def start():
    if STATE["cb"] is not None:
        return True
    try:
        STATE["cb"] = unreal.register_slate_post_tick_callback(_safe_tick)
        unreal.log("[ECHO T1] Trial 1 director armed (Play-In-Editor on %s)" % S.T1_MAP_NAME)
        return True
    except Exception as exc:
        unreal.log_warning("[ECHO T1] could not arm the director: %s" % exc)
        return False


def stop():
    if STATE["cb"] is not None:
        try:
            unreal.unregister_slate_post_tick_callback(STATE["cb"])
        except Exception:
            pass
    STATE["cb"] = None
    STATE["world"] = None


def status():
    b = _beat()
    s = "beat %s (%s) | alert %.0f%% | suspicion %.0f%% | done %s | shift %s" % (
        b["id"] if b else "-", b["name"] if b else "complete", STATE["alert"], STATE["susp"],
        ",".join(sorted(STATE["done"])) or "-", "playing" if STATE["shift_t0"] else "armed" if STATE["shift_at"] else "no")
    unreal.log("[ECHO T1] " + s)
    return s


def skip():
    w = _world()
    b = _beat()
    if w is not None and b is not None:
        _complete(w, b)
    return status()


def force_shift():
    w = _world()
    if w is None:
        unreal.log_warning("[ECHO T1] start Play-In-Editor on %s first" % S.T1_MAP_NAME)
        return False
    STATE["beat"] = len(TB.BEATS) - 1
    _play_shift(w)
    return True
