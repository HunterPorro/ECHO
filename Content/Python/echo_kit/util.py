"""Shared helpers: logging, defensive property setters, spawning, assets."""
import math
import os
import time
import traceback
from contextlib import contextmanager

import unreal

from . import settings as S

# --------------------------------------------------------------------------- logging
FAILURES = []          # (step, message) for the end-of-run summary
_LOG_FILE = None


def _log_path():
    global _LOG_FILE
    if _LOG_FILE is None:
        try:
            saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
            folder = os.path.join(saved, "Logs")
            os.makedirs(folder, exist_ok=True)
            _LOG_FILE = os.path.join(folder, "ECHO_build.log")
        except Exception:
            _LOG_FILE = ""
    return _LOG_FILE


def _write(level, msg):
    path = _log_path()
    if path:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("%s [%s] %s\n" % (time.strftime("%H:%M:%S"), level, msg))
        except Exception:
            pass


def log(msg):
    unreal.log("[ECHO] " + str(msg))
    _write("INFO", msg)


def warn(msg):
    unreal.log_warning("[ECHO] " + str(msg))
    _write("WARN", msg)


def error(msg):
    unreal.log_error("[ECHO] " + str(msg))
    _write("ERROR", msg)


@contextmanager
def step(name, critical=False):
    """Run a block; log + record failures instead of killing the whole build."""
    t0 = time.time()
    log(">> " + name)
    try:
        yield
        log("<< %s (%.1fs)" % (name, time.time() - t0))
    except Exception as exc:  # noqa: BLE001 - we want every failure logged
        error("!! %s failed: %s\n%s" % (name, exc, traceback.format_exc()))
        FAILURES.append((name, str(exc)))
        if critical:
            raise


# --------------------------------------------------------------------------- maths / structs
def V(x=0.0, y=0.0, z=0.0):
    return unreal.Vector(float(x), float(y), float(z))


def R(pitch=0.0, yaw=0.0, roll=0.0):
    # unreal.Rotator's positional order is (roll, pitch, yaw) - always use keywords.
    return unreal.Rotator(roll=float(roll), pitch=float(pitch), yaw=float(yaw))


def LC(r, g, b, a=1.0):
    return unreal.LinearColor(float(r), float(g), float(b), float(a))


def V4(x, y, z, w):
    return unreal.Vector4(float(x), float(y), float(z), float(w))


def look_at(src, dst):
    """(pitch, yaw) in degrees so an actor at src faces dst (X-forward convention)."""
    dx, dy, dz = dst[0] - src[0], dst[1] - src[1], dst[2] - src[2]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


def rot2d(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def local_to_world(origin, yaw, local):
    """Place a point given in an object's local frame (X forward) into the world."""
    lx, ly = rot2d(local[0], local[1], yaw)
    return (origin[0] + lx, origin[1] + ly, origin[2] + local[2])


# --------------------------------------------------------------------------- property helpers
# Known UE-version renames: a requested name also tries these (and, last, setter method(s)).
# The second entry may be a string or a list of setter method names.
_VOLFOG_NAMES = ["volumetric_fog", "enable_volumetric_fog", "b_enable_volumetric_fog",
                 "bEnableVolumetricFog", "EnableVolumetricFog", "VolumetricFog"]
_VOLFOG_SETTERS = ["set_volumetric_fog", "set_enable_volumetric_fog", "set_b_enable_volumetric_fog"]
PROP_ALIASES = {
    "volumetric_fog": (_VOLFOG_NAMES[1:], _VOLFOG_SETTERS),
    "enable_volumetric_fog": ([n for n in _VOLFOG_NAMES if n != "enable_volumetric_fog"], _VOLFOG_SETTERS),
    "bEnableVolumetricFog": ([n for n in _VOLFOG_NAMES if n != "bEnableVolumetricFog"], _VOLFOG_SETTERS),
}


def set_prop(obj, names, value, quiet=False):
    """Try each property name in turn (API names drift between UE versions)."""
    if isinstance(names, str):
        names = [names]
    names = list(names)
    setters = []
    for n in list(names):
        alias = PROP_ALIASES.get(n)
        if alias:
            names += [a for a in alias[0] if a not in names]
            extra = alias[1] if isinstance(alias[1], (list, tuple)) else ([alias[1]] if alias[1] else [])
            for s in extra:
                if s and s not in setters:
                    setters.append(s)
    for n in names:
        try:
            obj.set_editor_property(n, value)
            return n
        except Exception:
            continue
    for fn in setters:
        f = getattr(obj, fn, None)
        if f is not None:
            try:
                f(value)
                return fn
            except Exception:
                continue
    if not quiet:
        warn("could not set %s on %s" % ("/".join(names), _name(obj)))
    return None


def enable_volumetric_fog(comp, enabled=True):
    """Turn volumetric fog on (or off) across UE-version property names.

    UE 5.x has shipped this as volumetric_fog, enable_volumetric_fog and
    bEnableVolumetricFog. Tries each, then setter methods, then logs any
    volumetric* attributes still on the component and issues r.VolumetricFog 1
    so a missed rename does not silently leave the street un-hazed.
    """
    used = set_prop(comp, list(_VOLFOG_NAMES), bool(enabled), quiet=True)
    if used:
        log("volumetric fog: set via %s on %s (= %s)" % (used, _name(comp), enabled))
        return used
    found = []
    try:
        for attr in dir(comp):
            low = attr.lower()
            if "volumetric" in low or "vol_fog" in low or "volfog" in low:
                found.append(attr)
    except Exception:
        pass
    warn("could not set volumetric_fog/enable_volumetric_fog/bEnableVolumetricFog on %s%s" % (
        _name(comp), ("; candidate attrs: " + ", ".join(found[:24])) if found else "; no volumetric* attrs on the component"))
    try:
        console("r.VolumetricFog %d" % (1 if enabled else 0))
        log("volumetric fog: issued console r.VolumetricFog %d as a fallback" % (1 if enabled else 0))
    except Exception as exc:
        warn("volumetric fog console fallback failed: %s" % exc)
    return None


def get_prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def call(obj, method, *args, **kwargs):
    """Call a method if it exists; returns (ok, result)."""
    fn = getattr(obj, method, None)
    if fn is None:
        return False, None
    try:
        return True, fn(*args, **kwargs)
    except Exception as exc:
        warn("%s.%s failed: %s" % (_name(obj), method, exc))
        return False, None


def _name(obj):
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def enum(enum_cls_name, value_name, default=None):
    cls = getattr(unreal, enum_cls_name, None)
    if cls is None:
        return default
    return getattr(cls, value_name, default)


# --------------------------------------------------------------------------- subsystems
def actor_sub():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def level_sub():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def editor_world():
    try:
        return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    except Exception:
        return unreal.EditorLevelLibrary.get_editor_world()


def asset_tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def console(cmd):
    try:
        unreal.SystemLibrary.execute_console_command(editor_world(), cmd)
    except Exception as exc:
        warn("console '%s' failed: %s" % (cmd, exc))


# --------------------------------------------------------------------------- assets
def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def load(path):
    try:
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            return unreal.EditorAssetLibrary.load_asset(path)
    except Exception as exc:
        warn("load %s failed: %s" % (path, exc))
    return None


def create_asset(name, folder, cls, factory):
    """Create, or load if it already exists."""
    ensure_dir(folder)
    full = folder + "/" + name
    existing = load(full)
    if existing:
        return existing, False
    asset = asset_tools().create_asset(name, folder, cls, factory)
    if asset is None:
        raise RuntimeError("create_asset returned None for " + full)
    return asset, True


def save_asset(asset):
    try:
        unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
    except Exception as exc:
        warn("save failed for %s: %s" % (_name(asset), exc))


_ALL_ASSETS = None


def find_asset_by_name(asset_name, root="/Game", prefer_substring=None):
    """Find an asset object path by its short name anywhere under root (template content moves between versions)."""
    global _ALL_ASSETS
    if _ALL_ASSETS is None:
        try:
            _ALL_ASSETS = list(unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False))
        except Exception as exc:
            warn("list_assets failed: %s" % exc)
            _ALL_ASSETS = []
    hits = []
    for p in _ALL_ASSETS:
        p = str(p)
        short = p.rsplit("/", 1)[-1].split(".")[0]
        if short == asset_name:
            hits.append(p)
    if prefer_substring:
        hits.sort(key=lambda h: 0 if prefer_substring in h else 1)
    return hits[0] if hits else None


def reset_asset_cache():
    global _ALL_ASSETS
    _ALL_ASSETS = None


# --------------------------------------------------------------------------- spawning
SHAPES = {
    "cube": "/Engine/BasicShapes/Cube.Cube",
    "sphere": "/Engine/BasicShapes/Sphere.Sphere",
    "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
    "cone": "/Engine/BasicShapes/Cone.Cone",
    "plane": "/Engine/BasicShapes/Plane.Plane",
}
_MESH_CACHE = {}


def shape(name):
    if name not in _MESH_CACHE:
        m = unreal.EditorAssetLibrary.load_asset(SHAPES[name])
        if m is None:
            raise RuntimeError("missing engine basic shape " + name)
        _MESH_CACHE[name] = m
    return _MESH_CACHE[name]


def tag(actor, label=None, folder=None):
    try:
        tags = list(actor.get_editor_property("tags") or [])
        tags.append(unreal.Name(S.GEN_TAG))
        actor.set_editor_property("tags", tags)
    except Exception as exc:
        warn("tagging failed: %s" % exc)
    if label:
        try:
            actor.set_actor_label(label)
        except Exception:
            pass
    if folder:
        try:
            actor.set_folder_path(unreal.Name("ECHO/" + folder))
        except Exception:
            pass
    return actor


def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None, folder=None, scale=None):
    actor = actor_sub().spawn_actor_from_class(cls, V(*loc), R(*rot))
    if actor is None:
        raise RuntimeError("spawn failed for %s" % cls)
    if scale is not None:
        actor.set_actor_scale3d(V(*scale))
    return tag(actor, label, folder)


def component(actor, cls):
    try:
        c = actor.get_component_by_class(cls)
        if c:
            return c
    except Exception:
        pass
    try:
        comps = actor.get_components_by_class(cls)
        if comps:
            return comps[0]
    except Exception:
        pass
    return None


def spawn_mesh(shape_name, loc, scale, mat=None, rot=(0, 0, 0), label=None, folder=None,
               movable=False, shadows=True, collision=True):
    actor = spawn(unreal.StaticMeshActor, loc, rot, label, folder, scale)
    comp = actor.static_mesh_component
    if movable:
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(shape(shape_name))
    if mat is not None:
        n = 1
        try:
            n = max(1, int(comp.get_num_materials()))
        except Exception:
            pass
        for i in range(n):
            comp.set_material(i, mat)
    if not shadows:
        set_prop(comp, "cast_shadow", False, quiet=True)
    if not collision:
        try:
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            set_prop(comp, "collision_enabled", unreal.CollisionEnabled.NO_COLLISION, quiet=True)
    return actor


def box(center, size, mat=None, **kw):
    """Axis-aligned box from a centre point and a size in cm (engine Cube is 100 cm)."""
    return spawn_mesh("cube", center, (size[0] / 100.0, size[1] / 100.0, size[2] / 100.0), mat, **kw)


def box_from_min_max(mn, mx, mat=None, **kw):
    c = ((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, (mn[2] + mx[2]) / 2.0)
    s = (abs(mx[0] - mn[0]), abs(mx[1] - mn[1]), abs(mx[2] - mn[2]))
    return box(c, s, mat, **kw)


def cylinder(base_center, diameter, height, mat=None, **kw):
    c = (base_center[0], base_center[1], base_center[2] + height / 2.0)
    return spawn_mesh("cylinder", c, (diameter / 100.0, diameter / 100.0, height / 100.0), mat, **kw)


def sphere(center, diameters, mat=None, **kw):
    if not isinstance(diameters, (tuple, list)):
        diameters = (diameters, diameters, diameters)
    return spawn_mesh("sphere", center, tuple(d / 100.0 for d in diameters), mat, **kw)


def attach(child, parent):
    rule = unreal.AttachmentRule.KEEP_WORLD
    try:
        child.attach_to_actor(parent, unreal.Name(""), rule, rule, rule, False)
    except Exception as exc:
        warn("attach failed: %s" % exc)


def clear_generated_actors():
    sub = actor_sub()
    n = 0
    for a in list(sub.get_all_level_actors()):
        try:
            tags = [str(t) for t in (a.get_editor_property("tags") or [])]
        except Exception:
            continue
        if S.GEN_TAG in tags:
            sub.destroy_actor(a)
            n += 1
    log("removed %d previously generated actors" % n)


def kelvin(k):
    """Approximate blackbody colour (Tanner Helland fit) as LinearColor-ish sRGB 0..1."""
    t = k / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592)
        g = 288.1221695283 * ((t - 60) ** -0.0755148492)
        b = 255.0
    clamp = lambda v: max(0.0, min(255.0, v)) / 255.0  # noqa: E731
    # sRGB -> linear (approx gamma 2.2)
    return LC(clamp(r) ** 2.2, clamp(g) ** 2.2, clamp(b) ** 2.2)


# --------------------------------------------------------------------------- pivots + instancing
def pivot(loc, label=None, folder=None, movable=True):
    """An empty StaticMeshActor used as a transform root (groups, ISM holders)."""
    a = spawn(unreal.StaticMeshActor, loc, (0, 0, 0), label, folder)
    try:
        a.static_mesh_component.set_mobility(
            unreal.ComponentMobility.MOVABLE if movable else unreal.ComponentMobility.STATIC)
    except Exception:
        pass
    return a


ISM_STATE = {"ok": None, "fallback_spawned": 0}


def _add_ism_component(holder):
    """Adds a real (saved) InstancedStaticMeshComponent to a placed actor via the
    SubobjectDataSubsystem - the same path the Details panel's '+ Add' button uses."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_instance(holder)
    if not handles:
        raise RuntimeError("no subobject handles for holder")
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0],
                                          new_class=unreal.InstancedStaticMeshComponent,
                                          blueprint_context=None)
    res = sds.add_new_subobject(params)
    handle, fail = (res[0], res[1]) if isinstance(res, tuple) else (res, None)
    if fail is not None and str(fail).strip():
        raise RuntimeError("add_new_subobject: %s" % fail)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    comp = lib.get_object(lib.get_data(handle))
    if comp is None or not hasattr(comp, "add_instance"):
        raise RuntimeError("subobject is not an InstancedStaticMeshComponent")
    return comp


def instanced(shape_name, items, mat=None, label=None, folder=None, movable=False, shadows=True,
              collision=False, holder_loc=None, fallback_cap=None):
    """One draw call for many copies of a basic shape.
    items: list of (center, scale, rot) - centre in world cm, engine-shape scale, (pitch, yaw, roll).
    Returns the holder actor. If ISM creation fails once, every later call falls back to
    individual StaticMeshActors (attached to the holder, capped by fallback_cap)."""
    if not items:
        return None
    if holder_loc is None:
        n = float(len(items))
        holder_loc = (sum(i[0][0] for i in items) / n, sum(i[0][1] for i in items) / n,
                      sum(i[0][2] for i in items) / n)
    holder = pivot(holder_loc, label, folder, movable)
    if ISM_STATE["ok"] is not False and S.RIPPLE_USE_ISM:
        try:
            comp = _add_ism_component(holder)
            comp.set_mobility(unreal.ComponentMobility.MOVABLE if movable else unreal.ComponentMobility.STATIC)
            comp.set_static_mesh(shape(shape_name))
            if mat is not None:
                comp.set_material(0, mat)
            if not shadows:
                set_prop(comp, "cast_shadow", False, quiet=True)
            if not collision:
                try:
                    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass
            hx, hy, hz = holder_loc
            for (c, sc, rot) in items:
                t = unreal.Transform(location=V(c[0] - hx, c[1] - hy, c[2] - hz), rotation=R(*rot), scale=V(*sc))
                comp.add_instance(t)
            got = None
            try:
                got = int(comp.get_instance_count())
            except Exception:
                pass
            if got is not None and got < len(items):
                warn("ISM %s holds %d of %d instances" % (label, got, len(items)))
            ISM_STATE["ok"] = True
            return holder
        except Exception as exc:
            if ISM_STATE["ok"] is None:
                warn("instanced static meshes unavailable (%s) - falling back to separate actors" % exc)
            ISM_STATE["ok"] = False
    keep = items
    if fallback_cap is not None and len(items) > fallback_cap:
        step_n = len(items) / float(fallback_cap)
        keep = [items[int(i * step_n)] for i in range(fallback_cap)]
    for (c, sc, rot) in keep:
        a = spawn_mesh(shape_name, c, sc, mat, rot=rot, folder=folder, movable=movable, shadows=shadows,
                       collision=collision)
        attach(a, holder)
    ISM_STATE["fallback_spawned"] += len(keep)
    return holder


# --------------------------------------------------------------------------- asset discovery (art pass)
def _is_class(asset, class_name):
    """isinstance against unreal.<class_name>; True when the class can't be resolved (be permissive)."""
    cls = getattr(unreal, class_name, None)
    if not isinstance(cls, type):
        return True
    try:
        return isinstance(asset, cls)
    except Exception:
        return True


def find_first_asset(paths=(), names=(), class_name=None, prefer_substring=None):
    """First loadable asset among explicit package paths, then short names anywhere under /Game
    (asset-registry listing). class_name (e.g. 'SkeletalMesh') filters out same-named assets of
    another type (SK_Mannequin is a Skeleton, not a mesh). Returns (asset, path) or (None, None)."""
    tried = []
    for p in paths:
        tried.append(p)
        a = load(p)
        if a is not None and (class_name is None or _is_class(a, class_name)):
            return a, p
    for n in names:
        p = find_asset_by_name(n, prefer_substring=prefer_substring)
        if not p:
            continue
        tried.append(p)
        a = load(p.split(".")[0]) or load(p)
        if a is not None and (class_name is None or _is_class(a, class_name)):
            return a, p
    return None, None


def find_assets_matching(substring, root="/Game", exclude=(), limit=20):
    """Object paths whose short name contains substring (case-insensitive), minus any whose path
    contains one of `exclude`. Uses the cached /Game listing from find_asset_by_name."""
    global _ALL_ASSETS
    if _ALL_ASSETS is None:
        find_asset_by_name("__prime_asset_cache__", root)
    sub = substring.lower()
    out = []
    for p in _ALL_ASSETS or []:
        p = str(p)
        if not p.startswith(root):
            continue
        short = p.rsplit("/", 1)[-1].split(".")[0]
        if sub in short.lower() and not any(x.lower() in p.lower() for x in exclude):
            out.append(p)
            if len(out) >= limit:
                break
    return out


# --------------------------------------------------------------------------- easing (art pass)
def smootherstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def ease_in_out(t, power=2.0):
    t = max(0.0, min(1.0, t))
    return (2 ** (power - 1)) * t ** power if t < 0.5 else 1 - ((-2 * t + 2) ** power) / 2
