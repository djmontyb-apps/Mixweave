import unittest
import pandas as pd
from library_versions import LibraryVersions, attach_selected_versions

class VersionTests(unittest.TestCase):
 def setUp(self):
  self.library=pd.DataFrame([dict(Title='Night Song ('+name+' Remix)',Artist='DJ Example',File='/'+name+'.mp3',BPM=90,Energy=4,**{'Camelot Key':'3A','Status':'OK','Danceability':80,'Valence':70,'Acousticness':5,'Loudness LUFS':-10,'Essentia Top Style':'Electronic---'+style}) for name,style in [('Club','Electro House'),('Bass','Dubstep')]])
  self.playlist=pd.DataFrame([dict(Title='Night Song',Artist='DJ Example',File='/unavailable.mp3',BPM=128,Energy=70,**{'Camelot Key':'8A'})])
 def test_suggestions_never_apply_automatically(self):
  self.assertEqual(len(LibraryVersions(self.library).options(self.playlist.iloc[0])),2)
  out=attach_selected_versions(self.playlist,self.library).iloc[0]
  self.assertEqual(out['Library Genre Match'],'No library match')
  self.assertFalse(out['Essentia Top Style'])
 def test_selected_recording_preserves_playlist_metadata(self):
  self.playlist['Library Selected File']='/Bass.mp3'
  out=attach_selected_versions(self.playlist,self.library).iloc[0]
  self.assertEqual(out['Essentia Top Style'],'Electronic---Dubstep')
  self.assertEqual(out['Library Genre Match'],'User-selected recording')
  self.assertEqual(out['File'],'/unavailable.mp3')
  self.assertEqual((out['BPM'],out['Energy'],out['Camelot Key']),(128,70,'8A'))
 def test_other_artists_are_not_suggested(self):
  self.assertFalse(LibraryVersions(self.library).options({'Title':'Night Song','Artist':'Unrelated Singer'}))
 def test_manual_style_is_preserved(self):
  self.playlist['Library Selected File']='/Bass.mp3'
  self.playlist['Genre Style']='Custom choice'
  self.assertEqual(attach_selected_versions(self.playlist,self.library).iloc[0]['Genre Style'],'Custom choice')
 def test_exported_analysis_refreshes_when_version_changes(self):
  self.playlist['Library Selected File']='/Bass.mp3'
  self.playlist['Essentia Top Style']='Electronic---Electro House'
  self.playlist['Genre Style']='Electro House'
  self.playlist['Genre Style Source']='Essentia Discogs519'
  out=attach_selected_versions(self.playlist,self.library).iloc[0]
  self.assertEqual(out['Essentia Top Style'],'Electronic---Dubstep')
  self.assertEqual(out['Genre Style'],'Dubstep')
 def test_blank_then_text_model_column_from_csv(self):
  self.library['Danceability Model']=[float('nan'),'Discogs519 MAEST']
  self.playlist['Library Selected File']='/Bass.mp3'
  self.playlist['Danceability Model']=float('nan')
  self.playlist['Essentia Genre Model']=float('nan')
  self.library['Essentia Genre Model']=[float('nan'),'Discogs519 MAEST']
  out=attach_selected_versions(self.playlist,self.library).iloc[0]
  self.assertEqual(out['Danceability Model'],'Discogs519 MAEST')
  self.assertEqual(out['Essentia Genre Model'],'Discogs519 MAEST')
if __name__=='__main__':unittest.main()
