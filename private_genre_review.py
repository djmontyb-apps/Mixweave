"""Private genre decisions and server-side persistence; no bundled library data."""
import csv,gzip,hashlib,io,json,time,uuid
from urllib.parse import quote,urlparse
import requests
from genre_metadata import GENRE_FAMILIES

class ReviewError(ValueError):pass
class ReviewConflict(ReviewError):pass

def authorized_owner(user,allowed_emails):
    email=str(user.get('email','')).strip().casefold()
    if user.get('email_verified') is not True or not email or email not in {str(x).strip().casefold() for x in allowed_emails}:
        raise ReviewError('This account is not permitted to open the private review.')
    issuer=str(user.get('iss',''));subject=str(user.get('sub',''))
    if issuer not in {'https://accounts.google.com','accounts.google.com'} or not subject:
        raise ReviewError('A verified Google sign-in is required.')
    expiry=user.get('exp')
    if expiry is not None:
        try:valid_expiry=float(expiry)>time.time()
        except (TypeError,ValueError):valid_expiry=False
        if not valid_expiry:raise ReviewError('Please sign out and sign in again.')
    return hashlib.sha256(('https://accounts.google.com\0'+subject).encode()).hexdigest()

def parse_library(raw):
    if len(raw)>60_000_000:raise ReviewError('Use a library CSV under 60 MB.')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')));columns=reader.fieldnames or [];rows=list(reader)
    except (UnicodeError,csv.Error):raise ReviewError('Use a UTF-8 master-library CSV.')
    if not {'Title','Artist','File','Genre Family'}<=set(columns) or len(columns)!=len(set(columns)):
        raise ReviewError('Use the master-library CSV with Title, Artist, File and Genre Family.')
    if not rows or len(rows)>50000 or any(None in r or any(v is None for v in r.values()) for r in rows):raise ReviewError('The library CSV has malformed or missing records.')
    files=[r['File'] for r in rows]
    if any(not x for x in files) or len(set(files))!=len(files):raise ReviewError('Each recording needs a unique file path.')
    return columns,rows

def validate_decisions(value):
    if not isinstance(value,dict) or value.get('version')!=1:raise ReviewError('Use a saved genre-decisions JSON file.')
    result={'version':1,'groups':{},'files':{}}
    for key in ['groups','files']:
        entries=value.get(key)
        if not isinstance(entries,dict) or len(entries)>50000:raise ReviewError('Invalid genre decisions.')
        for name,family in entries.items():
            if not isinstance(name,str) or not isinstance(family,str) or family not in ['']+GENRE_FAMILIES:raise ReviewError('Unknown genre family in the decisions file.')
        result[key]=dict(entries)
    return result

def original_label(row):return row.get('Original Rekordbox Genres') or row.get('Genre') or ''
def resolved_family(row,decisions):
    if row['File'] in decisions['files']:return decisions['files'][row['File']]
    return decisions['groups'].get(original_label(row),row.get('Genre Family',''))
def reviewed_csv(columns,rows,decisions):
    columns=list(columns)
    for c in ['Genre Review Status','Genre Source']:
        if c not in columns:columns.append(c)
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=columns);w.writeheader()
    for old in rows:
        r=dict(old)
        if r['File'] in decisions['files'] or original_label(r) in decisions['groups']:
            r.update({'Genre Family':resolved_family(r,decisions),'Genre Review Status':'User reviewed','Genre Source':'User genre-family review; original Rekordbox labels retained'})
        w.writerow(r)
    return ('\ufeff'+out.getvalue()).encode()

class ReviewStore:
    def __init__(self,url,service_key,bucket='mixweave-private-review',session=None):
        parsed=urlparse(url)
        if parsed.scheme!='https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co') or parsed.path not in ('','/') or parsed.query or parsed.fragment:
            raise ReviewError('Configure an HTTPS Supabase project URL.')
        self.url=url.rstrip('/');self.bucket=bucket;self.session=session or requests.Session()
        self.headers={'apikey':service_key,'Authorization':'Bearer '+service_key}
    def request(self,method,path,**kwargs):
        try:r=self.session.request(method,self.url+path,headers={**self.headers,**kwargs.pop('headers',{})},timeout=45,**kwargs)
        except requests.RequestException:raise ReviewError('The private store is unavailable. Your changes have not been saved.')
        if not r.ok:
            try:code=r.json().get('code')
            except ValueError:code=None
            if code=='40001':raise ReviewConflict('Another device saved newer changes. Download your decisions, then reload the cloud copy before continuing.')
            raise ReviewError('The private store could not complete this request. No save is confirmed.')
        return r
    def require_private_bucket(self):
        b=self.request('GET','/storage/v1/bucket/'+quote(self.bucket,safe='')).json()
        if b.get('public') is not False:raise ReviewError('The review bucket must be private before library data can be used.')
    def state(self,owner):
        result=self.request('GET','/rest/v1/genre_review_workspaces',params={'owner_id':'eq.'+owner,'select':'*'}).json()
        if len(result)>1:raise ReviewError('Invalid review workspace.')
        return result[0] if result else {'revision':0,'decisions':{'version':1,'groups':{},'files':{}},'library_path':None}
    def save(self,owner,revision,decisions=None,library=None):
        body={'p_owner':owner,'p_expected':revision,'p_decisions':validate_decisions(decisions) if decisions is not None else None,'p_library_path':None,'p_library_name':None,'p_library_sha':None}
        if library:body.update(p_library_path=library['path'],p_library_name=library['name'],p_library_sha=library['sha'])
        result=self.request('POST','/rest/v1/rpc/save_genre_review',json=body).json()
        if not isinstance(result,list) or len(result)!=1:raise ReviewError('The store returned no confirmed saved revision.')
        return result[0]
    def upload_library(self,owner,raw,name):
        parse_library(raw);self.require_private_bucket()
        path=owner+'/'+uuid.uuid4().hex+'.csv.gz';sha=hashlib.sha256(raw).hexdigest()
        self.request('POST','/storage/v1/object/'+quote(self.bucket,safe='')+'/'+path,data=gzip.compress(raw),headers={'Content-Type':'application/gzip','x-upsert':'false'})
        return {'path':path,'sha':sha,'name':str(name)[:200]}
    def download_library(self,owner,state):
        path=state['library_path']
        if not path or not path.startswith(owner+'/') or '..' in path:raise ReviewError('Invalid private library location.')
        self.require_private_bucket()
        compressed=self.request('GET','/storage/v1/object/'+quote(self.bucket,safe='')+'/'+quote(path,safe='/')).content
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as f:raw=f.read(60_000_001)
        except (OSError,EOFError):raise ReviewError('The saved library is unreadable.')
        if len(raw)>60_000_000 or hashlib.sha256(raw).hexdigest()!=state['library_sha']:raise ReviewError('The saved library failed its integrity check.')
        parse_library(raw);return raw
