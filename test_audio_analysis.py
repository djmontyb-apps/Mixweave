import unittest
import pandas as pd
from audio_analysis import attach_features


def scan(file='original.mp3', title='Song - 8A/8B - 6', artist='Artist'):
    return dict(Title=title, Artist=artist, File=file, Status='OK',
                Danceability=100, Valence=63, Acousticness=1,
                **{'Loudness LUFS': -11.551, 'BPM': 120, 'Camelot Key': '8A/8B', 'Energy': 6})


class FeatureImportTests(unittest.TestCase):
    def test_preserves_metadata_and_retains_replaced_scores(self):
        playlist=pd.DataFrame([dict(Title='Song', Artist='Artist', BPM=122,
                                   Energy=8, Danceability=70, **{'Camelot Key':'2A/3A'})])
        out=attach_features(playlist, pd.DataFrame([scan()]))
        self.assertEqual(out.loc[0,'BPM'],122)
        self.assertEqual(out.loc[0,'Camelot Key'],'2A/3A')
        self.assertEqual(out.loc[0,'Energy'],8)
        self.assertEqual(out.loc[0,'Playlist Danceability'],70)
        self.assertEqual(out.loc[0,'Danceability'],100)
        self.assertIn('unverified',out.loc[0,'Essentia Match'])

    def test_ambiguous_edits_require_exact_path(self):
        sources=pd.DataFrame([scan(),scan(file='intro.mp3')])
        playlist=pd.DataFrame([dict(Title='Song',Artist='Artist')])
        out=attach_features(playlist,sources)
        self.assertTrue(pd.isna(out.loc[0,'Danceability']))
        playlist['File']='intro.mp3'
        out=attach_features(playlist,sources)
        self.assertEqual(out.loc[0,'Essentia File'],'intro.mp3')
        playlist['File']='absent.mp3'
        self.assertTrue(pd.isna(attach_features(playlist,sources).loc[0,'Danceability']))

    def test_failed_analysis_cannot_replace_existing_values(self):
        source=scan();source['Status']='ERROR'
        out=attach_features(pd.DataFrame([dict(Title='Song',Artist='Artist',Valence=42)]),pd.DataFrame([source]))
        self.assertEqual(out.loc[0,'Valence'],42)

    def test_garth_preference_and_other_performers(self):
        sources=pd.DataFrame([scan(title='Friends in Low Places',artist='Garth Brooks')])
        playlist=pd.DataFrame([dict(Title='Friends in Low Places',Artist='Brooks Jefferson'),
                               dict(Title='Friends in Low Places',Artist='Someone Else')])
        out=attach_features(playlist,sources)
        self.assertIn('Garth Brooks',out.loc[0,'Essentia Match'])
        self.assertTrue(pd.isna(out.loc[1,'Danceability']))

    def test_wrong_scale_rejected(self):
        source=scan();source['Acousticness']=101
        with self.assertRaises(ValueError):
            attach_features(pd.DataFrame([dict(Title='Song',Artist='Artist')]),pd.DataFrame([source]))


if __name__=='__main__':unittest.main()
