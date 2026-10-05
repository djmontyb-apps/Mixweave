import unittest
from unittest.mock import patch
import optimizer as opt


def rows():
    result = [dict(Title=str(i), Artist=str(i), BPM=bpm, Energy=5,
                   **{'Camelot Key': '8A', 'Genre Family': 'Country'})
              for i, bpm in enumerate([141,142,148,81,87,90,98,106,114,122,130,136])]
    for i in [1,2]: result[i]['Set Role']='After warm-up'
    return result


class OpeningPlanTests(unittest.TestCase):
    def test_opener_and_genre_runs_preserved_with_one_reset(self):
        original = rows()
        s = opt.Settings(lock_first=True,allow_opening_reset=True)
        result = opt.program_opening(original,s)
        self.assertIs(result[0], original[0])
        self.assertEqual(opt.opening_later_count(result),0)
        self.assertEqual(opt._route_program_stats(result,s)['hard'],1)
        self.assertEqual(sorted(id(t) for t in result),sorted(id(t) for t in original))
        self.assertLessEqual(opt.genre_pocket_stats(result)['cost'],opt.genre_pocket_stats(original)['cost'])

    def test_reset_opt_out_preserves_tempo_safety(self):
        original = rows();s=opt.Settings(lock_first=True)
        result=opt.program_opening(original,s)
        self.assertLessEqual(opt._route_program_stats(result,s)['hard'],opt._route_program_stats(original,s)['hard'])

    def test_no_roles_is_neutral(self):
        original=rows()
        for t in original:t.pop('Set Role',None)
        self.assertEqual(opt.program_opening(original,opt.Settings(allow_opening_reset=True)),original)

    def test_reset_label_does_not_hide_bpm_or_score(self):
        original=rows();s=opt.Settings(depth='Quick',lock_first=True,allow_opening_reset=True,energy_arc='Off')
        # Isolate integration with the final programming step from search randomness.
        with patch.object(opt,'program_genre_pockets',return_value=original):
            result,transitions=opt.optimize(original,s)
        reset=[(i,t) for i,t in enumerate(transitions) if t['quality']=='Deliberate reset']
        self.assertEqual(len(reset),1)
        i,detail=reset[0]
        raw=opt.transition_score(result[i],result[i+1],s)[1]
        self.assertEqual(detail['score'],raw['score'])
        self.assertEqual(detail['bpm_diff'],raw['bpm_diff'])
        self.assertIn('clean cut or fade',detail['reason'])

if __name__=='__main__':unittest.main()
