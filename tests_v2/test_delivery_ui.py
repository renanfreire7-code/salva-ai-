from pathlib import Path
import tempfile
import unittest


class DeliveryUITest(unittest.TestCase):
    def test_delivery_states_are_separate_from_payment(self):
        from salva_ai_v2.bootstrap import build_application
        with tempfile.TemporaryDirectory() as directory:
            app = build_application(Path(directory))
            try:
                self.assertIn('Pagamento', app.delivery_view.tree['columns'])
                self.assertIn('Situação', app.delivery_view.tree['columns'])
            finally:
                app.close()
