"""Session-only private reference suggestions; never load bundled chart data."""
import json
import io
import csv

REQUIRED = ['Title', 'Artist', 'BPM', 'Camelot Key', 'Energy', 'File']


def load_reference(raw):
    if len(raw) > 20_000_000:
        raise ValueError('Use a reference file smaller than 20 MB.')
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError('Upload a MixWeave private reference JSON file.')
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('Unsupported private reference format.')
    charts, library = data.get('charts'), data.get('library')
    if not isinstance(charts, list) or not isinstance(library, dict):
        raise ValueError('The reference file needs charts and library candidates.')
    if len(charts) > 100 or len(library) > 30000:
        raise ValueError('The reference file contains too many records.')
    for file_id, track in library.items():
        if not isinstance(track, dict) or any(k not in track for k in REQUIRED):
            raise ValueError('A library candidate is missing its music metadata.')
    for chart in charts:
        if not isinstance(chart, dict) or not isinstance(chart.get('name'), str) or not isinstance(chart.get('songs'), list) or len(chart['songs']) > 1000:
            raise ValueError('Invalid reference category.')
        for song in chart['songs']:
            if not isinstance(song, dict) or not isinstance(song.get('rank'), int) or song['rank'] < 1 or not all(isinstance(song.get(k), str) for k in ['title', 'artist']):
                raise ValueError('Invalid ranked song.')
            if not isinstance(song.get('candidate_ids'), list) or any(not isinstance(k, str) or k not in library for k in song['candidate_ids']):
                raise ValueError('A song points to an unavailable library candidate.')
    return data


def select_tracks(reference, chart_index, selections):
    """Require an explicit file choice for each song; retain all library values."""
    chart = reference['charts'][chart_index]
    output, seen = [], set()
    for song_index, file_id in selections:
        song = chart['songs'][song_index]
        if file_id not in song['candidate_ids']:
            raise ValueError('Choose an available recording for this song.')
        source = reference['library'][file_id]
        if source.get('Metadata Review'):
            raise ValueError('Resolve the conflicting Rekordbox metadata before using this recording.')
        if file_id in seen:
            continue
        seen.add(file_id)
        track = dict(source)
        track.update({'Reference Source': reference.get('source', ''),
                      'Reference Category': chart['name'], 'Reference Rank': song['rank'],
                      'Reference Snapshot': reference.get('snapshot_date', ''),
                      'Reference Title': song['title'], 'Reference Artist': song['artist']})
        output.append(track)
    return output


def playlist_csv(tracks):
    if not tracks:
        raise ValueError('Choose at least one recording.')
    columns = list(dict.fromkeys(k for row in tracks for k in row))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader(); writer.writerows(tracks)
    return out.getvalue().encode('utf-8-sig')
