"""Suggest library editions; only an explicit selection changes the recording."""
import re
from difflib import SequenceMatcher
from detailed_genres import clean, selected_style, attach_library_genres, style_parts
from genre_metadata import identity, file_path
from audio_analysis import attach_features


def song_identity(title, artist):
    title = re.sub(r'[(\[][^(\[]*(?:remix|redrum|mashup|bootleg|extended|intro|outro|clean|dirty|edit|mix)[^)]*[)\]]', '', clean(title), flags=re.I)
    title, artist = identity(title, clean(artist))
    # Edition/feature suffixes are used for suggestions only, never auto-matches.
    title = re.split(r'\b(?:feat|featuring|ft)\b', title)[0]
    title = re.split(r'\b(?:remix|redrum|mashup|bootleg|extended|intro|outro|clean|dirty|edit|original mix)\b', title)[0]
    artist = re.split(r'\b(?:feat|featuring|ft|presents)\b', artist)[0]
    return title.strip(), artist.strip()


class LibraryVersions:
    def __init__(self, library):
        self.rows = []
        self.by_title = {}
        self.by_token = {}
        for row in library.to_dict('records'):
            if not clean(row.get('File')):continue
            title, artist = song_identity(row.get('Title'), row.get('Artist'))
            entry = (title, artist, row)
            self.rows.append(entry)
            for token in set(title.split()):
                self.by_token.setdefault(token, []).append(entry)
            self.by_title.setdefault(title, []).append((title, artist, row))

    def options(self, track):
        title, artist = song_identity(track.get('Title'), track.get('Artist'))
        if not title or not artist:return []
        ranked = []
        # Exact normalized song titles include differently credited versions.
        pool = self.by_title.get(title, [])
        if not pool:
            tokens = [token for token in title.split() if len(token) > 2]
            pool = [entry for token in tokens for entry in self.by_token.get(token, [])]
        for other_title, other_artist, row in pool:
            title_score = SequenceMatcher(None, title, other_title).ratio()
            artist_score = SequenceMatcher(None, artist, other_artist).ratio()
            artist_overlap = set(artist.split()) & set(other_artist.split())
            if title_score < .78 or (artist_score < .45 and not artist_overlap):continue
            ranked.append((title_score * 2 + artist_score, row))
        ranked.sort(key=lambda item: (-item[0], clean(item[1].get('Title')), clean(item[1].get('File'))))
        unique = {}
        for _, row in ranked:unique.setdefault(file_path(row['File']), row)
        return list(unique.values())


def version_label(row):
    parts = [clean(row.get('Title')), clean(row.get('Artist')),
             (clean(row.get('BPM')) + ' BPM') if clean(row.get('BPM')) else '',
             clean(selected_style(row))]
    return ' · '.join(part for part in parts if part) + ' — ' + clean(row.get('File'))


def attach_selected_versions(playlist, library):
    working = playlist.copy()
    working['Library Genre File']=''
    working['Library Genre Match']=''
    original_file = playlist['File'].copy() if 'File' in playlist else None
    if 'Library Selected File' in playlist:
        if 'File' not in working:working['File']=''
        for idx, row in playlist.iterrows():
            selected = clean(row.get('Library Selected File'))
            if selected:
                working.at[idx, 'File']=selected
                # An exported playlist may contain analysis from an earlier choice.
                for field in working.columns:
                    if field.startswith('Essentia ') and field != 'Essentia File':
                        working.at[idx, field]=''

    out = attach_library_genres(attach_features(working, library), library)
    if original_file is None:out=out.drop(columns=['File'], errors='ignore')
    else:out['File']=original_file
    if 'Library Selected File' in playlist:
        for idx, row in playlist.iterrows():
            if clean(row.get('Library Selected File')) and clean(out.at[idx,'Library Genre File']):
                out.at[idx,'Library Genre Match']='User-selected recording'
                if clean(row.get('Genre Style Source')).startswith('Essentia'):
                    out.at[idx,'Genre Style']=style_parts(clean(out.at[idx,'Essentia Top Style']))[0]

    return out
