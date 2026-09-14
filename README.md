# Mixweave 1.2

**Mixweave** is a DJ playlist sequencing tool that turns a crate or playlist into a more performance-ready running order using BPM, Camelot key, Energy, artist spacing, broad Genre Pockets, and optional vibe metadata.

> **Make it mixable first. Make it harmonic second. Make the whole set flow.**

Mixweave does not try to replace DJ judgment. It does the tedious whole-playlist planning so the DJ can spend more time listening, programming, and performing.

## What Mixweave considers

### Mixing Brain
Mixweave first protects practical mixability.

- BPM neighborhoods and a hard BPM guardrail
- half/double-time interpretation when appropriate
- Camelot same-key, relative, adjacent, and selected energy moves
- BPM Escape Mode for tracks that fit by tempo better than by harmony
- BPM Bridge Planner to keep tempo outliers from creating a bad end-of-playlist cliff

### Programming Brain
Once the route is mixable, Mixweave shapes the playlist like a set.

- Energy Zones: **Warm-up → Groove → Build → Peak → Finish**
- optional Smooth or Build programming modes
- artist spacing across the whole set
- Genre Pockets: a soft preference for 2–4 tracks from the same broad musical family, with three as the sweet spot
- genre-island cleanup so repeated genres are less likely to appear as isolated one-offs
- adjacent-track Energy behavior

Genre never overrides the Mixing Brain. A pocket is created only when BPM safety, weak-link count, artist spacing, and Energy Zone guardrails remain protected. Blank or unfamiliar genre labels stay unclassified rather than being guessed.

### Vibe Polish
Danceability and Valence are optional **tie-breakers**. They may choose between otherwise similar safe routes, but they cannot override BPM safety, Camelot logic, Energy Zones, or artist spacing.

Popularity may be included in an input file and exported, but Mixweave 1.2 does not use it for sequencing.

## Playlist columns

Required columns:

- `Title`
- `Artist`
- `BPM`
- `Camelot Key`
- `Energy`

Optional columns:

- `Danceability`
- `Valence`
- `Popularity`
- `Genre` — strongly recommended for Genre Pockets

CSV, XLS, and XLSX files are supported.

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

Mixweave exports the optimized playlist plus DJ-facing transition information:

- `Mixweave #` — new running order
- `Program Zone` — broad role in the set
- `Transition Score` — Mixweave's 0–100 assessment of the incoming transition
- `Transition Quality` — Excellent, Good, DJ Workable, BPM Escape, or Weak
- `Transition Reason` — the main reason the transition was chosen
- `Camelot Move` — harmonic relationship
- `Effective BPM Δ` — practical BPM difference after legitimate half/double interpretation

The app also reports **Set Health**, weak links, hard BPM jumps, worst BPM difference, programming score, artist collisions, and genre islands.

## Design philosophy

Mixweave follows a few practical DJ rules:

1. A beautiful Camelot match does not rescue a terrible tempo jump.
2. A rhythmically clean transition can still work when the keys are not ideal.
3. One awful transition matters more than a tiny improvement to the playlist average.
4. Bridge tracks should not be spent too early and leave an impossible tempo island later.
5. Energy should shape broad sections of the set, not force a mathematically perfect curve.
6. Danceability and mood are polish, not steering wheels.
7. The DJ always gets the final vote.
8. When safe choices exist, prefer a short genre run over a stranded genre island.

## Running Mixweave

Mixweave is designed for Streamlit Community Cloud and can also be run locally.

Main files:

- `app.py` — Streamlit interface
- `optimizer.py` — sequencing engine
- `requirements.txt` — Python dependencies
- `sample_salsa.csv` — benchmark/sample playlist
- `test_optimizer.py` — regression tests

For a GitHub/Streamlit update, replace the changed files, commit them, let Streamlit redeploy, and reboot the app if it appears to be holding an older imported optimizer module.

## 1.2 status

Mixweave 1.2 preserves the core architecture developed through the Salsa and open-format benchmarks:

- tempo-safe BPM backbone
- practical Camelot scoring
- weak-link rescue
- Energy Zone programming
- artist spacing
- Danceability/Valence tie-breaking
- final conservative weak-link cleanup
- broad genre-family normalization
- safe 2–4 track Genre Pockets with a three-track sweet spot
- genre-island reporting
- streamlined app layout and Set Health summary

Future features should be added only if they improve real DJ workflow without compromising this foundation.


## Mixweave 1.2

Programming Brain refinement: adds broad Genre Pockets after the proven Artist Separation and Energy Zone guardrails. BPM safety remains the highest priority. Genre is recommended, not required, so older playlists remain compatible.
