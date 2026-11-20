"""ECHO Unreal build kit - builds the Prologue 'The Unveiling' gala level.

Modules:
    settings  - every tunable number (light levels, exposure, crowd size, paths)
    util      - logging, safe property setters, spawn helpers
    materials - procedural PBR master materials + instances
    gala      - the level: hall, stage, car, crowd, lights, fog, post, player start
    sequence  - Level Sequence for the opening shot + looping camera flashes
    render    - Movie Render Queue presets (1080p) and optional in-editor render
    main      - orchestrates the stages; entry point is ../echo_build_all.py
  Timeline Ripple demo: ripple_materials, riverside, ripple
  Trial 1 slice: trial1_beats (data), trial1_materials, trial1 (level), trial1_sequence,
                 trial1_runtime (Play-In-Editor director, armed by ../init_unreal.py)
"""
