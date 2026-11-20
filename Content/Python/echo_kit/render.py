"""Movie Render Queue: 1080p PNG presets + an optional in-editor (PIE) render.

Two saved presets (MoviePipelinePrimaryConfig assets in /Game/ECHO/Cinematics):
    MRQ_Gala_1080p_Draft  - 1 temporal sample, TSR. Quick look (minutes per second of film on an iGPU).
    MRQ_Gala_1080p_Final  - 8 temporal samples (AA none), cinematic scalability, high-quality cvars.

Command-line render (what setup.ps1 -Render does, no clicking):
    UnrealEditor.exe ECHO.uproject /Game/ECHO/Maps/L_Prologue_Gala -game
        -LevelSequence=/Game/ECHO/Cinematics/LS_Prologue_Unveiling.LS_Prologue_Unveiling
        -MoviePipelineConfig=/Game/ECHO/Cinematics/MRQ_Gala_1080p_Final.MRQ_Gala_1080p_Final
        -windowed -resx=1280 -resy=720 -log -unattended -nosplash -NoTextureStreaming
Frames land in <Project>/Saved/MovieRenders/Prologue_Unveiling/ (override with env ECHO_RENDER_DIR).

Every entry point takes target='gala' (default, unchanged) or target='ripple':
    MRQ_Ripple_1080p_Draft / _Final -> L_Riverside_Ripple + LS_Ripple_Demo -> Saved/MovieRenders/Ripple_Demo/
and target='trial1':
    MRQ_Trial1_1080p_Draft / _Final -> L_Trial1_Riverside2008 + LS_Trial1_Flythrough -> Saved/MovieRenders/Trial1_Flythrough/
"""
import os

import unreal

from . import settings as S
from .util import error, log, set_prop, warn

_KEEP = {}     # keep the executor alive while it renders


TARGETS = {
    "gala": lambda: dict(presets=S.MRQ_PRESETS, map_path=S.MAP_PATH, map_name=S.MAP_NAME, seq_path=S.SEQ_PATH,
                         seq_name=S.SEQ_NAME, subdir="Prologue_Unveiling", job="ECHO_Prologue_"),
    "ripple": lambda: dict(presets=S.RIPPLE_MRQ_PRESETS, map_path=S.RIPPLE_MAP_PATH, map_name=S.RIPPLE_MAP_NAME,
                           seq_path=S.RIPPLE_SEQ_PATH, seq_name=S.RIPPLE_SEQ_NAME, subdir=S.RIPPLE_RENDER_SUBDIR,
                           job="ECHO_Ripple_"),
    "trial1": lambda: dict(presets=S.T1_MRQ_PRESETS, map_path=S.T1_MAP_PATH, map_name=S.T1_MAP_NAME,
                           seq_path=S.T1_SEQ_PATH, seq_name=S.T1_SEQ_NAME, subdir=S.T1_RENDER_SUBDIR,
                           job="ECHO_Trial1_"),
}


def target_info(target="gala"):
    return TARGETS.get((target or "gala").lower(), TARGETS["gala"])()


def output_dir(target="gala"):
    d = os.environ.get("ECHO_RENDER_DIR")
    if not d:
        saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        d = os.path.join(saved, "MovieRenders", target_info(target)["subdir"])
    d = d.replace("\\", "/")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _setting(cfg, cls_name):
    cls = getattr(unreal, cls_name, None)
    if cls is None:
        warn("MRQ setting class missing: " + cls_name)
        return None
    try:
        return cfg.find_or_add_setting_by_class(cls)
    except Exception as exc:
        warn("find_or_add_setting_by_class(%s): %s" % (cls_name, exc))
        return None


def configure(cfg, temporal, spatial, aa_name, warmup, final, target="gala"):
    out = _setting(cfg, "MoviePipelineOutputSetting")
    if out:
        set_prop(out, "output_resolution", unreal.IntPoint(*S.RENDER_RESOLUTION))
        dp = unreal.DirectoryPath()
        dp.set_editor_property("path", output_dir(target))
        set_prop(out, "output_directory", dp)
        set_prop(out, "file_name_format", "{sequence_name}.{frame_number}")
        set_prop(out, "zero_pad_frame_numbers", 4)
        set_prop(out, "override_existing_output", True)
        set_prop(out, "use_custom_frame_rate", False)
    _setting(cfg, "MoviePipelineDeferredPassBase")
    _setting(cfg, "MoviePipelineImageSequenceOutput_PNG")
    aa = _setting(cfg, "MoviePipelineAntiAliasingSetting")
    if aa:
        set_prop(aa, "spatial_sample_count", int(spatial))
        set_prop(aa, "temporal_sample_count", int(temporal))
        set_prop(aa, "override_anti_aliasing", True)
        set_prop(aa, "anti_aliasing_method", getattr(unreal.AntiAliasingMethod, aa_name))
        set_prop(aa, "engine_warm_up_count", int(warmup))
        set_prop(aa, "render_warm_up_count", int(warmup))
        set_prop(aa, "render_warm_up_frames", True)
        set_prop(aa, "use_camera_cut_for_warm_up", False)
    go = _setting(cfg, "MoviePipelineGameOverrideSetting")
    if go:
        set_prop(go, "cinematic_quality_settings", True)
        set_prop(go, "use_lod_zero", True)
        set_prop(go, "disable_hlo_ds", True, quiet=True)
        set_prop(go, "use_high_quality_shadows", True)
        set_prop(go, "flush_streaming_managers", True, quiet=True)
        tsm = getattr(unreal, "MoviePipelineTextureStreamingMethod", None)
        if tsm is not None and hasattr(tsm, "FULLY_LOAD"):
            set_prop(go, "texture_streaming", tsm.FULLY_LOAD, quiet=True)
    cv = _setting(cfg, "MoviePipelineConsoleVariableSetting")
    if cv:
        cvars = dict(S.RENDER_CVARS)
        if not final:   # draft: keep the expensive ones closer to editor values
            cvars.update({"r.Lumen.ScreenProbeGather.DownsampleFactor": 16,
                          "r.VolumetricFog.GridPixelSize": 8,
                          "r.Shadow.Virtual.SMRT.RayCountLocal": 7})
        for k, v in cvars.items():
            ok = False
            for fn in ("add_or_update_console_variable", "add_console_variable"):
                try:
                    getattr(cv, fn)(k, float(v))
                    ok = True
                    break
                except Exception:
                    continue
            if not ok:
                warn("could not add render cvar " + k)
    return cfg


def build_presets(target="gala"):
    made = {}
    folder = S.CINE_DIR
    for name, (temporal, spatial, aa_name, warmup) in target_info(target)["presets"].items():
        path = folder + "/" + name
        try:
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                cfg = unreal.EditorAssetLibrary.load_asset(path)
            else:
                cfg = None
                factory = getattr(unreal, "MoviePipelinePrimaryConfigFactory", None)
                if factory is not None:
                    try:
                        cfg = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                            name, folder, unreal.MoviePipelinePrimaryConfig, factory())
                    except Exception as exc:
                        warn("config factory failed (%s); exporting a transient config instead" % exc)
                if cfg is None:
                    tmp = unreal.new_object(unreal.MoviePipelinePrimaryConfig)
                    configure(tmp, temporal, spatial, aa_name, warmup, "Final" in name, target)
                    res = unreal.MoviePipelineEditorLibrary.export_config_to_asset(tmp, folder, name, True)
                    cfg = res[0] if isinstance(res, tuple) else res
                    if cfg is None:
                        raise RuntimeError("export_config_to_asset failed: %s" % (res,))
            configure(cfg, temporal, spatial, aa_name, warmup, "Final" in name, target)
            unreal.EditorAssetLibrary.save_loaded_asset(cfg, False)
            made[name] = cfg
            log("MRQ preset ready: %s (temporal %d, %s)" % (path, temporal, aa_name))
        except Exception as exc:
            error("MRQ preset %s failed: %s" % (name, exc))
    return made


def command_line(preset=None, target="gala"):
    t = target_info(target)
    preset = preset or [n for n in t["presets"] if n.endswith("Final")][0]
    return ('"<UE>/Engine/Binaries/Win64/UnrealEditor.exe" "<Project>/ECHO.uproject" %s -game '
            '-LevelSequence=%s.%s -MoviePipelineConfig=%s/%s.%s -windowed -resx=1280 -resy=720 '
            '-log -unattended -nosplash -NoTextureStreaming'
            % (t["map_path"], t["seq_path"], t["seq_name"], S.CINE_DIR, preset, preset))


def render_in_editor(preset="MRQ_Gala_1080p_Draft", quit_when_done=True, target="gala"):
    """Queue the job and render with the PIE executor inside this editor session (needs a real GPU RHI)."""
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = subsystem.get_queue()
    queue.delete_all_jobs()
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    t = target_info(target)
    job.set_editor_property("job_name", t["job"] + preset)
    job.set_editor_property("sequence", unreal.SoftObjectPath(t["seq_path"] + "." + t["seq_name"]))
    job.set_editor_property("map", unreal.SoftObjectPath(t["map_path"] + "." + t["map_name"]))
    cfg = unreal.EditorAssetLibrary.load_asset(S.CINE_DIR + "/" + preset)
    if cfg is None:
        raise RuntimeError("preset missing: " + preset)
    job.set_configuration(cfg)
    executor = subsystem.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    if executor is None:
        raise RuntimeError("render_queue_with_executor returned None")
    _KEEP["executor"] = executor

    def _finished(exec_obj, success):
        log("MRQ finished, success=%s, frames in %s" % (success, output_dir(target)))
        if quit_when_done:
            unreal.SystemLibrary.quit_editor()

    def _error(exec_obj, pipeline, is_fatal, error_text):
        error("MRQ error (fatal=%s): %s" % (is_fatal, error_text))

    try:
        executor.on_executor_finished_delegate.add_callable_unique(_finished)
        executor.on_executor_errored_delegate.add_callable_unique(_error)
    except Exception as exc:
        warn("could not hook MRQ delegates (%s) - editor will stay open after the render" % exc)
    _KEEP["callbacks"] = (_finished, _error)
    log("MRQ rendering %s -> %s" % (preset, output_dir(target)))
    return executor
