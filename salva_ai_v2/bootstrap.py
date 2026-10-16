from pathlib import Path
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

