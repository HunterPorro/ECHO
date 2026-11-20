"""All tunables for the ECHO Prologue build. Edit numbers here, re-run, no code changes.

Units: Unreal centimetres, lights in candelas (local) / lux (directional),
exposure in EV100. Coordinates: +X runs from the street, through the glass
facade (X=0), down the hall to the stage (X~4700-6000). +Z is up.
"""

# ---------------------------------------------------------------- asset paths
ROOT = "/Game/ECHO"
MAT_DIR = ROOT + "/Materials"
MAP_DIR = ROOT + "/Maps"
CINE_DIR = ROOT + "/Cinematics"
MAP_NAME = "L_Prologue_Gala"
MAP_PATH = MAP_DIR + "/" + MAP_NAME
SEQ_NAME = "LS_Prologue_Unveiling"
SEQ_PATH = CINE_DIR + "/" + SEQ_NAME
FLASH_LOOP_NAME = "LS_Gala_FlashLoop"
MRQ_PRESETS = {
    # name: (temporal samples, spatial samples, AA method name, warmup frames)
    "MRQ_Gala_1080p_Draft": (1, 1, "AAM_TSR", 16),
    "MRQ_Gala_1080p_Final": (8, 1, "AAM_NONE", 48),
}
RENDER_RESOLUTION = (1920, 1080)

GEN_TAG = "ECHO_GEN"          # every generated actor carries this tag (re-runs delete them first)

# ---------------------------------------------------------------- hall layout
HALL_LEN = 6000.0             # X 0 -> 6000
HALL_HALF_W = 2000.0          # Y -2000 -> 2000
HALL_H = 1400.0
WALL_T = 40.0
STAGE_X0 = 4700.0
STAGE_H = 110.0
AISLE_HALF_W = 320.0
DOOR_HALF_W = 260.0
DOOR_H = 300.0
TRANSOM_Z = 460.0             # top of the door/transom glass band

PODIUM_POS = (5050.0, -500.0)
RIVERS_POS = (5135.0, -500.0)
CAR_POS = (5200.0, 850.0)
CAR_YAW = 155.0               # car nose points at the audience, three-quarter on

# ---------------------------------------------------------------- crowd
CROWD_ENABLED = True
TABLE_ROWS_X = [1450.0, 2100.0, 2750.0, 3400.0, 4000.0]
TABLE_COLS_Y = [-1500.0, -820.0, 820.0, 1500.0]
GUESTS_PER_TABLE = 3          # 20 tables x 3 = 60 mannequins (lower to 2 if the editor crawls)
PRESS_COUNT = 6
RANDOM_SEED = 1989

# ---------------------------------------------------------------- look / grade
EXPOSURE_MIN_EV = 4.5         # histogram auto-exposure clamp (EV100)
EXPOSURE_MAX_EV = 7.5
EXPOSURE_BIAS = 0.0
FOG_DENSITY = 0.022           # art pass: lighter height fog, volumetric does the beams
FOG_HEIGHT_FALLOFF = 0.05
FOG_INSCATTER = (0.05, 0.07, 0.085)  # deep teal haze (art pass)
VOLFOG_EXTINCTION = 1.2
VOLFOG_SCATTER_DIST = 0.65    # forward scattering -> visible beams
VOLFOG_DISTANCE = 9000.0

SKY_HORIZON = (0.30, 0.25, 0.30)  # dusky city glow
SKY_ZENITH = (0.02, 0.045, 0.11)  # blue hour
SKY_STRENGTH = 4.0
SKYLIGHT_INTENSITY = 1.0
MOON_LUX = 0.6

# Light levels (candelas)
KEY_RIVERS_CD = 30000.0       # v3 150000 metered Rivers to grey; now a low key so the suit reads dark
RIM_RIVERS_CD = 60000.0       # the rim (back/top) carries his silhouette instead
FOLLOW_SPOT_CD = 300000.0     # v3 900000
CAR_SPOT_CD_PRE = 3000.0
CAR_SPOT_CD_REVEAL = 70000.0
STAGE_WASH_CD = 25000.0
CHANDELIER_CD = 9000.0
UPLIGHT_CD = 7000.0
STREET_LAMP_CD = 2500.0
FLASH_CD = 120000.0

# Emissive strengths (~cd/m2). Reference: at EV100 7.5 (lit hall) mid-grey is ~22 nits,
# at EV100 4.5 (night plaza) ~2.8 nits. Emissives 3+ stops above that bloom nicely.
E_WARM = 120.0
E_CANDLE = 150.0
E_CRYSTAL = 300.0
E_LED_WALL = 6.0              # fallback LED colour only (MI_LED_Screen uses E_LED_SCREEN)
E_COOL_STRIP = 80.0
E_CAR_LIGHT = 400.0
E_STREET = 800.0
E_WINDOWS = 18.0

# ---------------------------------------------------------------- editor scalability for the 880M
# 0 low, 1 medium, 2 high, 3 epic. Lumen needs GI/Reflections >= 2.
EDITOR_SCALABILITY = {
    "sg.ResolutionQuality": 75,
    "sg.ViewDistanceQuality": 2,
    "sg.AntiAliasingQuality": 2,
    "sg.ShadowQuality": 2,
    "sg.GlobalIlluminationQuality": 2,
    "sg.ReflectionQuality": 2,
    "sg.PostProcessQuality": 2,
    "sg.TextureQuality": 2,
    "sg.EffectsQuality": 2,
    "sg.FoliageQuality": 1,
    "sg.ShadingQuality": 2,
}

# ---------------------------------------------------------------- Movie Render Queue cvars (final quality)
RENDER_CVARS = {
    "r.ScreenPercentage": 100,
    "r.MotionBlurQuality": 4,
    "r.DepthOfFieldQuality": 4,
    "r.DOF.Gather.RingCount": 5,
    "r.Lumen.ScreenProbeGather.DownsampleFactor": 8,
    "r.Lumen.ScreenProbeGather.TracingOctahedronResolution": 16,
    "r.Lumen.Reflections.DownsampleFactor": 1,
    "r.Lumen.Reflections.MaxRoughnessToTrace": 0.5,
    "r.Lumen.TranslucencyReflections.FrontLayer.Enable": 1,
    "r.VolumetricFog.GridPixelSize": 4,
    "r.VolumetricFog.GridSizeZ": 128,
    "r.VolumetricFog.HistoryMissSupersampleCount": 16,
    "r.Shadow.Virtual.SMRT.RayCountLocal": 16,
    "r.Shadow.Virtual.SMRT.SamplesPerRayLocal": 8,
    "r.Shadow.Virtual.ResolutionLodBiasLocal": 0.0,
    "r.BloomQuality": 5,
    "r.Tonemapper.Sharpen": 0.6,
}

# ---------------------------------------------------------------- sequence
FPS = 24
# shot boundaries (frames)
# legacy shot names (kept for anything still reading them); the art-pass cut list is GALA_SHOTS below
SHOT_ONER = (0, 312)          # establishing crane + aisle dolly
SHOT_SPEECH = (312, 456)      # Rivers medium
SHOT_POINT = (456, 552)       # Isabella reverse
SHOT_REVEAL = (552, 768)      # reveal + closing wide
COVER_LIFT = (566, 616)       # drape: tension at 566, pulled into the rig, clear by 616

# ---------------------------------------------------------------- upgrade hooks (see ASSETS.md)
# Swap any generated material for a downloaded one (Fab/Megascans). Key = our instance name,
# value = full asset path in the project. Missing paths are ignored with a warning.
MATERIAL_OVERRIDES = {
    # "MI_Floor_BlackMarble": "/Game/Fab/Megascans/Surfaces/Polished_Black_Marble/MI_Polished_Black_Marble",
    # "MI_Marble_White": "/Game/Fab/Megascans/Surfaces/White_Marble_Tiles/MI_White_Marble_Tiles",
    # "MI_CarPaint_Pearl": "/Game/AutomotiveMaterials/Materials/Exterior/CarPaint/MI_CarPaint_Pearl",
}
# Replace the primitive Echo with a real car mesh (StaticMesh or SkeletalMesh path). Empty = primitives.
ECHO_CAR_MESH = ""
ECHO_CAR_MESH_YAW_OFFSET = 0.0     # many car assets face +Y; set 90 or -90 if the nose points sideways
ECHO_CAR_MESH_SCALE = 1.0
# MetaHuman (or any) Blueprint actors for the cast. Empty = mannequins.
CAST_BLUEPRINTS = {
    "DrRivers": "",    # e.g. "/Game/MetaHumans/Rivers/BP_Rivers"
    "Isabella": "",    # e.g. "/Game/MetaHumans/Isabella/BP_Isabella"
    "Assistant": "",
}
CAST_BLUEPRINT_YAW_OFFSET = -90.0  # MetaHuman BPs, like the mannequins, face +Y
IDLE_ANIM = ""                     # force a specific idle (e.g. a Mixamo retarget); empty = auto-find MM_Idle

# =====================================================================================
# GALA ART PASS - look-dev tunables for L_Prologue_Gala / LS_Prologue_Unveiling
# =====================================================================================
# --- cinematic: six shots (frames @ 24 fps). Cut points are exclusive ends.
GALA_SHOTS = {
    "establish": (0, 168),     # crane down over the hall, 24mm f/2.8 (v5: more DOF separation)
    "dolly": (168, 312),       # push down the aisle toward the stage, 35mm f/2.8
    "rivers": (312, 456),      # medium on Rivers at the lectern, 50mm f/2.0
    "isabella": (456, 552),    # reverse: Isabella in the crowd, 50mm f/1.8
    "reveal": (552, 696),      # low 3/4 hero arc on the Echo, drape lift + beam sweep
    "wide": (696, 768),        # over-shoulder tableau through the crowd, 24mm f/2.8
}
GALA_SCOPE = True                    # 2.39:1 filmback (CineCamera letterboxes the 16:9 render)
GALA_SENSOR = (36.0, 15.06)          # full-frame width; height 36/2.39
GALA_SHOT_EXPOSURE = {"CAM_03_Rivers_Medium": -1.5}   # per-camera auto-exposure bias (EV)
GALA_USE_ISM = True                  # repeated dressing through util.instanced (falls back to actors)

# --- cast + crowd assets (tried in order; short names are then searched anywhere under /Game)
MANNY_MESH_PATHS = ["/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple",
                    "/Game/Characters/Mannequins/Meshes/SKM_Manny",
                    "/Game/Characters/Mannequins/Meshes/SK_Mannequin"]     # (a Skeleton in 5.x - skipped)
MANNY_MESH_NAMES = ["SKM_Manny_Simple", "SKM_Manny", "SKM_Manny_Complex"]
QUINN_MESH_PATHS = ["/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple",
                    "/Game/Characters/Mannequins/Meshes/SKM_Quinn"]
QUINN_MESH_NAMES = ["SKM_Quinn_Simple", "SKM_Quinn", "SKM_Quinn_Complex"]
MANNY_MATERIALS = ["/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New",
                   "/Game/Characters/Mannequins/Materials/Manny/MI_Manny_02_New"]
QUINN_MATERIALS = ["/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_01",
                   "/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_02"]
IDLE_ANIM_PATHS = ["/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle",
                   "/Game/Characters/Mannequins/Anims/Unarmed/MF_Idle",
                   "/Game/Characters/Mannequins/Anims/Idle/MM_Idle",
                   "/Game/Characters/Mannequins/Animations/MM_Idle"]
# outfit colours used ONLY if the M_ECHO_Surface master fails and we tint the template MIs
OUTFIT_TINTS = {"MI_Fabric_Tux": (0.01, 0.01, 0.012), "MI_Fabric_Charcoal": (0.04, 0.04, 0.045),
                "MI_Fabric_Navy": (0.01, 0.014, 0.035), "MI_Gown_Red": (0.055, 0.008, 0.018),
                "MI_Gown_Emerald": (0.008, 0.10, 0.05), "MI_Gown_Gold": (0.5, 0.34, 0.11),
                "MI_Gown_Midnight": (0.008, 0.014, 0.07), "MI_Gown_Black": (0.008, 0.008, 0.009),
                "MI_Gown_Silver": (0.45, 0.45, 0.47)}
ISABELLA_POS = (4200.0, -1180.0)     # front of the crowd, stage-left, clear eyeline to the lectern
CROWD_FACE_STAGE = 0.8               # share of guests turned to the stage (rest talk at their table)
BALCONY_X = (400.0, 4400.0)
BALCONY_Z = 650.0
BALCONY_GUESTS_PER_SIDE = 6
PRESS_Y0 = -600.0                    # press pit spans the lectern -> car (shoots both)
PRESS_SPACING = 300.0

# --- practical / accent lights (all shadowless; only 6 lights in the level cast shadows)
CANDLE_LIGHTS = True                 # one tiny point light per table (20); False if the editor crawls
CANDLE_CD = 30.0
CANDLE_RADIUS = 240.0
ISABELLA_KEY_CD = 2500.0
RIVERS_PRACTICAL_RIM_CD = 9000.0
PODIUM_PRACTICAL_CD = 60.0        # v3: was 350 at 13 cm over the lectern -> white slab
CAR_RIM_CD = 16000.0              # v5: was 40000 and washed the wheels white; now a body-edge kiss
SWEEP_CD = 60000.0
UNDERGLOW_CD = 350.0              # v3 1500 lit a pale pool on the turntable top; now a faint lift under the sills
TEXT_KICKER_CD = 5000.0
E_LED_SCREEN = 8.0                   # branded teal-black LED wall (nits); was a flat blue 20
FOG_MAX_OPACITY = 0.85
FOG_START_DISTANCE = 280.0           # v5: keep the nearby floor clear so chandelier reflections read
GRADE_WHITE_TEMP = 6800.0

# --- v5 art pass: wheels, table lamps, crowd rims, wine gown (see materials / gala / sequence)
E_RIM_ACCENT = 6.0                   # nits on the thin wheel lip (was 0.08 * E_CAR_LIGHT ~32, bloomed white)
TABLE_LAMPS = True                   # one warm shade per cocktail table (candle meshes stay, their points go off)
TABLE_LAMP_CD = 110.0
TABLE_LAMP_RADIUS = 520.0
E_LAMP_SHADE = 28.0                  # shade glow; enough to reflect in the floor, not a bloom ball
CROWD_RIM_CD = 14000.0               # shadowless backlight on the front of the house

# =====================================================================================
# RIPPLE TECH DEMO - Riverside, Lakemont: the bodega block rebuilds between two timelines
#   State A 'Vacant' (S0 after the 2010 robbery)  ->  State B 'Busy' (S1 after Trial 1)
# Coordinates (cm): main street (Delancey Ave) runs along Y, roadway |X| < 700, sidewalks to
# |X| = 1150. Cross street (Cutler St) runs along X, roadway |Y| < 450, sidewalks to |Y| = 800.
# The bodega is the north-east corner building X 1150..2350, Y 800..1700, storefront facing -X.
# The camera side is -X. The El runs over the main street (deck centred on X = 0, Z ~ 760).
# =====================================================================================
RIPPLE_MAP_NAME = "L_Riverside_Ripple"
RIPPLE_MAP_PATH = MAP_DIR + "/" + RIPPLE_MAP_NAME
RIPPLE_SEQ_NAME = "LS_Ripple_Demo"
RIPPLE_SEQ_PATH = CINE_DIR + "/" + RIPPLE_SEQ_NAME
RIPPLE_LIVE_SEQ_NAME = "LS_Ripple_Live"         # same world tracks, no cameras (for PIE / walk-through)
RIPPLE_LIVE_AUTOPLAY = False                    # True = the ripple fires 3 s after you press Play
                                                # (leave False when rendering: both sequences would fight)
RIPPLE_MAT_DIR = MAT_DIR + "/Ripple"
RIPPLE_MPC_NAME = "MPC_Ripple"
RIPPLE_MRQ_PRESETS = {
    "MRQ_Ripple_1080p_Draft": (1, 1, "AAM_TSR", 24),
    "MRQ_Ripple_1080p_Final": (8, 1, "AAM_NONE", 64),
}
RIPPLE_RENDER_SUBDIR = "Ripple_Demo"
RIPPLE_SEED = 2010

# --- the wave. Radius(f) = R_AT_CAMERA * ((f - START) / CAMERA_FRAMES) ** EXPONENT  (accelerating bloom)
RIPPLE_CENTER = (1140.0, 1010.0, 115.0)          # the bodega's front door
RIPPLE_FRAMES = 480                              # 20 s @ 24 fps
RIPPLE_START = 164                               # frame the wave is born at the door (6.8 s)
RIPPLE_R_AT_CAMERA = 2200.0                      # cm reached after CAMERA_FRAMES (camera sits at ~1850)
RIPPLE_CAMERA_FRAMES = 48
RIPPLE_EXPONENT_NEAR = 1.35                      # up to R_AT_CAMERA: near-steady, so the ring visibly CROSSES
                                                 # the street (~7.0-8.6 s) instead of snapping past in 0.5 s
RIPPLE_EXPONENT = 3.6                            # beyond: exponential - it outruns the eye and eats the sky
RIPPLE_R_MAX = 480000.0                          # past both sky domes (centre -1.5 km, r 6 km) -> the whole world has turned
RIPPLE_EDGE_WIDTH = 110.0                        # cm of burning edge (was 55: a hairline, now a readable band)
RIPPLE_TEAR_AMP = 32.0                           # cm of paper-tear wobble (was 140: that broke the ring into scribbles)
RIPPLE_TEAR_SCALE = 0.008                        # slightly larger features so the edge stays coherent
RIPPLE_EMBER_COLOR = (1.0, 0.36, 0.08)
RIPPLE_EMBER_STRENGTH = 320.0                    # nits on the burning edge (blooms at EV ~5-7)
RIPPLE_SHELL_COLOR = (0.72, 0.95, 1.25)          # cyan-white core of the chromatic leading edge
RIPPLE_SHELL_STRENGTH = 260.0                    # bright leading edge (the fill stays almost clear so it does not become a dark wall)
RIPPLE_SHELL_FRESNEL = 2.8                       # core of the chromatic rim
RIPPLE_SHELL_IOR = 1.18                          # stronger refraction of the street behind the front
RIPPLE_RIM_COLOR = (0.80, 0.95, 1.0)             # continuous shimmering line exactly at the wave radius
RIPPLE_RIM_STRENGTH = 180.0                      # nits (blooms); keyed up as the wave hits the lens
RIPPLE_RIM_ANGULAR = 0.004                       # rim width grows with distance so the sky ring still reads
RIPPLE_SHRED_COUNT = 40                          # burnt paper scraps trailing the wave
RIPPLE_EMBER_COUNT = 100                         # 1-4 cm orange embers, streaked along their motion
RIPPLE_FX_CLEARANCE = 450.0                      # no FX closer than this to the camera at the same frame (cm)
RIPPLE_SHRED_SIZE = (6.0, 24.0)                  # cm
RIPPLE_EMBER_SIZE = (1.2, 4.0)                   # cm

# --- set dressing density (lower these first if the editor crawls on the 880M)
RIPPLE_HOUSES_PER_SIDE = 7                       # row houses per block face
RIPPLE_PEDESTRIANS = 22                          # State B crowd (Manny/Quinn)
RIPPLE_WALKERS = 6                               # of those, how many walk (needs a walk anim)
RIPPLE_USE_ISM = True                            # instanced static meshes for repeated dressing
RIPPLE_SCOPE = True                              # 2.39:1 'anamorphic' filmback (letterboxed in 16:9)

# --- look per state. State A is a READABLE NIGHT (v3 was an underexposed 'overcast' that read as black).
# Moonlight (cool directional) + a few working sodium lamps + a security flood on the boarded deli
# + window glow, wet-asphalt reflections, lifted street fog, and a lower locked EV.
RIPPLE_EV = (6.7, 7.3)                           # (legacy) - each state now has its own locked EV:
RIPPLE_EV_A = 4.7                                # night street: more exposure than v3's 5.8 so forms read
RIPPLE_EV_B = 5.5                                # twilight, only ~0.8 stop tighter than A so the crossover never dives to black
A_SUN_LUX, A_SUN_K, A_SUN_ROT = 22.0, 7500.0, (-30.0, 168.0)  # moonlight from the SE sky (in shot, wet-street reflections)
B_SUN_LUX, B_SUN_K, B_SUN_ROT = 380.0, 3200.0, (-6.0, 150.0)  # last light: low, raking, warm
A_SKYLIGHT, B_SKYLIGHT = 1.55, 1.25              # ambient fill (A higher so unlit brick isn't a black hole)
# sky domes: horizon -> mid band -> zenith, with a cloud field (CloudTint multiplies the sky under cloud)
A_SKY = {"Horizon": (0.28, 0.32, 0.50), "Mid": (0.07, 0.09, 0.18), "Zenith": (0.012, 0.018, 0.055), "Strength": 11.0,
         "CloudTint": (0.22, 0.26, 0.42), "CloudAmount": 0.62, "CloudScale": 1.8}
B_SKY = {"Horizon": (1.25, 0.42, 0.10), "Mid": (0.62, 0.16, 0.32), "Zenith": (0.035, 0.045, 0.16), "Strength": 16.0,
         "CloudTint": (1.70, 0.72, 0.42), "CloudAmount": 0.72, "CloudScale": 2.0}
A_FOG_DENSITY, B_FOG_DENSITY = 0.013, 0.005      # A lifted so moonlight + sodium catch in the street
RIPPLE_FOG_FALLOFF = 0.18                        # a little taller than v3, still low
RIPPLE_FOG_SCATTER_G = 0.40
RIPPLE_SUN_VOLUMETRIC = 0.8                      # moonlight shafts in the haze
RIPPLE_LOCAL_VOLUMETRIC = 0.35                   # every practical light's fog scattering (keep <1: no glowing balls)
A_FOG_EXTINCTION, B_FOG_EXTINCTION = 1.15, 0.8
A_FOG_COLOR, B_FOG_COLOR = (0.14, 0.16, 0.22), (0.32, 0.16, 0.12)
RIPPLE_FOG_CUTOFF = 80000.0                      # 800 m: haze the street + skyline, never the sky dome
RIPPLE_FOG_MAX_OPACITY = 0.55                    # was 0.75: a lighter veil so the dusk sky still reads
RIPPLE_SKYLINE_WINDOWS_A = 0.12                  # a few cold TVs / night-owls so downtown isn't a black mass
RIPPLE_SKYLINE_WINDOWS_B = 0.28
A_STREETLAMP_CD = 3800.0                         # dimmer than B, but the vacant block is no longer unlit
A_STREETLAMP_VOLUMETRIC = 0.30
A_SECURITY_CD = 2800.0                           # flood on the boarded Lucky Star door
B_STREETLAMP_CD = 7000.0
B_STREETLAMP_VOLUMETRIC = 0.25                    # >1 makes fat glowing cones in the fog (read as blobs)
B_BODEGA_CD = 9000.0
B_NEON_CD = 2600.0
A_FLUORO_CD = 1800.0                             # the one flickering tube under the El in State A
E_NEON = 110.0                                   # emissive nits (EV ~6: middle grey ~10 nits)
E_LIGHTBOX = 22.0                                # low enough that the red sign lettering reads on it
E_WINDOW_LIT = 14.0                              # warm glow, not blank cream panels
E_SUN_DISC = 600.0                               # unused by default (no visible sun disc)
E_LAMP_LENS = 8.0                                # lamp heads: a glint, not a bloom ball
RIPPLE_BLOOM = {"A": 0.22, "B": 0.28, "hit": 0.9}
RIPPLE_WHITE_TEMP = {"A": 5000.0, "B": 7700.0}   # A: cool moonlight, sodium still reads amber
RIPPLE_SATURATION = {"A": 0.72, "B": 1.1}
RIPPLE_BODEGA_NAME = "LUCKY STAR DELI"           # fictional brand (A shows it faded, a letter missing)
RIPPLE_BODEGA_FADED = "LUCKY ST R DELI"

# =====================================================================================
# TRIAL 1 VERTICAL SLICE - chapter 6 'Trial 1' (script pp. 10-11), Riverside, Jan 22 2008
#   The SAME corner as the ripple demo, two years before the robbery: Delancey Ave (along Y,
#   under the El) x Cutler St (along X). Lucky Star Deli = NE corner (open, 2008). The Cortaz
#   building = SE corner (X 1150..2250, Y -1500..-800): a closed tailor shop with a 2-floor
#   apartment above. Arrival alley = behind the NW block (X -2850..-2250, Y 800..4200).
#   Player = Dr. Rivers (Third Person template character). Tyler + John = companions.
#   History-edit shift: State A 'Before' (the building lived in) -> State B 'Burning'
#   (gas + candle, the snap-back, the explosion), reusing MPC_Ripple + the ripple masters.
# =====================================================================================
T1_MAP_NAME = "L_Trial1_Riverside2008"
T1_MAP_PATH = MAP_DIR + "/" + T1_MAP_NAME
T1_SEQ_NAME = "LS_Trial1_Flythrough"          # establishing flythrough (MRQ render target)
T1_SEQ_PATH = CINE_DIR + "/" + T1_SEQ_NAME
T1_SHIFT_SEQ_NAME = "LS_Trial1_Shift"          # the history-edit swap A -> B (played by the PIE director)
T1_MRQ_PRESETS = {
    "MRQ_Trial1_1080p_Draft": (1, 1, "AAM_TSR", 24),
    "MRQ_Trial1_1080p_Final": (8, 1, "AAM_NONE", 64),
}
T1_RENDER_SUBDIR = "Trial1_Flythrough"
T1_SEED = 2008
T1_FLY_FRAMES = 480                             # 20 s @ 24 fps
T1_FLY_SHOTS = {                                # frames (exclusive ends)
    "arrival": (0, 132),       # low in the alley: the portal dies, the newspaper date, the trio walk out
    "crane": (132, 252),       # crane up the fire escapes: the El, the roofs, the neon at the end of the street
    "blend": (252, 372),       # follow the trio across Delancey; slow as they pass the Lucky Star
    "address": (372, 480),     # the Cortaz building: TV-blue upstairs, the bare bulb on the side door
}
T1_SHIFT_FRAMES = 264                           # 11 s: headache -> ignition -> burn spreads -> explosion -> burning
T1_SCOPE = True                                 # 2.39:1 filmback, like the gala and ripple

# --- look. 'night' follows the design doc (2008 anchor = cold rainy night) and concept frame 01.
#     The script slugs the scene '11 AM' - set T1_LOOK = "morning" for a stormy overcast late morning.
T1_LOOK = "night"
T1_LOOKS = {
    "night": {
        "ev": (4.1, 4.9), "cam_ev": 4.45,          # histogram range for play, locked EV for the flythrough
        "moon_lux": 26.0, "moon_k": 7800.0, "moon_rot": (-34.0, 205.0), "moon_angle": 3.0,
        "skylight": 1.5,
        "fog_density": 0.016, "fog_falloff": 0.16, "fog_color": (0.13, 0.15, 0.21), "fog_extinction": 1.1,
        # Lakemont under low cloud: sodium city-glow on the cloud base, deep blue overhead
        "sky": {"Horizon": (0.46, 0.25, 0.13), "Mid": (0.10, 0.08, 0.11), "Zenith": (0.010, 0.014, 0.034),
                "Strength": 10.0, "CloudTint": (0.36, 0.22, 0.15), "CloudAmount": 0.82, "CloudScale": 1.9},
        "practical_mult": 1.0, "white_temp": 5400.0, "saturation": 0.86,
    },
    "morning": {
        "ev": (8.6, 9.6), "cam_ev": 9.1,
        "moon_lux": 650.0, "moon_k": 6800.0, "moon_rot": (-24.0, 200.0), "moon_angle": 25.0,
        "skylight": 1.0,
        "fog_density": 0.022, "fog_falloff": 0.12, "fog_color": (0.42, 0.45, 0.50), "fog_extinction": 0.9,
        "sky": {"Horizon": (0.74, 0.76, 0.80), "Mid": (0.56, 0.58, 0.63), "Zenith": (0.36, 0.39, 0.45),
                "Strength": 190.0, "CloudTint": (0.62, 0.64, 0.68), "CloudAmount": 0.96, "CloudScale": 1.6},
        "practical_mult": 6.0, "white_temp": 6200.0, "saturation": 0.8,
    },
}
# practical lights (candelas, x practical_mult). Warm practicals = the path; cool moon = everywhere else.
T1_SODIUM_CD = 4200.0                           # cobra heads on Cutler + Delancey
T1_SODIUM_VOLUMETRIC = 0.3
T1_BODEGA_CD = 9000.0                           # Lucky Star interior fluorescents spilling onto the corner
T1_NEON_CD = 2400.0                             # red + blue neon wash (concept frame 01's two colours)
T1_ALLEY_BULB_CD = 900.0                        # caged back-door bulbs in the alley (breadcrumbs)
T1_DOOR_BULB_CD = 650.0                         # the bare bulb over the Cortaz side door (the destination)
T1_EL_FLUORO_CD = 1500.0                        # one tube under the El over the crosswalk
T1_PORTAL_CD = 60000.0                          # the dying portal (blue-white), keyed to 0
T1_TV_CD = 700.0                                # Cortaz's TV upstairs (flickers in the shift + read from the street)
T1_INTERIOR_CD = 420.0                          # kitchen pendant, living-room lamp, hall nightlight
T1_FIRE_CD = 26000.0                            # each room once the gas goes up (State B)
T1_BLAST_CD = 4.0e6                             # explosion flash (one frame peak, decays over ~1 s)
T1_LOCAL_VOLUMETRIC = 0.35                      # cap on local-light fog scattering (no glowing balls)
E_T1_NEON = 120.0                               # emissive nits
E_T1_WINDOW = 12.0
E_T1_FIRE = 260.0
E_T1_PORTAL = 900.0
T1_GRAIN = 0.22                                 # 2008 anchor: heavier grain + a touch of bleach bypass

# --- dressing density (lower first if the editor crawls on the 880M)
T1_HOUSES_PER_FACE = 5
T1_PEDESTRIANS = 9
T1_PARKED_CARS = 9
T1_USE_ISM = True
T1_CAPS = True                                  # baseball caps on Rivers / Tyler / John (script p.10)
T1_SHOW_CLIMB_PAINT = True                      # worn yellow paint on grab/climb edges (Uncharted language)
T1_NOTES = True                                 # editor-only Note actors describing each beat

# --- gameplay director (editor Python, runs during Play-In-Editor; no Blueprints needed)
T1_DIRECTOR_AUTOSTART = True                    # init_unreal.py arms the director when the editor starts
T1_FORCE_WALK = True                            # blend-in zone caps walk speed (Naughty Dog-style forced walk)
T1_WALK_SPEED = 165.0                           # cm/s inside the blend-in zone
T1_RUN_SPEED = 500.0                            # template default, restored outside the zone
T1_SUSPICION_SPEED = 260.0                      # if forced walk is off: moving faster than this raises suspicion
T1_SUSPICION_RATE = 45.0                        # % per second while too fast in view of the officer
T1_NOISE_ALERT = 40.0                           # alert % added per noise hazard (glass, floorboard)
T1_ALERT_DECAY = 6.0                            # % per second (x3 while hidden)
T1_SHIFT_DELAY = 3.0                            # seconds after the gas + candle before the snap-back
T1_HOLD_SECONDS = {"hide_suits": 1.5, "lockpick": 3.0}
T1_SHIFT_CENTER = (1930.0, -870.0, 470.0)       # the kitchen stove (MPC Center is keyed here)
T1_SHIFT_RADIUS = 3200.0                        # final burn radius (covers the building + the debris field)
