import unittest
from collections import Counter
from unittest.mock import patch
import optimizer as o

def tracks():
 return [dict(Title=str(i),Artist='Pair' if i in (1,4) else str(i),BPM=120,Energy=5,**{'Camelot Key':'8A','Genre Family':'Pop'}) for i in range(8)]

class ArtistRunTests(unittest.TestCase):
 def test_opt_in_pairs_and_preserves_locks_membership(self):
  r=tracks();s=o.Settings(artist_runs=('Pair',),lock_first=True,lock_last=True)
  out=o.program_artist_runs(r,s);pos=[i for i,t in enumerate(out) if t['Artist']=='Pair']
  self.assertEqual(pos[1]-pos[0],1);self.assertIs(out[0],r[0]);self.assertIs(out[-1],r[-1]);self.assertEqual(Counter(id(t) for t in r),Counter(id(t) for t in out))
 def test_disabled_is_neutral_and_counts_pair_collision(self):
  r=tracks();self.assertEqual(o.program_artist_runs(r,o.Settings()),r)
  self.assertEqual(o.artist_spacing_stats([r[1],r[4]])[0],1)
 def test_triple_is_not_exempt(self):
  r=tracks();pair=r[1];s=o.Settings(artist_runs=('Pair',))
  self.assertEqual(o.artist_spacing_stats([pair,pair,pair],s),(2,1))
 def test_held_tracks_remain_outside_warm_up(self):
  r=tracks();r[1]['Set Role']='After warm-up';r[4]['Set Role']='After warm-up'
  out=o.program_artist_runs(r,o.Settings(artist_runs=('Pair',),lock_first=True))
  self.assertEqual(o.opening_later_count(out),0)
 def test_reset_required_and_labeled(self):
  r=tracks();r[4]['BPM']=130;s=o.Settings(artist_runs=('Pair',),lock_first=True,allow_opening_reset=True,depth='Quick',energy_arc='Off')
  with patch.object(o,'program_genre_pockets',return_value=r):out,t=o.optimize(r,s)
  self.assertEqual(sum(x['quality']=='Deliberate reset' for x in t),1)
  pos=[i for i,x in enumerate(out) if x['Artist']=='Pair'];self.assertEqual(pos[1]-pos[0],1)
  self.assertEqual(t[pos[0]]['bpm_diff'],10)
 def test_family_mismatch_not_paired(self):
  r=tracks();r[4]['Genre Family']='Rock'
  self.assertEqual(o.program_artist_runs(r,o.Settings(artist_runs=('Pair',))),r)
 def test_stem_bridge_preserves_raw_score_and_bpm(self):
  r=tracks();r[4]['BPM']=200
  s=o.Settings(artist_runs=('Pair',),artist_run_bridges=True,lock_first=True,depth='Quick',energy_arc='Off')
  with patch.object(o,'program_genre_pockets',return_value=r):out,t=o.optimize(r,s)
  pos=[i for i,x in enumerate(out) if x['Artist']=='Pair']
  self.assertEqual(pos[1]-pos[0],1)
  detail=t[pos[0]];raw=o.transition_score(out[pos[0]],out[pos[1]],s)[1]
  self.assertEqual(detail['quality'],'Artist bridge')
  self.assertEqual(detail['score'],raw['score']);self.assertEqual(detail['bpm_diff'],raw['bpm_diff'])
  self.assertEqual(sorted(x['BPM'] for x in out),sorted(x['BPM'] for x in r))
if __name__=='__main__':unittest.main()
