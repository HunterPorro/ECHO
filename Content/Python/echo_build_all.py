"""Entry point for:  UnrealEditor-Cmd.exe ECHO.uproject -ExecutePythonScript="<Project>/Content/Python/echo_build_all.py"

Content/Python is on the editor's sys.path automatically, so the echo_kit package imports
directly. It can also be re-run from the editor:  Tools > Execute Python Script..., or in the
Output Log's Python console:  import echo_build_all  (set ECHO_QUIT=0 first to keep the editor open).
"""
import os
import sys

try:
    _here = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _here = os.environ.get("ECHO_KIT_DIR", "")
if _here and _here not in sys.path:
    sys.path.insert(0, _here)

import importlib  # noqa: E402

import echo_kit.settings  # noqa: E402
import echo_kit.util  # noqa: E402
import echo_kit.materials  # noqa: E402
import echo_kit.gala  # noqa: E402
import echo_kit.sequence  # noqa: E402
import echo_kit.render  # noqa: E402
import echo_kit.ripple_materials  # noqa: E402
import echo_kit.riverside  # noqa: E402
import echo_kit.ripple  # noqa: E402
import echo_kit.trial1_beats  # noqa: E402
import echo_kit.trial1_materials  # noqa: E402
import echo_kit.trial1  # noqa: E402
import echo_kit.trial1_sequence  # noqa: E402
import echo_kit.trial1_runtime  # noqa: E402
import echo_kit.main  # noqa: E402

# reload so edits are picked up when re-running inside a live editor session
for _m in (echo_kit.settings, echo_kit.util, echo_kit.materials, echo_kit.gala, echo_kit.sequence,
           echo_kit.render, echo_kit.ripple_materials, echo_kit.riverside, echo_kit.ripple,
           echo_kit.trial1_beats, echo_kit.trial1_materials, echo_kit.trial1, echo_kit.trial1_sequence,
           echo_kit.main):     # (trial1_runtime is not reloaded: a live director keeps its tick callback)
    importlib.reload(_m)
echo_kit.util.FAILURES.clear()

echo_kit.main.run()
