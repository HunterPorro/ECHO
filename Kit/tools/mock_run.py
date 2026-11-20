"""Static smoke test (runs on any machine, no Unreal): executes the whole build against a
fake `unreal` module that accepts every API call. Catches Python logic errors in the kit
(NameError, bad arithmetic, wrong helper signatures) and reports what would be spawned.
It can NOT prove Unreal API names are right - that is what the editor log is for.

    python tools/mock_run.py            # gala ('all') + Timeline Ripple ('ripple'), new + existing assets
    python tools/mock_run.py ripple     # only the ripple stages
"""
import os
import sys
import types
from collections import Counter

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ECHO", "Content", "Python")
sys.path.insert(0, os.path.abspath(KIT))

CALLS = Counter()
SPAWNED = Counter()


class Auto:
    """Accepts any attribute / call / arithmetic."""
    def __init__(self, name="auto"):
        self._n = name

    def __getattr__(self, item):
        if item.startswith("__"):
            raise AttributeError(item)
        CALLS[self._n + "." + item] += 1
        if item in ("get_all_channels", "get_channels_by_type"):
            return lambda *a, **k: [Auto("chan%d" % i) for i in range(9)]
        return Auto(self._n + "." + item)

    def __call__(self, *a, **k):
        return Auto(self._n + "()")

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return True

    def __int__(self):
        return 2

    def __float__(self):
        return 1.0

    def __index__(self):
        return 2

    def __str__(self):
        return self._n

    def get_editor_property(self, n):
        return Auto(self._n + ":" + n)

    def set_editor_property(self, n, v):
        CALLS["set:" + n] += 1


class Vector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Rotator:
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        self.roll, self.pitch, self.yaw = float(roll), float(pitch), float(yaw)


class Struct:
    def __init__(self, *a, **k):
        self.args, self.kw = a, k

    def set_editor_property(self, n, v):
        setattr(self, n, v)

    def get_editor_property(self, n):
        return getattr(self, n, Auto(n))


class FakeActor(Auto):
    def __init__(self, cls, loc, rot):
        super().__init__("actor<%s>" % getattr(cls, "_n", cls))
        self.loc, self.rot, self.scl = loc, rot, Vector(1, 1, 1)
        self.tags = []

    def get_actor_location(self):
        return self.loc

    def get_actor_rotation(self):
        return self.rot

    def get_actor_scale3d(self):
        return self.scl

    def set_actor_location(self, v, sweep=False, teleport=False):
        assert isinstance(v, Vector), "location must be a Vector"
        self.loc = v

    def set_actor_rotation(self, r, teleport=False):
        assert isinstance(r, Rotator), "rotation must be a Rotator"
        self.rot = r

    def set_actor_scale3d(self, s):
        assert isinstance(s, Vector), "scale must be a Vector"
        self.scl = s

    def get_editor_property(self, n):
        if n == "tags":
            return self.tags
        return Auto(n)

    def set_editor_property(self, n, v):
        if n == "tags":
            self.tags = v


class ActorSub(Auto):
    def spawn_actor_from_class(self, cls, loc, rot):
        assert isinstance(loc, Vector) and isinstance(rot, Rotator), "spawn needs Vector/Rotator"
        SPAWNED[getattr(cls, "_n", str(cls))] += 1
        return FakeActor(cls, loc, rot)

    def get_all_level_actors(self):
        return []


class Assets(Auto):
    EXIST = False

    def does_asset_exist(self, p):
        return Assets.EXIST

    def does_directory_exist(self, p):
        return True

    def list_assets(self, root, recursive=True, include_folder=False):
        return ["/Game/Characters/Mannequins/Meshes/SKM_Manny.SKM_Manny",
                "/Game/Characters/Mannequins/Meshes/SKM_Quinn.SKM_Quinn",
                "/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle",
                "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode"]


ISM = Counter()


class FakeISM(Auto):
    def __init__(self):
        super().__init__("ISM")
        self.n = 0

    def add_instance(self, t):
        self.n += 1
        ISM["instances"] += 1

    def get_instance_count(self):
        return self.n


class FakeSDS(Auto):
    def k2_gather_subobject_data_for_instance(self, actor):
        return [Auto("handle")]

    def add_new_subobject(self, params):
        ISM["components"] += 1
        return (Auto("new_handle"), "")


class FakeSubLib:
    @staticmethod
    def get_data(h):
        return h

    @staticmethod
    def get_object(d):
        return FakeISM()


def make_unreal():
    u = types.ModuleType("unreal")
    u.__getattr__ = lambda name: Auto("unreal." + name)  # module-level fallback (PEP 562)
    u.Vector, u.Rotator = Vector, Rotator
    for n in ("LinearColor", "Vector4", "Color", "FrameNumber", "FrameRate", "IntPoint", "Name",
              "SoftObjectPath", "DirectoryPath", "SingleAnimationPlayData", "MovieSceneObjectBindingID"):
        setattr(u, n, Struct)
    u.EditorAssetLibrary = Assets("EditorAssetLibrary")
    for n in ("SkeletalMesh", "StaticMesh", "SpotLightComponent", "PointLightComponent"):   # used with isinstance()
        setattr(u, n, type(n, (), {"_n": "unreal." + n}))
    sds = FakeSDS("SubobjectDataSubsystem")
    u.get_engine_subsystem = lambda cls: sds
    u.SubobjectDataBlueprintFunctionLibrary = FakeSubLib
    u.AddNewSubobjectParams = Struct
    sub = ActorSub("EditorActorSubsystem")
    u.get_editor_subsystem = lambda cls: sub if "Actor" in str(cls) else Auto("subsystem")
    u.log = lambda m: None
    u.log_warning = lambda m: print("WARN", m)
    u.log_error = lambda m: print("ERROR", m)

    class Paths:
        @staticmethod
        def project_saved_dir():
            return "/tmp/echo_mock_saved/"

        @staticmethod
        def convert_relative_path_to_full(p):
            return p
    u.Paths = Paths
    return u


def main():
    sys.modules["unreal"] = make_unreal()
    os.environ["ECHO_QUIT"] = "1"
    import echo_kit.main as main_mod
    import echo_kit.util as util
    import echo_kit.settings as S
    only = sys.argv[1:] or ["all", "ripple"]
    total_fail = 0
    for target in only:
        for exist, use_ism in ((False, True), (True, True), (False, False)):
            if target != "ripple" and not use_ism:
                continue
            Assets.EXIST = exist
            S.RIPPLE_USE_ISM = use_ism
            util.ISM_STATE.update({"ok": None, "fallback_spawned": 0})
            util.FAILURES.clear()
            SPAWNED.clear()
            ISM.clear()
            main_mod.run(target)
            print("\n--- %s, assets %s, ISM %s: %d failures" % (target, "existing" if exist else "new",
                                                              "on" if use_ism else "off (fallback)", len(util.FAILURES)))
            for f in util.FAILURES:
                print("   FAIL", f)
            print("    spawned actors:", sum(SPAWNED.values()), dict(SPAWNED.most_common(8)))
            if target == "ripple":
                import echo_kit.riverside as RV
                import echo_kit.ripple as RP
                print("    ISM components %d, instances %d, fallback actors %d" % (
                    ISM["components"], ISM["instances"], util.ISM_STATE["fallback_spawned"]))
                print("    groups A %d / B %d, lights A %d / B %d, people B %d, sequence %s" % (
                    len(RV.GROUPS["A"]), len(RV.GROUPS["B"]), len(RV.LIGHTS["A"]), len(RV.LIGHTS["B"]),
                    len(RV.PEOPLE_B), RP.INFO))
            if target == "all":
                total_fail += _gala_checks()
            if target == "trial1":
                total_fail += _trial1_checks()
            total_fail += len(util.FAILURES)
    return 1 if total_fail else 0


def _gala_checks():
    """Regression guards for the gala (v2 bug: the Echo turntable root was a non-uniformly scaled
    cylinder whose sequence keys reset its scale to 1, collapsing the plinth and stretching the car)."""
    import echo_kit.gala as G
    bad = 0
    roots = [G.ACTORS.get("turntable"), G.ACTORS.get("follow")] + list(G.ACTORS.get("sweeps", []))
    for a in roots:
        if a is None or not hasattr(a, "scl"):
            continue
        sc = a.get_actor_scale3d()
        if max(abs(sc.x - 1), abs(sc.y - 1), abs(sc.z - 1)) > 1e-6:
            print("   FAIL gala: animated root %s has scale (%.2f, %.2f, %.2f) - sequence keys reset it to 1"
                  % (a._n, sc.x, sc.y, sc.z))
            bad += 1
    parts = len(getattr(G, "CAR_PARTS", []))
    if parts < 20:
        print("   FAIL gala: only %d Echo car parts built" % parts)
        bad += 1
    print("    gala checks: %d Echo parts, animated roots scale-1: %s" % (parts, "ok" if not bad else "NO"))
    return bad


def _trial1_checks():
    """Trial 1 slice guards: every beat has its trigger volume, State B is saved parked under the world,
    the shift keys every group + light, the flythrough has its 4 cameras + the walking trio."""
    import echo_kit.trial1 as T
    import echo_kit.trial1_beats as TB
    import echo_kit.trial1_sequence as TS
    bad = []
    missing = [b["trigger"] for b in TB.BEATS if b["trigger"] not in T.TRIGGERS]
    if missing:
        bad.append("beats without a trigger volume: %s" % missing)
    if len(T.TRIGGERS) != len(TB.TRIGGERS):
        bad.append("%d/%d trigger volumes spawned" % (len(T.TRIGGERS), len(TB.TRIGGERS)))
    if len(T.GROUPS["A"]) < 6 or len(T.GROUPS["B"]) < 4:
        bad.append("state groups A %d / B %d (want >= 6 / 4)" % (len(T.GROUPS["A"]), len(T.GROUPS["B"])))
    for g in T.GROUPS["B"]:
        z = g.root.get_actor_location().z
        if z > T.HIDE_Z / 2:
            bad.append("State B group %s saved visible (z %.0f)" % (g.name, z))
    if TS.INFO["groups"] != len(T.GROUPS["A"]) + len(T.GROUPS["B"]):
        bad.append("shift keyed %d of %d groups" % (TS.INFO["groups"], len(T.GROUPS["A"]) + len(T.GROUPS["B"])))
    nl = sum(1 for k in ("A", "B", "blast") for l in T.LIGHTS[k] if l[1] is not None)
    if TS.INFO["lights"] != nl:
        bad.append("shift keyed %d of %d lights" % (TS.INFO["lights"], nl))
    if TS.INFO["cameras"] != 4 or len(TS.CAM_PATHS) != 4:
        bad.append("flythrough cameras %d (want 4)" % TS.INFO["cameras"])
    if len(T.CINE) != 3 or len(TS.TRIO_PATHS) != 3:
        bad.append("flythrough trio %d / paths %d (want 3)" % (len(T.CINE), len(TS.TRIO_PATHS)))
    for k in ("player_start", "ppv", "ppv_headache", "ppv_blast", "door", "door_open", "portal", "candle"):
        if T.ACTORS.get(k) is None:
            bad.append("missing actor: " + k)
    if len(T.SOLIDS) < 300:
        bad.append("only %d collidable boxes registered" % len(T.SOLIDS))
    if len(T.MARKERS["cover"]) < 8 or len(T.MARKERS["climb"]) < 3:
        bad.append("cover %d / climb %d markers" % (len(T.MARKERS["cover"]), len(T.MARKERS["climb"])))
    for b in bad:
        print("   FAIL trial1:", b)
    print("    trial1: %d solids, groups A %d / B %d, lights A %d / B %d / base %d / blast %d, triggers %d, "
          "cover %d, climb %d, shift %s (%d groups, %d lights), fly %s" % (
              len(T.SOLIDS), len(T.GROUPS["A"]), len(T.GROUPS["B"]), len(T.LIGHTS["A"]), len(T.LIGHTS["B"]),
              len(T.LIGHTS["base"]), len(T.LIGHTS["blast"]), len(T.TRIGGERS), len(T.MARKERS["cover"]),
              len(T.MARKERS["climb"]), TS.INFO["shift_mode"], TS.INFO["groups"], TS.INFO["lights"], TS.INFO["fly"]))
    return len(bad)


if __name__ == "__main__":
    sys.exit(main())
