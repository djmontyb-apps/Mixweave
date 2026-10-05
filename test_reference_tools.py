import json,unittest
from reference_tools import load_reference,select_tracks,playlist_csv

def fixture():
 return {'schema_version':1,'source':'Private chart','snapshot_date':'2026-10-05','library':{'edit':{'Title':'Song (Clean) - 8A/9A - 7','Artist':'Original artist','BPM':120.3,'Camelot Key':'8A/9A','Energy':7,'File':'/music/edit.mp3','Danceability':63},'conflict':{'Title':'Song','Artist':'Original artist','BPM':0,'Camelot Key':'','Energy':'','File':'/music/review.mp3','Metadata Review':True}},'charts':[{'name':'Last dances','songs':[{'rank':2,'title':'Song','artist':'Original artist','candidate_ids':['edit','conflict']}]}]}

class ReferenceTests(unittest.TestCase):
 def test_explicit_choice_retains_metadata(self):
  data=fixture();before=json.dumps(data);row=select_tracks(data,0,[(0,'edit')])[0]
  for k,v in data['library']['edit'].items():self.assertEqual(row[k],v)
  self.assertEqual(row['Reference Rank'],2);self.assertEqual(json.dumps(data),before)
  self.assertIn(b'8A/9A',playlist_csv([row]))
 def test_conflicting_and_unlisted_files_rejected(self):
  for file in ['conflict','missing']:
   with self.assertRaises(ValueError):select_tracks(fixture(),0,[(0,file)])
 def test_duplicate_selection_does_not_duplicate_file(self):
  self.assertEqual(len(select_tracks(fixture(),0,[(0,'edit'),(0,'edit')])),1)
 def test_invalid_upload_and_missing_links_rejected(self):
  for raw in [b'not json',b'[]',b'{"schema_version":9}']:
   with self.assertRaises(ValueError):load_reference(raw)
  data=fixture();data['charts'][0]['songs'][0]['candidate_ids']=['missing']
  with self.assertRaises(ValueError):load_reference(json.dumps(data).encode())
 def test_missing_energy_stays_blank(self):
  data=fixture();data['library']['edit']['Energy']=''
  self.assertEqual(select_tracks(data,0,[(0,'edit')])[0]['Energy'],'')
if __name__=='__main__':unittest.main()
