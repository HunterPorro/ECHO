# ECHO: free assets to upgrade the Prologue gala

The kit builds the gala **with no downloads**. Every surface is a procedural material, the car is made from basic shapes, and the crowd is Epic's mannequins. This list covers what to swap in, in priority order, to move the look from a greybox toward a GTA-style frame. Everything here is free with a free Epic account (Adobe ID for Mixamo).

> **Engine version note (Nov 2026):** Epic retired the MetaHuman Creator web app on **Nov 5, 2026**, so MetaHumans are now made *inside* Unreal Engine **5.6+** with the built-in MetaHuman Creator. If you're installing fresh, **install the newest UE 5.x (5.6 or later)**, not 5.5. The kit works on 5.5+, and `setup.ps1` picks the highest version installed.

Licensing: Fab content is under the **Fab Standard License** (commercial use allowed; you can't resell the raw assets) or **CC-BY** (credit the author). As of **Nov 5, 2026** the whole Quixel Megascans library is free on Fab again. Always check the price and license on the listing before you build around an asset.

---

## How to plug things in without editing code

Open `Content/Python/echo_kit/settings.py` in the project and fill in the upgrade hooks at the bottom, then re-run `setup.ps1 -Stages "level,sequence"`. The level and cinematic rebuild with your assets.

| Hook | What it does | Example value |
|---|---|---|
| `MATERIAL_OVERRIDES` | Swaps any generated material (e.g. `MI_Floor_BlackMarble`) for a downloaded one | `"/Game/Fab/Megascans/Surfaces/Black_Marble/MI_Black_Marble"` |
| `ECHO_CAR_MESH` (+ `_YAW_OFFSET`, `_SCALE`) | Replaces the primitive Echo with a real car mesh or Blueprint on the turntable | `"/Game/Vehicles/Concept/SM_ConceptCar"` |
| `CAST_BLUEPRINTS` | Spawns MetaHuman Blueprints for Dr. Rivers, Isabella and the assistant instead of mannequins | `"/Game/MetaHumans/Rivers/BP_Rivers"` |
| `IDLE_ANIM` | Forces a specific idle, e.g. a retargeted Mixamo clip | `"/Game/ECHO/Anims/Mixamo/A_Idle_Talking"` |

**Folder rule:** let Fab import where it wants (usually `Content/Fab/...`). Put anything you import by hand (FBX from Mixamo, etc.) under `Content/ECHO/Imported/<Source>/`. Never put files inside `Content/ECHO/Materials|Maps|Cinematics`, because those folders are regenerated.

---

## 1. Megascans / Fab surfaces (biggest win for the least effort)

In the editor: **Window > Fab**, sign in, search, then **Add to Project**. Set **Fab Settings > Megascans > Preferred Quality Tier = Medium**. 2K textures are plenty on the Radeon 880M; use High only for close-ups.

| Search Fab for | Replaces | Hook key |
|---|---|---|
| "black marble" / "polished marble floor" (Megascans surface) | glossy dark hall floor | `MI_Floor_BlackMarble` |
| "white marble" / "Calacatta marble" | columns, back wall | `MI_Marble_White` |
| "walnut wood panel" / "wood veneer" | side walls | `MI_Wall_Walnut` |
| "wet asphalt" + "puddle" decals | street | `MI_Asphalt_Wet` |
| "concrete pavement wet" | plaza | `MI_Concrete_Wet` |
| "carpet" / "velvet fabric" | red carpet, ropes | `MI_RedCarpet`, `MI_VelvetRope` |
| "brushed gold metal" / "brass" | trims, stanchions, chandelier frames | `MI_Gold` |
| Megascans 3D: "stanchion", "planter", "bollard", "trash can", "manhole" | exterior dressing (place by hand) | n/a |

## 2. Epic's free sample content (Fab, publisher "Epic Games")

| Pack | Why | Notes |
|---|---|---|
| **Automotive Materials** | Real car paint (clear coat + flakes), tinted glass, chrome, tire rubber | Point `MI_CarPaint_Pearl`, `MI_CarGlass_Dark`, `MI_Chrome` and `MI_Tire` at these. This is the single best upgrade for the Echo reveal. |
| **City Sample Vehicles** | Drivable Chaos vehicles for the street outside, plus later the drive home | Large download. Import only the vehicles. `ChaosVehiclesPlugin` is already enabled. |
| **City Sample Crowds** | Realistic people with Mass crowd setup | Better than mannequins for background guests. They wear casual clothes, so use them for the exterior and press, not the black-tie tables. |
| **Game Animation Sample** | 500+ free mocap animations on the UE5 mannequin skeleton (idles, talking, gestures) | Already on the Manny/Quinn skeleton, so no retargeting needed. Use for crowd idles via `IDLE_ANIM`. |
| **City Sample** (the full Matrix Awakens city) | Building kits for Lakemont's Midtown later | ~100 GB and far too heavy for the 880M as a whole city. Migrate single buildings only. |

## 3. The Echo car

The script calls it "futuristic shaped... with little light on it". Search Fab for **"concept car"**, **"sci-fi car"**, **"futuristic vehicle"** and filter **Free**. Pick a model with clean topology and separate glass and light materials. Then:
1. Import it under `Content/ECHO/Imported/EchoCar/`.
2. Set `ECHO_CAR_MESH` to its path. Set `ECHO_CAR_MESH_YAW_OFFSET` to 90 or -90 if the nose points sideways, and `ECHO_CAR_MESH_SCALE` if it's in the wrong units.
3. Apply the Automotive Materials paint, and add an emissive strip to its light material.

The cover, turntable, spotlights and the sequence keep working, because they key off the turntable.

## 4. MetaHumans: Dr. Rivers and Isabella (UE 5.6+)

1. **Edit > Plugins**, enable **MetaHuman Creator** and **MetaHuman Core Tech**, and restart.
2. **Content Browser > right-click > MetaHuman > MetaHuman Character**. Name it `MHC_Rivers`, then sculpt and choose a preset.
   - **Dr. Rivers:** 50s, CEO, salt-and-pepper short hair, clean shave or a light beard, tuxedo or dark suit (script p.1, gala).
   - **Isabella:** his wife, elegant, a deep-red gown (that matches the kit's `MI_Gown_Red`). She's sick in the script, so give her a slightly pale complexion.
3. Use **Assemble** to build the Blueprint into `Content/MetaHumans/Rivers/` (and `/Isabella/`). On the 880M, choose an **optimized / cinematic-off** quality, or card-based hair rather than strand grooms, for editor work.
4. Set `CAST_BLUEPRINTS["DrRivers"] = "/Game/MetaHumans/Rivers/BP_Rivers"` (and Isabella's), then rebuild. The cameras' focus tracking follows whatever stands at Rivers' mark.
5. For close-ups in Movie Render Queue, set the MetaHuman's LOD to 0. The MRQ preset already forces LOD 0 through `use_lod_zero`.

> Want a face that looks like a specific actor? MetaHuman Animator / Mesh to MetaHuman can build a face from a scan or iPhone capture. You need consent from anyone whose likeness you use.

## 5. Mixamo animations (mixamo.com, free with an Adobe ID)

| Download (search term) | Use |
|---|---|
| "Talking", "Speech", "Giving A Speech" | Rivers at the podium (shot 2) |
| "Pointing", "Point Forward" | Rivers points at the car (shot 3, frame ~540) |
| "Clapping", "Standing Clap" | crowd on the reveal |
| "Idle", "Standing Idle", "Talking On Phone" | crowd variety |
| "Taking Photo" / "Camera" | press pit |

**Settings:** Format **FBX for Unity (.fbx)** or FBX Binary, **With Skin** on the first clip and **Without Skin** for the rest, 30 fps, **In Place** checked.

**Into Unreal (5.4+):**
1. Import the FBX into `Content/ECHO/Imported/Mixamo/`.
2. Right-click the Mixamo skeletal mesh and choose **Retarget Animations** (auto IK Retargeter), with the source as the Mixamo skeleton and the target as `SKM_Manny`.
3. Export the retargeted sequences to `Content/ECHO/Anims/`.
4. In Sequencer, add an **Animation** track on `DrRivers` and drop the talking clip at 384 and the pointing clip at 528. Or set `IDLE_ANIM` for the crowd.

## 6. Sound (for when we cut the cinematic)

- **Fab > Audio > "crowd applause", "camera shutter", "ambience party"**: Fab has free SFX packs.
- **freesound.org** (CC0 / CC-BY): "camera flash pop", "large hall applause", "rain on glass".
- Hunter's script line for the voice-over is in `rivers-game/script.txt` p.1.

## 7. Concept-art targets (rivers-game/concept-art)

| Frame | What the gala should borrow |
|---|---|
| `01-alley-2008.png` | wet reflections, warm practicals against a cool night: the **exterior plaza** and street lamps |
| `02-portal-lab.png` | the volumetric beams and the blue-white key: the **stage wash** and follow spot |
| `04-funeral.png` | the overcast cool ambience: the **sky dome** horizon colour |
| `03-miami-1989.png` | not used for the gala (golden-hour palette is for chapter 18) |

**Not shippable from the concept art:** the RDR/GTA-style HUD elements, the "Red Dead Redemption" label, the real Chicago Tribune masthead, and the Budweiser and Dolphins logos (see design-doc §10.3).
