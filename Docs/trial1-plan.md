# ECHO: Trial 1 vertical slice plan

**Map:** `L_Trial1_Riverside2008`. **Sequences:** `LS_Trial1_Flythrough` (the render target) and `LS_Trial1_Shift` (the history edit).
**Source:** design doc ch. 6 and script pp. 10–11. **Data:** `echo_kit/trial1_beats.py`, which the level, the director, the tools and this page all share.

**Where.** It's the ripple demo's corner, two years earlier: Delancey × Cutler under the El.
- The arrival alley runs behind the NW block.
- The Lucky Star (NE corner) is open.
- The Cortaz building (SE corner) is a closed shoe-repair shop with a two-floor apartment above (L1 = 380 cm, L2 = 710 cm).
- The critical path is about 150 m and takes 6–8 minutes.

**Look.** A cold, rainy 2008 night (design doc §10.1, concept 01): moonlight, wet asphalt, red and blue neon. Warm practicals appear only where the player goes next.
- The script slugs the scene "11 AM", so `T1_LOOK = "morning"` swaps in a stormy overcast morning.
- **Decision needed:** should the scene be night or morning?

## Beat chart (critical path)

| # | Beat | Player does | Mechanic | Light that leads |
|---|---|---|---|---|
| B01 | Arrival | Portal dies; hide the suits | Hold 1.5 s at the dumpster | Caged bulb over the green dumpster |
| B02 | The Alley | Walk to Cutler (optional climb: crate → dumpster lid → fire escape → clipping) | Traverse; 70/80/85 cm hops | Red DELI blade sign framed by the alley mouth |
| B03 | Blend In | Walk to the corner | Forced walk in the blend-in zone; officer watches the crossing | Sodium heads, the El's fluorescent tube |
| B04 | The Lucky Star | Cross Delancey past the owner and his son | Walk-by eye-contact beat | LUCKY STAR neon, lit produce stand |
| B05 | The Address | Cross Cutler to the side door | Walk; "This is it. On my mark." | Bare bulb on the door, TV-blue top window |
| B06 | The Lock | Pick the lock while Tyler and John screen you | Hold 3 s; DOOR_Cortaz opens | Bare bulb |
| B07 | Split Up | Climb stair 1 | Stealth begins | Stair bulb, hall nightlight |
| B08 | Downstairs | Search L1; avoid the glass; hide in the pantry or behind the couch | Noise → alert; hide spots; checkpoint at 100% | Living-room lamp |
| B09 | Upstairs | Follow the TV to the bedroom door | Creaky floorboard; Tyler's shot (stub) | TV flicker |
| B10 | Gas and a Candle | Regroup in the kitchen | NPC action (stub); the candle appears | The candle |
| B11 | Snap-Back | Wait T1_SHIFT_DELAY (3 s) | The shift: headache, then the burn front from the stove, then the explosion at f132; player snaps across Cutler to watch | Fire |

There is also an optional lore item (the Ledger front page, dated Tuesday, January 22, 2008) and one collectible (a 2006 clipping on the upper fire escape).

## Built (blueprint-free)

- **Level:**
  - Collidable shells, floors, two stairs (19.2 and 19.4 cm risers), partitions with door gaps, cover (dumpsters, the dock, the produce stand, 10 cars) and yellow climb paint.
  - 20 trigger volumes, tagged `T1.Id.*`, `T1.Kind.*` and `T1.Beat.*`.
  - Checkpoint, mark, cover and climb TargetPoints; a Note per beat; invisible bounds.
  - PlayerStart, plus a Third Person GameMode override.
- **Director (`trial1_runtime`):** runs the beats in Play-In-Editor. Hold progress, objectives, forced walk, suspicion, noise and alert, hiding, checkpoints, companion marks, door, candle and shift are all live. `D.status()`, `D.skip()` and `D.force_shift()` are available from the console.
- **Shift:**
  - State A is saved visible and torn away by the ripple materials.
  - State B is saved parked under the world and burns in at the front.
  - A blast group (glass, the door, debris) appears at f132.
  - The burn uses MPC Center at the stove and RimStrength 0. A lights die where the front passes, the fire lights flicker in, and the headache and blast grades are applied.
- **Flythrough (20 s):**
  1. S1 low at the newspaper; the portal folds; rack focus to the trio.
  2. S2 crane up the alley to the El, the roofs and the DELI sign.
  3. S3 follow across Delancey.
  4. S4 the Cortaz building, from TV-blue down to the door.

  It is shot 2.39:1 with locked EV, and the MRQ presets `MRQ_Trial1_1080p_Draft` and `_Final` are built.

## Stubbed or next

- **Tyler's shot and John's gas and candle:** on-screen text plus warps. Needs anim montages, an audio cue and a cutscene sequence.
- **Locomotion:** no crouch, cover-snap or climb animations. The template jumps (apex about 143 cm) cover the climb stack.
- **Director:** editor-only. Porting it to a GameMode or Blueprint is required for a packaged build; the tags and data are already in place for that.
- **AI:** the officer and Cortaz don't perceive; suspicion and alert are zone-based.
- **Audio:** no rain, El rumble, ringing or explosion yet.
- **Rain:** wet surfaces and steam only. Niagara rain, drips and fire are the next pass.
- **Characters:** mannequins (Rivers is the template character) with tinted fabrics and caps.
- **Fixed in Phase 1:** the night vs. 11 AM look; the companions' pathing (they currently warp to marks).
