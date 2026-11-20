"""Orchestrates the build. Stages (env ECHO_STAGES, comma list, default 'all'):
    perf       - editor scalability tuned for the Radeon 880M
    materials  - master materials + instances
    level      - the gala level (implies materials if they don't exist yet)
    sequence   - Level Sequences (needs the level actors from this run or a rebuild)
    render     - Movie Render Queue presets
  Timeline Ripple tech demo (never part of 'all'):
    ripple            - = ripple_materials,ripple_level,ripple_sequence,ripple_render
    ripple_materials  - MPC_Ripple + ripple masters + Riverside instances (needs gala masters; builds them if missing)
    ripple_level      - L_Riverside_Ripple (State A + State B + base dressing)
    ripple_sequence   - LS_Ripple_Demo + LS_Ripple_Live (rebuilds the level if this run didn't)
    ripple_render     - MRQ_Ripple_1080p_Draft / _Final presets
  Trial 1 vertical slice (never part of 'all'):
    trial1            - = trial1_materials,trial1_level,trial1_sequence,trial1_render
    trial1_materials  - MIT1_* instances (needs the gala masters + ripple masters; builds them if missing)
    trial1_level      - L_Trial1_Riverside2008 (route, Lucky Star, Cortaz building A + B, triggers, cast)
    trial1_sequence   - LS_Trial1_Flythrough (render target) + LS_Trial1_Shift (the history edit)
    trial1_render     - MRQ_Trial1_1080p_Draft / _Final presets
Env:
    ECHO_QUIT=1           quit the editor when finished (default 1)
    ECHO_RENDER=editor    after building, render the Draft preset inside the editor (PIE executor)
    ECHO_RENDER_PRESET    preset for ECHO_RENDER=editor (default MRQ_Gala_1080p_Draft / MRQ_Ripple_1080p_Draft)
    ECHO_RENDER_TARGET    gala (default) | ripple | trial1
"""
import os
import time

import unreal

from . import settings as S
from . import util as U


def apply_editor_perf():
    for k, v in S.EDITOR_SCALABILITY.items():
        U.console("%s %s" % (k, v))
    # keep Lumen alive in the editor even on a modest preset
    U.console("r.DynamicGlobalIlluminationMethod 1")
    U.console("r.ReflectionMethod 1")


def _wait_for_assets():
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        ar.search_all_assets(True)
        ar.wait_for_completion()
    except Exception as exc:
        U.warn("asset registry wait: %s" % exc)


def run(stages=None, quit_editor=None):
    t0 = time.time()
    stages = (stages or os.environ.get("ECHO_STAGES", "all")).lower()
    want = set(s.strip() for s in stages.split(",")) if stages != "all" else {
        "perf", "materials", "level", "sequence", "render"}
    if "ripple" in want:
        want |= {"ripple_materials", "ripple_level", "ripple_sequence", "ripple_render"}
    if "trial1" in want:
        want |= {"trial1_materials", "trial1_level", "trial1_sequence", "trial1_render"}
    if quit_editor is None:
        quit_editor = os.environ.get("ECHO_QUIT", "1") == "1"
    render_mode = os.environ.get("ECHO_RENDER", "").lower()
    U.log("==== ECHO build start: stages=%s, UE %s ====" % (sorted(want), unreal.SystemLibrary.get_engine_version()))
    _wait_for_assets()
    for d in (S.ROOT, S.MAT_DIR, S.MAT_DIR + "/Masters", S.MAP_DIR, S.CINE_DIR):
        U.ensure_dir(d)

    if "perf" in want:
        with U.step("editor scalability for integrated GPU"):
            apply_editor_perf()

    from . import materials, gala, sequence, render

    if "materials" in want or ("level" in want and not unreal.EditorAssetLibrary.does_asset_exist(
            S.MAT_DIR + "/MI_Floor_BlackMarble")):
        with U.step("materials"):
            materials.build_all()

    actors = {}
    if "level" in want:
        actors = gala.build()
    if "sequence" in want:
        if not actors:
            U.warn("sequence stage needs the level actors - rebuilding the level first")
            actors = gala.build()
        sequence.build(actors)
        with U.step("save level (sequence actors)"):
            gala.save_level()
    if "render" in want:
        with U.step("Movie Render Queue presets"):
            render.build_presets()
            U.log("command-line render: " + render.command_line())

    # ---------------------------------------------------------------- Timeline Ripple tech demo
    if want & {"ripple_materials", "ripple_level", "ripple_sequence", "ripple_render"}:
        from . import ripple_materials, riverside, ripple
        U.ensure_dir(S.RIPPLE_MAT_DIR)
        need_mats = "ripple_materials" in want or (
            ("ripple_level" in want or "ripple_sequence" in want)
            and not unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/MIR_B_Neon_Red"))
        if need_mats:
            if not unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/Masters/M_ECHO_Surface"):
                with U.step("gala master materials (ripple needs M_ECHO_Surface)"):
                    materials.build_all()
            with U.step("ripple materials"):
                ripple_materials.build_all()
        rv_actors = {}
        if "ripple_level" in want:
            rv_actors = riverside.build()
        if "ripple_sequence" in want:
            if not rv_actors:
                U.warn("ripple_sequence needs the riverside actors - rebuilding the level first")
                rv_actors = riverside.build()
            ripple.build(rv_actors)
            with U.step("save riverside level (sequence actors)"):
                gala.save_level()
        if "ripple_render" in want:
            with U.step("Movie Render Queue presets (ripple)"):
                render.build_presets("ripple")
                U.log("command-line render: " + render.command_line(target="ripple"))

    # ---------------------------------------------------------------- Trial 1 vertical slice
    if want & {"trial1_materials", "trial1_level", "trial1_sequence", "trial1_render"}:
        from . import ripple_materials, trial1_materials, trial1, trial1_sequence
        U.ensure_dir(S.RIPPLE_MAT_DIR)
        need_t1 = "trial1_materials" in want or (
            ("trial1_level" in want or "trial1_sequence" in want)
            and not unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/MIT1_Dumpster_Green"))
        if need_t1:
            if not unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/Masters/M_ECHO_Surface"):
                with U.step("gala master materials (trial1 needs M_ECHO_Surface)"):
                    materials.build_all()
            if not unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/MI_Brick_Red") or \
                    not unreal.EditorAssetLibrary.does_asset_exist(S.MAT_DIR + "/Masters/M_ECHO_RippleSurface"):
                with U.step("ripple materials (trial1 reuses Riverside's brick/street + the ripple masters)"):
                    ripple_materials.build_all()
            with U.step("trial1 materials"):
                trial1_materials.build_all()
        t1_actors = {}
        if "trial1_level" in want:
            t1_actors = trial1.build()
        if "trial1_sequence" in want:
            if not t1_actors:
                U.warn("trial1_sequence needs the trial1 actors - rebuilding the level first")
                t1_actors = trial1.build()
            trial1_sequence.build(t1_actors)
            with U.step("save trial1 level (sequence actors)"):
                gala.save_level()
        if "trial1_render" in want:
            with U.step("Movie Render Queue presets (trial1)"):
                render.build_presets("trial1")
                U.log("command-line render: " + render.command_line(target="trial1"))

    with U.step("save all ECHO assets"):
        unreal.EditorAssetLibrary.save_directory(S.ROOT, only_if_is_dirty=True, recursive=True)

    U.log("==== ECHO build done in %.0fs - %d step(s) failed ====" % (time.time() - t0, len(U.FAILURES)))
    for name, msg in U.FAILURES:
        U.warn("FAILED: %s -> %s" % (name, msg))
    # machine-readable status for setup.ps1
    try:
        saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        with open(os.path.join(saved, "ECHO_build_status.txt"), "w", encoding="utf-8") as fh:
            fh.write("OK\n" if not U.FAILURES else "PARTIAL\n")
            for name, msg in U.FAILURES:
                fh.write("%s :: %s\n" % (name, msg))
    except Exception:
        pass

    if render_mode == "editor":
        with U.step("in-editor render", critical=False):
            tgt = os.environ.get("ECHO_RENDER_TARGET", "gala").lower()
            default = {"ripple": "MRQ_Ripple_1080p_Draft",
                       "trial1": "MRQ_Trial1_1080p_Draft"}.get(tgt, "MRQ_Gala_1080p_Draft")
            render.render_in_editor(os.environ.get("ECHO_RENDER_PRESET", default),
                                    quit_when_done=quit_editor, target=tgt)
            return   # the MRQ finished-callback quits the editor
    if quit_editor:
        U.log("quitting editor")
        unreal.SystemLibrary.quit_editor()
