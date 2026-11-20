# ECHO: Unreal Engine project kit (Prologue, "The Unveiling")

This kit builds the ECHO project and the opening gala level automatically, with no clicking in the editor. The target machine is Hunter's laptop: Windows 11, Ryzen AI 9 365, **Radeon 880M** integrated graphics, 32 GB RAM.

## What you get

Once `setup.ps1` finishes:

| | |
|---|---|
| **Project** | `C:\UnrealProjects\ECHO\ECHO.uproject` (Blueprint-only). Uses Lumen GI and reflections, Virtual Shadow Maps, DX12/SM6, and fully dynamic lighting. |
| **Level** | `/Game/ECHO/Maps/L_Prologue_Gala`:<br>• **Outside:** a wet blue-hour plaza with a red carpet, sodium street lamps and a skyline.<br>• **Facade:** a glass front with a walkable doorway.<br>• **Hall:** a black-marble hall with white-marble columns, walnut walls, ceiling coffers and 3 crystal chandeliers.<br>• **Stage:** a stage with an LED wall, a podium and the covered **Echo** on a turntable.<br>• **Atmosphere:** volumetric fog with spotlight beams and a cinematic post-process grade.<br>• **People:** about 60 black-tie mannequins plus a press pit, and **Dr. Rivers**, **Isabella** and the assistant as placeholders.<br>• **Flashes:** camera flashes in the crowd.<br>• **Play:** a PlayerStart on the red carpet. Press Play and you walk in as the Third Person character. |
| **Cinematic** | `/Game/ECHO/Cinematics/LS_Prologue_Unveiling`. 32 s at 24 fps, in 4 shots with CineCameras and depth of field:<br>1. **Oner:** exterior, through the glass, over the crowd, to the podium.<br>2. **Speech:** an 85mm MCU on Rivers.<br>3. **Point:** a pan to the car as the follow spot swings over.<br>4. **Reveal:** a low hero shot as the cover lifts away, the car spots ramp up and the turntable turns. |
| **Render presets** | `MRQ_Gala_1080p_Draft` (fast) and `MRQ_Gala_1080p_Final` (8 temporal samples). Output is 1080p PNGs, plus an MP4 if ffmpeg is installed. |

## Requirements

1. Install the **Epic Games Launcher**, sign in, and use **Unreal Engine > Library > +** to install **5.5 or newer**. 5.6+ is recommended because the MetaHuman Creator now lives inside the engine (see ASSETS.md). Leave the default "Templates and Feature Packs" option checked, since the kit copies the Third Person template from it.
2. Install the latest **AMD Adrenalin driver** for the Radeon 880M.
3. Optional: run `winget install Gyan.FFmpeg` to get MP4s from renders.

## Run it

Copy the whole `unreal-kit` folder to the laptop (for example `C:\ECHO-kit`), then in PowerShell:

```powershell
cd C:\ECHO-kit
powershell -ExecutionPolicy Bypass -File .\setup.ps1                       # create + build (first run: 30-90 min of shader compiling)
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipBuild -Render    # render the Draft cinematic (1080p PNG [+ MP4])
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipBuild -Render -Preset Final   # final quality (slow on the iGPU)
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipBuild -Open      # open the editor on the gala
```

| Flag | Meaning |
|---|---|
| `-ProjectDir` | Where to create the project. The default `C:\UnrealProjects\ECHO` has no spaces on purpose. |
| `-EngineDir` | Force an engine, e.g. `"C:\Program Files\Epic Games\UE_5.6"`. |
| `-Stages` | `all` (default), or a comma list of `perf`, `materials`, `level`, `sequence` and `render`. |
| `-Render` / `-Preset Draft\|Final` | Renders through the documented MRQ command line (`-game -LevelSequence -MoviePipelineConfig`). |
| `-RenderInEditor` | Renders with the in-editor PIE executor instead. |
| `-NullRHI` | Builds without the GPU (faster and fully headless). Rendering still needs the GPU. |
| `-Force` | Recopies the kit over an existing project. Content assets are kept. |
| `-SkipTemplate`, `-SkipEditorScalability` | Skip those steps. |
| `-TimeoutMinutes` | Default 240. |

These are what the headless step actually runs:

```text
UnrealEditor-Cmd.exe "C:\UnrealProjects\ECHO\ECHO.uproject" -ExecutePythonScript="C:/UnrealProjects/ECHO/Content/Python/echo_build_all.py" -unattended -nosplash -nopause -stdout -FullStdOutLogOutput -NoSound
UnrealEditor.exe "...\ECHO.uproject" /Game/ECHO/Maps/L_Prologue_Gala -game -LevelSequence="/Game/ECHO/Cinematics/LS_Prologue_Unveiling.LS_Prologue_Unveiling" -MoviePipelineConfig="/Game/ECHO/Cinematics/MRQ_Gala_1080p_Draft.MRQ_Gala_1080p_Draft" -windowed -resx=1280 -resy=720 -log -unattended -nosplash -NoTextureStreaming
```

You can also rebuild from inside a running editor. Open the Output Log, switch it to **Python**, and type `import os; os.environ["ECHO_QUIT"]="0"`, then use **Tools > Execute Python Script > Content/Python/echo_build_all.py**. Re-runs are idempotent: every generated actor is tagged `ECHO_GEN` and deleted first, and the materials and sequences are rebuilt in place.

## Outputs and logs

- **Frames:** `C:\UnrealProjects\ECHO\Saved\MovieRenders\Prologue_Unveiling\LS_Prologue_Unveiling.0000.png …`, plus `ECHO_Prologue_Unveiling_<Preset>.mp4`.
- **Build log:** `Saved\Logs\ECHO_build.log` covers every step, each one wrapped in try/except, and failures don't stop later steps. The full editor log is `Saved\Logs\ECHO.log`.
- **Status:** `Saved\ECHO_build_status.txt` is `OK` or `PARTIAL`, followed by the failed steps. setup.ps1 prints it.

## Tuning without code

All numbers live in `Content/Python/echo_kit/settings.py`: light levels in candelas, exposure clamps, fog density, crowd size, shot timings, render cvars and the iGPU scalability.

- **If the editor crawls:** set `GUESTS_PER_TABLE = 2`, or `CROWD_ENABLED = False`.
- **To get MetaHumans, real materials or a real car in:** see **ASSETS.md**.

## Files

```text
unreal-kit/
  README.md                this file
  ASSETS.md                free upgrades: Megascans/Fab, Automotive Materials, MetaHuman, Mixamo
  setup.ps1                engine discovery, project + template copy, scalability, headless build, render
  tools/mock_run.py        offline smoke test of the Python against a fake `unreal` module
  tools/camera_clearance.py  offline check that the sequence cameras never fly through geometry
  ECHO/
    ECHO.uproject          plugins: PythonScriptPlugin, EditorScriptingUtilities, SequencerScripting,
                           MovieRenderPipeline, Niagara, ChaosVehiclesPlugin, EnhancedInput, ModelingToolsEditorMode
    Config/DefaultEngine.ini   Lumen, VSM, DX12 SM6, [SystemSettingsEditor] iGPU tuning, startup map
    Config/DefaultGame.ini, DefaultInput.ini, DefaultEditor.ini
    Content/Python/echo_build_all.py   entry point for -ExecutePythonScript
    Content/Python/echo_kit/  settings, util, materials, gala, sequence, render, main
                              + ripple_materials, riverside, ripple   (Timeline Ripple tech demo)
```

## Timeline Ripple tech demo (Riverside, Lakemont)

A second, separate map: `/Game/ECHO/Maps/L_Riverside_Ripple` with `/Game/ECHO/Cinematics/LS_Ripple_Demo`
(20 s, 24 fps, 480 frames) and `LS_Ripple_Live` (the same world tracks with no cameras, for PIE). The
default `setup.ps1` run (`-Stages all`) never touches it, and the gala works exactly as before.

```powershell
# build (materials + level + sequences + MRQ presets), skipping the template copy you already did
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -Stages ripple
# render the Draft (1080p PNG -> Saved\MovieRenders\Ripple_Demo\, plus an MP4 if ffmpeg is on PATH)
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Render -Preset Draft -Target Ripple
# Final quality (8 temporal samples; much slower)
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Render -Preset Final -Target Ripple
# rebuild only the level + sequence after tweaking settings.py, then open the map
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -Stages "ripple_level,ripple_sequence" -Open
```

Stages: `ripple` = `ripple_materials,ripple_level,ripple_sequence,ripple_render`. `-Target` defaults to
Gala, and it is inferred as Ripple when `-Stages` mentions ripple. All the tunables are the `RIPPLE_*` /
`A_*` / `B_*` keys at the bottom of `settings.py`: wave speed, edge width, density, light levels and
the per-state sun and fog.

**How the ripple works.**
- `MPC_Ripple` holds Center, Radius, Enable and the edge look.
- Every Riverside surface uses `M_ECHO_RippleSurface` or `M_ECHO_RippleEmissive`. These are masked
  by a world-space sphere: State A parts (Side −1) are visible outside it, State B parts (Side +1)
  inside it.
- The edge chars to black, burns as an ember band, and tears along a noise field. The noise comes
  from `materials.noise3`, which falls back to a math field on 5.8.4.
- Sequencer keys `Radius` with R(f) = 3000·((f−168)/50)^3.6: slow when it is born at the bodega door,
  then exponential, so it overtakes the camera at about frame 212 and swallows the sky by frame ~370.
- Per-group transform keys clean up what a mask can't hide (text, B props before the wave). If the
  MPC track can't be built, the kit sets `Enable=0` and every prop tears or pops on the frame the
  front crosses it instead (log: `mode=swap`).
- Lights strike on or die by intensity keys. Sun angle, sun intensity and temperature, sky light,
  fog density and extinction, and the PPV blend weights cross over while the wave is on the lens.
  A third PPV adds the "hit" (chromatic split, flash, vignette).

**Shots.**
1. **S1 (0–150):** crane down the dead block onto the boarded door (24→30 mm, f/4).
2. **S2 (150–350):** the camera waits low on Delancey facing the door (40→32 mm, f/2). The wave is
   born there, the street tears from grey to gold toward us, and it passes through the lens with a
   handheld jolt. Then the camera cranes up and back to watch the sky tear while the first train
   rolls in on the El.
3. **S3 (350–480):** a slow push past Josh's shoulder to his father behind the counter (45→60 mm, f/2).

All three use a 2.39:1 filmback for the anamorphic feel.

### Art direction (environment / lighting)

- **One corner, two lives.** The story is told by what *changes*, so everything shared is base: the
  street, the row houses, the El, the skyline, Josh. It is dense, layered and instanced. That includes
  cornices with dentils, stone lintels, stoops with iron rails, NYC fire escapes with stairs and drop
  ladders, Chicago water towers, AC units, catenary wires (and the sneakers on a wire), cobra-head
  lamps, newspaper boxes (*Lakemont Ledger*, *The Daily Circuit*), hydrants, curb granite, sidewalk
  joints, zebra crossings, manholes with steam, and 38 mirror-black puddles that catch the neon.
- **State A, Vacant: grief as a palette.**
  - High, weak, 8200 K sun behind overcast, heavy volumetric haze, lifted cyan blacks, 0.72 saturation
    and heavy grain.
  - The only practical is one fluorescent tube buzzing under the El.
  - Rolled-down shutters, tags (*NO HOPE ON CUTLER*), the faded "LUCKY ST R DELI" sign, a memorial of
    dead candles at the door, a car on cinder blocks, and trash.
- **Exposure is locked per state.** EV 5.8 for Vacant and EV 6.4 for Busy (histogram min = max).
  Sky domes are graded three-band gradients (horizon, mid band, zenith) with a cloud field: blue-grey
  overcast in A, amber to magenta to indigo twilight in B. Height fog cuts off at 1 km so the domes
  read as sky rather than a wall of fog. Downtown's windows switch on as the wave reaches them.
- **The rewrite line.** A thin, shimmering blue-white rim sits exactly on the wave radius in every
  ripple material, with its width growing with distance so the ring reads across the sky. Behind it
  is the charring ember band, and the wavefront bubble is a translucent refracting Fresnel rim.
  Paper scraps (5–20 cm, burnt-edged) and 1–3 cm orange embers ride the front as motion streaks.
  None is spawned within 4.5 m of the lens.
- **State B, Busy: the corner if Dad lived.**
  - A low, raking 3300 K golden-hour sun from down Cutler that throws the El's tie-comb shadow across
    the street, with thinner fog so the light shafts read.
  - Teal shadows and warm highlights, neon bloom and a touch of flare.
  - Sodium lamps, the LUCKY STAR DELI lightbox sign, OPEN and 24 HRS neon, a striped awning, produce stands, flower
    buckets, string lights over Cutler, neighbour neon (LAUNDROMAT, PIZZA, NAILS), a cab where the
    wreck was, ~22 people, and a train overhead.
  - "Nothing changed... except": the Cortaz house across Cutler is a burned lot behind chain-link.
- **Budget for the Radeon 880M.**
  - Only the sun casts shadows. ~16 non-shadow local lights are faded in by Sequencer.
  - Base dressing is ~7.8k instances in ~60 ISM draw calls.
  - State props are ~57 movable groups. FX are 86 small keyed meshes (Niagara stand-ins).
  - Lumen runs in software RT with VSM, and fog runs at the iGPU grid size in Draft.
- **Future path.** Data Layers (World Partition) per state for gameplay, Niagara shreds instead of
  keyed meshes, and Megascans brick and asphalt (ASSETS.md) on the same masters.

## Trial 1 vertical slice (Riverside, January 22, 2008)

A third map, separate from the others: `/Game/ECHO/Maps/L_Trial1_Riverside2008`. It is chapter 6's first
history edit, built as a playable, art-directed blockout on the ripple demo's corner two years earlier.
The Lucky Star is open, and the Cortaz building at the SE corner is lived in. Neither `-Stages all` nor
the ripple stages touch it. The beat chart, mechanics and stubs are in `../trial1-plan.md`.

```powershell
# build (MIT1_* materials + level + both sequences + MRQ presets)
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -Stages trial1
# render the establishing flythrough (Draft, 1080p PNG -> Saved\MovieRenders\Trial1_Flythrough\ + MP4)
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Render -Preset Draft -Target Trial1
# open the map and press Play: the director (Content/Python/init_unreal.py) runs the beats
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Open -Target Trial1
```

- **Stages.** `trial1` expands to `trial1_materials,trial1_level,trial1_sequence,trial1_render`. If the
  gala and ripple masters are missing, it builds them first.
- **Modules.**
  - `trial1_beats.py` holds the beats B01–B11, triggers, marks, the route and the climb stack, as pure data.
  - `trial1_materials.py` makes the `MIT1_*` / `MIRT1_*` instances.
  - `trial1.py` is the level.
  - `trial1_sequence.py` builds `LS_Trial1_Flythrough` and `LS_Trial1_Shift`.
  - `trial1_runtime.py` is the Play-In-Editor director. It has no Blueprints.
- **Gameplay hooks.**
  - Every beat is a `TriggerBox` tagged `T1.Trigger`, `T1.Id.<id>`, `T1.Kind.<hold|objective|lore|collectible|blend|watch|noise|hide|shift>`
    and `T1.Beat.<Bxx>`.
  - Checkpoints, marks, cover and climb spots are `TargetPoint`s tagged `T1.Checkpoint.*`, `T1.Mark.*`, `T1.Cover.*` and `T1.Climb.*`.
  - Each beat also has a `Note` actor describing it.
  - In PIE, the director handles hold-to-complete, forced walk in the blend-in zones, suspicion, noise and alert, hiding, checkpoints, companion marks, the lockpicked door and John's candle.
  - It then plays `LSA_Trial1_Shift`.
  - From the Python console: `import echo_kit.trial1_runtime as D; D.status(); D.skip(); D.force_shift()`.
- **The shift.** It reuses the ripple A/B approach.
  - State A ("Before": glass, curtains, plants, the couch and bed, TV, lamps, candle) is saved visible.
  - State B ("Burning": window fires, room fires, smoke, charred furniture, plus a blast group of glass, the door and debris) is saved parked under the world.
  - `LS_Trial1_Shift` keys `MPC_Ripple` from the stove with `Center` (Radius 0→350→1400→3200, RimStrength 0). A tears and B burns in pixel by pixel. At f132 the explosion fires: glass out, debris in, the blast light and the blast PPV.
  - The headache PPV runs from f0 to f60. If the ripple masters are missing, it falls back to transform swaps (log: `mode=swap`).
- **Offline checks.**
  - `python3 tools/mock_run.py trial1` builds everything against a fake `unreal`.
  - `python3 tools/camera_clearance.py trial1` runs:
    - the cameras and the walking trio against every primitive;
    - a 34 cm / 45 cm-step capsule walk along the critical path;
    - the climb hops.

## Known limits (honest)

- **Look:** this is a **look-dev greybox**. The lighting, fog, grade, DOF and camera language are what carry the frame. The hall, car and people are primitives and mannequins until the ASSETS.md upgrades go in.
- **Speed:** the Radeon 880M gives an editor viewport of roughly 15–30 fps at "High / 75%" in this level. Draft renders take minutes per second of film, and Final renders take a lot longer. Close other apps and plug in the charger.
- **Ripple in the editor:** without the sequence playing, the MPC defaults (Radius 0, Enable 1) show
  only State A surfaces, but State B *text* and lights stay at their saved transforms and intensities
  (B lights are saved at 0). Scrub `LS_Ripple_Demo` in Sequencer to see the real states.
- **Trial 1:** the director runs in Play-In-Editor only (editor Python). A packaged build needs these
  hooks ported to a Blueprint or C++ GameMode. The tags and trial1_beats.py data are designed for that.
  Tyler's shot and John's gas and candle are text stubs (see trial1-plan.md).
- **Rivers' gestures:** he doesn't point or talk yet. Add the Mixamo clips described in ASSETS.md §5.
