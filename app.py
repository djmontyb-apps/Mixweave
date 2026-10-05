import io
import hashlib
import re
import pandas as pd
import pdfplumber
import streamlit as st
from audio_analysis import attach_features
from genre_metadata import GENRE_FAMILIES, RekordboxGenres, genre_family
from optimizer import (
    Settings,
    optimize,
    energy_arc_details,
    energy_zone_labels,
    artist_spacing_stats,
    vibe_program_details,
    genre_pocket_stats,
    track_genre_family,
    opening_later_count,
)


st.set_page_config(page_title="Mixweave 1.4.5", page_icon="🎚️", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1420px;}
h1 {letter-spacing: -0.045em; margin-bottom: .15rem;}
h2, h3 {letter-spacing: -0.02em;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.15);}
.sf-eyebrow {font-size:.82rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; opacity:.65;}
.sf-hero {padding:.1rem 0 .45rem 0;}
.sf-tagline {font-size:1.08rem; opacity:.76; margin-top:.1rem; max-width:760px;}
.sf-card {border:1px solid rgba(128,128,128,.22); border-radius:16px; padding:1rem 1.05rem; min-height:126px; background:rgba(128,128,128,.035);}
.sf-card b {font-size:1rem;}
.sf-card p {margin:.42rem 0 0 0; opacity:.76; line-height:1.45;}
.sf-health {border:1px solid rgba(128,128,128,.22); border-radius:16px; padding:1rem 1.1rem; margin:.2rem 0 1rem 0;}
.sf-health-title {font-size:1.05rem; font-weight:750;}
.sf-muted {opacity:.70;}
div[data-testid="stFileUploader"] section {border-radius:14px;}
div[data-testid="stButton"] button[kind="primary"] {font-weight:700; min-height:3rem;}
</style>
""",
    unsafe_allow_html=True,
)


def _clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def _clean_number(value):
    try:
        x = float(_clean_text(value))
        if not pd.notna(x):
            return None
        return round(x, 2)
    except Exception:
        return None


def load_crate_hackers_pdf(file):
    """Read a modern Crate Hackers playlist PDF directly from its table layout."""
    rows = []
    playlist_title = ""
    file.seek(0)
    with pdfplumber.open(file) as pdf:
        if pdf.pages:
            first_text = pdf.pages[0].extract_text() or ""
            lines = [_clean_text(x) for x in first_text.splitlines() if _clean_text(x)]
            if lines:
                playlist_title = lines[0]
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header = [_clean_text(x).lower() for x in table[0]]
                if not ({"title", "artist", "bpm", "danceability", "energy", "mood"} <= set(header)):
                    continue
                for raw in table[1:]:
                    cells = dict(zip(header, raw))
                    number, title, artist, bpm, key, dance, energy, mood = (
                        cells.get(c) for c in ("#", "title", "artist", "bpm", "key", "danceability", "energy", "mood")
                    )
                    if not _clean_text(title) or not _clean_text(artist):
                        continue
                    rows.append({
                        "#": _clean_number(number),
                        "Title": _clean_text(title),
                        "Artist": _clean_text(artist),
                        "BPM": _clean_number(bpm),
                        "Camelot Key": _clean_text(key).upper(),
                        "Danceability": _clean_number(dance),
                        "Energy": _clean_number(energy),
                        "Mood": _clean_number(mood),
                        "Genre Family": _clean_text(cells.get("genre family", "")),
                        "Genre": _clean_text(cells.get("genre", cells.get("genres", ""))),
                    })
    if not rows:
        raise ValueError("No Crate Hackers playlist table was found in this PDF.")
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["#", "Title", "Artist"], keep="first").reset_index(drop=True)
    df.attrs["playlist_title"] = playlist_title
    return df


def normalize_columns(df):
    """Accept common playlist-export header variants without changing the optimizer schema."""
    aliases = {
        "title": "Title",
        "artist": "Artist",
        "bpm": "BPM",
        "camelot key": "Camelot Key",
        "camelot": "Camelot Key",
        "energy": "Energy",
        "dance": "Danceability",
        "danceability": "Danceability",
        "valence": "Valence",
        "acousticness": "Acousticness",
        "loudness lufs": "Loudness LUFS",
        "pop.": "Popularity",
        "pop": "Popularity",
        "popularity": "Popularity",
        "genre family": "Genre Family",
        "genre": "Genre",
        "genres": "Genre",
        "location": "File",
    }
    df = df.copy()
    df.columns = [aliases.get(str(c).strip().lower(), str(c).strip()) for c in df.columns]
    return df


def load_playlist(file):
    name = file.name.lower()
    if name.endswith(".pdf"):
        return normalize_columns(load_crate_hackers_pdf(file))
    if name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return normalize_columns(df)


def set_health(avg_score, weak, hard_bpm, max_bpm_diff, adjacent_artist, programming):
    if hard_bpm > 0:
        return "Needs Review", "A hard BPM jump remains. Check transition details before performing."
    if weak == 0 and adjacent_artist == 0 and avg_score >= 82 and programming >= 75:
        return "Excellent", "Tempo-safe, clean artist spacing, and no weak transitions."
    if weak <= 2 and adjacent_artist == 0 and avg_score >= 78:
        return "Strong", "Performance-ready route with only a couple of transitions worth previewing."
    if weak <= 4 and avg_score >= 74:
        return "Good", "Solid route. Preview the weak links and make any taste-based edits you want."
    return "Review", "The route is usable, but several transitions deserve a manual listen."


with st.sidebar:
    st.markdown("### 🎚️ Mixweave 1.4.5")
    st.caption("Whole-set DJ sequencing")

    mode = st.segmented_control("Preset", ["Smooth", "Balanced", "Harmonic"], default="Balanced")
    defaults = {
        "Smooth": (0.45, 0.55),
        "Balanced": (0.60, 0.40),
        "Harmonic": (0.75, 0.25),
    }
    kw, bw = defaults.get(mode, (0.60, 0.40))

    st.markdown("#### Mixing Brain")
    key_pct = st.slider(
        "Key preference",
        0,
        100,
        int(kw * 100),
        5,
        help="Inside a safe BPM neighborhood, how much should Camelot harmony matter?",
    )
    bpm_pct = 100 - key_pct
    st.caption(f"Inside a safe tempo zone: Key {key_pct}% • BPM {bpm_pct}%")

    bpm_tolerance = st.slider("Ideal BPM tolerance", 1, 12, 4, 1)
    bpm_guardrail = st.slider(
        "BPM guardrail",
        5,
        16,
        8,
        1,
        help="Beyond this difference, a great Camelot match cannot rescue the transition.",
    )

    with st.expander("Mixing safety", expanded=False):
        half_double = st.checkbox("Allow half / double tempo as a last resort", value=True)
        escape_mode = st.checkbox(
            "BPM Escape Mode",
            value=True,
            help="When key harmony is awkward, prefer practical tempo placement.",
        )
        bpm_spine = st.checkbox(
            "BPM Bridge Planner",
            value=True,
            help="Protects bridge tracks so tempo islands do not create a cliff later in the set.",
        )
        min_target = st.slider("Minimum transition target", 40, 80, 60, 5)
        half_double_penalty = st.slider("Half/double caution", 0, 20, 10, 2, help="Demotes half/double-time matches when a normal-tempo route is available.") / 100.0
        energy_cliff_threshold = st.slider("Energy cliff threshold", 10, 35, 20, 5, help="Downward Energy change that starts receiving a strong penalty.")

    st.markdown("#### Programming Brain")
    energy_arc = st.selectbox(
        "Energy program",
        ["Party Zones", "Build Zones", "Smooth", "Off"],
        index=0,
        help="Party Zones = Warm-up → Groove → Build → Peak → Finish.",
    )
    energy_arc_influence = st.slider(
        "Energy Zone influence",
        0,
        50,
        25,
        5,
        help="Soft whole-set programming preference. BPM safety still wins.",
    ) / 100.0

    artist_rule = st.select_slider(
        "Artist spacing", options=["Off", "Light", "Normal", "Strong"], value="Normal"
    )
    artist_penalty = {"Off": 0.0, "Light": 0.04, "Normal": 0.08, "Strong": 0.14}[artist_rule]

    genre_rule = st.segmented_control(
        "Genre pockets", ["Off", "Light", "Normal", "Strong"], default="Normal",
        help="Keep compatible tracks in sustained genre runs. The final pass preserves BPM safety, weak-link counts, artist spacing, and energy guardrails.")
    genre_influence = {"Off": 0.0, "Light": 0.10, "Normal": 0.20, "Strong": 0.30}.get(genre_rule, 0.20)

    with st.expander("Fine-tune the set", expanded=False):
        energy_mode = st.selectbox("Adjacent energy", ["Smooth", "Build"], index=0)
        energy_influence = st.slider("Adjacent Energy influence", 0, 40, 10, 5) / 100.0

        st.markdown("**Vibe tie-breaker**")
        vibe_mode = st.segmented_control(
            "Danceability + Valence", ["Off", "Light", "Normal"], default="Light"
        )
        vibe_defaults = {"Off": (0, 0), "Light": (5, 5), "Normal": (10, 8)}
        dv, vv = vibe_defaults.get(vibe_mode, (5, 5))
        danceability_influence = st.slider(
            "Danceability influence", 0, 15, dv, 1,
            help="Tie-breaker only. It cannot override BPM safety or Energy Zones."
        ) / 100.0
        valence_influence = st.slider(
            "Valence influence", 0, 15, vv, 1,
            help="Tie-breaker only. Helps reduce abrupt mood whiplash."
        ) / 100.0

        depth = st.selectbox("Optimization depth", ["Quick", "Standard", "Deep"], index=1)
        lock_first = st.checkbox("Lock first track", value=False)
        lock_last = st.checkbox("Lock last track", value=False)

st.markdown('<div class="sf-hero">', unsafe_allow_html=True)
st.markdown('<div class="sf-eyebrow">DJ playlist optimizer</div>', unsafe_allow_html=True)
st.title("🎚️ Mixweave")
st.markdown(
    '<div class="sf-tagline">Make it mixable first. Make it harmonic second. Make the whole set flow.</div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Upload a playlist", type=["pdf", "xlsx", "xls", "csv"])
st.caption("Required: Title, Artist, BPM, Camelot Key, Energy  •  Optional: Danceability, Valence, Acousticness, Loudness LUFS, Popularity")

required = ["Title", "Artist", "BPM", "Camelot Key", "Energy"]

if not uploaded:
    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="sf-card"><b>🎛️ Mixing Brain</b><p>Builds a tempo-safe route first, then uses Camelot harmony inside practical BPM neighborhoods.</p></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="sf-card"><b>📈 Programming Brain</b><p>Shapes broad Energy Zones and spaces artists so the playlist feels like a set, not a spreadsheet.</p></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="sf-card"><b>✨ Vibe Polish</b><p>Danceability and Valence break close ties without steering BPM, Camelot, or the energy plan.</p></div>',
            unsafe_allow_html=True,
        )
    st.caption("Tip: the Balanced preset + Party Zones is the recommended starting point.")
    st.stop()

try:
    df = load_playlist(uploaded)
except Exception as e:
    st.error(f"Could not read that file: {e}")
    st.stop()

with st.expander("Add Essentia analysis", expanded=False):
    st.caption("Upload the scanner results CSV to add scores to this playlist. Existing BPM, key, and energy stay as supplied.")
    analysis_file = st.file_uploader("Scanner results", type=["csv"], key="essentia_analysis")
    if analysis_file:
        try:
            df = attach_features(df, normalize_columns(pd.read_csv(analysis_file)))
        except ValueError as e:
            st.error(str(e))
            st.stop()
        matched = df["Essentia Match"].isin(["Exact file", "Artist/title — recording unverified", "Garth Brooks version — performer differs"]).sum()
        st.caption(f"{matched}/{len(df)} tracks received Essentia scores. Review the matches below.")
        st.dataframe(df[["Title", "Artist", "Essentia Match", "Essentia File"]] if "Essentia File" in df else df[["Title", "Artist", "Essentia Match"]], hide_index=True, width="stretch")
        st.caption("Artist/title matches do not confirm the same recording. When several edits exist, add the exact scanner File path to your playlist.")

missing = [c for c in required if c not in df.columns]
if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.info("Mixweave needs: Title, Artist, BPM, Camelot Key, Energy.")
    st.stop()

st.subheader("Playlist ready")
meta1, meta2, meta3 = st.columns(3)
meta1.metric("Tracks", len(df))

invalid_keys = ~df["Camelot Key"].astype(str).str.upper().str.match(r"^(1[0-2]|[1-9])[AB](?:/(?:1[0-2]|[1-9])[AB])*$")
meta2.metric("Valid Camelot keys", f"{len(df) - int(invalid_keys.sum())}/{len(df)}")

energy_num = pd.to_numeric(df["Energy"], errors="coerce")
suspicious_energy = energy_num.isna() | (energy_num <= 0) | (energy_num > 100)
meta3.metric("Usable Energy", f"{len(df) - int(suspicious_energy.sum())}/{len(df)}")

optional = [c for c in ["Danceability", "Valence", "Acousticness", "Loudness LUFS", "Popularity", "Genre Family"] if c in df.columns]
if optional:
    st.caption("Optional metadata detected: " + " • ".join(optional))
if invalid_keys.any():
    st.warning(f"{int(invalid_keys.sum())} track(s) have missing or invalid Camelot keys. Key scoring will stay neutral for those tracks.")
if df["Camelot Key"].astype(str).str.contains("/", regex=False).any():
    st.caption("Slash-separated keys indicate a key change. They are preserved; harmonic scoring stays neutral for those tracks.")
if suspicious_energy.any():
    st.info(f"{int(suspicious_energy.sum())} track(s) have missing/suspicious Energy values. SetFlow treats those as neutral, not literal zero.")
if vibe_mode != "Off":
    missing_optional = [c for c in ["Danceability", "Valence"] if c not in df.columns]
    if missing_optional:
        st.caption("Vibe tie-breaker: " + ", ".join(missing_optional) + " missing — neutral scoring will be used.")


with st.expander("Import Rekordbox genres", expanded=False):
    st.caption("Upload your exported Rekordbox collection XML. Saved genres will fill missing labels; existing genre choices stay intact.")
    genre_xml = st.file_uploader("Rekordbox collection", type=["xml"], key="rekordbox_genres")
    if genre_xml:
        try:
            collection = RekordboxGenres(io.BytesIO(genre_xml.getvalue()))
            if "Genre" not in df:
                df["Genre"] = ""
            df["Genre"] = df["Genre"].fillna("").astype(str)
            for idx, track in df.iterrows():
                if track["Genre"].strip():
                    continue
                genre, source = collection.lookup(
                    path=next((str(v) for v in [track.get("File"), track.get("Essentia File")] if pd.notna(v) and str(v).strip()), ""),
                    title=track.get("Title", ""), artist=track.get("Artist", ""))
                if genre:
                    df.at[idx, "Genre"] = genre
                df.at[idx, "Genre Source"] = source
        except ValueError as error:
            st.error(str(error))

st.subheader("Genre Families")
if "Genre Family" not in df.columns:
    df["Genre Family"] = ""

df["Genre Family"] = df["Genre Family"].fillna("").astype(str)
if "Genre" in df:
    missing_family = df["Genre Family"].str.strip().eq("")
    df.loc[missing_family, "Genre Family"] = df.loc[missing_family, "Genre"].fillna("").map(genre_family)
classified = int(df["Genre Family"].str.strip().ne("").sum())
st.caption(f"{classified}/{len(df)} tracks have a genre family. Recognized genres are filled automatically; review any blanks below.")

with st.expander("Review or assign genre families", expanded=classified < len(df)):
    genre_editor = st.data_editor(
        df[["Title", "Artist", "Genre Family"]],
        hide_index=True,
        disabled=["Title", "Artist"],
        width="stretch",
        column_config={
            "Genre Family": st.column_config.SelectboxColumn(
                "Genre Family", options=[""] + GENRE_FAMILIES + sorted(set(df["Genre Family"]) - set(GENRE_FAMILIES) - {""})
            )
        },
        key="genre_editor_" + hashlib.sha256(uploaded.getvalue()).hexdigest(),
    )
    df["Genre Family"] = genre_editor["Genre Family"].fillna("")
    st.caption("Use your DJ judgment for crossover tracks. These Genre Family choices are passed into the Mixweave optimizer.")

with st.expander("Two-song artist runs", expanded=False):
    artist_counts = df["Artist"].fillna("").str.strip().value_counts()
    artist_run_bridges = st.checkbox("Allow stems or cuts within artist runs", value=False,
                                      help="For selected artists only. Suggest a vocal stem bridge or clean cut even when full-track BPM/key matching is awkward. MixWeave does not render stems or audio. Other set transitions retain the mixing limits.")
    run_artists = st.multiselect("Artists to pair for a quick mix",
                                sorted(a for a, n in artist_counts.items() if a and n == 2),
                                help="Optional. Try a two-song run for selected artists when genre, native BPM, key, and placement checks permit it. A pair is not guaranteed.")

with st.expander("Plan the opening", expanded=False):
    st.caption("Choose your opener and songs to save until after the warm-up (the first 18% of the set). These are required placements. If they cannot be met within your mixing limits, Mixweave will ask you to revise the choices instead of exporting an incorrect order.")
    track_options = list(range(len(df)))
    def track_label(index):
        if index is None:
            return "Let Mixweave choose"
        row = df.iloc[index]
        return f"{index + 1}. {row['Title']} — {row['Artist']}"
    saved_opener = next((i for i, value in enumerate(df.get("Set Role", [])) if value == "Opener"), None)
    opener = st.selectbox("Opening track", [None] + track_options, format_func=track_label,
                          index=0 if saved_opener is None else saved_opener + 1)
    deferred = st.multiselect("Save until after warm-up", track_options,
                             format_func=track_label,
                             default=[i for i, value in enumerate(df.get("Set Role", [])) if value == "After warm-up"])
    opening_reset = st.checkbox("Allow one deliberate reset for placements or artist runs", value=False,
                               help="An opening placement or selected artist pair may need a clean cut or fade. At most one reset is allowed. Any reset is labeled in the result; BPM and transition scores stay unchanged.")
    if opener in deferred:
        st.warning("The opener cannot also be saved for later. Its opener choice takes priority.")
    df["Set Role"] = ["Opener" if i == opener else ("After warm-up" if i in deferred else "Automatic") for i in track_options]

with st.expander("Preview uploaded playlist", expanded=False):
    st.dataframe(df, width="stretch", hide_index=True)

if st.button("⚡ Build my Mixweave set", type="primary", width="stretch"):
    records = df.to_dict(orient="records")
    settings = Settings(
        key_weight=key_pct / 100.0,
        bpm_weight=bpm_pct / 100.0,
        bpm_tolerance=float(bpm_tolerance),
        bpm_guardrail=float(bpm_guardrail),
        allow_half_double=half_double,
        escape_mode=escape_mode,
        bpm_spine=bpm_spine,
        min_transition_target=float(min_target),
        half_double_penalty=half_double_penalty,
        energy_cliff_threshold=float(energy_cliff_threshold),
        energy_influence=energy_influence,
        energy_mode=energy_mode,
        energy_arc=energy_arc,
        energy_arc_influence=energy_arc_influence,
        artist_spacing=artist_penalty,
        artist_runs=tuple(run_artists),
        artist_run_bridges=artist_run_bridges,
        genre_pockets=genre_rule != "Off",
        genre_pocket_influence=genre_influence,
        danceability_influence=danceability_influence,
        valence_influence=valence_influence,
        depth=depth,
        lock_first=lock_first or opener is not None,
        allow_opening_reset=opening_reset,
        lock_last=lock_last,
    )

    try:
        with st.spinner("Mixweave is planning the whole set…"):
            ordered, transitions = optimize(records, settings)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    out = pd.DataFrame(ordered).drop(columns=["Mixweave #"], errors="ignore").copy()
    out.insert(0, "Mixweave #", range(1, len(out) + 1))
    out["Transition Score"] = [None] + [t["score"] for t in transitions]
    out["Transition Reason"] = ["OPEN"] + [t["reason"] for t in transitions]
    out["Transition Quality"] = ["OPEN"] + [t["quality"] for t in transitions]
    out["Camelot Move"] = [None] + [t["camelot_relationship"] for t in transitions]
    out["Effective BPM Δ"] = [None] + [t["bpm_diff"] for t in transitions]
    out["Program Zone"] = energy_zone_labels(ordered, settings)

    avg_score = sum(t["score"] for t in transitions) / max(len(transitions), 1)
    weak = sum(1 for t in transitions if t["score"] < min_target)
    great = sum(1 for t in transitions if t["score"] >= 85)
    bad_bpm = sum(1 for t in transitions if t["bpm_zone"] in ("Hard BPM Jump", "BPM Incompatible"))
    bpm_diffs = [t["bpm_diff"] for t in transitions if t["bpm_diff"] is not None]
    max_bpm_diff = max(bpm_diffs) if bpm_diffs else 0.0
    arc = energy_arc_details(ordered, settings)
    vibe = vibe_program_details(ordered, settings)
    if run_artists:
        paired_artists = {str(a.get("Artist", "")).strip()
                          for a, b in zip(ordered, ordered[1:])
                          if str(a.get("Artist", "")).strip() == str(b.get("Artist", "")).strip()
                          and str(a.get("Artist", "")).strip() in run_artists}
        if paired_artists:
            st.caption("Two-song artist runs: " + ", ".join(sorted(paired_artists)))
        unpaired_artists = set(run_artists) - paired_artists
        if unpaired_artists:
            st.info("No acceptable two-song placement found for: " + ", ".join(sorted(unpaired_artists)) + ". These songs retain normal spacing.")
    adjacent_artist, near_artist = artist_spacing_stats(ordered, settings)
    health, health_note = set_health(avg_score, weak, bad_bpm, max_bpm_diff, adjacent_artist, arc["score"])

    genre_before, genre_after = genre_pocket_stats(records), genre_pocket_stats(ordered)
    pocket_labels = []
    pocket_number = 0
    last_family = ""
    for track in ordered:
        family = track_genre_family(track)
        if family and family != last_family:
            pocket_number += 1
        pocket_labels.append(pocket_number if family else None)
        last_family = family
    out["Genre Pocket"] = pocket_labels
    st.caption(f"Genre pockets (2–4 tracks): {genre_before['pockets']} → {genre_after['pockets']} • Isolated genre tracks: {genre_before['islands']} → {genre_after['islands']}")
    st.success("Mixweave complete.")
    if opening_later_count(ordered):
        st.warning("Some songs saved for later remain in the warm-up. The planner could not move them within the tempo-reset and genre limits; review the opening.")
    resets = sum(t["quality"] == "Deliberate reset" for t in transitions)
    if resets:
        st.info("One deliberate reset is marked below. Use a clean cut or fade at that transition.")
    st.markdown(
        f'<div class="sf-health"><div class="sf-health-title">Set Health: {health}</div><div class="sf-muted">{health_note}</div></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Avg transition", f"{avg_score:.1f}")
    c2.metric("Weak links", weak)
    c3.metric("Hard BPM jumps", bad_bpm)
    c4.metric("Worst BPM Δ", f"{max_bpm_diff:.1f}")
    c5.metric("Programming", f"{arc['score']:.1f}")
    c6.metric("Artist collisions", adjacent_artist)

    qualities = pd.Series([t["quality"] for t in transitions]).value_counts().to_dict()
    st.caption(
        "Route quality: "
        + " • ".join(
            [
                f"Excellent {qualities.get('Excellent', 0)}",
                f"Good {qualities.get('Good', 0)}",
                f"DJ Workable {qualities.get('DJ Workable', 0)}",
                f"BPM Escape {qualities.get('BPM Escape', 0)}",
                f"Weak {qualities.get('Weak', 0)}",
            ]
        )
    )
    if energy_arc != "Off":
        st.caption(
            f"Energy: start {arc['start']} • peak {arc['peak']} at track {arc.get('peak_position', '—')} • "
            f"finish {arc['finish']} • Vibe {vibe['score']:.1f} • near artist repeats {near_artist}"
        )

    if bad_bpm:
        st.warning("A hard BPM transition remains. Review that link before performing the set.")
    elif weak == 0:
        st.info("No transitions fell below your minimum target.")

    st.subheader("Optimized running order")
    show_cols = ["Mixweave #", "Title", "Artist", "BPM", "Camelot Key", "Energy"]
    for col in ["Set Role", "Genre", "Genre Family", "Genre Pocket", "Danceability", "Valence", "Acousticness", "Loudness LUFS"]:
        if col in out.columns:
            show_cols.append(col)
    show_cols += ["Program Zone", "Transition Score", "Transition Quality", "Transition Reason", "Effective BPM Δ"]
    st.dataframe(out[show_cols], width="stretch", hide_index=True, column_config={
        **{c: st.column_config.NumberColumn(c, format="%.0f") for c in ["Danceability", "Valence", "Acousticness"]},
        "Loudness LUFS": st.column_config.NumberColumn("Loudness (LUFS)", format="%.1f"),
    })

    with st.expander("Transition details"):
        detail_rows = []
        for i, t in enumerate(transitions):
            detail_rows.append(
                {
                    "From": ordered[i]["Title"],
                    "To": ordered[i + 1]["Title"],
                    "Score": t["score"],
                    "Quality": t["quality"],
                    "Reason": t["reason"],
                    "Camelot move": t["camelot_relationship"],
                    "BPM zone": t["bpm_zone"],
                    "Tempo mode": t["tempo_mode"],
                    "Effective BPM Δ": t["bpm_diff"],
                    "Key score": t["key_score"],
                    "BPM score": t["bpm_score"],
                    "Energy score": t["energy_score"],
                    "Energy drop": t.get("energy_drop"),
                    "Energy cliff": t.get("energy_cliff"),
                    "Same genre family": t.get("same_genre_family"),
                    "Same artist": t["same_artist"],
                }
            )
        st.dataframe(pd.DataFrame(detail_rows), width="stretch", hide_index=True)

    d1, d2 = st.columns(2)
    csv_bytes = out.to_csv(index=False).encode("utf-8")
    d1.download_button(
        "Download CSV",
        csv_bytes,
        file_name="Mixweave_v1.4.5_optimized_playlist.csv",
        mime="text/csv",
        width="stretch",
    )

    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="SetFlow Order")
    d2.download_button(
        "Download Excel",
        xbuf.getvalue(),
        file_name="Mixweave_v1.4.5_optimized_playlist.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
