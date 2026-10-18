"""Demonstração isolada: python -m scripts.demo_v2. Nunca abre o banco da loja."""
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from salva_ai_v2.bootstrap import build_application
from salva_ai_v2.inventory.models import PurchaseLine


def main():
    with TemporaryDirectory(prefix='salva_ai_v2_demo_') as folder:
        public=Path.home()/'SalvaAiHeadshopV2'/'auth_service.json'
        if public.is_file():
            from salva_ai_v2.security.email_config import load_email_config,save_email_config
            config=load_email_config(public)
            if config:save_email_config(Path(folder)/'auth_service.json',config)
        app = build_application(Path(folder))
        try:
            def start(session):
                app.unlock(session)
                for name, price in (('Cerveja lata', 500), ('Água mineral', 300), ('Refrigerante', 600)):
                    pid = app.services.inventory.create_product(name, price, 12, 6, str(uuid4()))
                    app.services.inventory.receive_purchase([PurchaseLine(pid, 24, price * 12)], 0,
                        app.services.clock.today(), app.services.clock.today(), str(uuid4()))
                products=app.services.inventory.products()
                app.services.pricing.set_promotion(next(p["id"] for p in products if p["name"]=="Cerveja lata"),3,1200,True,str(uuid4()))
                for key,product in enumerate(products,1):
                    app.services.inventory.assign_shortcut(key,product["id"],str(uuid4()))
                app.window.status.set("Demonstração isolada: dados fictícios; use seu acesso fictício e abra o caixa para ensaiar.")
                app.refresh()
            app.access_view.on_authenticated=start
            app.run()
        finally:
            app.close()


if __name__ == '__main__':
    main()
