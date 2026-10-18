"""Detailed genre import and pocket identities. Never estimates tempo/key/energy."""
import re
from functools import lru_cache
from genre_metadata import GENRE_FAMILIES, genre_family, normalize, identity, file_path


def clean(value):
    if value is None:return ''
    value=str(value).strip()
    return '' if value.casefold() in {'nan','none','<na>'} else value

@lru_cache(maxsize=4096)
def style_parts(value):
    """Keep the leaf style; use its taxonomy parent only to disambiguate names."""
    value=clean(value)
    parent,sep,leaf=value.partition('---')
    if not sep:parent,leaf='',value
    leaf=leaf.strip();name=normalize(leaf)
    if not name:return '', '', ''
    special={'country rock':'Country','classic rock':'Rock','nu disco':'Disco/Funk',
             'electro house':'EDM','deep house':'EDM','tech house':'EDM',
             'contemporary r b':'Hip-Hop/R&B','new jack swing':'Hip-Hop/R&B'}
    family=special.get(name) or genre_family(leaf)
    if not family and sep:
        family={'Rock':'Rock','Pop':'Pop','Hip Hop':'Hip-Hop/R&B','Electronic':'EDM',
                'Funk / Soul':'Soul/Motown','Latin':'Latin','Reggae':'Reggae',
                'Jazz':'Jazz','Classical':'Instrumental / Classical'}.get(parent,'')
    aliases={'drum n bass':'drum and bass','drum bass':'drum and bass','dnb':'drum and bass',
             'hiphop':'hip hop','rnb':'r b'}
    name=aliases.get(name,name)
    return leaf, (normalize(family or parent)+':'+name), family


def saved_detail(value):
    """Coarse and mixed Rekordbox labels do not become artificial subgenres."""
    value=clean(value)
    if not value or any(x in value for x in [',',';','|','/']):return ''
    if normalize(value) in {normalize(f) for f in GENRE_FAMILIES}:return ''
    leaf,_,family=style_parts(value)
    return leaf if family else ''


def selected_style(track):
    # An explicit style field, including an intentional blank, is authoritative.
    if 'Genre Style' in track:return clean(track.get('Genre Style'))
    family=clean(track.get('Genre Family'))
    manual='user' in clean(track.get('Genre Source')).casefold() or 'user' in clean(track.get('Genre Review Status')).casefold()
    for field in ['Genre','Original Rekordbox Genres']:
        detail=saved_detail(track.get(field,''))
        if detail:
            if manual and (not family or style_parts(detail)[2]!=family):return ''
            return detail
    model=clean(track.get('Essentia Top Style'))
    if model and manual:
        if not family or (style_parts(model)[2] and style_parts(model)[2]!=family):return ''
    return model


def style_key(track):
    style=selected_style(track)
    if not style:return ''
    model=clean(track.get('Essentia Top Style'))
    if clean(track.get('Genre Style Source')).startswith('Essentia') and normalize(style_parts(model)[0])==normalize(style):
        return style_parts(model)[1]
    leaf,key,family=style_parts(style)
    # For a manually assigned custom style, keep it distinct within its family.
    return key if family else normalize(clean(track.get('Genre Family')))+':'+normalize(style)


@lru_cache(maxsize=4096)
def _family_key(value):
    family=genre_family(value)
    return 'family:'+normalize(family) if family else ''

def pocket_key(track,detailed=True):
    if detailed:
        key=style_key(track)
        if key:return 'style:'+key
    return _family_key(clean(track.get('Genre Family')) if 'Genre Family' in track else clean(track.get('Genre')))


def prepare_genres(frame):
    """Add explicit style/source columns without overwriting saved genres."""
    out=frame.copy()
    if 'Genre Family' not in out:out['Genre Family']=''
    for field in ['Genre Family','Genre Style','Genre Style Source']:
        if field in out:out[field]=out[field].map(clean)
    records=out.to_dict('records')
    for idx,row in zip(out.index,records):
        family=clean(row.get('Genre Family'))
        manual='user' in clean(row.get('Genre Review Status')).casefold() or 'user' in clean(row.get('Genre Source')).casefold()
        style=selected_style(row)
        if 'Genre Style' in row:source=clean(row.get('Genre Style Source')) or 'Playlist style'
        elif any(saved_detail(row.get(k,'')) for k in ['Genre','Original Rekordbox Genres']):source='Saved genre label'
        else:source='Essentia Discogs519' if style else ''
        out.at[idx,'Genre Style']=style_parts(style)[0] if style else ''
        out.at[idx,'Genre Style Source']=source
        if not family and not manual:
            original=clean(row.get('Genre')) or clean(row.get('Original Rekordbox Genres'))
            family=genre_family(original) or style_parts(style)[2]
            out.at[idx,'Genre Family']=family
    return out


def attach_library_genres(playlist,library):
    """Exact recording paths first; only unique full artist/title fallback."""
    if not {'Title','Artist','File'}<=set(library.columns):raise ValueError('Library needs Title, Artist and File columns.')
    paths,identities={},{}
    for row in library.to_dict('records'):
        path=file_path(clean(row.get('File')))
        if not path:continue
        paths.setdefault(path,[]).append(row)
        key=identity(clean(row.get('Title')),clean(row.get('Artist')))
        if all(key):identities.setdefault(key,[]).append(row)
    fields=['Genre','Original Rekordbox Genres','Genre Family','Genre Source','Genre Review Status',
            'Genre Style','Genre Style Source','Essentia Top Style','Essentia Genre Model Score',
            'Essentia Suggested Genre Family','Essentia Genre Model','Essentia Genre Source','Version Type']
    out=playlist.copy()
    for field in fields+['Library Genre Match','Library Genre File']:
        if field not in out:out[field]=''
        else:out[field]=out[field].astype(object)
    for idx,row in playlist.iterrows():
        path=file_path(clean(row.get('File')) or clean(row.get('Essentia File')))
        candidates=paths.get(path,[]) if path else identities.get(identity(clean(row.get('Title')),clean(row.get('Artist'))),[])
        if len(candidates)!=1:
            out.at[idx,'Library Genre Match']='Ambiguous editions — use an exact file' if candidates else 'No library match';continue
        source=candidates[0]
        manual_family='user' in clean(row.get('Genre Source')).casefold() or 'user' in clean(row.get('Genre Review Status')).casefold()
        for field in fields:
            if field in {'Genre Style','Genre Style Source'} and 'Genre Style' in playlist:continue
            if field in {'Genre Family','Genre Source','Genre Review Status'} and manual_family:continue
            if clean(row.get(field)):continue
            # A populated playlist genre/family takes precedence over library classification.
            if field in {'Genre Family','Genre Source','Genre Review Status'} and clean(row.get('Genre Family')):continue
            if field in {'Genre Source','Genre Review Status'} and clean(row.get('Genre')):continue
            if field in source:out.at[idx,field]=clean(source[field])
        out.at[idx,'Library Genre File']=source['File']
        out.at[idx,'Library Genre Match']='Exact file' if path else 'Artist/title — recording unverified'
    # A library may have no explicit style. Do not let added blank columns suppress derivation.
    if 'Genre Style' not in playlist and 'Genre Style' not in library:out=out.drop(columns=['Genre Style','Genre Style Source'])
    return out
