# Mixweave 1.2 — Genre Pockets

Built on the supplied PDF-capable v0.5 app and separately patched optimizer.
The adaptive search budgets, 55+ track Standard fast path, Mood handling,
Energy Flow, playlist titles, and PDF/Excel/CSV exports are retained.

## Genre Pockets in 1.2

- Import your Crate Hackers PDF directly, as before.
- The supplied Corporate Dance Party PDF has 100 tracks and no Genre column.
  Genre cannot be inferred from BPM, key, energy or mood. Assign broad families
  in the app's editable genre table; blanks are neutral, never guessed.
- Genre/Genres columns are accepted from spreadsheets and from PDF tables
  that contain them. Genre Family overrides are retained in Excel/CSV exports.
- Use Pop, Hip-Hop/R&B, Rock, Country, Latin, Disco/Funk, EDM, Reggae,
  Soul/Motown or Jazz. A crossover's family is your programming choice.
- The default Normal preference favors 2–4 track runs, with three cheapest,
  and discourages repeated-family singletons. Single-family crates are unchanged.
- The final bounded pass runs on both optimizer paths, including 55+ tracks.
  Cumulative budgets protect tempo jumps, weak links, artist spacing, energy
  guardrails, Energy Flow, and transition quality. A suitable safe move may
  not exist; genre pockets are not guaranteed.
- No automatic anthem/banger or line-dance roles are added in this release.
- Replace app.py, optimizer.py, README.md, and requirements.txt in your repo.
  Use those exact filenames. Run with `streamlit run app.py`.

The sections below document the retained v0.5 behavior.

**Mixweave** is a DJ playlist sequencing tool. It takes an already-built crate or playlist and turns it into a more performance-ready running order using the metadata that matters most to a working DJ:

**BPM • Camelot Key • Energy • Danceability • Mood**

> **Make it mixable first. Make it harmonic second. Make the whole set flow.**

Mixweave does not replace DJ judgment and it does not analyze audio files. It uses existing playlist metadata to plan the whole set, protect practical transitions, shape energy, and surface weak links for previewing.

## Preferred workflow

The primary Mixweave workflow is now:

**Build crate in Crate Hackers → Export playlist PDF → Upload PDF to Mixweave → Optimize → Download running order**

No MP3 upload is required.

### Why Crate Hackers PDF?

Modern Crate Hackers playlist PDFs contain the exact fields Mixweave needs:

- `Title`
- `Artist`
- `BPM`
- `Key`
- `Danceability`
- `Energy`
- `Mood`

The PDF format also keeps commas and long titles/artists intact more reliably than some Crate Hackers CSV exports.

Mixweave still accepts CSV, XLS, and XLSX files as alternate inputs.

## Import validation

For harmonic sequencing, Mixweave expects Camelot keys in the form `1A` through `12A` or `1B` through `12B`.

Older Crate Hackers archive PDFs may contain legacy/non-Camelot key data or a layout where the key is not extractable as a modern Camelot code. Mixweave will import the playlist but warn when keys are missing or invalid rather than guessing.

Numeric metadata from PDFs is cleaned and rounded on import.

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
- adjacent-track Energy behavior
- **Programming Flow** pass to reduce obvious Energy whiplash inside a zone without giving back BPM safety

### Vibe Polish

Danceability and Mood are optional **tie-breakers**. They may choose between otherwise similar safe routes, but they cannot override BPM safety, Camelot logic, Energy Zones, or artist spacing.

## Recommended starting settings

For a typical open-format or party playlist:

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

## Output

Mixweave exports the optimized playlist plus DJ-facing transition information:

- `Mixweave #` — new running order
- `Program Zone` — broad role in the set
- `Transition Score` — 0–100 assessment of the incoming transition
- `Transition Quality` — Excellent, Good, DJ Workable, BPM Escape, or Weak
- `Transition Reason` — main reason the transition was chosen
- `Camelot Move` — harmonic relationship
- `Effective BPM Δ` — practical BPM difference after legitimate half/double interpretation

The app also reports **Set Health**, weak links, hard BPM jumps, worst BPM difference, programming score, **Energy flow**, and artist collisions.

## Design philosophy

1. A beautiful Camelot match does not rescue a terrible tempo jump.
2. A rhythmically clean transition can still work when the keys are not ideal.
3. One awful transition matters more than a tiny improvement to the playlist average.
4. Bridge tracks should not be spent too early and leave an impossible tempo island later.
5. Energy should shape broad sections of the set, not force a mathematically perfect curve.
6. Danceability and Mood are polish, not steering wheels.
7. The DJ always gets the final vote.

## Main files

- `app.py` — Streamlit interface and playlist importers
- `optimizer.py` — sequencing engine
- `requirements.txt` — Python dependencies
- `README.md` — project overview

## Mixweave 0.5 changes

- Added **Zone Shape** refinement: Warm-up gently rises, Build has a stronger upward bias, Peak resists deep collapses, and Groove remains flexible
- Zone Shape is conservative: it may not add hard BPM jumps, weak links, or artist collisions
- Preserves the v0.4 Energy Flow measurement and BPM-safe route hierarchy
- Preserves the original Crate Hackers playlist title during PDF import
- PDF header now shows the original playlist title plus **Mixweave 0.5 - Optimized Running Order**
- Excel, PDF, and CSV filenames now include the playlist title and Mixweave version
- Retains Crate Hackers PDF import plus Excel/PDF/CSV export

### v0.5 benchmark goal

The Kurt & Anika cocktail crate remains the primary regression test. v0.5 should keep **zero hard BPM jumps**, avoid increasing weak links, and improve the musical direction inside Warm-up/Build/Peak. After that, the 50-track Carlos Wedding Cocktails crate becomes the first broader stress test.
