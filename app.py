import io
import hashlib
import re
import pandas as pd
import pdfplumber
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from optimizer import (
    Settings,
    optimize,
    energy_arc_details,
    energy_zone_labels,
    artist_spacing_stats,
    vibe_program_details,
    energy_flow_stats,
    GENRE_FAMILIES, genre_family, genre_pocket_stats,
)

APP_NAME = "Mixweave"
APP_VERSION = "1.2"

st.set_page_config(page_title=f"{APP_NAME} {APP_VERSION}", page_icon="🎚️", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1420px;}
h1 {letter-spacing: -0.045em; margin-bottom: .15rem;}
h2, h3 {letter-spacing: -0.02em;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.15);}
.mw-eyebrow {font-size:.82rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; opacity:.65;}
.mw-hero {padding:.1rem 0 .45rem 0;}
.mw-tagline {font-size:1.08rem; opacity:.76; margin-top:.1rem; max-width:760px;}
.mw-card {border:1px solid rgba(128,128,128,.22); border-radius:16px; padding:1rem 1.05rem; min-height:126px; background:rgba(128,128,128,.035);}
.mw-card b {font-size:1rem;}
.mw-card p {margin:.42rem 0 0 0; opacity:.76; line-height:1.45;}
.mw-health {border:1px solid rgba(128,128,128,.22); border-radius:16px; padding:1rem 1.1rem; margin:.2rem 0 1rem 0;}
.mw-health-title {font-size:1.05rem; font-weight:750;}
.mw-muted {opacity:.70;}
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


def normalize_columns(df):
    """Accept Mixweave and common playlist-export header variants."""
    aliases = {
        "title": "Title",
        "artist": "Artist",
        "bpm": "BPM",
        "key": "Camelot Key",
        "camelot key": "Camelot Key",
        "camelot": "Camelot Key",
        "energy": "Energy",
        "dance": "Danceability",
        "danceability": "Danceability",
        "mood": "Mood",
        "valence": "Mood",
        "pop.": "Popularity",
        "pop": "Popularity",
        "popularity": "Popularity",
        "genre": "Genre",
        "genres": "Genre",
        "genre family": "Genre Family",
    }
    attrs = dict(getattr(df, "attrs", {}))
    df = df.copy()
    df.columns = [aliases.get(_clean_text(c).lower(), _clean_text(c)) for c in df.columns]
    df.attrs.update(attrs)
    return df


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
                # Crate Hackers prints the playlist title as the first line, before "Hacked by:".
                playlist_title = lines[0]
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header = [_clean_text(x).lower() for x in table[0]]
                # Crate Hackers currently exports 8 columns in this order.
                if not ({"title", "artist", "bpm", "danceability", "energy", "mood"} <= set(header)):
                    continue
                for raw in table[1:]:
                    cells = dict(zip(header, raw))
                    number, title, artist, bpm, key, dance, energy, mood = (
                        cells.get(c) for c in ("#", "title", "artist", "bpm", "key", "danceability", "energy", "mood")
                    )
                    if not _clean_text(title) or not _clean_text(artist):
                        continue
                    rows.append(
                        {
                            "#": _clean_number(number),
                            "Title": _clean_text(title),
                            "Artist": _clean_text(artist),
                            "BPM": _clean_number(bpm),
                            "Camelot Key": _clean_text(key).upper(),
                            "Danceability": _clean_number(dance),
                            "Energy": _clean_number(energy),
                            "Mood": _clean_number(mood),
                            "Genre": _clean_text(cells.get("genre", cells.get("genres", ""))),
                        }
                    )
    if not rows:
        raise ValueError("No Crate Hackers playlist table was found in this PDF.")
    df = pd.DataFrame(rows)
    # Remove page-boundary duplicates if a PDF renderer repeats a row.
    subset = ["#", "Title", "Artist"]
    df = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)
    df.attrs["playlist_title"] = playlist_title
    return df


def load_playlist(file):
    name = file.name.lower()
    if name.endswith(".pdf"):
        return normalize_columns(load_crate_hackers_pdf(file)), "Crate Hackers PDF"
    if name.endswith(".csv"):
        df = pd.read_csv(file)
        return normalize_columns(df), "CSV"
    df = pd.read_excel(file)
    return normalize_columns(df), "Excel"



def _pdf_safe(value):
    """Keep ReportLab's built-in fonts happy with common DJ metadata."""
    text = _clean_text(value)
    swaps = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
    }
    for old, new in swaps.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def _safe_filename(value):
    text = _clean_text(value) or "Playlist"
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
    return text[:120] or "Playlist"


def build_mixweave_pdf(out, playlist_title, health, health_note, avg_score, weak, bad_bpm, max_bpm_diff, programming, flow):
    """Create the clean DJ-facing Mixweave running-order PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
        title=f"{playlist_title} - Mixweave {APP_VERSION} Optimized Running Order",
        author="Mixweave",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MWTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=23, alignment=TA_CENTER, spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "MWSub", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.5, leading=12, alignment=TA_CENTER, spaceAfter=10,
    )
    cell = ParagraphStyle("MWCell", parent=styles["BodyText"], fontSize=7.2, leading=8.4)
    cell_center = ParagraphStyle("MWCellCenter", parent=cell, alignment=TA_CENTER)
    head = ParagraphStyle("MWHead", parent=cell_center, fontName="Helvetica-Bold", textColor=colors.white)

    story = [
        Paragraph(_pdf_safe(playlist_title), title_style),
        Paragraph(f"Mixweave {APP_VERSION} - Optimized Running Order", sub_style),
        Paragraph(
            _pdf_safe(
                f"Set Health: {health} | Avg transition {avg_score:.1f} | Weak links {weak} | "
                f"Hard BPM jumps {bad_bpm} | Worst BPM delta {max_bpm_diff:.1f} | "
                f"Programming {programming:.1f} | Energy flow {flow:.1f}"
            ),
            sub_style,
        ),
        Paragraph(_pdf_safe(health_note), sub_style),
        Spacer(1, 4),
    ]

    cols = ["Mixweave #", "Title", "Artist", "BPM", "Camelot Key", "Energy", "Danceability", "Mood", "Program Zone"]
    headers = ["#", "Title", "Artist", "BPM", "Key", "Energy", "Dance", "Mood", "Zone"]
    data = [[Paragraph(h, head) for h in headers]]
    for _, row in out.iterrows():
        vals = []
        for col in cols:
            value = row.get(col, "")
            if pd.isna(value):
                value = ""
            if col in ("BPM", "Energy", "Danceability", "Mood") and value != "":
                try:
                    f = float(value)
                    value = f"{f:.0f}" if abs(f - round(f)) < 0.01 else f"{f:.1f}"
                except Exception:
                    pass
            style = cell_center if col not in ("Title", "Artist") else cell
            vals.append(Paragraph(_pdf_safe(value), style))
        data.append(vals)

    table = Table(
        data,
        repeatRows=1,
        colWidths=[34, 170, 128, 42, 46, 48, 48, 46, 62],
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20252B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DADF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F5F7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()


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
    st.markdown(f"### 🎚️ {APP_NAME} {APP_VERSION}")
    st.caption("Whole-set DJ sequencing")

    mode = st.segmented_control("Preset", ["Smooth", "Balanced", "Harmonic"], default="Balanced")
    defaults = {"Smooth": (0.45, 0.55), "Balanced": (0.60, 0.40), "Harmonic": (0.75, 0.25)}
    kw, bw = defaults.get(mode, (0.60, 0.40))

    st.markdown("#### Mixing Brain")
    key_pct = st.slider("Key preference", 0, 100, int(kw * 100), 5,
                        help="Inside a safe BPM neighborhood, how much should Camelot harmony matter?")
    bpm_pct = 100 - key_pct
    st.caption(f"Inside a safe tempo zone: Key {key_pct}% • BPM {bpm_pct}%")

    bpm_tolerance = st.slider("Ideal BPM tolerance", 1, 12, 4, 1)
    bpm_guardrail = st.slider("BPM guardrail", 5, 16, 8, 1,
                              help="Beyond this difference, a great Camelot match cannot rescue the transition.")

    with st.expander("Mixing safety", expanded=False):
        half_double = st.checkbox("Allow half / double tempo matches", value=True)
        escape_mode = st.checkbox("BPM Escape Mode", value=True,
                                  help="When key harmony is awkward, prefer practical tempo placement.")
        bpm_spine = st.checkbox("BPM Bridge Planner", value=True,
                                help="Protects bridge tracks so tempo islands do not create a cliff later in the set.")
        min_target = st.slider("Minimum transition target", 40, 80, 60, 5)

    st.markdown("#### Programming Brain")
    energy_arc = st.selectbox("Energy program", ["Party Zones", "Build Zones", "Smooth", "Off"], index=0,
                              help="Party Zones = Warm-up → Groove → Build → Peak → Finish.")
    energy_arc_influence = st.slider("Energy Zone influence", 0, 50, 25, 5,
                                     help="Soft whole-set programming preference. BPM safety still wins.") / 100.0

    artist_rule = st.select_slider("Artist spacing", options=["Off", "Light", "Normal", "Strong"], value="Normal")
    artist_penalty = {"Off": 0.0, "Light": 0.04, "Normal": 0.08, "Strong": 0.14}[artist_rule]
    genre_rule = st.select_slider("Genre Pockets", options=["Off", "Light", "Normal", "Strong"], value="Normal",
                                   help="Prefers 2–4 track runs, centered on three. BPM safety still wins.")
    genre_influence = {"Off": 0.0, "Light": 0.08, "Normal": 0.15, "Strong": 0.24}[genre_rule]

    with st.expander("Fine-tune the set", expanded=False):
        energy_mode = st.selectbox("Adjacent energy", ["Smooth", "Build"], index=0)
        energy_influence = st.slider("Adjacent Energy influence", 0, 40, 10, 5) / 100.0

        st.markdown("**Vibe tie-breaker**")
        vibe_mode = st.segmented_control("Danceability + Mood", ["Off", "Light", "Normal"], default="Light")
        vibe_defaults = {"Off": (0, 0), "Light": (5, 5), "Normal": (10, 8)}
        dv, mv = vibe_defaults.get(vibe_mode, (5, 5))
        danceability_influence = st.slider("Danceability influence", 0, 15, dv, 1,
                                           help="Tie-breaker only. It cannot override BPM safety or Energy Zones.") / 100.0
        mood_influence = st.slider("Mood influence", 0, 15, mv, 1,
                                   help="Tie-breaker only. Helps reduce abrupt emotional whiplash.") / 100.0

        depth = st.selectbox("Optimization depth", ["Quick", "Standard", "Deep"], index=1)
        lock_first = st.checkbox("Lock first track", value=False)
        lock_last = st.checkbox("Lock last track", value=False)

st.markdown('<div class="mw-hero">', unsafe_allow_html=True)
st.markdown('<div class="mw-eyebrow">DJ playlist optimizer</div>', unsafe_allow_html=True)
st.title("🎚️ Mixweave")
st.markdown('<div class="mw-tagline">Make it mixable first. Make it harmonic second. Make the whole set flow.</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Upload a playlist", type=["pdf", "xlsx", "xls", "csv"])
st.caption("Best: Crate Hackers PDF  •  Also supports CSV/XLS/XLSX")
st.caption("Uses: Title • Artist • BPM • Camelot Key • Energy • Danceability • Mood")

required = ["Title", "Artist", "BPM", "Camelot Key", "Energy"]

if not uploaded:
    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="mw-card"><b>🎛️ Mixing Brain</b><p>Builds a tempo-safe route first, then uses Camelot harmony inside practical BPM neighborhoods.</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="mw-card"><b>📈 Programming Brain</b><p>Shapes broad Energy Zones and spaces artists so the playlist feels like a set, not a spreadsheet.</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="mw-card"><b>✨ Vibe Polish</b><p>Danceability and Mood break close ties without steering BPM, Camelot, or the energy plan.</p></div>', unsafe_allow_html=True)
    st.caption("Tip: Export your finished crate from Crate Hackers as PDF, then drop it here.")
    st.stop()

try:
    df, import_type = load_playlist(uploaded)
    playlist_title = _clean_text(df.attrs.get("playlist_title", ""))
    if not playlist_title:
        playlist_title = re.sub(r"\.(pdf|csv|xlsx|xls)$", "", uploaded.name, flags=re.I)
except Exception as e:
    st.error(f"Could not read that file: {e}")
    if uploaded.name.lower().endswith(".pdf"):
        st.info("Mixweave currently expects the Crate Hackers playlist PDF table format.")
    st.stop()

missing = [c for c in required if c not in df.columns]
if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.info("Mixweave needs: Title, Artist, BPM, Camelot Key, Energy.")
    st.stop()

st.subheader("Playlist ready")
meta1, meta2, meta3, meta4 = st.columns(4)
meta1.metric("Tracks", len(df))
meta2.metric("Import", import_type)

invalid_keys = ~df["Camelot Key"].astype(str).str.upper().str.match(r"^(1[0-2]|[1-9])[AB]$")
meta3.metric("Valid Camelot keys", f"{len(df) - int(invalid_keys.sum())}/{len(df)}")

energy_num = pd.to_numeric(df["Energy"], errors="coerce")
suspicious_energy = energy_num.isna() | (energy_num <= 0) | (energy_num > 100)
meta4.metric("Usable Energy", f"{len(df) - int(suspicious_energy.sum())}/{len(df)}")

optional = [c for c in ["Danceability", "Mood", "Popularity"] if c in df.columns]
if optional:
    st.caption("Optional metadata detected: " + " • ".join(optional))
if invalid_keys.any():
    st.warning(f"{int(invalid_keys.sum())} track(s) have missing or non-Camelot keys. Harmonic scoring will stay neutral for those tracks.")
if suspicious_energy.any():
    st.info(f"{int(suspicious_energy.sum())} track(s) have missing/suspicious Energy values. Mixweave treats those as neutral, not literal zero.")
if vibe_mode != "Off":
    missing_optional = [c for c in ["Danceability", "Mood"] if c not in df.columns]
    if missing_optional:
        st.caption("Vibe tie-breaker: " + ", ".join(missing_optional) + " missing — neutral scoring will be used.")

st.subheader("Genre Pockets")
if "Genre Family" not in df.columns:
    df["Genre Family"] = df.get("Genre", pd.Series("", index=df.index)).fillna("").map(genre_family)
else:
    df["Genre Family"] = df["Genre Family"].fillna("").map(genre_family)
classified = int(df["Genre Family"].ne("").sum())
st.caption(f"{classified}/{len(df)} tracks have a genre family. Blank entries stay neutral.")
if classified == 0:
    st.info("This playlist has no usable genre labels. Assign families below to use Genre Pockets. You can still optimize with the existing BPM, key and energy rules.")
with st.expander("Review or assign genre families", expanded=classified == 0):
    genres = st.data_editor(df[["Title", "Artist", "Genre Family"]], hide_index=True,
        disabled=["Title", "Artist"], width="stretch",
        column_config={"Genre Family": st.column_config.SelectboxColumn(
            "Genre Family", options=[""] + GENRE_FAMILIES)},
        key="genre_editor_" + hashlib.sha256(uploaded.getvalue()).hexdigest())
    df["Genre Family"] = genres["Genre Family"].fillna("")
    st.caption("Use your DJ judgment for crossover tracks. Excel and CSV exports retain these choices for reuse.")

with st.expander("Preview imported playlist", expanded=False):
    preview_cols = [c for c in ["#", "Title", "Artist", "BPM", "Camelot Key", "Danceability", "Energy", "Mood"] if c in df.columns]
    st.dataframe(df[preview_cols], width="stretch", hide_index=True)

if st.button("⚡ Build my Mixweave", type="primary", width="stretch"):
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
        energy_influence=energy_influence,
        energy_mode=energy_mode,
        energy_arc=energy_arc,
        energy_arc_influence=energy_arc_influence,
        artist_spacing=artist_penalty,
        genre_pockets=genre_rule != "Off",
        genre_pocket_influence=genre_influence,
        danceability_influence=danceability_influence,
        valence_influence=mood_influence,
        depth=depth,
        lock_first=lock_first,
        lock_last=lock_last,
    )

    with st.spinner("Mixweave is planning the whole set…"):
        ordered, transitions = optimize(records, settings)

    out = pd.DataFrame(ordered).copy()
    out = out.drop(columns=["#", "Mixweave #", "SetFlow #"], errors="ignore")
    out.insert(0, "Mixweave #", range(1, len(out) + 1))
    out["Transition Score"] = [None] + [t["score"] for t in transitions]
    out["Transition Reason"] = ["OPEN"] + [t["reason"] for t in transitions]
    out["Transition Quality"] = ["OPEN"] + [t["quality"] for t in transitions]
    out["Camelot Move"] = [None] + [t["camelot_relationship"] for t in transitions]
    out["Effective BPM Δ"] = [None] + [t["bpm_diff"] for t in transitions]
    out["Program Zone"] = energy_zone_labels(ordered, settings)

    avg_score = sum(t["score"] for t in transitions) / max(len(transitions), 1)
    weak = sum(1 for t in transitions if t["score"] < min_target)
    bad_bpm = sum(1 for t in transitions if t["bpm_zone"] in ("Hard BPM Jump", "BPM Incompatible"))
    bpm_diffs = [t["bpm_diff"] for t in transitions if t["bpm_diff"] is not None]
    max_bpm_diff = max(bpm_diffs) if bpm_diffs else 0.0
    arc = energy_arc_details(ordered, settings)
    vibe = vibe_program_details(ordered, settings)
    flow = energy_flow_stats(ordered, settings)
    adjacent_artist, near_artist = artist_spacing_stats(ordered)
    health, health_note = set_health(avg_score, weak, bad_bpm, max_bpm_diff, adjacent_artist, arc["score"])

    st.success("Mixweave complete.")
    genre_before, genre_after = genre_pocket_stats(records), genre_pocket_stats(ordered)
    st.caption(f"Genre islands: {genre_before['islands']} in uploaded order → {genre_after['islands']} in result. "
               f"2–4 track pockets: {genre_after['pockets']}. Genre Pockets: {genre_rule}.")
    st.markdown(f'<div class="mw-health"><div class="mw-health-title">Set Health: {health}</div><div class="mw-muted">{health_note}</div></div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Avg transition", f"{avg_score:.1f}")
    c2.metric("Weak links", weak)
    c3.metric("Hard BPM jumps", bad_bpm)
    c4.metric("Worst BPM Δ", f"{max_bpm_diff:.1f}")
    c5.metric("Programming", f"{arc['score']:.1f}")
    c6.metric("Artist collisions", adjacent_artist)

    qualities = pd.Series([t["quality"] for t in transitions]).value_counts().to_dict()
    st.caption("Route quality: " + " • ".join([
        f"Excellent {qualities.get('Excellent', 0)}",
        f"Good {qualities.get('Good', 0)}",
        f"DJ Workable {qualities.get('DJ Workable', 0)}",
        f"BPM Escape {qualities.get('BPM Escape', 0)}",
        f"Weak {qualities.get('Weak', 0)}",
    ]))
    if energy_arc != "Off":
        st.caption(
            f"Energy: start {arc['start']} • peak {arc['peak']} at track {arc.get('peak_position', '—')} • "
            f"finish {arc['finish']} • Energy flow {flow['score']:.1f} • whiplash flags {flow['whiplash']} • "
            f"Vibe {vibe['score']:.1f} • near artist repeats {near_artist}"
        )

    if bad_bpm:
        st.warning("A hard BPM transition remains. Review that link before performing the set.")
    elif weak == 0:
        st.info("No transitions fell below your minimum target.")

    st.subheader("Optimized running order")
    show_cols = ["Mixweave #", "Title", "Artist", "BPM", "Camelot Key", "Energy"]
    for col in ["Danceability", "Mood", "Genre Family"]:
        if col in out.columns:
            show_cols.append(col)
    show_cols += ["Program Zone", "Transition Score", "Transition Quality", "Transition Reason", "Effective BPM Δ"]
    st.dataframe(out[show_cols], width="stretch", hide_index=True)

    with st.expander("Transition details"):
        detail_rows = []
        for i, t in enumerate(transitions):
            detail_rows.append({
                "From": ordered[i]["Title"], "To": ordered[i + 1]["Title"],
                "Score": t["score"], "Quality": t["quality"], "Reason": t["reason"],
                "Camelot move": t["camelot_relationship"], "BPM zone": t["bpm_zone"],
                "Tempo mode": t["tempo_mode"], "Effective BPM Δ": t["bpm_diff"],
                "Key score": t["key_score"], "BPM score": t["bpm_score"],
                "Energy score": t["energy_score"], "Same artist": t["same_artist"],
            })
        st.dataframe(pd.DataFrame(detail_rows), width="stretch", hide_index=True)

    st.subheader("Export")
    export_base = f"{_safe_filename(playlist_title)}_Mixweave_v{APP_VERSION}"
    st.caption(f"Playlist: {playlist_title} • Mixweave v{APP_VERSION}")
    d1, d2 = st.columns(2)

    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="Mixweave Order")
    d1.download_button(
        "Download Excel",
        xbuf.getvalue(),
        file_name=f"{export_base}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    pdf_bytes = build_mixweave_pdf(
        out, playlist_title, health, health_note, avg_score, weak, bad_bpm,
        max_bpm_diff, arc["score"], flow["score"],
    )
    d2.download_button(
        "Download PDF",
        pdf_bytes,
        file_name=f"{export_base}.pdf",
        mime="application/pdf",
        width="stretch",
    )

    with st.expander("More export options", expanded=False):
        csv_bytes = out.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            csv_bytes,
            file_name=f"{export_base}.csv",
            mime="text/csv",
            width="stretch",
        )
