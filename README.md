# MixWeave 1.3

**MixWeave** is a DJ playlist sequencing tool that turns a crate or playlist into a more performance-ready running order using BPM, Camelot key, Energy, artist spacing, genre-family information, and optional vibe metadata.

> **Make it mixable first. Make it harmonic second. Make the whole set flow.**

MixWeave does not replace DJ judgment. It handles the tedious whole-playlist planning so the DJ can spend more time listening, programming, and performing.

## What MixWeave considers

### Mixing Brain
MixWeave first protects practical mixability.

- BPM neighborhoods and a hard BPM guardrail
- half/double-time interpretation when appropriate
- Camelot same-key, relative, adjacent, and selected energy moves
- BPM Escape Mode for tracks that fit by tempo better than by harmony
- BPM Bridge Planner to keep tempo outliers from creating a bad end-of-playlist cliff

### Programming Brain
Once the route is mixable, MixWeave shapes the playlist like a DJ set.

- Energy Zones: **Warm-up → Groove → Build → Peak → Finish**
- optional Smooth or Build programming modes
- artist spacing across the whole set
- adjacent-track Energy behavior
- genre-family awareness to encourage more natural genre runs

### Vibe Polish
Danceability and Valence are optional tie-breakers. They may choose between otherwise similar safe routes, but they cannot override BPM safety, Camelot logic, Energy Zones, or artist spacing.

Popularity may be included in an input file and exported, but it is not a primary sequencing control.

## Large-playlist performance in 1.3

MixWeave 1.3 adds a dedicated performance path for large playlists (80+ tracks).

The main sequencing logic remains intact, but expensive late-stage polishing is restricted so the optimizer does not repeatedly brute-force thousands of full-playlist swaps and relocations. This keeps large open-format playlists practical while preserving the core BPM, Camelot, Energy, artist-spacing, genre, bridge-planning, and weak-transition logic.

Smaller playlists continue to use the fuller polishing process.

## Playlist columns

Core columns:

- `Title`
- `Artist`
- `BPM`
- `Camelot Key`
- `Energy`

Optional metadata can include:

- `Genre Family`
- `Danceability`
- `Valence`
- `Popularity`

CSV, XLS, XLSX, and supported PDF playlist inputs can be used through the app.

## Recommended starting settings

For a typical open-format or party playlist, start with:

- Preset: **Balanced**
- Ideal BPM tolerance: **4**
- BPM guardrail: **8**
- Half / double tempo: **On**
- BPM Escape Mode: **On**
- BPM Bridge Planner: **On**
- Energy program: **Party Zones**
- Energy Zone influence: **25**
- Artist spacing: **Normal**
- Vibe tie-breaker: **Light**
- Optimization depth: **Standard**

Then adjust by ear for the event and genre.

## Reading the results

MixWeave exports the optimized playlist plus DJ-facing transition and programming information. Depending on the input and selected options, the output can include:

- new running order
- Program Zone
- Transition Score
- Transition Quality
- Transition Reason
- Camelot Move
- Effective BPM difference
- genre-family information
- Set Health and programming diagnostics

The app can export an optimized Excel workbook and a DJ-facing PDF report.

## Design philosophy

MixWeave follows practical DJ rules:

1. A beautiful Camelot match does not rescue a terrible tempo jump.
2. A rhythmically clean transition can still work when the keys are not ideal.
3. One awful transition matters more than a tiny improvement to the playlist average.
4. Bridge tracks should not be spent too early and leave an impossible tempo island later.
5. Energy should shape broad sections of the set, not force a mathematically perfect curve.
6. Genre runs should feel intentional rather than constantly bouncing between unrelated styles.
7. Danceability and mood are polish, not steering wheels.
8. The DJ always gets the final vote.

## Running MixWeave

MixWeave is designed for Streamlit Community Cloud and can also be run locally.

Main files:

- `app.py` — Streamlit interface
- `optimizer.py` — sequencing engine
- `requirements.txt` — Python dependencies

For a GitHub/Streamlit update, replace the changed files, commit them, let Streamlit redeploy, and reboot the app if it appears to be holding an older imported optimizer module.

## Version 1.3

Version 1.3 establishes a clean version number and focuses on large-playlist performance without changing MixWeave's core DJ sequencing philosophy.

Use a large reception/open-format playlist of roughly 80–100+ tracks as a performance benchmark after deployment. The goal is a substantial reduction in optimization time while retaining useful DJ-quality sequencing.
