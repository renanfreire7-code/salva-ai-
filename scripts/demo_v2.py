"""Demonstração isolada: python -m scripts.demo_v2. Nunca abre o banco da loja."""
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from salva_ai_v2.bootstrap import build_application
from salva_ai_v2.inventory.models import PurchaseLine


def main():
    with TemporaryDirectory(prefix='salva_ai_v2_demo_') as folder:
        app = build_application(Path(folder))
        try:
            for name, price in (('Cerveja lata', 500), ('Água mineral', 300), ('Refrigerante', 600)):
                pid = app.services.inventory.create_product(name, price, 12, 6, str(uuid4()))
                app.services.inventory.receive_purchase([PurchaseLine(pid, 24, price * 12)], 0,
                    app.services.clock.today(), app.services.clock.today(), str(uuid4()))
            app.refresh()
            app.run()
        finally:
            app.close()


if __name__ == '__main__':
    main()
