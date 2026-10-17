from pathlib import Path
import tempfile
import unittest


class NavigationTest(unittest.TestCase):
    def setUp(self):
        from salva_ai_v2.bootstrap import build_application
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app=build_application(Path(self.temp.name));self.addCleanup(self.app.close)

    def test_all_destinations_and_identity_are_available(self):
        self.assertIn('SALVA AI HEADSHOP',self.app.window.title())
        self.assertEqual(len(self.app.views),11)
        for view in self.app.views:
            self.app.show_view(view);self.app.window.update()
            self.assertIs(self.app.shell.selected_view,view)
            self.assertTrue(view.winfo_ismapped())
        self.assertTrue(self.app.window.logo_label['image'])
        self.assertTrue(self.app.delivery_view.motorcycle_label['image'])

    def test_navigation_preserves_current_cart(self):
        from salva_ai_v2.inventory.models import PurchaseLine
        self.app.security.setup('681');s=self.app.services
        pid=s.inventory.create_product('Produto',500,1,0,'product')
        s.inventory.receive_purchase([PurchaseLine(pid,10,2000)],0,s.clock.today(),s.clock.today(),'buy')
        s.cash.open(10000,'open')
        self.app.sales_view.add_product(pid,2)
        cart=self.app.sales_view.cart_id
        self.app.show_view(self.app.products_view)
        self.app.show_view(self.app.sales_view)
        self.assertEqual(self.app.sales_view.cart_id,cart)
        self.assertEqual(self.app.sales_view.total_cents,1000)

    def test_assets_load_offline_at_header_and_icon_sizes(self):
        from salva_ai_v2.ui.assets import load_asset
        logo=load_asset(self.app.window,'logo.png',56)
        moto=load_asset(self.app.window,'motorcycle.png',24)
        self.assertGreater(logo.width(),40)
        self.assertLessEqual(logo.width(),56)
        self.assertLessEqual(moto.width(),24)

    def test_asset_load_preserves_png_dimensions_when_decoded(self):
        from pathlib import Path
        from math import ceil
        import struct
        from salva_ai_v2.ui.assets import load_asset
        for name,size in [('logo.png',56),('motorcycle.png',24)]:
            data=(Path('salva_ai_v2/assets')/name).read_bytes()
            width,height=struct.unpack('>II',data[16:24]);factor=ceil(max(width,height)/size)
            loaded=load_asset(self.app.window,name,size)
            self.assertEqual((loaded.width(),loaded.height()),(ceil(width/factor),ceil(height/factor)))
