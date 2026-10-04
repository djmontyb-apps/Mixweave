"""Attach local scanner measurements without changing existing musical metadata."""
import re
import unicodedata
import pandas as pd

FEATURES = ('Danceability', 'Valence', 'Acousticness', 'Loudness LUFS')
MIK_SUFFIX = re.compile(r'\s*-\s*(?:1[0-2]|[1-9])[AB](?:/(?:1[0-2]|[1-9])[AB])*\s*-\s*\d+(?:\.\d+)?\s*$', re.I)


def text(value):
    return '' if pd.isna(value) else str(value).strip()


def identity(row):
    title = MIK_SUFFIX.sub('', text(row.get('Title', '')))
    def normalize(value):
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
        return re.sub(r'[^a-z0-9]+', ' ', value).strip()
    artist = normalize(text(row.get('Artist', '')))
    # Explicit user preference: use Garth Brooks for the Spotify substitute.
    if artist == 'brooks jefferson':
        artist = 'garth brooks'
    return normalize(title), artist


def attach_features(playlist, analysis):
    """Prefer exact paths; unique artist/title matches are flagged as unverified.

    Existing BPM/key/energy are never overwritten. Ambiguous edits require an
    exact File path. Existing feature values are retained in Playlist columns.
    """
    required = {'Title', 'Artist', 'File', 'Status', *FEATURES}
    missing = required - set(analysis.columns)
    if missing:
        raise ValueError('Scanner results are missing: ' + ', '.join(sorted(missing)))
    usable = analysis[analysis['Status'].eq('OK')].copy()
    for field in FEATURES:
        values = pd.to_numeric(usable[field], errors='coerce')
        if values.isna().any() or (~values.map(lambda v: float('-inf') < v < float('inf'))).any():
            raise ValueError(f'Scanner results contain invalid {field} values.')
        if field != 'Loudness LUFS' and not values.between(0, 100).all():
            raise ValueError(f'{field} must be on the scanner 0–100 scale.')
        usable[field] = values
    paths, identities = {}, {}
    for _, row in usable.iterrows():
        path = text(row['File'])
        if path:
            paths.setdefault(path, []).append(row)
        key = identity(row)
        if all(key):
            identities.setdefault(key, []).append(row)
    out = playlist.copy()
    for field in FEATURES:
        if field in out:
            backup = 'Playlist ' + field
            if backup not in out:
                out[backup] = out[field]
        else:
            out[field] = float('nan')
    for field in FEATURES:
        out[field] = pd.to_numeric(out[field], errors='coerce').astype(float)
    out['Essentia Match'] = ''
    for idx, row in out.iterrows():
        path = text(row.get('File', ''))
        # A supplied path identifies the recording; never fall back if it fails.
        candidates = paths.get(path, []) if path else identities.get(identity(row), [])
        if len(candidates) != 1:
            out.at[idx, 'Essentia Match'] = 'Ambiguous edits — select an exact file' if candidates else 'No scanner match'
            continue
        source = candidates[0]
        for field in FEATURES:
            out.at[idx, field] = source[field]
        for field in ['Genre', 'Genre Source']:
            if field in source and (field not in out or not text(row.get(field, ''))):
                out.at[idx, field] = source[field]
        for field in source.index:
            if field.startswith(('Danceability Raw', 'Valence Raw', 'Acousticness Raw')) or field.endswith('Model'):
                out.at[idx, field] = source[field]
        out.at[idx, 'Essentia File'] = source['File']
        out.at[idx, 'Essentia Match'] = 'Exact file' if path else 'Artist/title — recording unverified'
        if text(row.get('Artist', '')).lower() == 'brooks jefferson':
            out.at[idx, 'Essentia Match'] = 'Garth Brooks version — performer differs'
    return out
