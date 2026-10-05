import unittest
import optimizer as opt


def track(title, bpm, key='8A'):
    return {'Title': title, 'Artist': title, 'BPM': bpm, 'Camelot Key': key, 'Energy': 70}


class TempoFallbackTests(unittest.TestCase):
    def test_workable_normal_link_beats_exact_double_time(self):
        rows = [track('current', 80), track('normal', 84), track('double', 160)]
        s = opt.Settings(energy_arc='Off')
        index, _ = opt._choose_next(0, [1, 2], rows, s, [(2, 1)] * 3)
        self.assertEqual(index, 1)

    def test_fallback_remains_available_when_normal_link_is_impractical(self):
        rows = [track('current', 80), track('far', 110), track('double', 160)]
        index, _ = opt._choose_next(0, [1, 2], rows, opt.Settings(), [(2, 1)] * 3)
        self.assertEqual(index, 2)

    def test_route_prefers_fewer_fallbacks_and_retains_bpm(self):
        rows = [track('a', 80), track('b', 84), track('c', 160), track('d', 164)]
        s = opt.Settings(energy_arc='Off')
        normal_run = [rows[0], rows[1], rows[2], rows[3]]
        alternating = [rows[1], rows[2], rows[0], rows[3]]
        self.assertGreater(opt.objective(normal_run, s), opt.objective(alternating, s))
        result, _ = opt.optimize(rows, opt.Settings(depth='Quick', energy_arc='Off'))
        self.assertEqual(sorted(t['BPM'] for t in result), [80, 84, 160, 164])
        self.assertEqual(opt._route_program_stats(result, s)['tempo_fallbacks'], 1)

    def test_disabled_fallback_reports_native_jump(self):
        _, d = opt.transition_score(track('a', 80), track('b', 160), opt.Settings(allow_half_double=False))
        self.assertEqual(d['tempo_mode'], 'Normal')
        self.assertEqual(d['bpm_diff'], 80)


if __name__ == '__main__':
    unittest.main()
