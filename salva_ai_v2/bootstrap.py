from pathlib import Path
from types import SimpleNamespace
from tkinter import ttk
from .common.db import Database
from .common.errors import BusinessError
from .security.service import SecurityService
from .ui.app import MainWindow
from .ui.dialogs import AdminDialog


class Application:
    def __init__(self, data_dir):
        self._closed = False
        self.window = None
        self.db = None
        self.instance_lock = None
        self.views = []
        self.data_dir = Path(data_dir).resolve()
        from .common.instance import InstanceLock
        self.instance_lock = InstanceLock(self.data_dir)
        try:
            self._initialize()
        except BaseException:
            self.close()
            raise

    def _initialize(self):
        from .maintenance.restore import recover_restore
        recover_restore(self.data_dir)
        self.db = Database(self.data_dir / "dados" / "salva_ai.sqlite3")
        try:
            from .maintenance.restore import recover_restore
            from .maintenance.backup import BackupService
            self.db.upgrade(BackupService(self.db,self.data_dir / "backups"))
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
        from .ui.results import ResultsView, ReplenishmentView
        from .ui.history import HistoryView
        from .reporting.queries import ReportingQueries
        from .finance.settings import FinancialSettings
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
            finance=finance, recurrence=recurrence, delivery=delivery, settlements=settlements,
            reports=ReportingQueries(self.db), settings=FinancialSettings(self.db,self.security))
        for widget in self.window.body.winfo_children():
            widget.destroy()
        from .maintenance.backup import BackupService
        from .cash.closing import ClosingService
        self.services.backups = BackupService(self.db, self.data_dir / "backups")
        self.services.backups.db_security = self.security
        from .maintenance.restore import RestoreService
        self.services.restore = RestoreService(self.data_dir,self.services.backups,self.security)
        self.services.closing = ClosingService(self.db, cash, self.services.backups, self.services.reports)
        self.notebook = ttk.Notebook(self.window.body)
        self.notebook.pack(fill="both", expand=True)
        self.views = []
        self.groups = {}
        for name in ("Atendimento", "Controle", "Gestão"):
            group=ttk.Notebook(self.notebook)
            self.notebook.add(group,text=name)
            self.groups[name]=group
        definitions=(
            (SalesView,"Venda direta","sales_view","Atendimento"),
            (TabsView,"Comandas","tabs_view","Atendimento"),
            (DeliveryView,"Delivery","delivery_view","Atendimento"),
            (ProductsView,"Produtos e estoque","products_view","Controle"),
            (CashView,"Caixa","cash_view","Controle"),
            (HistoryView,"Histórico","history_view","Controle"),
            (FinanceView,"Financeiro mensal","finance_view","Gestão"),
            (ResultsView,"Lucro por produto","results_view","Gestão"),
            (ReplenishmentView,"Previsão de compras","replenishment_view","Gestão"))
        for cls,label,attr,group in definitions:
            container=self.groups[group]
            view=cls(container,self.services)
            container.add(view,text=label)
            setattr(self,attr,view)
            self.views.append(view)
        for key in range(1,13):
            self.window.bind(f"<F{key}>",lambda event,k=key:self.shortcut(k))
        self.refresh()
        for pending in self.services.closing.pending():
            try:
                self.services.closing.resume(pending)
            except (OSError, BusinessError):
                self.notify("Fechamento pendente. Use Retomar fechamento na aba Caixa.")
        self.refresh()

    def notify(self, message):
        if not self._closed:
            self.window.status.set(message)

    def show_view(self, view):
        self.notebook.select(view.master)
        view.master.select(view)
        view.refresh()

    def shortcut(self, key):
        group=self.window.nametowidget(self.notebook.select())
        selected=self.window.nametowidget(group.select())
        if hasattr(selected,"select_shortcut"):
            selected.select_shortcut(key)

    def refresh(self):
        if self._closed:
            return
        for view in self.views:
            try:
                view.refresh()
            except (BusinessError,ValueError):
                # Um filtro em edição não invalida uma operação já confirmada.
                continue

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
            if self.window is not None:
                self.window.destroy()
        finally:
            if self.db is not None:
                self.db.close()
            if self.instance_lock is not None:
                self.instance_lock.close()


def build_application(data_dir=None):
    return Application(Path(data_dir) if data_dir is not None else Path.home() / "SalvaAiHeadshopV2")
