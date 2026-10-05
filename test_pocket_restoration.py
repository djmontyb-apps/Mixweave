import unittest
from collections import Counter
import optimizer as opt


def tracks(n=12):
    return [dict(Title=str(i),Artist='Artist '+str(i),BPM=120,Energy=70,
                 **{'Camelot Key':'8A','Genre Family':['Hip-Hop/R&B','Pop','Country'][i%3]}) for i in range(n)]


class PocketRestorationTests(unittest.TestCase):
    def test_no_single_song_pop_detour_and_toggle(self):
        rows=tracks(3);rows[2]['Genre Family']='Hip-Hop/R&B'
        on=opt.program_genre_pockets(rows,opt.Settings(energy_arc='Off'))
        self.assertEqual(opt.genre_pocket_stats(on)['islands'],0)
        off=opt.program_genre_pockets(rows,opt.Settings(genre_pockets=False))
        self.assertEqual(off,rows)

    def test_large_crate_preserves_membership_locks_and_guardrails(self):
        rows=tracks(100)
        for i,t in enumerate(rows):t['BPM']=100+(i%7)*2
        s=opt.Settings(lock_first=True,lock_last=True)
        before=opt._route_program_stats(rows,s)
        result=opt.program_genre_pockets(rows,s)
        after=opt._route_program_stats(result,s)
        self.assertEqual(Counter(t['Title'] for t in rows),Counter(t['Title'] for t in result))
        self.assertIs(result[0],rows[0]);self.assertIs(result[-1],rows[-1])
        for key in ['hard','severe','weak','energy_cliffs','adjacent_artist','near_artist','peak_low','build_low']:
            self.assertLessEqual(after[key],before[key],key)
        self.assertLessEqual(opt.genre_pocket_stats(result)['cost'],opt.genre_pocket_stats(rows)['cost'])

    def test_optimize_invokes_final_pocket_pass(self):
        from unittest.mock import patch
        real=opt.program_genre_pockets
        with patch.object(opt,'program_genre_pockets',wraps=real) as final_pass:
            order,transitions=opt.optimize(tracks(9),opt.Settings(depth='Quick',energy_arc='Off'))
        final_pass.assert_called_once()
        self.assertEqual(len(order),9);self.assertEqual(len(transitions),8)
        for i,transition in enumerate(transitions):
            self.assertAlmostEqual(transition['score'],opt.transition_score(order[i],order[i+1],opt.Settings(depth='Quick',energy_arc='Off'))[1]['score'])


if __name__=='__main__':unittest.main()
