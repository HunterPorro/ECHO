"""Runs automatically when the ECHO editor starts (Unreal executes Content/Python/init_unreal.py).
Arms the Trial 1 Play-In-Editor director (echo_kit/trial1_runtime.py). It only acts while you
Play-In-Editor on L_Trial1_Riverside2008, so the gala and ripple maps are untouched.
Turn it off with settings.T1_DIRECTOR_AUTOSTART = False (or env ECHO_T1_DIRECTOR=0)."""
import os

try:
    import unreal
    if os.environ.get("ECHO_T1_DIRECTOR", "1") != "0" and not unreal.SystemLibrary.is_unattended():
        from echo_kit import settings as _S
        if getattr(_S, "T1_DIRECTOR_AUTOSTART", False):
            from echo_kit import trial1_runtime as _D
            _D.start()
except Exception as _exc:     # never block the editor from starting
    try:
        unreal.log_warning("[ECHO T1] init_unreal: director not armed (%s)" % _exc)
    except Exception:
        pass
