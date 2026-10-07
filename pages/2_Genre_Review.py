"""Only the authenticated private-review page touches persistent library data."""
import copy,json,hashlib
from datetime import datetime,timezone
from collections import Counter
import streamlit as st
from genre_metadata import GENRE_FAMILIES
from private_genre_review import (ReviewError,ReviewConflict,ReviewStore,authorized_owner,
    parse_library,validate_decisions,original_label,resolved_family,reviewed_csv)

st.set_page_config(page_title='MixWeave — Private Genre Review',page_icon='🎚️',layout='wide')
st.title('Private genre review')
try:
    cfg=st.secrets['private_review']
    allowed=list(cfg['allowed_emails'])
    if len(allowed)!=1:raise KeyError('Only the owner may be configured initially.')
    if not all(st.secrets['auth'].get(k) for k in ['client_id','client_secret','redirect_uri','cookie_secret','server_metadata_url']):raise KeyError('Authentication not configured')
except (KeyError,FileNotFoundError,TypeError):
    st.info('Private review is not connected yet. Your library is not available on this page.')
    st.stop()

if not st.user.is_logged_in:
    st.write('Sign in to review your private library and continue saved work on any device.')
    st.button('Sign in with Google',on_click=st.login,type='primary')
    st.stop()
try:owner=authorized_owner(dict(st.user),allowed)
except ReviewError:
    st.error('This account cannot access the private review.')
    st.button('Sign out',on_click=st.logout)
    st.stop()

def sign_out():
    for k in list(st.session_state):
        if k.startswith('private_review_'):del st.session_state[k]
    st.logout()
st.sidebar.button('Sign out',on_click=sign_out)
prefix='private_review_'+owner+'_'
try:
    store=ReviewStore(cfg['supabase_url'],cfg['supabase_service_key'],cfg.get('bucket','mixweave-private-review'))
    if prefix+'state' not in st.session_state:
        st.session_state[prefix+'state']=store.state(owner)
    state=st.session_state[prefix+'state']
    if state.get('library_path') and prefix+'library' not in st.session_state:
        st.session_state[prefix+'library']=parse_library(store.download_library(owner,state))
except (ReviewError,KeyError):
    st.error('The private store is not available. No library has been loaded or saved.')
    st.stop()

def persist(decisions=None,library=None):
    if decisions is not None:st.session_state[prefix+'draft']=decisions
    try:
        new=store.save(owner,state['revision'],decisions,library)
        st.session_state[prefix+'state']=new
        st.session_state.pop(prefix+'draft',None)
        st.session_state[prefix+'notice']='Saved to your private account.'
        st.rerun()
    except ReviewConflict as e:st.error(str(e))
    except ReviewError as e:st.error(str(e))

if prefix+'notice' in st.session_state:st.success(st.session_state.pop(prefix+'notice'))
if prefix+'draft' in st.session_state:
    st.warning('These local choices have not been saved online. Download them before reloading the cloud copy.')

with st.expander('Library and saved progress',expanded=not bool(state.get('library_path'))):
    if state.get('library_name'):st.write('Current library: '+state['library_name'])
    upload=st.file_uploader('Upload your master-library CSV',type=['csv'],key=prefix+'upload')
    if upload and st.button('Save this library privately',key=prefix+'save_library',disabled=prefix+'draft' in st.session_state):
        try:
            raw=upload.getvalue();parse_library(raw)
            library=store.upload_library(owner,raw,upload.name)
            new=store.save(owner,state['revision'],library=library)
            st.session_state[prefix+'state']=new
            st.session_state[prefix+'library']=parse_library(raw)
            st.session_state.pop(prefix+'draft',None)
            st.rerun()
        except ReviewError as e:st.error(str(e))
    imported=st.file_uploader('Import your desktop genre decisions',type=['json'],key=prefix+'import')
    if imported and st.button('Save imported decisions online',key=prefix+'save_import'):
        try:
            if imported.size>10_000_000:raise ReviewError('Use a decisions file under 10 MB.')
            persist(validate_decisions(json.loads(imported.getvalue())))
        except (ValueError,UnicodeError) as e:st.error('Could not import decisions: '+str(e))
    reload_label='Discard local draft and reload saved progress' if prefix+'draft' in st.session_state else 'Reload saved progress from the cloud'
    if st.button(reload_label):
        for suffix in ['state','library','draft']:
            st.session_state.pop(prefix+suffix,None)
        st.rerun()

if not state.get('library_path'):st.info('Upload the prepared master-library CSV once. It will then be available on your other devices.');st.stop()
columns,rows=st.session_state[prefix+'library']
try:decisions=validate_decisions(st.session_state.get(prefix+'draft',state['decisions']))
except ReviewError:st.error('Saved decisions could not be read.');st.stop()
remaining=sum(not resolved_family(r,decisions) for r in rows)
st.caption(f'{len(rows):,} songs retained · {remaining:,} still without a family · saved revision {state["revision"]}')
st.write('Original Rekordbox genres remain intact. Save a group choice, then make individual exceptions as needed.')
only_missing=st.checkbox('Show groups with unresolved songs first',value=True)
counts=Counter(original_label(r) for r in rows)
missing=Counter(original_label(r) for r in rows if not resolved_family(r,decisions))
options=sorted(counts,key=lambda g:(-missing[g] if only_missing else 0,-counts[g],g))
group=st.selectbox('Original genre labels',options,format_func=lambda g:f'{g or "(no saved genre)"} — {counts[g]:,} songs · {missing[g]:,} unresolved',key=prefix+'group')
group_id=hashlib.sha256(group.encode()).hexdigest()
with st.form(prefix+'group_form_'+group_id):
    current=decisions['groups'].get(group,'')
    chosen=st.selectbox('Genre family for this group',['']+GENRE_FAMILIES,index=(['']+GENRE_FAMILIES).index(current),format_func=lambda f:f or 'Choose a family',key=prefix+'group_family_'+group_id)
    if st.form_submit_button('Save group choice',type='primary'):
        if not chosen:st.warning('Choose a family before saving.')
        else:
            draft=copy.deepcopy(decisions);draft['groups'][group]=chosen;persist(draft)
st.caption('Individual song choices take priority over the group choice.')
search=st.text_input('Find a song or artist in this group',key=prefix+'search')
visible=[r for r in rows if original_label(r)==group and search.casefold() in (r['Title']+' '+r['Artist']).casefold()]
if visible:
    by_file={r['File']:r for r in visible}
    selected=st.selectbox('Song to review',list(by_file),format_func=lambda f:by_file[f]['Title']+' — '+by_file[f]['Artist'],key=prefix+'song_'+group_id)
    row=by_file[selected];current=resolved_family(row,decisions)
    song_id=hashlib.sha256(selected.encode()).hexdigest()
    with st.form(prefix+'song_form_'+song_id):
        family=st.selectbox('Genre family for this song',['']+GENRE_FAMILIES,index=(['']+GENRE_FAMILIES).index(current) if current in GENRE_FAMILIES else 0,format_func=lambda f:f or 'Leave unresolved',key=prefix+'song_family_'+song_id)
        save=st.form_submit_button('Save song choice',type='primary')
        reset=st.form_submit_button('Use the group/default family')
        if save or reset:
            draft=copy.deepcopy(decisions)
            if reset:draft['files'].pop(row['File'],None)
            else:draft['files'][row['File']]=family
            persist(draft)
else:st.info('No songs match that search in this group.')
st.subheader('Download a backup')
backup={**decisions,'savedAt':datetime.now(timezone.utc).isoformat()}
st.download_button('Download my genre decisions',json.dumps(backup,indent=2),file_name='Mixweave_genre_decisions_'+datetime.now(timezone.utc).strftime('%Y-%m-%d')+'.json',mime='application/json')
st.download_button('Download reviewed master library',reviewed_csv(columns,rows,decisions),file_name='Mixweave_master_library_reviewed.csv',mime='text/csv')
