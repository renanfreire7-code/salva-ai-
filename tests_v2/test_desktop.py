import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from salva_ai_v2.common.errors import BusinessError


class DesktopTests(unittest.TestCase):
    def test_launcher_selects_pythonw_beside_actual_interpreter(self):
        from salva_ai_v2.desktop import find_pythonw
        with tempfile.TemporaryDirectory(prefix='Bar com acentuação ') as folder:
            root=Path(folder);exe=root/'python.exe';exe.touch();windowless=root/'pythonw.exe';windowless.touch()
            self.assertEqual(find_pythonw(exe),windowless)
            windowless.unlink()
            with self.assertRaises(BusinessError):find_pythonw(exe)

    def test_launch_uses_argument_list_correct_directory_and_no_console(self):
        from salva_ai_v2.desktop import launch
        with tempfile.TemporaryDirectory(prefix='Programa com espaços & acentuação ') as folder:
            root=Path(folder);target=root/'Bar_Simples.pyw';target.write_text('# fixture')
            pythonw=root/'pythonw.exe';pythonw.touch()
            with patch('salva_ai_v2.desktop.find_pythonw',return_value=pythonw),patch('salva_ai_v2.desktop.subprocess.Popen') as spawn:
                self.assertEqual(launch(root),0)
            args,kw=spawn.call_args
            self.assertEqual(args[0],[str(pythonw),str(target)])
            self.assertEqual(kw['cwd'],root);self.assertEqual(kw['creationflags'],0x08000000)
            self.assertNotIn('shell',kw)

    def test_check_only_never_opens_program_or_creates_account(self):
        from salva_ai_v2.desktop import launch
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'Bar_Simples.pyw').touch()
            with patch('salva_ai_v2.desktop.find_pythonw',return_value=root/'pythonw.exe'),patch('salva_ai_v2.desktop.subprocess.Popen') as spawn:
                self.assertEqual(launch(root,check_only=True),0)
            spawn.assert_not_called();self.assertFalse((root/'dados').exists())

    def test_missing_launcher_returns_visible_actionable_error(self):
        from salva_ai_v2.desktop import launch
        with tempfile.TemporaryDirectory() as folder,patch('salva_ai_v2.desktop.notify_error') as notify:
            self.assertEqual(launch(Path(folder)),1)
        self.assertIn('extra',notify.call_args.args[0].lower())

    def test_silent_entry_runs_and_closes_direct_application(self):
        from salva_ai_v2.desktop import run_program
        app=Mock()
        with patch('salva_ai_v2.bootstrap.build_application',return_value=app),patch('salva_ai_v2.desktop.notify_error') as notify:
            self.assertEqual(run_program(),0)
        app.run.assert_called_once();app.close.assert_called_once();notify.assert_not_called()

    def test_startup_error_is_visible_logged_without_secrets_and_resources_close(self):
        from salva_ai_v2.desktop import run_program
        app=Mock();app.run.side_effect=RuntimeError('fixture sensitive contents')
        with tempfile.TemporaryDirectory() as folder,patch('salva_ai_v2.desktop.Path.home',return_value=Path(folder)),patch('salva_ai_v2.bootstrap.build_application',return_value=app),patch('salva_ai_v2.desktop.notify_error') as notify:
            self.assertEqual(run_program(),1)
            contents=(Path(folder)/'SalvaAiHeadshopV2'/'logs'/'inicializacao.log').read_text()
        app.close.assert_called_once();self.assertIn('RuntimeError',contents);self.assertNotIn('fixture sensitive',contents)
        self.assertNotIn('fixture sensitive',notify.call_args.args[0])

    def test_already_open_error_is_shown_without_resetting_data(self):
        from salva_ai_v2.desktop import run_program
        with tempfile.TemporaryDirectory() as folder,patch('salva_ai_v2.desktop.Path.home',return_value=Path(folder)),patch('salva_ai_v2.bootstrap.build_application',side_effect=BusinessError('O Bar Simples já está aberto nesta pasta de dados.')),patch('salva_ai_v2.desktop.notify_error') as notify:
            self.assertEqual(run_program(),1)
            self.assertFalse((Path(folder)/'SalvaAiHeadshopV2'/'dados').exists())
        self.assertIn('já está aberto',notify.call_args.args[0])
