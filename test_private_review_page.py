import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from private_genre_review import ReviewConflict
class User(dict):
    is_logged_in=True
class Store:
    saved=[]
    conflict=False
    def __init__(self,*args):pass
    def state(self,owner):return {'revision':1,'decisions':{'version':1,'groups':{},'files':{}},'library_path':owner+'/test.csv.gz','library_name':'test.csv'}
    def download_library(self,owner,state):return b'Title,Artist,File,Genre Family,Original Rekordbox Genres\nSong A,Artist A,/a,,Rock\nSong B,Artist B,/b,Pop,Pop\n'
    def save(self,owner,revision,decisions=None,library=None):
        if self.conflict:raise ReviewConflict('Another device saved newer changes.')
        self.saved.append(decisions)
        return {**self.state(owner),'revision':revision+1,'decisions':decisions}
class PageTests(unittest.TestCase):
    def app(self):
        at=AppTest.from_file('pages/2_Genre_Review.py')
        at.secrets={'auth':{k:'configured' for k in ['client_id','client_secret','redirect_uri','cookie_secret','server_metadata_url']},'private_review':{'allowed_emails':['owner@example.com'],'supabase_url':'https://example.supabase.co','supabase_service_key':'placeholder'}}
        return at
    def test_denied_account_never_accesses_store(self):
        user=User(email='other@example.com',email_verified=True,iss='https://accounts.google.com',sub='1')
        with patch('streamlit.user',user),patch('private_genre_review.ReviewStore') as store:
            at=self.app().run();self.assertFalse(at.exception);store.assert_not_called();self.assertIn('cannot access',at.error[0].value)
    def test_group_save_and_stale_draft_recovery(self):
        Store.saved=[];Store.conflict=False
        user=User(email='owner@example.com',email_verified=True,iss='https://accounts.google.com',sub='1')
        with patch('streamlit.user',user),patch('private_genre_review.ReviewStore',Store):
            at=self.app().run();self.assertFalse(at.exception)
            family=next(x for x in at.selectbox if x.label=='Genre family for this group');family.select('Rock')
            Store.conflict=True
            next(x for x in at.button if x.label=='Save group choice').click().run()
            self.assertFalse(at.exception);self.assertTrue(at.error)
            # A second rerun shows the retained draft and an explicit recovery action.
            at.run();self.assertFalse(at.exception)
            self.assertTrue(any(x.label=='Discard local draft and reload saved progress' for x in at.button))
            next(x for x in at.button if x.label=='Discard local draft and reload saved progress').click().run()
            self.assertFalse(at.exception)
            Store.conflict=False
            next(x for x in at.selectbox if x.label=='Genre family for this group').select('Rock')
            next(x for x in at.button if x.label=='Save group choice').click().run()
            self.assertFalse(at.exception);self.assertEqual(Store.saved[-1]['groups']['Rock'],'Rock')
if __name__=='__main__':unittest.main()
