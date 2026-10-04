# Rekordbox genre import validation

Prepared from merged MixWeave 1.4, commit a406c37.

- Four genre tests cover recognized/ambiguous labels, duplicate entries, percent-encoded file paths, conflicting genres, multiple editions, and invalid collection files.
- The five audio-import tests continue to pass.
- App tests use the existing 54-track reception results and the saved Rekordbox XML export: 53 tracks have a consistent genre and 32 map to existing genre families.
- Scanner CSV import and separate Rekordbox XML import are exercised in the interface. Genre fields are retained after optimization and spreadsheet export.
- Existing test_genre_pockets.py remains incompatible with the unchanged optimizer, as recorded for MixWeave 1.4.

The user-specific XML file, library metadata, and scanner settings are local only. The published changes contain generic genre import code and synthetic test fixtures.
