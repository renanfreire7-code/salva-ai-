from pathlib import Path
from types import SimpleNamespace
from tkinter import ttk
from .common.db import Database
from .security.service import SecurityService
from .ui.app import MainWindow
from .ui.dialogs import AdminDialog


class Application:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.db = Database(self.data_dir / "dados" / "salva_ai.sqlite3")
        try:
            self.db.migrate()
            self.security = SecurityService(self.db)
            self.window = MainWindow(self.close)
            self.admin = AdminDialog(self.window, self.security)
        except BaseException:
            self.db.close()
            raise
        self._closed = False
        from .inventory.service import InventoryService
        from .pricing.service import PricingService
        from .cash.service import CashService
        from .sales.service import SalesService
        from .ui.products import ProductsView
        from .ui.sales import SalesView
        from .ui.tabs import TabsView
        from .ui.cash import CashView
        from .ui.finance import FinanceView
        from .ui.delivery import DeliveryView
        from .delivery.service import DeliveryService
        from .delivery.settlement import SettlementService
        from .finance.service import FinanceService
        from .finance.recurrence import RecurrenceService
        inventory = InventoryService(self.db, self.security)
        pricing = PricingService(self.db)
        cash = CashService(self.db, self.security)
        sales = SalesService(self.db, inventory, pricing, cash, self.security)
        finance = FinanceService(self.db, cash, self.security)
        inventory.finance = finance
        recurrence = RecurrenceService(self.db, finance)
        delivery = DeliveryService(self.db, inventory, pricing, sales, cash, finance, self.security)
        settlements = SettlementService(self.db, cash, finance, self.security)
        self.services = SimpleNamespace(application=self, inventory=inventory, pricing=pricing,
            cash=cash, sales=sales, security=self.security, clock=self.db.clock,
            finance=finance, recurrence=recurrence, delivery=delivery, settlements=settlements)
        for widget in self.window.body.winfo_children():
            widget.destroy()
        self.notebook = ttk.Notebook(self.window.body)
        self.notebook.pack(fill="both", expand=True)
        self.views = []
        for cls, label, attr in ((SalesView,"Venda direta","sales_view"),
                (TabsView,"Comandas","tabs_view"),(ProductsView,"Produtos e estoque","products_view"),
                (CashView,"Caixa","cash_view"),(FinanceView,"Financeiro mensal","finance_view"),(DeliveryView,"Delivery","delivery_view")):
            view = cls(self.notebook, self.services)
            self.notebook.add(view, text=label)
            setattr(self,attr,view)
            self.views.append(view)
        for key in range(1,13):
            self.window.bind(f"<F{key}>",lambda event,k=key:self.shortcut(k))
        self.refresh()

    def notify(self, message):
        self.window.status.set(message)

    def shortcut(self, key):
        selected=self.window.nametowidget(self.notebook.select())
        if hasattr(selected,"select_shortcut"):
            selected.select_shortcut(key)

    def refresh(self):
        for view in self.views:
            view.refresh()

    def run(self):
        if not self.security.configured and not self.admin.setup():
            self.close()
            return
        self.window.status.set("Pronto para trabalhar.")
        self.window.mainloop()

    def close(self):
        if getattr(self, "_closed", False):
            return
        self._closed = True
        try:
            if hasattr(self, "window"):
                self.window.destroy()
        finally:
            self.db.close()


def build_application(data_dir=None):
    return Application(Path(data_dir) if data_dir is not None else Path.home() / "SalvaAiHeadshopV2")

