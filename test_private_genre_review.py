import unittest,gzip,hashlib,time
from unittest.mock import Mock
from private_genre_review import *
RAW=b'Title,Artist,File,Genre Family,Genre,BPM,Camelot Key,Energy\nSong,Artist,/one.mp3,,Rock/Pop,120,8A,5\n'
class ReviewTests(unittest.TestCase):
 def user(self):return dict(email='owner@example.com',email_verified=True,iss='https://accounts.google.com',sub='123',exp=time.time()+600)
 def test_stable_identity(self):
  u=self.user();a=authorized_owner(u,['owner@example.com']);u['email']='OWNER@example.com';self.assertEqual(a,authorized_owner(u,['owner@example.com']))
 def test_denied_accounts(self):
  for field,value in [('email_verified',False),('email','other@example.com'),('iss','https://evil.example'),('exp',1),('sub','')]:
   u=self.user();u[field]=value
   with self.assertRaises(ReviewError):authorized_owner(u,['owner@example.com'])
 def test_export_preservation_and_override(self):
  c,r=parse_library(RAW);d={'version':1,'groups':{'Rock/Pop':'Rock'},'files':{'/one.mp3':'Pop'}};_,out=parse_library(reviewed_csv(c,r,d));self.assertEqual(out[0]['Genre Family'],'Pop')
  for k in ['Genre','BPM','Camelot Key','Energy','File']:self.assertEqual(out[0][k],r[0][k])
 def test_duplicate_missing_file(self):
  for data in [RAW+RAW.splitlines()[-1]+b'\n',RAW.replace(b'/one.mp3',b'')]:
   with self.assertRaises(ReviewError):parse_library(data)
 def test_decision_validation(self):
  d={'version':1,'groups':{'Rock/Pop':'Rock'},'files':{},'savedAt':'old'};self.assertEqual(validate_decisions(d)['groups'],d['groups']);d['files']['x']='arbitrary'
  with self.assertRaises(ReviewError):validate_decisions(d)
 def response(self,data=None,ok=True,content=b''):
  r=Mock(ok=ok,content=content);r.json.return_value=data;return r
 def store(self,responses):
  session=Mock();session.request.side_effect=responses;return ReviewStore('https://project.supabase.co','test-key',session=session)
 def test_public_bucket_refused(self):
  s=self.store([self.response({'public':True})])
  with self.assertRaises(ReviewError):s.upload_library('owner',RAW,'library.csv')
  self.assertEqual(s.session.request.call_count,1)
 def test_conflict_not_successful(self):
  s=self.store([self.response({'code':'40001'},ok=False)])
  with self.assertRaises(ReviewConflict):s.save('owner',2,{'version':1,'groups':{},'files':{}})
  self.assertEqual(s.session.request.call_args.kwargs['json']['p_expected'],2)
 def test_download_integrity_and_owner(self):
  state={'library_path':'owner/file.csv.gz','library_sha':hashlib.sha256(RAW).hexdigest()};s=self.store([self.response({'public':False}),self.response(content=gzip.compress(RAW))]);self.assertEqual(s.download_library('owner',state),RAW)
  with self.assertRaises(ReviewError):s.download_library('other',state)
  s=self.store([self.response({'public':False}),self.response(content=gzip.compress(b'wrong'))])
  with self.assertRaises(ReviewError):s.download_library('owner',state)
 def test_network_error(self):
  session=Mock();session.request.side_effect=requests.ConnectionError('secret detail')
  with self.assertRaisesRegex(ReviewError,'unavailable'):ReviewStore('https://project.supabase.co','key',session=session).state('owner')
if __name__=='__main__':unittest.main()
