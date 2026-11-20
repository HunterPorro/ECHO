# ECHO
Story-first action game (Unreal Engine 5.8.4), adapted from the Dr. Rivers screenplay. Set in Lakemont.

- `ECHO.uproject`, `Config/`, `Content/` - the Unreal project. Open the .uproject in UE 5.8.
- `Content/Python/echo_kit/` - Python build scripts that generate the levels, materials and sequences.
- `Kit/` - setup.ps1, tools (mock_run, camera_clearance) and kit README. Run `Kit\setup.ps1` to rebuild levels or render.
- `Docs/` - design doc and Trial 1 plan.

Levels: Prologue_Unveiling (gala), Ripple_Demo, L_Trial1_Riverside2008 (playable; press Play).
Movement uses the stock Third Person template: `Content/ThirdPerson/Blueprints/BP_ThirdPersonCharacter` with Enhanced Input in `Content/Input`. No C++ module yet.
