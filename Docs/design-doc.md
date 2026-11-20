# ECHO — Game Design Doc (draft v0.3)

*Adapted from Hunter Porro's 54-page screenplay "Untitled Script". Working title **ECHO**, after the AI car that opens and closes the story. Grok Bot, Nov 19, 2026.*

**What's new in v0.3** (from Hunter, Nov 19: "explorable world but also very Uncharted, more story based"; placeholder city **Lakemont**; "extra edits and more shifts"; "full-fledged game, longer, more things in story"; "story and action sequences of Uncharted with action sets"):
- **Structure:** a **narrative-first, linear-leaning campaign of cinematic chapters**. **Lakemont** is an explorable *wide-linear* hub between and within chapters, in the spirit of Uncharted 4's Madagascar, Lost Legacy's Western Ghats and TLOU Part II's Seattle Day 1. **No GTA-style sandbox busywork.**
- **Main story:** tightly directed **Uncharted-style set pieces** (§8.2).
- **The hub:** optional exploration, side quests, collectibles, companion conversations, and time-limited content that expires with each shift (§6).
- **More shifts:** **more Rivers history edits**. Four new edits (*new*, specifics need Hunter's approval) bring the city to 10 timeline states (§4.1).
- **Longer game:** new chapters bring the target to **15–20 hours** (§8).
- **Kept from v0.2:** the changing world, live ripples, expiring content, player time travel, Timeline Sight, the concept art and the UE5 technical plan.
- **Previous versions:** `design-doc.v0.2.md` and `design-doc.v0.1.md`. Design inventions not in the script are marked *(new)*.

---

## 1. Story summary (from the script only)

**Act 1: Dr. Rivers.** At a black-tie gala, Dr. Rivers, the CEO of Rivers Industries, a former medical researcher who cured arthritis and 3 cancers, unveils **the Echo**, the world's first fully AI-driven car. Three million orders come in within the hour. His wife **Isabella** is sick (coughing, raspy). She tells him to stay and takes a limo home alone. There, two robbers break in. She hides, fights back with her heel, and is shot by Robber 1 on Robber 2's orders ("She saw us. KILL HER"). Rivers comes home at 11 PM and finds her body.

After the rainy funeral ("I let some stupid car unveiling kill my wife"), Rivers builds an investigation board in his garage. CCTV of the killers airs on the news. His "algorithm" finds their location. He drives there in gloves, sneaks around the house, shoots both men, and covers it up: he pockets the casings, pours gasoline, turns on the gas stove and lights a candle. Revenge doesn't heal him.

Tearing up the killer's photo, he realizes time is "like paper" and can be torn. His old Harvard professor **Witmore** says the theory "could work." Rivers' lab builds a time portal under **Project Isabella**. When his assistant objects to his plan to kill a test target, he strikes her and locks her in a glass lab cage.

**Trial 1:** they pick **John Cortaz**, who robbed a bodega on Jan 22, 2010 and killed its owner. Rivers, Tyler and John travel back to **Jan 22, 2008**, pass the bodega owner and his son, pick Cortaz's lock, shoot him, and set a gas fire. Then they're violently pulled back with headaches and nosebleeds.

**Act 2: Josh.** **Josh** is the bodega owner's son. He wakes in a timeline where his dad is alive, but reality flickers. He has headaches and sees two worlds at once: a billboard of Dr. Rivers, then a vision of Rivers in the bodega years ago. Then he sees WW3: Nazis vs. America with modern tanks. He flees to his ruined school and passes out.

Meanwhile Rivers now runs a **Death Squad** of helmeted, portal-hopping tactical units. They kill a young Al Capone in early-1900s Chicago and Genghis Khan as a child. Rivers personally leads a squad back to the night of the robbery and executes both burglars before they enter. Isabella comes home, takes her medicine, and lives. Crossing back, Rivers collapses.

At the school, Josh's friends **Dylan, Charlie and Ava** don't know him. In this timeline Ava isn't his girlfriend. Ava explains that "Adolf Hitler the 3rd" rose 4 years ago. Josh uses personal facts to convince them and works out on the chalkboard that Rivers caused this. Ava half-remembers him and passes out.

Rivers has a seizure. In a convoy chase, an armored ambulance carries him through a war zone to the Rivers Industries fortress, under fire from Germans and covered by friendly helicopters. He's revived by defibrillator. Later he wears an electronic leg brace. CT scans show brain abnormalities in him and in every Death Squad member.

**Act 3: The heist.** The friends plan to get into Rivers Industries (75+ guards, tanks, anti-air):
- **Route:** through the sewers, guided by Charlie's friend.
- **Cover:** a mass unarmed protest as a distraction.
- **Allies:** to organize the protest, Josh and Dylan get recruited (bagged and zip-tied) into the militia **F.A.R.** (Freedom Alliance), which DNA-screens them.

Rivers' lab detects a time "disturbance" at the F.A.R. warehouse, and the Death Squad breaches it. The F.A.R. leader escapes with Josh and Dylan through a hatch, holds a knife to Josh's throat, and then agrees to the plan.

Protest day brings 2,000 to 5,000 people. The Death Squad doesn't fire, but the **National Guard** boxes the crowd in and shoots a man who runs. The friends come up from the sewer and slip through a door with Dylan's foot. In a guard room they take a keycard, and Ava stays on the cameras with a gun. She guides them through the halls but is found and killed while on comms ("I love you"). Alarms go off.

Next comes a hide-and-seek sequence: a giant mechanical spider with laser scanners searches the rooms. Then the boys ride a glass elevator under fire (with elevator music), take the stairs, and breach the lab. Confronted, Rivers gets his own flash of memory, realizes "I caused all of this," and shoots himself. Josh sets the portal (the screen says **1992 Jan 1**) and the boys jump.

**Act 4: Miami 1989.** They land in a dirty 1989 Miami. They shoplift 80s clothes, with Charlie distracting the cashier. The Death Squad Commander follows them through a portal. At Miami High, the boys find a teenage, "nerd" Rivers in the library. They argue over whether to kill him. The Death Squad storms the school firing. Slow motion: bullets fly toward Josh, then one gunshot, then black.

**Epilogue.** Josh wakes up in his normal life and hugs his mom. Ten years later, **Dr. Joshua** gives Rivers' exact gala speech, unveils the Echo at "Joshua Industries", and his wife is revealed to be **Ava**. ("I could tell.") THE END.

### Story gaps and inconsistencies to resolve (flagged, not invented)

1. **Who fires the last shot in the library?** Josh, the Death Squad, or someone else? Is young Rivers killed or spared? This is the game's climax, so it has to be defined.
2. **Dates:** the bodega robbery is "January 22, 2010", but the trial lands "Jan 22 2008, two years before." Josh types "1992 January 1" and arrives in "January 3rd 1989."
3. **Isabella in the war timeline:** Rivers saves her, but she never appears again. Is she alive in Act 2/3? Does she know about the Death Squad?
4. **How Hitler/WW3 happened:** Josh flashes on the Death Squad stamping Hitler's art-school rejection "accepted". So how is there an "Adolf Hitler the 3rd"? Was this deliberate, or a side effect of the Capone and Khan killings?
5. **Josh's family:** Act 2 has Mom saying "Dad is going to pick you up". The epilogue line becomes "I am going to pick you up." Is the dad alive at the end?
6. **Why can Josh perceive both timelines?** He suspects his father's survival was the "first time travel trial". The script hints at a rule but never states it.
7. **The killers' "algorithm"** and how Rivers' tech finds people is never explained.
8. **Unnamed key characters:** the F.A.R. leader, the Death Squad Commander, Charlie's friend, the assistant, Robbers 1/2, Tyler and John.
9. **The Echo car** appears only at the gala and in the epilogue. It does nothing in the plot (Rivers drives "the car" to the killers' house; it may be an Echo).
10. **Ava's death vs. epilogue:** she dies in the war timeline but is Josh's wife after the reset. The reset rule is implied, not stated.
11. **The sewer scene is shown twice** (pp. 22–23 as a "scenario" on the map, then for real on p. 33). This is good material for a planning mechanic.
12. **Rivers' illness/brace:** the seizure, brain abnormalities and leg brace are never paid off.

---


## 2. Genre, structure and camera

- **Genre:** a **story-driven, cinematic third-person action-adventure**: Uncharted-style traversal, stealth, gunplay, chases and set pieces, plus time travel.
- **Structure: a narrative-first, linear-leaning campaign** of about 28 cinematic chapters (§8).
  - **Main story chapters** are **tightly directed set pieces**: authored pacing, scripted camera moments, chases, collapses, shootouts and climbing under fire. The game controls the rhythm, as Uncharted does.
  - **Lakemont, the explorable hub.** Between chapters, and inside some of them, the game opens into **wide-linear** spaces: large, hand-crafted districts with multiple routes and optional corners, bounded by the story. The models:
    - **Uncharted 4's Madagascar** (drive and explore a valley with optional caches and conversations).
    - **The Lost Legacy's Western Ghats** (a semi-open chapter with optional objectives).
    - **TLOU Part II's Seattle Day 1** (a semi-open downtown with optional buildings and story-rich side discoveries).
  - **What's in the hub:** optional exploration, side quests, collectibles, **companion conversations** (walk-and-talks, optional dialogue prompts), and **time-limited content that expires with each timeline shift**.
  - **What's not in the hub:** no GTA-style sandbox busywork. No map full of icons, no car theft, no repeatable activities, no wanted level, and no filler collect-a-thons. Every optional thing tells a piece of the story or of what a ripple changed.
  - **Gating:** at any time, only the districts the story has reached are open. The city opens and closes chapter by chapter, and **timeline shifts reshape what's reachable**.
  - **Anchor eras** (§5) are compact, story-driven past spaces visited by portal.
  - **Setting:** **Lakemont** (placeholder name, chosen by Hunter), a **fictional American city** that blends **Philly** (row houses, corner bodegas, stoops), **NYC** (glass towers, subway grit, dense avenues) and **Chicago** (elevated L trains, back alleys, a lakefront). The real-world eras the player visits (1989 Miami, early-1900s Chicago, and the visions of Mongolia and Germany) stay **real places**.
- **Camera:**
  - **Default:** third-person over-the-shoulder, with Uncharted-style camera framing in set pieces (the camera pulls out for scale during chases and collapses).
  - **First person** where the script asks for it: Josh's wake-up, the manhole peek, Rivers' blurry ambulance view.
  - **Seamless in-engine cutscenes** that hand straight back to gameplay with no loading.
  - **Timeline Sight:** a split/flicker view.
- **Rating:** M/18+ as written; see Q3.

## 3. Core gameplay loop

**Directed story chapter (set pieces) → a wide-linear Lakemont stretch (explore, talk to companions, take on side quests before they expire) → story beat or time jump → RIPPLE: the city transforms around you → explore what changed → repeat.** The pacing alternates between high-intensity set pieces and quieter, story-rich exploration, like Uncharted's rhythm of action, traversal, conversation and puzzle.

- **Act 1 (Rivers):** you *cause* the ripples.
- **Acts 2–4 (Josh):** you *suffer* them, and then use time travel and Timeline Sight to fight back.
- **The emotional engine:** you learn a place in one timeline (the bodega, the school, a friend's apartment), and then you watch it become something else.

## 4. The living world: timeline states and ripples

### 4.0 The city: Lakemont

**Name:** **Lakemont**, a placeholder Hunter chose on Nov 19. It needs a trademark and existing-game check before any public use.

**How it plays:** Lakemont isn't one seamless sandbox. Each district is a **wide-linear space** that opens in specific chapters, with a main path plus optional streets, rooftops, interiors and alleys to explore. Districts get revisited across timeline states. The thrill is walking a street you know after it's been rewritten.

**Fictional brands rule:** the in-world newspaper, sports teams, beer and stores are all invented. The concept art's real marks are reference only and won't ship: the *Chicago Tribune* in 01, and the Budweiser sign and Dolphins-style jacket in 03. For example, the alley paper becomes something like *The Lakemont Ledger*.

**Districts and how each changes across timelines:**

| District | Real-city DNA | S0 Origin | S1 Ripple | S2 Fracture | S3 Martial Law | S4 Lockdown | S5 Restored |
|---|---|---|---|---|---|---|---|
| **Riverside** (Josh's block: the bodega, the alley, row houses, his school) | Philly row houses and corner bodegas, plus a Chicago back alley | Working-class and lived-in. The **Riverside Bodega** shutters after the 2010 robbery | The bodega is open with Josh's dad behind the counter. The Cortaz building is a burned lot | Bombed streets, soldiers, the school a ruined shelter (pp. 12–13) | Curfew posters, ration lines, checkpoints | Abandoned, with patrols sweeping through | Thriving. The bodega is busy and the school intact |
| **Midtown** (the gala hall, the news studio, towers) | NYC glass towers and avenues | Glamorous: the Echo launch, billboards, press | Same, plus Rivers' "time machine" billboards seeded in | Half-ruined skyline; propaganda screens | The President's decrees on every screen; armored traffic | Evacuated; National Guard staging | The Joshua Industries gala; the Echo billboards return |
| **The Elevated** (L-train corridor, markets, underpasses) | Chicago L, NYC subway grit | Busy commuter trains; buskers | Unchanged ("nothing changed... except") | The L becomes a military supply line; stations are bunkers | Trains stopped; tracks used as walkways and sniper perches | Partly collapsed | Trains running again, under new brand names |
| **Lakeshore Heights** (the Rivers estate, wealthy homes) | Chicago lakefront mansions | The Rivers house: the break-in, the funeral nearby | Same | Isabella alive here (p. 16) but cut off by the war | A Death Squad cordon around the estate | Dark and abandoned | Different owners; the house "never happened" |
| **South District** (warehouses, the bridge, rail yards) | Philly/Chicago industrial | The killers' house (Chapter 3) and the docks | Same | Militia territory begins | **F.A.R. territory**: the warehouse HQ and the snowy bridge (pp. 26–28) | Raided and burned after the breach | Redeveloped |
| **Rivers Industries campus** | NYC/Chicago tech campus | An elegant HQ and labs | A wing expands (Project Isabella) | A **fortress**: walls, tanks, anti-air, the time lab (p. 22) | Fortified further; it's the protest site | Sealed; mech spiders and alarms | Becomes **Joshua Industries** |
| **Underground** (subway and sewers) | NYC subway, Chicago tunnels | Utility tunnels, mostly locked | Same | Shelters for civilians | Sewer smuggling routes; Charlie's guide (p. 23) | The infiltration route into the campus (p. 33) | Back to utility tunnels |

*Off-hub, single-chapter spaces:* Harvard (chapter 4), the Death Squad HQ, and the anchor eras (§5).

### 4.1 Timeline states (macro states of the hub city)

| State | Trigger (script) | What the city looks like (proposed) | Chapters |
|---|---|---|---|
| **S0 Origin** | Game start | The "bright" present: clean downtown, Rivers Industries' modest HQ, the gala hall, the busy Riverside Bodega... and then the bodega vacant after its owner's 2010 murder. Police and News 11 cover the Isabella case. | P–6 |
| **S1 Ripple** | Trial 1: Cortaz killed in 2008 (p. 11) | Small, *local* changes. The bodega is alive with Josh's dad behind the counter. The Cortaz building is a burned lot. Josh's family photos change. Most of the city is the same, which is the hook: "nothing changed... except." | End of 6 → 6b (then S1a, S1b; see below) |
| **S2 Fracture** | The Death Squad's Capone and Khan edits, plus the Hitler art-school flash (pp. 12–16) | **Total transformation:** WW3 (Nazi Germany vs. America with modern tanks). Fighter jets, a ruined suburb and school. Rivers Industries is a fortress campus and the only beautiful thing left. Isabella is saved (p. 16). | 7–11b (S2a from 11b) |
| **S3 Martial Law** | In-story escalation: the presidential martial-law decree, the F.A.R. rise, the warehouse raid (pp. 24–29) | Curfews, checkpoints, propaganda screens. F.A.R. territory in the south district. Death Squad patrols. Snow. | 12–14 (+13b; S3a from 13c) |
| **S4 Lockdown** | The protest crackdown: the National Guard boxes in the crowd and shoots (p. 35) | Riot aftermath. The Rivers Industries perimeter is sealed, alarms run, and mech spiders patrol. | 15–17 |
| **S5 Restored** | Miami 1989 finale (p. 51) | The reset world, 10 years on. **Joshua Industries** replaces Rivers Industries. The bodega is open, the school intact. It mirrors S0 with the differences highlighted. | E |

*S3 and S4 are aftershock states caused by story events. The script's own history edits produce S1 and S2.*

**Extra Rivers edits: more shifts** *(new, approved in principle by Hunter on Nov 19; the specific targets need his sign-off)*

These add **4 more history edits**, for **10 timeline states** in total. They give Rivers a slower, more believable descent: the doc's earlier note was that his turn felt too fast. Every target is a **fictional Lakemont figure or event**, never a real person.

| New state | When | Rivers' edit *(new)* | What Lakemont shows the player |
|---|---|---|---|
| **S1a Saved Block** | Act 1, after Trial 1 | **Trial 2:** Rivers' team goes back to **1978** to stop the arson that burned a Riverside tenement and killed 30 people. It's a heroic edit, and he believes he's doing good. | Riverside rebuilds itself: the burned lot becomes a living row-house block, a park becomes houses, and new families (and side quests) appear. The cost: a community center built in the fire victims' memory never existed. |
| **S1b Rivers' City** | Act 1, end | **Trial 3:** Rivers erases a corrupt 1990s Lakemont councilman who blocked his early research funding. | Midtown becomes a Rivers-funded tech district: Echo cars everywhere, Rivers Industries towers grow, and surveillance cameras appear on every corner. Utopian on the surface, quietly controlled underneath. |
| **S2a The Severed Line** | Act 2, mid | The Death Squad erases the **1960s construction of the Elevated extension**, to cut the rebels' supply routes. | **The Elevated district vanishes mid-chapter** while Josh is on it (the set piece in chapter 15b). The L line is replaced by a walled military highway, and old routes become dead ends. |
| **S3a No Home** | Act 3, mid | Rivers, hunting the "anomaly", edits **Josh's own family history**: his parents never move to Lakemont. | **Josh's house and street change in front of him.** His mom becomes a stranger, and his room belongs to someone else. This is the most personal ripple. Collectibles from Josh's life become "Erased." |

*Revised state order:* S0 → S1 → **S1a** → **S1b** → S2 → **S2a** → S3 → **S3a** → S4 → S5. *Each new state needs its own district variants, so they're scoped as **partial** changes (1–2 districts each) to contain the art cost (§12).*

### 4.2 What a ripple changes
- **Districts:** geometry swaps (a block of shops becomes a bombed-out ruin), new walls and checkpoints, closed or opened routes.
- **Landmarks:**
  - **The bodega:** vacant or busy.
  - **Rivers Industries:** an office, then a fortress, then Joshua Industries.
  - **The school:** a school or a shelter.
  - **The gala hall.**
  - **Billboards:** Rivers' face, "time machine to fix history" (p. 15).
- **NPCs:** who's alive, their jobs and their memories. Dylan, Charlie and Ava don't know Josh in S2.
- **Factions:**
  - **S0:** police and press.
  - **S2:** the Death Squad, the German military and the US military.
  - **S3:** the F.A.R. and the National Guard.
  - **S4:** mech spiders.
  - **S5:** police and press again.
- **Systemic changes:**
  - Traffic (Echo AI cars in S0 → convoys and armored vehicles in S2+).
  - Radio and news content.
  - Weather (the snowy bridge in S3).
  - Music.
  - Shops and economy.
- **The map UI:** the minimap and world map visibly redraw. Old labels "burn away" like torn paper, matching the script's "time is like paper."

### 4.3 The ripple sequence (live, on screen)
1. **Warning:** headache audio, ringing, and a screen-edge tear effect. The Journal flags "Ripple imminent" before any story chapter that will shift the state, so the player gets a point-of-no-return prompt.
2. **The wave:** a world-space ripple expands from the point of change (or from the portal). Behind the wave, the new timeline's geometry, materials, lighting and NPCs resolve. Ahead of it, the old world still stands. NPCs freeze, flicker and swap mid-stride.
3. **Aftermath:** the map redraws, the Journal's "Erased" page updates with lost quests and NPCs, and a news broadcast in the new world sets the new status quo, echoing the script's news anchors.
4. **Duration:** about 10–20 seconds, playable (you can walk through it) or as an in-engine cinematic at key moments (S1 → S2 is the showpiece, chapter 7).

## 5. Player time travel (Josh)

- **Unlock:** mid-game, in **chapter 13b "The Tether"** (new). The F.A.R. salvaged a Death Squad car that overturned in the chapter 10 convoy chase. Inside is a field portal rig. Before this point, Josh only *sees* other timelines through Timeline Sight. Afterward, he can *go*. (The script's own jump in chapter 17 uses Rivers' lab machine; the field rig is a design addition so travel can be a mid-game system.)
- **Anchor eras** (fixed, hand-built maps; no free choice of date):

| Anchor | From the script | Play there |
|---|---|---|
| **A1: 2008, the alley and the bodega block** (Jan 22, 2008; the hub city's Riverside district, 2008 version) | Trial 1 (p. 10) | Revisit Rivers' first crime scene; watch Rivers, Tyler and John from hiding; meet Josh's dad, alive and younger |
| **A2: 2010, the bodega robbery day** (Jan 22, 2010) | The Cortaz file (p. 9) | Witness the original robbery (Timeline Sight). Side content around the bodega |
| **A3: the night of Isabella's robbery** (year unstated) | pp. 3–4, 16 | A tense, "crowded night": the original robbers, Rivers' Death Squad ambush, and Josh, all present. Mostly observe, high risk |
| **A4: early-1900s Chicago** (Capone's apartment; a real place) | p. 12 | Death Squad raid aftermath. A real-world noir-era map (not the fictional hub) |
| *A6: 1978 Riverside; A7: 1990s Midtown* *(new)* | Rivers' Trials 2 and 3 (chapters 6b, 6c) | Played as Rivers in Act 1. Josh can revisit them after 13b to find the Rivers journal pages and Echoes |
| **A5: 1989 Miami** (Jan 3) | pp. 43–51 | The finale map; locked until chapter 18 |
| *Mongolia, 1100s; Germany, 1939* | Visions only (pp. 13, 15) | **Not visitable:** too sensitive (child killing) and too big in scope. Shown only through Timeline Sight flashes |

- **Cause and effect** (the rules are new):
  - **Micro-ripples:** small acts in an anchor change *facts* in the present state, not the whole state. Examples: warn a shopkeeper and his store is open now; leave a note in a wall and it's still there; pick up a keycard in 2010 and a door opens in S3; help someone and they're an ally now. These are tracked as flags (§11.4).
  - **Fixed points:** the script's key events (Isabella's death in S0, Cortaz's death, the Capone and Khan erasures, Ava's death) are protected. Interfering triggers a "paradox snap-back" and a headache spike. This keeps the story intact and the scope finite. *(If Hunter wants a "save Ava" branch, this is where it would go; see Q2.)*
  - **No rollback:** travel can't restore a previous macro state. Expired side quests stay lost; that's the point.
  - **Cost:** each jump fills the headache meter. That's grounded in the script: headaches, nosebleeds, seizures, and Rivers' CT scans showing brain abnormalities in everyone who travels (p. 33). Overuse causes blackouts and can lock travel until he rests.

## 6. Exploration, side quests and collectibles (the Lakemont hub)

### 6.0 Exploration model (wide-linear, story-first)
- **The shape of a district:** a large, hand-built district with a clear main route and branching optional spaces. Examples: a row-house block with enterable homes, a market under the L, rooftops, a flooded subway station. It's like Madagascar or the Western Ghats, not a GTA grid.
- **Pacing:** most hub stretches take **20–60 minutes** if fully explored, and the main route is always readable. Players who just want the story can push straight through.
- **Movement:** on foot plus Uncharted-style urban traversal (fire escapes, rooftops, scaffolding, L-train girders). Vehicles appear only where a chapter calls for them, like the jeep in Madagascar.
- **Discovery is story:** every optional space holds something specific, such as a note, a photo, a conversation, a side quest, or evidence of what a ripple changed. **No checklists, no icon-cluttered map, no repeatable activities.**
- **Revisiting:** the same districts return in new timeline states, so exploring becomes "spot the difference." Timeline Sight shows what used to be there.

### 6.1 Collectibles (each one tells part of the story)
- **Echoes:** objects that survived from an erased timeline, like Josh's family photo with his dad or a ticket stub from Ava's ice-cream date. Only Josh can see them through Timeline Sight. They fill the "Erased" album.
- **Lakemont Ledger front pages:** one newspaper per timeline state. Together they're a history of every edit.
- **Rivers' journals:** pages from Rivers' notebooks that trace his descent. They're hidden across eras.
- **Treasures, Uncharted-style:** period objects in the anchor eras (2008, 1978, 1989, early-1900s Chicago).

### 6.2 Companion conversations
- **Optional walk-and-talk prompts** with Dylan, Charlie, Ava, the F.A.R. leader and others. They react to the place and to what changed, the way Uncharted's optional conversations do.
- **They build the relationships the script needs to pay off:** Ava's half-memories, Dylan's parents, Charlie's sarcasm, the friends learning to trust Josh.
- **Some conversations expire with the timeline**, like everything else in the hub.

### 6.3 Limited-time side quests

- **Every side quest is tagged with the timeline states it exists in.** When a ripple happens, unfinished quests **expire permanently**. Their NPCs may be dead, never born, or strangers.
- **Telegraphed, never a surprise:**
  - The Journal shows a "fraying" icon on quests that are tied to the current state.
  - A "Ripple imminent" warning plus a confirm prompt comes before point-of-no-return story chapters.
  - An **"Erased" page** remembers what was lost. Only Josh can remember it, because only he perceives both timelines. That makes the mechanic a story beat.
- **Echoes:** some completed quests leave residue in the next state, like an NPC who half-remembers Josh (as Ava does), or an item that persists.
- **Example quests** (seeded from script places and characters; the specifics are new and need Hunter's approval):
  - **S0:**
    - "Tip Line": follow up the News 11 tip hotline for the Isabella case (p. 6).
    - Errands for Professor Witmore (Harvard, off-hub).
    - Rivers Industries investor favors after the Echo launch.
  - **S1:** "Two Dads": time with Josh's dad at the bodega. It expires at the S2 ripple, which is deliberately painful.
  - **S1a/S1b** *(new states, played as Rivers)*: meet the families of the saved 1978 block; investigate who's behind the new surveillance cameras. Both expire when the war arrives.
  - **S2a:** get the last civilians off the Elevated before the line is erased (a timed rescue that's lost at the ripple).
  - **S3a:** recover pieces of Josh's old life before they fade (Echo collectibles that expire).
  - **S2:**
    - Find survivors in the ruined suburb.
    - Learn what happened to Dylan's parents (p. 27).
    - Scavenge supplies with Charlie's friend, the sewer guide.
  - **S3:**
    - Recruit marchers for the protest (more recruits means a bigger crowd in chapter 14).
    - Intercept a supply caravan, using the F.A.R. caravan story (p. 25).
    - Get past checkpoints.
  - **S4:** rescue protesters boxed in by the National Guard.
  - **A5 (1989 Miami):**
    - Pay back the clothing-store cashier.
    - Small period errands.

## 7. Playable characters

| Character | Acts | Plays like | Signature ability (proposed, kept to what the script supports) |
|---|---|---|---|
| **Dr. Rivers** | 1 (and a cameo leading the squad in Act 2) | A deliberate, methodical stealth intruder; an investigator | Investigation board/deduction; lockpicking; cover-up actions (casings, gas) |
| **Isabella Rivers** | Chapter 1 | Vulnerable; hide and survive | Hide, improvised weapon (heel). The outcome is fixed by the story. |
| **Josh** | 2–4 (lead) | Agile civilian, a reluctant shooter | **Timeline Sight**: flicker between realities to see clues and memories. A persuasion system built on things he remembers. **Field portal travel** to anchor eras, from chapter 13b on. |
| **Death Squad operative (Unit 14)** | Interludes | Military tactical; vehicle combat | Drives the armored ambulance in the convoy chase. Breach-and-clear raids. |
| **Ava** | Act 3 (overwatch) | Security-camera operator | Switches cameras, marks guards, calls "now" (asymmetric support; could be co-op later) |
| Dylan, Charlie | Companions (AI) | Comic relief, door-blocker, distractor | Context actions (Dylan's foot in the door, Charlie's distraction in the store) |


## 8. Chapter breakdown (mapped to script scenes and timeline states)

### 8.1 Chapters

**Target:** about 28 chapters and **15–20 hours** of story, plus optional hub content. Rows marked *(new)* add story beyond the script, at Hunter's request for a longer, fuller game, and need his approval. Chapters marked **wide-linear hub** open up for exploration. The rest are tightly directed.

| # | Chapter | Script pages | Timeline state | Play as | Gameplay |
|---|---|---|---|---|---|
| **P** | **The Unveiling** | 1–3 | S0 Origin | Rivers | Tutorial for walking and talking: the speech (timed dialogue prompts that move the crowd), red-carpet photos, the assistant's walk-and-talk, the conversation with Isabella (dialogue choices; she still insists he stay) |
| **1** | **The Ride Home** | 3–4 | S0 Origin | Isabella | Limo ride (passenger mode, world reveal). At home: hear glass break, hide along the wall, ambush with the heel. A **scripted loss**; the player can't save her. |
| **2** | **Rain** | 4–6 | S0 Origin | Rivers | Mostly non-interactive: finding her, the rainy funeral (eulogy choices), the friend's conversation. The garage **investigation board** (link CCTV stills and suspects), and the news broadcast. |
| **3** | **The Algorithm** | 6–7 | S0 Origin | Rivers | Drive at night to the killers' home (driving, possibly in an Echo). Stealth around the house (windows, backyard, an ajar door). The shooting (a forced, shaky aim). **Cover-up checklist**: casings, gasoline, the stove, a candle. Finished at the bathroom mirror. |
| **4** | **Paper** | 7–8 | S0 Origin (+ Harvard, off-hub) | Rivers | The torn-photo realization leads into a whiteboard formula puzzle, then Harvard: a dialogue scene with Professor Witmore. |
| **5** | **Project Isabella** | 8–10 | S0 Origin | Rivers | Lab-building time-lapse (light management/hub). The assistant confrontation (dialogue with a fixed outcome; she's caged). Choosing the target (the Cortaz file). |
| **6** | **Trial 1** *(vertical slice)* | 10–11 | S0 → anchor 2008 → **ripple to S1** | Rivers (+Tyler, John) | Portal launch, 2008 alley, the newspaper date. **Blend in** (low-profile walk; eye contact with the bodega owner and his son). Lockpick Cortaz's door while the team screens you. Split up. **Stealth through a 2-floor apartment**: Tyler's shot, John's gas and candle. Time snap-back (headache, nosebleed, the building explodes). |
| **6b** | **Trial 2: The Fire of '78** *(new)* | — | Anchor 1978 Riverside → **ripple to S1a** | Rivers (+Tyler, John) | Rivers proves time travel can do good. **Set piece:** a rooftop chase across 1978 Riverside to stop the arsonist, a partial fire anyway, and an escape through a collapsing tenement while carrying a child out. Back in the present, the block is reborn (a live ripple). |
| **6c** | **Trial 3: The Councilman** *(new)* | — | Anchor 1990s Midtown → **ripple to S1b** | Rivers | A stealth infiltration of a 1990s political fundraiser (a dark mirror of the gala), the kill, then a **car chase** escape through period Midtown. The ripple builds Rivers' tech-utopia Midtown. The assistant's doubts start here, setting up chapter 5's confrontation. *(Ordering note: 5's cage scene could move after 6c.)* |
| **7** | **Two Worlds** | 11–12 | S1 Ripple → **live ripple to S2** | Josh | First-person wake-up. **Timeline Sight intro**: photos with and without Dad. Run to the corner: bodega vacant or busy, the billboard, the memory of the bodega. Bombs and tanks start. **Chase/escape** through the alley to the ruined school, then pass out. |
| **8** | **Interlude: The Squad** | 12–13, 15–16 | Anchors (Chicago, the robbery night) → S2 | Death Squad | **Chicago, early 1900s:** a breach-and-clear raid on a young Capone's apartment. The Khan scene is recommended as a non-playable flash, or cut (see Q3). **The Rivers home**: Rivers ambushes the burglars from the side of the house; Isabella lives (shown from her side). |
| **9** | **Strangers** | 13–18 | S2 Fracture | Josh | Wake to the friends, who don't know him. **Memory persuasion**: pick the right personal facts (Dylan's birthday, Ava's violet and mint ice cream) to win trust. Ava's history flashback. **Chalkboard deduction** (link the bodega, the fire and Rivers). The textbook that changes from "50 colonies" to "History of America" is a time-flicker beat. |
| **9b** | **Ruins of Riverside** *(new)* | (expands pp. 21–23) | S2 Fracture (**wide-linear hub**) | Josh (+Dylan, Charlie, Ava) | The **Seattle Day 1–style** chapter. Cross the war-torn Riverside district to find Charlie's sewer guide, with optional buildings, survivors, Echo collectibles and the first big companion conversations. Patrols can be avoided or fought. |
| **10** | **Code Red Convoy** | 18–21 | S2 Fracture | Death Squad driver (Unit 14) | Armored-ambulance **convoy chase** through a war zone: dodge German vehicles that ram you, take the wheel when the driver is hit, PIT the Nazi car (slow-motion flip), then helicopter support to the gates. Intercut with Rivers' blurry first-person view and the defib beats. |
| **11** | **The Plan** | 21–25 | S2 Fracture | Josh & friends | A heist-planning hub on the school map. **Simulated sewer run** (a playable "what-if" rehearsal that ends when Dylan says "we forgot the guns", as in the script). Choose the distraction approach, which leads to the F.A.R. |
| **11b** | **The Severed Line** *(new)* | — | S2 → **live ripple to S2a** | Josh (+Dylan) | Riding the Elevated to the F.A.R. contact, Josh is caught by the Death Squad's edit. **Set piece:** the track dissolves in a paper-tear wave *ahead of the moving train*. Jump cars, climb along the outside, and leap to a collapsing station as the L line is erased behind you. |
| **12** | **Recruited** | 26–28 | S2 → **S3 Martial Law** | Josh | Under the snowy bridge with comms. Van abduction (Josh loses his comms; Dylan whispers to Ava). The F.A.R. warehouse, the DNA test and the reveal about Dylan's parents. |
| **13** | **Breach** | 28–30 | S3 Martial Law | Josh | The Death Squad blows the doors. **Survive and escape** in smoke and cover. Follow the leader to the hatch (a soldier's last stand). The **knife standoff** is a high-stakes dialogue where a wrong answer means failure. |
| **13b** | **The Tether** *(new, not in script)* | — | S3 Martial Law | Josh | The F.A.R. salvaged the overturned Death Squad car from the Chapter 10 convoy. Inside is a field portal rig. Steal it back from a scavenger yard (stealth). Ava and Charlie get it working, and **player time travel unlocks** (see §5). |
| **13c** | **No Place Like Home** *(new)* | — | S3 → **live ripple to S3a** | Josh | Josh goes home with the new portal rig and watches his street, house and mother rewrite themselves (the S3a ripple). **Set piece:** a Death Squad team homing in on the anomaly ambushes him there. A rooftop and row-house escape follows across the changing block. |
| **14** | **March on Rivers** | 30–33 | S3 Martial Law | Josh (+ cutaways) | The protest builds (huge crowds and news-chopper shots, mostly cinematic). Rivers' lab scenes (CT scans). The **sewer infiltration for real** follows the guide, then peek out of the manhole (first person). |
| **15** | **Eyes in the Sky** | 34–38 | S3 → **S4 Lockdown** (crackdown) | Josh ↔ Ava | Tail a guard and block the door. Guard room: grab the keycard and take Ava's camera view. **Overwatch stealth**: Ava spots on camera and the boys move. The National Guard shooting is seen on the monitors. Charlie trips. **Ava's death** comes over comms (scripted). Alarms. |
| **16** | **The Spider** | 38–41 | S4 Lockdown | Josh | A **hide-and-seek** set piece: hide under a desk or in a closet while the mech spider scans with lasers (a hold-breath mechanic). The **glass elevator** under fire (hit the deck, pick a floor). Stairwell flanking, then breach the lab (**combat**). |
| **17** | **Remember** | 41–43 | S4 Lockdown | Josh | **Confrontation dialogue** with Rivers (Timeline Sight forces his memories); Rivers' suicide happens in a cutscene. Set the portal. The guards are coming; push Dylan in, and Charlie hesitates. |
| **18** | **Miami, 1989** | 43–47 | Anchor 1989 Miami | Josh, Charlie, Dylan | A period Miami street. **Shoplifting distraction**: Charlie distracts the cashier while Josh and Dylan grab clothes and tip-jar cash (a light stealth minigame). Charlie's mirror flashback. A cutaway shows the Death Squad arriving and questioning the cashier. |
| **19** | **Miami High** | 47–51 | Anchor 1989 Miami → **final ripple** | Josh | **Blend in** at school (social stealth), ask students where Rivers is, argue over what to do (a dialogue choice; see Q1). The Death Squad storms in, then a hallway escape to the library. **Final choice and slow-motion finale**, depending on how Hunter resolves gap #1. |
| **E** | **Echo** | 51–54 | S5 Restored | Josh (Dr. Joshua) | Mirrors the prologue exactly: wake up and hug Mom, then 10 years later the Joshua Industries gala, the same speech, the same walk-and-talk, and the Ava reveal. Credits. |

*Optional anchor chapters (from §5, after 13b): **A2 The Robbery Day (2010)**, **A3 The Crowded Night** (Isabella's robbery night, with Rivers' squad present), and **A4 Capone's Chicago**. Each is a compact story chapter of about 30–60 minutes with its own treasures and micro-ripples.*

*About 28 chapters in total. Story-only playtime is about 15–20 hours, plus 5–10 hours of hub exploration.*

### 8.2 Uncharted-style set pieces

The main path is built around **directed, cinematic action sequences**: authored camera work, scripted destruction, chases and "the world falling apart under you" moments. Players keep control throughout, and cutscenes are kept for the emotional beats.

| # | Set piece | Chapter | Source |
|---|---|---|---|
| 1 | **Home invasion**: hide and fight back as Isabella; a horror-style chase through a dark house | 1 | Script |
| 2 | **Arson and escape**: pour, light, and slip out of the killers' house as the gas builds | 3 | Script |
| 3 | **The snap-back**: the team rips back through time while the Cortaz building explodes behind them | 6 | Script |
| 4 | **The burning tenement**: a rooftop chase, then an escape from a collapsing 1978 building | 6b | New |
| 5 | **The fundraiser getaway**: a car chase through 1990s Midtown | 6c | New |
| 6 | **Two Worlds run**: sprint through a street flickering between peace and war while bombs land and buildings fall | 7 | Script |
| 7 | **Code Red Convoy**: the ambulance convoy, ramming cars, a slow-motion flip, helicopters, taking the wheel | 10 | Script |
| 8 | **The Severed Line**: the L train erased under you mid-ride | 11b | New |
| 9 | **Warehouse Breach**: escape through smoke and gunfire to the hidden hatch | 13 | Script |
| 10 | **No Place Like Home**: the house rewritten, then an ambush and rooftop escape | 13c | New |
| 11 | **The March and the sewers**: crowd scale above, then a flooding sewer infiltration below | 14 | Script, with the flood new |
| 12 | **Eyes in the Sky**: stealth guided by Ava on camera, ending in her death over comms | 15 | Script |
| 13 | **The Spider**: hide-and-seek from the mech spider's lasers | 16 | Script |
| 14 | **The glass elevator**: under fire in silence except for the elevator music, then the stairwell breach | 16 | Script |
| 15 | **The portal escape**: the machine spinning up while guards storm the lab | 17 | Script |
| 16 | **Miami pursuit**: the Death Squad hunts the trio through 1989 streets and rooftops. *The school-interior gunfight is recommended to move outside or into cutscenes (Q3).* | 18–19 | Script (with relocation proposed) |

## 9. Key mechanics

1. **Third-person movement, cover and stealth.** Crouch, lean, sight cones, noise (glass, tripping, door slams), and hiding spots (desk, closet, cabinet). Holding your breath is an active input.
2. **Timeline Sight (Josh).** Hold a button to see the other timeline, which shows clues, routes and memories. It costs **headache meter**, matching the script's headaches. Overuse causes blackouts, echoing the script's nosebleeds, seizures and fainting.
3. **Dialogue and persuasion.** Choices are timed, as in Telltale or Mass Effect. Memory-based persuasion means choosing the facts only Josh could know. Most major outcomes stay fixed to honor the script, with a few real branches (see Q2).
4. **Investigation board and chalkboard deduction.** Connect evidence to unlock the next chapter.
5. **Driving (chapter-specific only).** The Echo, a limo ride as a passenger, Rivers' car, the 1990s getaway car, the armored ambulance and the convoy. There's no free-roam car theft. Vehicles appear where the story uses them, as in Uncharted 4's Madagascar jeep.
6. **Overwatch/camera hacking.** Ava's security feeds drive a stealth section played from an asymmetric view.
7. **Gunplay.** Light and grounded. The friends are untrained: shaky aim, little ammo. Death Squad interludes are tactical.
8. **Contextual co-op companions.** Dylan, Charlie and the F.A.R. leader each have scripted assists.
9. **Ripples and time travel.** Live world transformations (§4.3). The player-controlled field portal to anchor eras, with micro-ripple cause and effect (§5). The headache meter is shared with Timeline Sight.
10. **Mirrored bookends.** The prologue and epilogue are the same playable scene, with the differences highlighted.
11. **Expiring side quests and the Journal.** Quests are tagged by state, warnings come before a ripple, and an "Erased" page records what was lost (§6).
12. **Living map (minimal).** A sparse, hand-drawn-style map with no icon clutter. It redraws per state, with districts and labels tearing away and re-forming.
13. **Uncharted-style traversal.** Climb fire escapes, scaffolding, L-train girders and rooftops. Jumps and grabs, slides, and climbing under fire. Traversal is the backbone of both the set pieces and hub exploration.
14. **Set-piece framework.** Scripted destruction, chase cameras and slow-motion beats (the convoy flip and the library are already in the script), with gameplay that never stops mid-action (§8.2).

## 10. Art direction and concept art

### 10.1 Target grade
- **Photoreal and grounded, "GTA VI-like."** Contemporary America in a fictional city that blends Philly row houses and bodegas, NYC towers and subway grit, and Chicago L trains, alleys and the lakefront (§4.0).
- **Look rules taken from Hunter's concept art:**
  - **Wet reflections** everywhere at night: puddles, neon on asphalt, rain on glass.
  - **Atmospheric haze**: steam from manholes, volumetric fog, light shafts.
  - **Warm practical lights against cool ambient light**: sodium and tungsten lamps, neon signs and window glow against a blue-grey sky and skylight.
  - **Cinematic contrast** with filmic tonemapping and a shallow depth of field in cutscenes.
- **Timeline palettes:**
  - **Bright states (S0, S1, S5):** warmer and cleaner, with gala gold and chrome.
  - **Torn states (S2 to S4):** desaturated ash-grey with orange fire, smoke and snow.
  - **Anchors:**
    - **2008:** cold, rainy night.
    - **1989 Miami:** sun-bleached golden hour, pastels, and dirt as the script describes.
    - **Early-1900s Chicago:** sepia noir.
- **Signature visual: "time is like paper."** Ripples and portals tear reality along paper-like edges.
- **Characters:** MetaHuman-level faces are essential for the script's close-ups and crying.
- **Honest expectation:** GTA VI fidelity is achievable in *focused* spaces. GTA VI *scale* is not (§12).

### 10.2 Concept art (Hunter's reference frames)

| File | Chapter(s) | What to take from it | What to fix before it becomes in-game |
|---|---|---|---|
| `concept-art/01-alley-2008.png` | **6 Trial 1** (anchor A1, 2008), also the base for the **Riverside** district | A rainy night alley: a steaming manhole, a red-and-blue neon "Riverside Bodega" sign, fire escapes, warm window light, and a gloved figure in a cap (matching the script's caps and plastic gloves). A newspaper dated Jan 22, 2008 sells the time jump. | Replace the real *Chicago Tribune* masthead with a fictional paper. The city is now fictional. |
| `concept-art/02-portal-lab.png` | **5 Project Isabella** (also the portal launch at the start of 6) | The ring portal with a blue-white energy core, an industrial hangar with cranes and server racks, Rivers in a suit berating a crew member (p. 8), and a "Project Isabella" screen. | It has an AI-baked minimap and "Objective prompt" HUD. Mood reference only. |
| `concept-art/03-miami-1989.png` | **18 Miami, 1989** and **19 Miami High** (anchor A5) | The trio in 80s clothes, golden-hour backlight, palm trees, Art Deco school facade, graffiti and litter (dirty Miami, as the script says), and a period car. | Real brands: a Budweiser sign and a Dolphins-style jacket. Swap in fictional ones. "Miami High" is a real school name, so decide whether to use a fictional school (Q7). |
| `concept-art/04-funeral.png` | **2 Rain** | A rainy cemetery, black umbrellas, mourners, Rivers at the casket with white lilies, and overcast diffuse light with a chapel in the fog. | It has an AI-baked HUD (minimap, health bar, clock) and a fake **"Red Dead Redemption"** objective label. Mood reference only. |

### 10.3 HUD and UI: must be original
- Two frames (02, 04) contain AI-generated UI that imitates **Rockstar's Red Dead Redemption and GTA HUDs**, including the "Red Dead Redemption" text. **None of that ships.** We won't copy the RDR or GTA minimap shape, health and armor bars, or fonts.
- **Our own direction (proposal):** a minimal, diegetic-leaning HUD built on the "paper and time" motif.
  - **Objectives** appear as torn-paper notes.
  - **The minimap** redraws when ripples hit.
  - **The headache meter** reads as a subtle vignette and pulse, not a bar.
  - **The timeline-state indicator** appears only during Timeline Sight.
  - **Typography** comes from licensed or open fonts.
- **Concept art for UI:** commission or design fresh mockups. Don't trace the AI frames.

## 11. Engine and stack

### 11.1 Decision
- **Unreal Engine 5 is the production engine.** It has Lumen, Nanite, MetaHuman, Megascans, Chaos vehicles, Sequencer and Movie Render Queue. Its World Partition and Data Layers are built for exactly the "swap parts of the map" problem this design creates.
- **Hardware:**
  - **Hunter's laptop** (Ryzen AI 9 365, 32 GB RAM, Radeon 880M integrated graphics) can run the editor at medium settings and render cinematics offline with Movie Render Queue, slowly.
  - **Real open-world iteration** wants a discrete RTX-class GPU (owned or rented cloud).
  - **I can't run UE5 on my own Linux box** (no GPU). I can drive Unreal on Hunter's laptop through its Python and command-line tools once it's installed.
- **The browser prototype (React Three Fiber)** remains optional, as a quick gameplay greybox and shareable link. It isn't the graphics target.

### 11.2 Living world in UE5: World Partition and Data Layers
- **One persistent World Partition map** for Lakemont, streamed in cells. Because the game is **wide-linear**, each chapter activates only its own playable bounds and districts (chapter Data Layers plus blocking volumes). That keeps memory, streaming and art budgets far below a GTA-style sandbox. Directed set pieces (the convoy, the Severed Line, the tenement) are built as **dedicated set-piece sublevels**, with Sequencer-driven destruction (Chaos) and camera rails. Anchor eras are separate small levels (portal travel triggers a level transition behind the ripple effect).
- **One runtime Data Layer per timeline state, per district.** Examples: `DL_Riverside_S0`, `DL_Riverside_S2`, plus a shared `DL_Base` for terrain, roads and invariant buildings.
  - A ripple **deactivates the old state's layers and activates the new ones** (Data Layer runtime states Unloaded/Loaded/Activated, driven by a `UTimelineSubsystem`).
  - **Only changed content lives in state layers.** Unchanged geometry stays in `DL_Base`, which keeps memory and art cost down.
- **Level Instances for landmarks:** each landmark (the bodega, the school, the Rivers Industries campus, the gala hall) is a packed Level Instance with per-state variants, such as `LI_Bodega_Vacant`, `LI_Bodega_Busy`, `LI_Bodega_Ruined`. A `ALandmarkSwapper` actor picks the variant from the current state plus micro-ripple flags, so a 2010 act can open the bodega without a full state change.
- **Cheap variation:** material parameter swaps (grime, scorch, snow), decal sets, PCG (Procedural Content Generation) graphs for rubble and debris per state, and Mass AI crowd profiles per state (shoppers vs. soldiers vs. protesters).
- **Lighting:** fully dynamic **Lumen**. Baked lighting can't survive geometry swaps. Each state has its own sky, fog and post-process volume (bright vs. torn grade).
- **Navigation and AI:** use dynamic NavMesh (or nav invokers) so routes update when walls appear. State Trees per faction.

### 11.3 The ripple transition
- **Material function `MF_RippleReveal`** goes into every master material that can change. A Material Parameter Collection drives a world-space sphere (center + radius + edge width).
  - Pixels inside the radius show the **new** state; pixels outside it show the **old** state.
  - The edge renders a burning paper-tear dissolve with emissive embers.
- **During the wave:** both states' data layers are briefly **loaded at once**. The old layer's meshes dissolve out as the new layer's meshes dissolve in, and the old layer is unloaded when the wave has passed.
- **Niagara effects:** a paper-shred and ember particle front that rides the wave, with dust, light flicker and NPC "glitch" ghosts (afterimages of the old NPCs).
- **Post-process:** chromatic split, a heat-haze distortion ring and a headache vignette. Audio: ringing plus muffled-world filter (script-accurate).
- **Timeline Sight reuses the same tech in reverse:** it renders the *other* state's key actors through custom depth and stencil as translucent "ghost" overlays, without fully loading the whole layer.
- **Pre-warm:** a ripple only fires after the target layers have streamed in (point-of-no-return prompt, then pre-stream, then play). This avoids hitches.

### 11.4 Save state and tracking
- **`UEchoSaveGame`** (USaveGame), holding:
  - `CurrentTimelineState` (enum S0–S5, plus sub-states).
  - `TimelineFlags`: a **GameplayTag container** for micro-ripples, e.g. `Timeline.Riverside.BodegaOpen`, `Timeline.Ally.Cashier1989`.
  - `QuestStates`: each quest's status plus `ValidStates`. On a ripple, anything unfinished outside the new state becomes `Expired`, and its record is written to the **Erased** log.
  - NPC fates (alive, dead, never-born), unlocked anchors, the headache meter, inventory.
- **On load:** the `TimelineSubsystem` applies the state's Data Layers, then the landmark swappers, then the flags. That way the world is rebuilt deterministically from data, not from saved actor positions.
- **Safety:** autosaves land right before point-of-no-return ripples, and an "Erased" archive survives across saves. Expiring quests are permanent *in a playthrough*, not a save-scum trap.
- **Tooling:** an editor utility to preview any district in any state (toggle data layers), plus automated tests that load each state and check for missing landmarks and navigation errors.

## 12. Scope risks (honest)

1. **The Uncharted model is smaller than GTA, but not small.** Moving to narrative-first, wide-linear play is the right call for scope: there's no sandbox systems, traffic AI or city-wide simulation to build. But the bar Hunter is pointing at is very high. Uncharted 4 and TLOU Part II were made by studios of hundreds over several years. **Custom set pieces, full performance capture and cinematics are the most expensive content in games.**
2. **10 timeline states multiply content.** Mitigation:
   - Only *changed* content gets authored.
   - The 4 new states are **partial** (1–2 districts each).
   - S3 and S4 reuse S2 with overlays.
   - PCG, decals and material swaps handle variation.
   - Wide-linear chapters only build what the player can reach.
3. **15–20 hours is long.** Every set piece in §8.2 is weeks to months of work for a pro team. Recommendation: build and judge the vertical slice first, then decide which new chapters (6b, 6c, 9b, 11b, 13c) earn their cost.
4. **Animation and faces.** Uncharted-quality storytelling depends on motion capture and facial performance. MetaHuman Animator (an iPhone or depth camera) and marketplace mocap help, but voice actors and performance capture are a real budget line.
5. **Hardware.** The integrated Radeon 880M in Hunter's laptop will struggle with Lumen, Chaos destruction and two loaded timeline layers during ripples. Real development needs a discrete GPU (owned or a cloud rental at about $1–3 an hour).
6. **Combinatorial bugs.** Expiring quests, micro-ripples and per-state NPCs create many states to test. Mitigation: data-driven flags, fixed points, automated state-load tests.
7. **Narrative coherence.** New chapters and player time travel can contradict the script. Mitigation: fixed points, no rollback, and Hunter approving all *(new)* plot.
8. **Players resenting lost content.** Warnings, the Erased log and echoes turn loss into meaning.
9. **Sensitive content and branding.** The rating issues are unchanged (Q3). Real brands and the AI-generated RDR/GTA UI in the concept art won't ship (§10.3).

## 13. Phased roadmap (updated)

| Phase | Deliverable | Where |
|---|---|---|
| **0. Pre-production** | This doc; Hunter's answers; a story bible that resolves the gaps; picking the city name; the district list locked | My box |
| **1. Look-dev slice** | The **gala (Prologue)** in UE5 on Hunter's laptop, matching the concept-art grade (wet reflections, haze, warm and cool lighting); a Movie Render Queue cinematic | Hunter's laptop (UE5) |
| **2. Ripple tech demo** | **One block of Riverside in two states** (S0 → S1, bodega vacant → busy), with `MF_RippleReveal`, Niagara, data-layer swapping and save flags. This proves the core hook | UE5 |
| **3. Vertical slice** | Chapter 6 Trial 1 playable: the A1 2008 alley (concept art 01), stealth, the return through the portal, and a **live ripple** into S1 | UE5 |
| **4. Hub v1 and a set piece** | Riverside as a **wide-linear district** in S0, S1 and S2, with 2–3 expiring side quests, collectibles and companion conversations; the S1 → S2 showpiece ripple (chapter 7); and one full Uncharted-style set piece (proposed: the Code Red Convoy) | UE5 + discrete GPU |
| **5. Act 1 complete** | Chapters P–6c (including Trials 2 and 3, S1a and S1b) with temp voice-over | UE5 |
| **6. Acts 2–3** | S3 and S4, the F.A.R., the infiltration; **player time travel** (13b) and anchors A2–A4 | UE5, small team |
| **7. Act 4 + epilogue** | Miami 1989 (A5), the S5 Restored city, polish, rating, a Steam page | UE5 |

## 14. Open questions for Hunter

*Answered so far: the city is **Lakemont** (placeholder); **more Rivers edits and more shifts**; a **longer, full game**; an **Uncharted-style, story-first, explorable** structure.*

1. **Ending:** who fires the final gunshot in the 1989 library? Is teenage Rivers killed, and should the player choose?
2. **Branching:** should the game follow the script's fixed outcomes, or allow real choices like saving Ava or Isabella (via the fixed-point system)?
3. **Sensitive content:** the school gunfight, the child killing (Khan), Rivers' suicide and the killing of a teenager. Can these be cutscenes, off-screen, or reworked? I recommend moving the 1989 action out of the school interior.
4. **New story:** do you approve the 4 new Rivers edits and the 5 new chapters? Those are Trial 2 (1978 fire), Trial 3 (the councilman), the Severed Line, Ruins of Riverside and No Place Like Home. Any you'd swap?
5. **Set-piece priorities:** which 2–3 set pieces matter most to you? They'd be built first.
6. **Time-travel scope:** are the anchor eras (2008, 1978, the 1990s, 2010, the robbery night, early-1900s Chicago, 1989 Miami) the right set?
7. **Miami High:** keep the real school name, or use a fictional one?
8. **Hardware and budget:** will you get a discrete-GPU PC or rent a cloud GPU? Is there any budget for voice actors, mocap and assets?
9. **Goal:** is this a portfolio piece, a pitch demo or a commercial Steam release?
10. **Lore gaps:** the date mismatches (2008/2010, 1992/1989), Isabella's fate in the war timeline, how Hitler/WW3 happened, and names for the F.A.R. leader, the Commander, Charlie's friend and the assistant.
