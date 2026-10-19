from tkinter import messagebox, simpledialog
from ..common.errors import BusinessError


class AdminDialog:
    def __init__(self, parent, security):
        self.parent, self.security = parent, security

    def setup(self):
        pin = simpledialog.askstring("Configurar acesso", "Crie um PIN de três dígitos:", show="*", parent=self.parent)
        if pin is None:
            return False
        confirm = simpledialog.askstring("Confirmar PIN", "Digite o PIN novamente:", show="*", parent=self.parent)
        if confirm != pin:
            messagebox.showerror("PIN não confirmado", "Os números não coincidem. Tente novamente.", parent=self.parent)
            return False
        try:
            key = self.security.setup(pin)
        except BusinessError as error:
            messagebox.showerror("Não foi possível configurar", str(error), parent=self.parent)
            return False
        messagebox.showinfo("Guarde sua chave de recuperação",
            "Guarde esta chave fora do computador. Ela permite trocar o PIN.\n\n" + key +
            "\n\nEla não será exibida novamente.", parent=self.parent)
        return True

    def request(self, action):
        if not self.security.configured and not self.setup():return None
        pin = simpledialog.askstring("Autorização administrativa", f"Informe seu PIN de {self.security.pin_length} dígitos:", show="*", parent=self.parent)
        if pin is None:
            return None
        try:
            return self.security.authorize(pin, action)
        except BusinessError as error:
            messagebox.showerror("Operação não autorizada", str(error), parent=self.parent)
            return None

    def recover(self):
        key = simpledialog.askstring("Recuperar acesso", "Chave de recuperação:", show="*", parent=self.parent)
        if key is None:
            return
        pin = simpledialog.askstring("Novo PIN", "Novo PIN de três dígitos:", show="*", parent=self.parent)
        if pin is None:
            return
        confirm = simpledialog.askstring("Confirmar novo PIN", "Digite novamente:", show="*", parent=self.parent)
        if confirm != pin:
            raise BusinessError("Os números não coincidem.")
        new_key = self.security.recover(key, pin)
        messagebox.showinfo("Nova chave de recuperação", "A chave anterior não funciona mais. Guarde a nova chave:\n\n" + new_key, parent=self.parent)
