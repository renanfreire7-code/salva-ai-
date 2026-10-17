from dataclasses import replace,asdict
import hashlib
from pathlib import Path
import tempfile,unittest
from tests_v2.delivery_support import DeliveryCase
from salva_ai_v2.delivery.models import DeliveryDraft
from salva_ai_v2.common.commands import canonical


class DeliveryComplementTest(DeliveryCase):
    def setUp(self):
        super().setUp();self.assertIn('complement',DeliveryDraft.__dataclass_fields__,'Complemento ainda não existe')

    def test_complement_is_optional_and_survives_restart(self):
        from salva_ai_v2.delivery.queries import DeliveryQueries
        from salva_ai_v2.ui.order_details import delivery_text
        from salva_ai_v2.common.db import Database
        order=self.delivery.confirm(replace(self.draft(),complement='Apartamento 202, bloco B'),'complement')
        path=self.db.path;self.db.close();self.db=Database(path,self.clock);self.addCleanup(self.db.close)
        detail=DeliveryQueries(self.db).detail(order.id)
        self.assertEqual(detail['order']['complement'],'Apartamento 202, bloco B')
        self.assertEqual(detail['order']['reference'],'Portão azul')
        self.assertIn('Complemento: Apartamento 202, bloco B',delivery_text(detail))

    def test_previous_v02_command_fingerprint_replays_with_empty_complement(self):
        draft=replace(self.draft(),payment_timing='ON_DELIVERY',payment_channel='MONEY')
        old=asdict(draft);old.pop('complement')
        order=self.delivery.confirm(draft,'old')
        fingerprint=hashlib.sha256(canonical({'draft':old}).encode()).hexdigest()
        self.assertEqual(self.scalar('SELECT fingerprint FROM command_results WHERE id=?',('old',)),fingerprint)
        self.assertEqual(self.delivery.confirm(draft,'old'),order)
        self.assertEqual(self.scalar('SELECT count(*) FROM delivery_orders'),1)

    def test_redelivery_copies_complement_and_snapshots(self):
        from salva_ai_v2.delivery.queries import DeliveryQueries
        draft=replace(self.draft(),payment_timing='ON_DELIVERY',payment_channel='MONEY',complement='Fundos')
        order=self.delivery.confirm(draft,'old');self.delivery.cancel(order.id,self.grant('delivery.cancel'),'Cliente reagendou','cancel')
        new=self.delivery.redeliver(order.id,self.grant('delivery.redeliver'),'Enviar novamente','retry')
        detail=DeliveryQueries(self.db).detail(new)
        self.assertEqual(detail['order']['complement'],'Fundos');self.assertEqual(detail['order']['previous_order_id'],order.id)
        self.assertEqual(detail['order']['state'],'PREPARING');self.assertEqual(self.scalar('SELECT count(*) FROM trips'),0)


class DeliveryComplementUITest(unittest.TestCase):
    def test_editor_error_keeps_complement(self):
        from tests_v2.application_support import build_test_application
        with tempfile.TemporaryDirectory() as directory:
            app=build_test_application(Path(directory))
            try:
                editor=app.delivery_view.create();self.assertIn('complement',editor.fields)
                for key,value in dict(customer='Cliente',phone='123',address='Rua',complement='Apto 202').items():editor.fields[key].insert(0,value)
                self.assertFalse(editor.submit());self.assertEqual(editor.fields['complement'].get(),'Apto 202')
                editor.winfo_toplevel().destroy()
            finally:app.close()
