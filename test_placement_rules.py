import unittest
from collections import Counter
from copy import deepcopy
import optimizer as opt


def track(i,bpm=120,role='Automatic'):
    return {'Title':f'Song {i}','Artist':f'Artist {i}','BPM':bpm,'Camelot Key':'8A',
            'Energy':5,'Genre Family':['Pop','Country','Rock'][i%3],
            'Set Role':role,'File':f'/sample/{i}.mp3'}


class PlacementRulesTests(unittest.TestCase):
    def test_saved_opener_is_honored_by_optimizer_without_app_reordering(self):
        rows=[track(i,role='Opener' if i==7 else 'After warm-up' if i in [0,1,3] else 'Automatic') for i in range(15)]
        before=deepcopy(rows)
        ordered,_=opt.optimize(rows,opt.Settings(depth='Quick',energy_arc='Off'))
        self.assertIs(ordered[0],rows[7])
        self.assertEqual(opt.opening_later_count(ordered),0)
        self.assertEqual(Counter(t['File'] for t in ordered),Counter(t['File'] for t in rows))
        self.assertEqual(rows,before)

    def test_reverse_deferred_block_can_avoid_a_hard_jump(self):
        bpms=[141,142,148,140,136,130,125,119,112,105,98,90,87,81]
        rows=[track(i,bpm,'After warm-up' if i in [1,2] else 'Automatic') for i,bpm in enumerate(bpms)]
        rows[0]['Set Role']='Opener'
        s=opt.Settings(lock_first=True,allow_opening_reset=False)
        result=opt.program_opening(rows,s)
        self.assertEqual(opt.opening_later_count(result),0)
        self.assertEqual(opt._route_program_stats(result,s)['hard'],0)
        self.assertEqual([t['BPM'] for t in result[-2:]],[148,142])

    def test_impossible_choices_raise_instead_of_returning_wrong_playlist(self):
        rows=[track(0,80),track(1,80,'After warm-up')]+[track(i,140) for i in range(2,12)]
        s=opt.Settings(lock_first=True,allow_half_double=False,allow_opening_reset=False)
        with self.assertRaisesRegex(ValueError,'could not honor'):
            opt.program_opening(rows,s)

    def test_too_many_deferred_tracks_rejected_before_search(self):
        rows=[track(i,role='After warm-up') for i in range(3)]
        with self.assertRaisesRegex(ValueError,'Too many'):
            opt.optimize(rows,opt.Settings())

    def test_conflicting_opener_and_last_lock_rejected(self):
        rows=[track(0),track(1,role='Opener')]
        with self.assertRaisesRegex(ValueError,'locked last'):
            opt.optimize(rows,opt.Settings(lock_last=True))

    def test_multiple_openers_rejected(self):
        with self.assertRaisesRegex(ValueError,'only one'):
            opt.optimize([track(0,role='Opener'),track(1,role='Opener')],opt.Settings())

    def test_large_set_retains_all_instances_and_saved_roles(self):
        rows=[track(i,role='After warm-up' if i in [1,2,3] else 'Opener' if i==40 else 'Automatic') for i in range(100)]
        ordered,_=opt.optimize(rows,opt.Settings(depth='Quick',energy_arc='Off'))
        self.assertIs(ordered[0],rows[40])
        self.assertEqual(opt.opening_later_count(ordered),0)
        self.assertEqual(Counter(t['File'] for t in ordered),Counter(t['File'] for t in rows))

if __name__=='__main__':unittest.main()
