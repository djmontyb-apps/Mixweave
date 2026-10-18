import unittest
from collections import Counter
import pandas as pd
import optimizer as opt
from detailed_genres import prepare_genres,selected_style,pocket_key,attach_library_genres

def row(title,style,bpm=128):
 return {'Title':title,'Artist':'Artist '+title,'BPM':bpm,'Energy':70,'Camelot Key':'8A','Genre Family':'EDM','Essentia Top Style':'Electronic---'+style}
class DetailedTests(unittest.TestCase):
 def test_three_styles_are_not_one_edm_pocket(self):
  rows=[row(str(i),['Electro House','Dubstep','Deep House'][i%3]) for i in range(9)]
  s=opt.Settings(energy_arc='Off',depth='Standard')
  self.assertEqual(opt.genre_pocket_stats(rows)['families'],1)
  self.assertEqual(opt.genre_pocket_stats(rows)['groups'],3)
  result=opt.program_genre_pockets(rows,s)
  self.assertEqual(opt.genre_pocket_stats(result)['islands'],0)
  self.assertEqual(opt.genre_pocket_stats(result)['pockets'],3)
  self.assertEqual(Counter(r['Title'] for r in result),Counter(r['Title'] for r in rows))
 def test_saved_style_and_manual_family_priority(self):
  track=row('A','Dubstep');track['Genre']='Deep House'
  out=prepare_genres(pd.DataFrame([track])).iloc[0]
  self.assertEqual(out['Genre Style'],'Deep House');self.assertEqual(out['Genre'],'Deep House')
  track['Genre Family']='Country';track['Genre Source']='User genre-family review'
  self.assertEqual(selected_style(track),'')
  track['Genre']=''
  self.assertEqual(selected_style(track),'')
  track['Genre Style']='Salsa';self.assertEqual(selected_style(track),'Salsa')
 def test_mixed_labels_model_detail_and_alias(self):
  track=row('A','Electro House');track['Genre']='Pop,Dance / EDM';track['Camelot Key']='4A/5A'
  out=prepare_genres(pd.DataFrame([track])).iloc[0].to_dict()
  self.assertEqual(out['Genre Style'],'Electro House');self.assertEqual(out['Genre'],'Pop,Dance / EDM');self.assertEqual(out['Camelot Key'],'4A/5A')
  self.assertEqual(pocket_key(out),pocket_key({'Genre':'Electro House'}))
 def test_import_preserves_metadata_and_avoids_wrong_editions(self):
  library=pd.DataFrame([dict(row('Song','Dubstep'),File='/a.mp3'),dict(row('Song','Deep House'),File='/b.mp3')])
  playlist=pd.DataFrame([dict(Title='Song',Artist='Artist Song',BPM=126,Energy=5,**{'Camelot Key':'7A/8A'})])
  ambiguous=attach_library_genres(playlist,library);self.assertIn('Ambiguous',ambiguous.loc[0,'Library Genre Match']);self.assertEqual(ambiguous.loc[0,'Essentia Top Style'],'')
  playlist['File']='/a.mp3';matched=prepare_genres(attach_library_genres(playlist,library))
  self.assertEqual(matched.loc[0,'Genre Style'],'Dubstep')
  for key in ['BPM','Energy','Camelot Key']:self.assertEqual(matched.loc[0,key],playlist.loc[0,key])
  playlist['File']='/absent.mp3';self.assertEqual(attach_library_genres(playlist,library).loc[0,'Library Genre Match'],'No library match')
 def test_taxonomy_context_survives_leaf_display(self):
  source=[dict(row('A','Hardcore'),**{'Essentia Top Style':'Rock---Hardcore'}),row('B','Hardcore')]
  out=prepare_genres(pd.DataFrame(source)).to_dict('records')
  self.assertEqual(out[0]['Genre Style'],out[1]['Genre Style'])
  self.assertNotEqual(pocket_key(out[0]),pocket_key(out[1]))
 def test_import_respects_explicit_blank_user_decisions(self):
  source=dict(row('Song','Dubstep'),File='/a.mp3',**{'Genre Style':'Dubstep'})
  original=dict(Title='Song',Artist='Artist Song',File='/a.mp3',**{'Genre Style':'','Genre Family':'','Genre Source':'User genre-family review'})
  out=prepare_genres(attach_library_genres(pd.DataFrame([original]),pd.DataFrame([source])))
  self.assertEqual(out.loc[0,'Genre Style'],'');self.assertEqual(out.loc[0,'Genre Family'],'')
  self.assertEqual(out.loc[0,'Genre Source'],'User genre-family review')
 def test_style_bonus_does_not_override_tempo_or_create_resets(self):
  a=row('A','Dubstep',140);same=row('B','Dubstep',140);other=row('C','Electro House',140)
  for track in [a,same,other]:track['Camelot Key']=''
  s=opt.Settings(energy_arc='Off',allow_half_double=False)
  self.assertGreater(opt.transition_score(a,same,s)[0],opt.transition_score(a,other,s)[0])
  self.assertTrue(opt.transition_score(a,same,s)[1]['same_genre_style'])
  unsafe=row('D','Dubstep',128)
  self.assertIn(opt.transition_score(a,unsafe,s)[1]['bpm_zone'],['Hard BPM Jump','BPM Incompatible'])
  route=[row(str(i),['Dubstep','Electro House'][i%2],100+4*i) for i in range(10)]
  before=opt._route_program_stats(route,s);after=opt._route_program_stats(opt.program_genre_pockets(route,s),s)
  for key in ['hard','severe','weak','tempo_fallbacks','energy_cliffs']:self.assertLessEqual(after[key],before[key])
 def test_explicit_blank_style_and_legacy_neutrality(self):
  track=row('A','Dubstep');track['Genre Style']='';self.assertEqual(pocket_key(track),'family:edm')
  self.assertEqual(pocket_key({'Genre Family':''}), '')
  self.assertEqual(opt.genre_pocket_stats([row('A','Dubstep'),row('B','Electro House')],False)['groups'],1)
if __name__=='__main__':unittest.main()
