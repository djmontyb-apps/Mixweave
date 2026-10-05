# Genre-pocket restoration validation

Restored the archived 1.2.1 pocket pass, adapting safety fields to the current optimizer and increasing the bounded proposal pool so safe moves are not hidden behind infeasible candidates. Genre classification is cached; 80+ track crates use at most four final-pass iterations.

- The previously failing genre-pocket script passes: pocket building, safety, locks, membership, neutral input, and explicit blank genre overrides.
- Three regression tests cover a hip-hop/pop/hip-hop detour, the Off toggle, 100-track safeguards, and invocation from optimize with transitions recalculated for the final order.
- Existing five audio-import and four genre-import tests pass.
- Streamlit is exercised with a previously exported 54-track reception playlist, including the retained 52 genre families and new Genre Pocket column.

Final-pass benchmark on that saved reception order: isolated genre tracks 24 → 15; 2–4 track pockets 9 → 12; hard BPM jumps 0 → 0; weak transitions 2 → 2; maximum effective BPM gap does not increase; artist-repeat and energy guardrail counts do not increase. Average transition score falls from 86.9 to 85.5 within the bounded allowance. This is a final-pass comparison, not a claim that all playlists produce the same change or that every isolated track can be eliminated.

Personal playlists and local archive files are not published.
