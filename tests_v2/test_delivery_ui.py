from pathlib import Path
import tempfile
import unittest


class DeliveryUITest(unittest.TestCase):
    def test_delivery_states_are_separate_from_payment(self):
        from tests_v2.application_support import build_test_application as build_application
        with tempfile.TemporaryDirectory() as directory:
            app = build_application(Path(directory))
            try:
                self.assertIn('Pagamento', app.delivery_view.tree['columns'])
                self.assertIn('Situação', app.delivery_view.tree['columns'])
            finally:
                app.close()
