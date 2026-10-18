import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from salva_ai_v2.common.errors import BusinessError

URL='https://fixtureproject.supabase.co'
KEY='sb_publishable_'+'fixture'*8


class EmailConfigTest(unittest.TestCase):
    def test_public_config_rejects_secret_keys_and_project_change(self):
        from salva_ai_v2.security.email_config import SupabaseConfig,load_email_config,save_email_config
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'auth_service.json'
            self.assertIsNone(load_email_config(path))
            for url in ('http://fixtureproject.supabase.co',URL+'/wrong','https://evil.example',URL+'?x=1','https://user@fixtureproject.supabase.co'):
                with self.subTest(url=url),self.assertRaises(BusinessError):SupabaseConfig(url,KEY)
            role=base64.urlsafe_b64encode(json.dumps({'role':'service_role'}).encode()).decode().rstrip('=')
            for key in ('sb_secret_not_public','head.'+role+'.signature','anything'):
                with self.subTest(key=key),self.assertRaises(BusinessError):SupabaseConfig(URL,key)
            save_email_config(path,SupabaseConfig(URL,KEY))
            original=path.read_bytes()
            with self.assertRaises(BusinessError):save_email_config(path,SupabaseConfig('https://anotherproject.supabase.co',KEY),bound_issuer=URL)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(load_email_config(path).url,URL)
            with self.assertRaises(BusinessError):load_email_config(path,bound_issuer='https://anotherproject.supabase.co')

    def test_config_writes_only_public_settings_atomically(self):
        from salva_ai_v2.security.email_config import SupabaseConfig,load_email_config,save_email_config
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'auth_service.json';save_email_config(path,SupabaseConfig(URL,KEY));original=path.read_bytes()
            self.assertEqual(set(json.loads(original)),{'url','publishable_key'})
            with patch('salva_ai_v2.security.email_config.os.replace',side_effect=OSError('disk')):
                with self.assertRaises(BusinessError):save_email_config(path,SupabaseConfig(URL,KEY+'next'))
            self.assertEqual(path.read_bytes(),original)
            path.write_text(json.dumps({'url':URL,'publishable_key':KEY,'smtp_password':'not permitted'}))
            with self.assertRaises(BusinessError):load_email_config(path)
