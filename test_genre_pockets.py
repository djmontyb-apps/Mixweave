"""Run: python test_genre_pockets.py [path-to-Crate-Hackers-PDF]."""
import ast
import io
import sys
import time
from pathlib import Path
from collections import Counter
import optimizer as opt


def app_functions():
    # Load the actual import/export helpers without starting Streamlit's UI.
    tree = ast.parse(Path(__file__).with_name('app.py').read_text())
    keep = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))
            or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                                               ('APP_NAME', 'APP_VERSION') for t in n.targets)]
    scope = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'app.py', 'exec'), scope)
    return scope


def run():
    settings = opt.Settings(energy_arc='Off', depth='Standard')
    tracks = [dict(Title=str(i), Artist='Artist ' + str(i), BPM=120,
                   Energy=70, **{'Camelot Key': '8A', 'Genre': f})
              for i, f in enumerate(['Rock', 'Country', 'Latin'] * 3)]
    result = opt.program_genre_pockets(tracks, settings)
    assert opt.genre_pocket_stats(result)['islands'] == 0
    assert opt.genre_pocket_stats(result)['pockets'] == 3
    assert Counter(t['Title'] for t in result) == Counter(t['Title'] for t in tracks)
    settings.lock_first = settings.lock_last = True
    locked = opt.program_genre_pockets(tracks, settings)
    assert locked[0] is tracks[0] and locked[-1] is tracks[-1]
    # Genre cannot create a new tempo cliff to join same-family outliers.
    unsafe = [dict(t, BPM=80 + i * 4) for i, t in enumerate(tracks)]
    safe = opt.program_genre_pockets(unsafe, settings)
    assert opt._route_program_stats(safe, settings)['hard'] == 0
    no_genre = [{k: v for k, v in t.items() if k != 'Genre'} for t in tracks]
    assert opt.program_genre_pockets(no_genre, settings) == no_genre
    single = [dict(t, Genre='Tech House') for t in tracks]
    assert opt.program_genre_pockets(single, settings) == single
    assert opt.genre_family('Dubstep') == 'EDM'
    assert opt.genre_family('Trap') == 'Hip-Hop/R&B'
    assert opt.genre_family('unrecognized') == ''
    assert opt.track_genre_family({'Genre': 'Rock', 'Genre Family': ''}) == ''
    print('Genre, safety, locks, membership and neutral-input checks passed.')

    if len(sys.argv) > 1:
        helpers = app_functions()
        with open(sys.argv[1], 'rb') as pdf:
            df, kind = helpers['load_playlist'](pdf)
        assert kind == 'Crate Hackers PDF' and len(df) == 100
        assert df['#'].tolist() == list(range(1, 101))
        assert df['Camelot Key'].str.match(r'^(1[0-2]|[1-9])[AB]$').all()
        assert df['Genre'].eq('').all()
        records = df.to_dict('records')
        start = time.monotonic()
        ordered, transitions = opt.optimize(records, opt.Settings(depth='Standard'))
        assert len(ordered) == 100 and len(transitions) == 99
        assert Counter(t['#'] for t in ordered) == Counter(range(1, 101))
        print('Actual PDF: 100 rows, 100 valid keys; Standard seconds:', round(time.monotonic()-start, 2))
        print('Hard/weak:', sum(t['bpm_zone'] in ('Hard BPM Jump', 'BPM Incompatible') for t in transitions),
              sum(t['score'] < 60 for t in transitions))
        # Exercise the final programming pass at benchmark size using declared
        # synthetic labels, not claimed musical classifications of these songs.
        labelled = [dict(t, **{'Genre Family': ['Rock','Country','Latin'][i % 3]})
                    for i, t in enumerate(ordered)]
        start = time.monotonic()
        pocketed = opt.program_genre_pockets(labelled, opt.Settings())
        floor, after = (opt._route_program_stats(x, opt.Settings()) for x in (labelled, pocketed))
        for k in ('hard', 'severe', 'weak', 'adjacent_artist', 'near_artist'):
            assert after[k] <= floor[k]
        print('100-row genre pass seconds:', round(time.monotonic()-start, 2))
        import pandas as pd
        out = pd.DataFrame(ordered)
        out.insert(0, 'Mixweave #', range(1, 101))
        out['Program Zone'] = opt.energy_zone_labels(ordered, opt.Settings())
        data = helpers['build_mixweave_pdf'](out, df.attrs['playlist_title'], 'Review',
                    'Test export', 80, 0, 0, 4, 80, 80)
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
            assert 'Mixweave 1.2' in text and 'Corporate Dance Party' in text
            print('PDF export verified:', len(pdf.pages), 'pages')
        buffer = io.BytesIO()
        out.to_excel(buffer, index=False)
        buffer.seek(0)
        assert len(pd.read_excel(buffer)) == 100
        assert len(pd.read_csv(io.StringIO(out.to_csv(index=False)))) == 100
        print('Excel and CSV exports retain 100 rows.')


if __name__ == '__main__':
    run()
