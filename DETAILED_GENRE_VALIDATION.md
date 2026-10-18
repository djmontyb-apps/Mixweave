# Detailed genre validation — MixWeave 1.4.6

The import/editor/export flow and route planner now retain detailed styles. Synthetic EDM fixtures demonstrate that Electro House, Dubstep and Deep House can form separate three-song pockets even when their broad family is identical. They also verify tempo guardrails, explicit blank decisions, mixed saved labels, taxonomy context, unique/exact recording matching, and authoritative existing BPM, slash-separated keys and energy. The actual Streamlit page was exercised through a library upload, editable style table and set build.

The previous 35 unit tests passed. Nine additional tests cover style metadata, safety and the app flow; the standalone genre/pocket script also passed.

## Private 100-track corporate regression

The same 100-song source was compared in broad-only and detailed-style modes with the same seed and placement settings. Only uniquely identifiable recordings were enriched: 20 full-title/artist matches (all recording-unverified), 7 ambiguous matches deliberately skipped, 73 unmatched. Fifteen tracks had usable detailed styles. No fuzzy edition guessing was added. This limits the comparison's coverage and should not be presented as a whole-library matching accuracy measure.

| Measure | Broad-only | Detailed-style |
|---|---:|---:|
| Local build seconds | 26.23 | 27.79 |
| Isolated detailed/fallback groups | 34 | 24 |
| Detailed/fallback 2–4-song pockets | 21 | 22 |
| Weak transitions | 10 | 9 |
| Hard BPM transitions | 1 | 1 |
| Half/double-time transitions | 4 | 4 |
| Energy cliffs | 7 | 8 |
| Average transition score | 79.24 | 77.20 |

Both runs retained all 100 tracks, the selected opener and all four after-warm-up placements. Titles, performers, saved BPM, keys and energy were unchanged. Family and style costs differ by mode and must not be compared directly; isolation/pocket counts above use detailed labels for both routes.

The detailed route has one fewer weak transition and fewer style detours, but one additional large energy drop and a lower average score. These are route-level tradeoffs, not a claim that every transition improves. Existing genre-pass guardrails still prohibit making the pass's input route worse on protected safety metrics; the full optimizer can choose different candidate routes. A DJ should review the exported order before performing it.

No private master library, chart reference, playlist records, saved decisions or credentials are bundled in this change. Existing hosted sign-in and storage code are unchanged. Deployment has not yet been verified in Streamlit Cloud.
