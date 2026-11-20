"""Trial 1 (chapter 6, script pp. 10-11) - the critical-path beat chart as DATA.

No `unreal` import: the level builder (trial1.py), the Play-In-Editor director (trial1_runtime.py),
the offline tools (tools/mock_run.py, tools/camera_clearance.py) and trial1-plan.md all read this.

Coordinates (cm), the same grid as the ripple demo (riverside.py): Delancey Ave along Y (roadway
|X|<700, sidewalks to |X|=1150, the El overhead), Cutler St along X (roadway |Y|<450, sidewalks to
|Y|=800). Floors: street/sidewalk 0/15, Cortaz apartment L1 = 380, L2 = 710.

Trigger kinds
    hold        stand inside for HOLD seconds (progress shown on screen) -> completes the beat
    objective   enter -> completes the beat (only when it is the current beat)
    lore        optional read; any time
    collectible optional pickup; any time, once
    blend       low-profile zone: forced walk (or suspicion if T1_FORCE_WALK is off)
    watch       the officer's view: suspicion only rises inside it
    noise       hazard: adds alert (glass, floorboard); too much alert -> checkpoint
    hide        hiding spot: alert decays 3x faster, 'Hidden' shown
    shift       the history edit: armed by its beat, fires LS_Trial1_Shift (State A -> State B)
"""

CURB = 15.0
L1 = 380.0
L2 = 710.0
CAPSULE_Z = 97.0          # template capsule half height (+1): spawn/teleport height above a floor

# ----------------------------------------------------------------------------------------- beats
# companions: where Tyler / John stand while the beat is current (x, y, floor z, facing yaw).
# checkpoint: where a failed beat (blend-in spotted / too much noise) restarts (x, y, floor z, yaw).
BEATS = [
    {"id": "B01", "name": "Arrival", "script": "p.10 'they look back, the portal disappears'",
     "objective": "Hide the suits.", "trigger": "TRG_B01_HideSuits", "mechanic": "hold (1.5 s) at the dumpster",
     "light_guide": "caged back-door bulb over the green dumpster; the portal's dying blue behind you",
     "on_start": "January 22, 2008. Riverside, Lakemont. The portal folds shut behind you.",
     "on_done": "Suits in the dumpster. Caps on. Just three guys in an alley.",
     "checkpoint": (-2550, 3650, CURB, -90),
     "companions": {"Tyler": (-2690, 3560, CURB, -80), "John": (-2420, 3590, CURB, -100)}},
    {"id": "B02", "name": "The Alley", "script": "p.10 'walk to the address'",
     "objective": "Find the street.", "trigger": "TRG_B02_AlleyMouth", "mechanic": "traverse (optional high route: fire escape)",
     "light_guide": "sodium spill + the red DELI blade sign at the far end of Cutler St, framed by the alley mouth",
     "on_start": "", "on_done": "Cutler Street. Two years before the robbery.",
     "checkpoint": (-2550, 3100, CURB, -90),
     "companions": {"Tyler": (-2720, 1480, CURB, -90), "John": (-2380, 1430, CURB, -95)}},
    {"id": "B03", "name": "Blend In", "script": "p.10 'trying not to draw attention to themselves'",
     "objective": "Walk to the corner. Keep your head down.", "trigger": "TRG_B03_Corner",
     "mechanic": "low-profile walk zone; a beat cop watches the crossing",
     "light_guide": "sodium cobra heads down Cutler, the El's fluorescent tube over the crosswalk",
     "on_start": "", "on_done": "",
     "checkpoint": (-2550, 1000, CURB, -90),
     "companions": {"Tyler": (-1260, 560, CURB, 0), "John": (-1380, 720, CURB, 0)}},
    {"id": "B04", "name": "The Lucky Star", "script": "p.10 'eye contact with the owner and his son'",
     "objective": "Cross Delancey.", "trigger": "TRG_B04_LuckyStar", "mechanic": "walk past (eye-contact beat)",
     "light_guide": "LUCKY STAR DELI red + blue neon, the lit produce stand",
     "on_start": "", "on_done": "The owner looks up from his broom. His boy waves at you. Two years from today...",
     "checkpoint": (-900, 640, CURB, 0),
     "companions": {"Tyler": (840, 520, CURB, 10), "John": (760, 720, CURB, -20)}},
    {"id": "B05", "name": "The Address", "script": "p.10-11 'This is it. On my mark.'",
     "objective": "Cross Cutler. Find the address.", "trigger": "TRG_B05_Address", "mechanic": "walk",
     "light_guide": "a single bare bulb over a green steel side door; TV-blue in the top-floor window",
     "on_start": "", "on_done": "Rivers: \"This is it. On my mark.\"",
     "checkpoint": (950, 640, CURB, -90),
     "companions": {"Tyler": (1840, -560, CURB, 0), "John": (2160, -560, CURB, 180)}},
    {"id": "B06", "name": "The Lock", "script": "p.11 'picks the lock while Tyler and John stand around him'",
     "objective": "Pick the lock. Tyler and John screen you.", "trigger": "TRG_B06_Lockpick",
     "mechanic": "hold (3 s) at the door -> the door opens",
     "light_guide": "the bare bulb", "on_start": "", "on_done": "Click.",
     "checkpoint": (1560, -630, CURB, 0),
     "companions": {"Tyler": (1880, -610, CURB, 100), "John": (2150, -610, CURB, 80)}},
    {"id": "B07", "name": "Split Up", "script": "p.11 'Split up and find him' (whispering)",
     "objective": "Split up. Find him.", "trigger": "TRG_B07_Landing", "mechanic": "stealth: climb the stairs",
     "light_guide": "a hall nightlight at the top of the stairs", "on_start": "",
     "on_done": "Rivers (whispering): \"Split up and find him.\"",
     "checkpoint": (2010, -880, CURB, -90),
     "companions": {"Tyler": (2120, -1330, L1, 180), "John": (1900, -1180, L1, 180)}},
    {"id": "B08", "name": "Downstairs", "script": "p.11 (apartment, 11:02 AM)",
     "objective": "Search the apartment. Stay quiet.", "trigger": "TRG_B08_Stair2",
     "mechanic": "stealth: noise (glass on the floor), hiding spots (pantry, behind the couch)",
     "light_guide": "living-room lamp; cold window light from Delancey", "on_start": "", "on_done": "",
     "checkpoint": (2150, -1425, L1, 180),
     "companions": {"Tyler": (1720, -1160, L1, 180), "John": (1900, -1180, L1, 90)}},
    {"id": "B09", "name": "Upstairs", "script": "p.11 'toward the sound of the killer watching TV in bed'",
     "objective": "Follow the TV.", "trigger": "TRG_B09_BedroomDoor",
     "mechanic": "stealth: creaky floorboard; cutscene stub (Tyler's shot)",
     "light_guide": "TV-blue flicker under the bedroom door", "on_start": "",
     "on_done": "Tyler slips past you into the bedroom. One suppressed shot. Tyler: \"CLEAR.\"",
     "checkpoint": (1240, -1405, L1, 0),
     "companions": {"Tyler": (1790, -1395, L2, 90), "John": (1930, -950, L1, 90)}},
    {"id": "B10", "name": "Gas and a Candle", "script": "p.11 'JOHN turns on gas and lights a candle'",
     "objective": "Regroup downstairs.", "trigger": "TRG_B10_Kitchen", "mechanic": "walk (NPC action stub)",
     "light_guide": "the candle on the kitchen table", "on_start": "",
     "on_done": "John opens the gas on the stove. Strikes a match. Lights a candle.",
     "checkpoint": (1800, -1405, L2, 180),
     "companions": {"Tyler": (1700, -1100, L1, 0), "John": (1930, -945, L1, 90)}},
    {"id": "B11", "name": "Snap-Back", "script": "p.11 'headaches... noses bleed... violently teleported'",
     "objective": "Get out-", "trigger": "TRG_SHIFT_SnapBack",
     "mechanic": "SHIFT: LS_Trial1_Shift swaps State A (lived-in) for State B (burning), the building explodes",
     "light_guide": "", "on_start": "",
     "on_done": "TRIAL 1 - COMPLETE.  Lakemont, January 22, 2008.  History edited.",
     "checkpoint": (1960, -1080, L1, 90),
     "companions": {"Tyler": (-5000, -5000, -4000, 0), "John": (-5000, -5000, -4000, 0)}},
]

# ---------------------------------------------------------------------------------------- triggers
# id: (kind, centre (x, y, z), size (x, y, z), beat id or None, text, extra)
TRIGGERS = {
    "TRG_B01_HideSuits": ("hold", (-2640, 3150, 115), (240, 300, 210), "B01", "Hiding the suits", {"hold": "hide_suits"}),
    "TRG_L01_Newspaper": ("lore", (-2470, 3330, 110), (200, 200, 200), None,
                          "LAKEMONT LEDGER - Tuesday, January 22, 2008. Two years before the robbery.", {}),
    "TRG_C01_Clipping": ("collectible", (-2305, 1880, 680), (110, 160, 200), None,
                         "Ledger clipping, 2006: 'Riverside man questioned in bodega holdups - released.' "
                         "The photo is John Cortaz.", {"mesh": "T1_Clipping"}),
    "TRG_B02_AlleyMouth": ("objective", (-2550, 980, 120), (600, 300, 240), "B02", "", {}),
    "TRG_Z_BlendIn_Cutler": ("blend", (-850, 625, 150), (4200, 420, 300), None, "Low profile.", {}),
    "TRG_Z_BlendIn_Corner": ("blend", (1500, 0, 150), (1700, 1640, 300), None, "Low profile.", {}),
    "TRG_W_Officer": ("watch", (-300, 200, 150), (2400, 1500, 300), None, "The officer is watching the crossing.", {}),
    "TRG_B03_Corner": ("objective", (-900, 640, 120), (320, 380, 240), "B03", "", {}),
    "TRG_B04_LuckyStar": ("objective", (980, 760, 120), (360, 300, 240), "B04", "", {}),
    "TRG_B05_Address": ("objective", (1560, -630, 120), (500, 330, 240), "B05", "", {}),
    "TRG_B06_Lockpick": ("hold", (2010, -700, 120), (200, 170, 240), "B06", "Picking the lock",
                         {"hold": "lockpick", "opens": "DOOR_Cortaz"}),
    "TRG_B07_Landing": ("objective", (2150, -1440, L1 + 100), (160, 120, 200), "B07", "", {}),
    "TRG_N01_Glass": ("noise", (1560, -1300, L1 + 50), (170, 80, 120), None, "*crunch* - broken glass.", {}),
    "TRG_H01_Pantry": ("hide", (1885, -1420, L1 + 50), (100, 90, 120), None, "Hidden (pantry).", {}),
    "TRG_H02_Couch": ("hide", (1580, -1125, L1 + 50), (90, 250, 120), None, "Hidden (behind the couch).", {}),
    "TRG_B08_Stair2": ("objective", (1240, -1405, L1 + 100), (100, 130, 200), "B08", "", {}),
    "TRG_N02_Floorboard": ("noise", (2060, -1385, L2 + 50), (90, 120, 120), None, "*creak* - a loose floorboard.", {}),
    "TRG_B09_BedroomDoor": ("objective", (1810, -1285, L2 + 100), (110, 70, 200), "B09", "", {"tyler_to": (1560, -1060, L2, 180)}),
    "TRG_B10_Kitchen": ("objective", (1960, -1080, L1 + 100), (260, 360, 200), "B10", "", {}),
    "TRG_SHIFT_SnapBack": ("shift", (1960, -1150, L1 + 110), (420, 620, 220), "B11", "", {"delay": "T1_SHIFT_DELAY"}),
}

# named marks (TargetPoints tagged T1.Mark.<name>)
MARKS = {
    "SnapBackView": (1900, 560, CURB, -95),      # across Cutler: where the snap-back drops the player to watch it burn
    "PortalCenter": (-2550, 3850, 185, -90),
    "Officer": (-900, -620, CURB, 60),
    "Owner": (1065, 1000, CURB, 215),
    "OwnersSon": (1090, 905, CURB, 200),
    "Cortaz": (1300, -1055, L2 + 55, 0),
}

# the critical path for the offline walk test: (x, y) waypoints at capsule centre height.
# 'stairs' segments may climb up to 45 cm per sample; everything else must stay level or step <= 45.
ROUTE = [
    (-2550, 3650), (-2600, 3200), (-2560, 2400), (-2490, 1600), (-2550, 1000), (-2550, 640),
    (-1150, 640), (-760, 640), (700, 640), (950, 640), (950, 760),            # B04 at the Lucky Star
    (885, 420), (885, -480), (1000, -620), (1500, -620), (2010, -650),         # across Cutler, to the door
    (2010, -900), (2150, -900), (2150, -1400), (2150, -1430),                  # through the door, stair 1 -> L1
    (2000, -1330), (2010, -1200), (1880, -1090), (1810, -1090), (1700, -1090),  # kitchen -> living room
    (1400, -1300), (1240, -1300), (1240, -1405),                                # -> stair 2 foot
    (1290, -1405), (1760, -1405), (1800, -1405), (1810, -1270), (1600, -1100),  # stair 2 -> L2 -> bedroom
    (1810, -1270), (1800, -1405), (1760, -1405), (1290, -1405), (1240, -1405),  # back down
    (1240, -1300), (1400, -1300), (1700, -1090), (1810, -1090), (1960, -1080),  # regroup in the kitchen
]
# optional high route: (label, top z of each foothold in order) - every step must be <= 100 cm
CLIMB_STACK = [("crate", 85.0), ("dumpster lid", 165.0), ("fire escape, lower", 250.0)]


def beat(bid):
    for b in BEATS:
        if b["id"] == bid:
            return b
    return None


def beat_index(bid):
    for i, b in enumerate(BEATS):
        if b["id"] == bid:
            return i
    return -1
