from pathlib import Path
import tempfile
import unittest
import zipfile
import subprocess
import sys


class DistributionTest(unittest.TestCase):
    def test_clean_package_and_extracted_entrypoint(self):
        from scripts.build_v2 import build_v2
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            archive=build_v2(root/'dist')
            with zipfile.ZipFile(archive) as z:
                names=z.namelist()
                self.assertEqual(archive.name,'Salva_AI_novo_0.2.0-dev.zip')
                import json,hashlib
                manifest=json.loads(z.read('MANIFEST-SHA256.json'))
                self.assertEqual(set(manifest),set(names)-{'MANIFEST-SHA256.json'})
                for name,digest in manifest.items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest,name)
                self.assertIn('INICIAR_V2.bat',names)
                self.assertIn('salva_ai_v2/__main__.py',names)
                self.assertIn('MANIFEST-SHA256.json',names)
                self.assertIn('salva_ai_v2/assets/logo.png',names)
                self.assertIn('salva_ai_v2/assets/motorcycle.png',names)
                self.assertFalse(any(name.endswith(('.sqlite3','.pyc')) for name in names))
                self.assertFalse(any('tests_v2/' in name or 'backups/' in name for name in names))
                self.assertIsNone(z.testzip())
                z.extractall(root/'extraído com espaços')
            result=subprocess.run([sys.executable,'-m','salva_ai_v2','--help'],cwd=root/'extraído com espaços',capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('--data-dir',result.stdout)
            code="from pathlib import Path; from salva_ai_v2.bootstrap import build_application; app=build_application(Path('dados fictícios')); app.window.update(); app.close()"
            result=subprocess.run([sys.executable,'-c',code],cwd=root/'extraído com espaços',capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_single_instance_guard(self):
        from salva_ai_v2.common.instance import InstanceLock
        from salva_ai_v2.common.errors import BusinessError
        with tempfile.TemporaryDirectory() as directory:
            first=InstanceLock(Path(directory))
            try:
                with self.assertRaises(BusinessError):
                    InstanceLock(Path(directory))
            finally:
                first.close()
            second=InstanceLock(Path(directory));second.close()
