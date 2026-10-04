import io
import unittest
from genre_metadata import RekordboxGenres, genre_family


def xml(rows):
    return io.BytesIO(('<DJ_PLAYLISTS><COLLECTION>'+rows+'</COLLECTION></DJ_PLAYLISTS>').encode())


class GenreTests(unittest.TestCase):
    def test_recognized_and_ambiguous_labels(self):
        for genre, expected in [('Salsa','Latin'),('Tech House','EDM'),('R&B','Hip-Hop/R&B'),('Country ','Country'),('Nu Disco','Disco/Funk'),('Line Dance','Line Dance / Group Participation')]:
            self.assertEqual(genre_family(genre),expected)
        for genre in ['Miscellaneous','Billboard',"Eras / 80's",'Country / Rock','']:
            self.assertEqual(genre_family(genre),'')

    def test_duplicate_entries_and_url_encoding(self):
        rows='<TRACK Name="Song" Artist="Artist" Genre="Country" Location="file://localhost/Music/Song%20One.mp3"/><TRACK Name="Song" Artist="Artist" Genre="" Location="file://localhost/Music/Song%20One.mp3"/>'
        genres=RekordboxGenres(xml(rows))
        self.assertEqual(genres.lookup('/Music/Song One.mp3')[0],'Country')
        self.assertEqual(genres.lookup(title='Song - 8A/8B - 6',artist='Artist')[0],'Country')
        self.assertEqual(genres.lookup('/Music/Other.mp3',title='Song',artist='Artist')[0],'')

    def test_conflicts_and_multiple_editions(self):
        rows='<TRACK Name="Song" Artist="Artist" Genre="Country" Location="file://localhost/a.mp3"/><TRACK Name="Song" Artist="Artist" Genre="Rock" Location="file://localhost/a.mp3"/><TRACK Name="Song" Artist="Artist" Genre="Pop" Location="file://localhost/b.mp3"/>'
        genres=RekordboxGenres(xml(rows))
        self.assertIn('Conflicting',genres.lookup('/a.mp3')[1])
        self.assertIn('Ambiguous',genres.lookup(title='Song',artist='Artist')[1])
        self.assertEqual(genres.lookup('/b.mp3')[0],'Pop')

    def test_non_collection_is_rejected(self):
        with self.assertRaises(ValueError):RekordboxGenres(io.BytesIO(b'<root/>'))


if __name__=='__main__':unittest.main()
