"""Exercise the actual Streamlit import/editor/export flow with synthetic tracks."""
import io,unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest

class Upload(io.BytesIO):
    name='test.csv'

class DetailedAppTests(unittest.TestCase):
 def test_library_styles_survive_import_editor_and_running_order(self):
  playlist=[];master=[]
  for i,style in enumerate(['Electro House','Dubstep','Deep House']*2):
   base={'Title':'Song '+str(i),'Artist':'Artist '+str(i),'BPM':128,'Energy':70,'Camelot Key':'8A','File':'/'+str(i)+'.mp3'}
   playlist.append(base)
   master.append({**base,'BPM':90,'Energy':4,'Camelot Key':'3A','Status':'OK','Genre Family':'EDM','Essentia Top Style':'Electronic---'+style,'Essentia Genre Model Score':0.9,'Danceability':80,'Valence':70,'Acousticness':5,'Loudness LUFS':-10})
  raw=pd.DataFrame(playlist).to_csv(index=False).encode();analysis=pd.DataFrame(master).to_csv(index=False).encode()
  def upload(label,*args,**kwargs):
   if kwargs.get('key')=='essentia_analysis':return Upload(analysis)
   if 'playlist' in label.casefold():return Upload(raw)
   return None
  with patch('streamlit.file_uploader',side_effect=upload):
   at=AppTest.from_file('app.py').run(timeout=30)
   self.assertFalse(at.exception)
   self.assertTrue(any('6/6 tracks have detailed styles' in c.value for c in at.caption))
   build=next(b for b in at.button if 'Build my Mixweave set' in b.label)
   build.click().run(timeout=30)
   self.assertFalse(at.exception)
   frames=[x.value for x in at.dataframe if 'Mixweave #' in x.value.columns]
   self.assertTrue(frames)
   out=frames[0];self.assertEqual(len(out),6)
   self.assertEqual(set(out['Genre Style']),{'Electro House','Dubstep','Deep House'})
   self.assertTrue(out['BPM'].eq(128).all());self.assertTrue(out['Energy'].eq(70).all());self.assertTrue(out['Camelot Key'].eq('8A').all())
 def test_choose_remix_then_clear_selection(self):
  raw=pd.DataFrame([{'Title':'Night Song','Artist':'DJ Example','BPM':128,'Energy':70,'Camelot Key':'8A'}]).to_csv(index=False).encode()
  master=pd.DataFrame([{'Title':'Night Song (Bass Remix)','Artist':'DJ Example','File':'/bass.mp3','Status':'OK','Danceability':80,'Valence':70,'Acousticness':5,'Loudness LUFS':-10,'Essentia Top Style':'Electronic---Dubstep'}]).to_csv(index=False).encode()
  def upload(label,*args,**kwargs):
   if kwargs.get('key')=='essentia_analysis':return Upload(master)
   if 'playlist' in label.casefold():return Upload(raw)
   return None
  with patch('streamlit.file_uploader',side_effect=upload):
   at=AppTest.from_file('app.py').run(timeout=30)
   picker=next(x for x in at.selectbox if str(x.key).startswith('library_version_'))
   picker.set_value('/bass.mp3').run(timeout=30)
   self.assertFalse(at.exception)
   self.assertTrue(any('1/1 tracks have detailed styles' in x.value for x in at.caption))
   picker=next(x for x in at.selectbox if str(x.key).startswith('library_version_'))
   picker.set_value('').run(timeout=30)
   self.assertFalse(at.exception)
   self.assertFalse(any('1/1 tracks have detailed styles' in x.value for x in at.caption))
if __name__=='__main__':unittest.main()
