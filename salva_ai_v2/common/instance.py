import os
from pathlib import Path
from .errors import BusinessError


class InstanceLock:
    """Um processo por pasta de dados; o sistema operacional libera após falha."""
    def __init__(self,data_dir):
        root=Path(data_dir)
        root.mkdir(parents=True,exist_ok=True)
        self.handle=(root/".salva_ai.lock").open("a+b")
        try:
            if os.name=="nt":
                import msvcrt
                self.handle.seek(0,2)
                if not self.handle.tell():
                    self.handle.write(b"0");self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise BusinessError("O Salva AI já está aberto nesta pasta de dados.") from None

    def close(self):
        if self.handle.closed:
            return
        if os.name=="nt":
            import msvcrt
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close()
