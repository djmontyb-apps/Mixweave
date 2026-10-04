"""Read Rekordbox genres and map clear labels to MixWeave's existing families."""
import re
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

GENRE_FAMILIES = ['Pop', 'Hip-Hop/R&B', 'Rock', 'Country', 'Latin', 'Disco/Funk',
                  'EDM', 'Reggae', 'Soul/Motown', 'Jazz',
                  'Line Dance / Group Participation', 'Acoustic', 'Instrumental / Classical']


def normalize(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def genre_family(genre):
    value = normalize(genre)
    for family in GENRE_FAMILIES:
        if value == normalize(family):
            return family
    rules = {
        'Pop': r'\b(pop|top 40)\b',
        'Hip-Hop/R&B': r'\b(hip hop|hiphop|rap|r b|rnb|trap)\b',
        'Rock': r'\b(rock|punk|metal|alternative|grunge)\b',
        'Country': r'\b(country|bluegrass|americana)\b',
        'Latin': r'\b(latin|salsa|merengue|bachata|cumbia|reggaeton|mambo|tropical|tejano)\b',
        'Disco/Funk': r'\b(disco|funk)\b',
        'EDM': r'\b(edm|electronic|electronica|house|techno|trance|dubstep|drum and bass|drum bass|dnb|dance|electro|hardstyle)\b',
        'Reggae': r'\b(reggae|dancehall|ska)\b',
        'Soul/Motown': r'\b(soul|motown)\b',
        'Jazz': r'\b(jazz|swing)\b',
        'Line Dance / Group Participation': r'\b(line dance|group participation)\b',
        'Acoustic': r'\bacoustic\b',
        'Instrumental / Classical': r'\b(instrumental|classical|orchestral)\b',
    }
    if value in ('dance pop', 'pop dance'):
        return 'Pop'
    hits = {family for family, pattern in rules.items() if re.search(pattern, value)}
    # Recognize line-dance labels without also classifying them as EDM.
    if 'Line Dance / Group Participation' in hits:
        hits.discard('EDM')
    return next(iter(hits)) if len(hits) == 1 else ''


def file_path(value):
    value = str(value or '').strip()
    return unquote(urlparse(value).path) if value.startswith('file://') else value


def identity(title, artist):
    title = re.sub(r'\s*-\s*(?:1[0-2]|[1-9])[AB](?:\s*/\s*(?:1[0-2]|[1-9])[AB])*\s*-\s*\d+(?:\.\d+)?\s*$', '', str(title or ''), flags=re.I)
    artist = normalize(artist)
    if artist == 'brooks jefferson':
        artist = 'garth brooks'
    return normalize(title), artist


class RekordboxGenres:
    def __init__(self, source):
        data = source.read() if hasattr(source, 'read') else open(source, 'rb').read()
        if isinstance(data, str):
            data = data.encode()
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
            raise ValueError('Use a standard Rekordbox collection XML export.')
        try:
            root = ET.fromstring(data)
        except ET.ParseError as error:
            raise ValueError('Could not read the Rekordbox XML export.') from error
        if root.tag != 'DJ_PLAYLISTS' or root.find('COLLECTION') is None:
            raise ValueError('Use File → Export Collection in xml format in Rekordbox.')
        self.paths, self.identities = {}, {}
        for track in root.findall('./COLLECTION/TRACK'):
            path = file_path(track.get('Location'))
            if not path:
                continue
            self.paths.setdefault(path, []).append(track.get('Genre', '').strip())
            key = identity(track.get('Name'), track.get('Artist'))
            if all(key):
                self.identities.setdefault(key, set()).add(path)

    def lookup(self, path='', title='', artist=''):
        path = file_path(path)
        exact = bool(path)
        if not path:
            candidates = self.identities.get(identity(title, artist), set())
            if len(candidates) != 1:
                return '', 'Ambiguous editions' if candidates else 'No Rekordbox match'
            path = next(iter(candidates))
        if path not in self.paths:
            return '', 'No Rekordbox match'
        genres = {value for value in self.paths[path] if value}
        if len(genres) > 1:
            return '', 'Conflicting Rekordbox genres'
        genre = next(iter(genres), '')
        return genre, ('Rekordbox XML: exact file' if exact else 'Rekordbox XML: artist/title (recording unverified)') if genre else 'Rekordbox genre blank'
