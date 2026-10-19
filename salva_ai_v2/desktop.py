"""Inicialização Windows sem console, usando o mesmo programa e diretório de dados."""
from datetime import datetime,timezone
from pathlib import Path
import subprocess
import sys
from .common.errors import BusinessError


def notify_error(message):
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,message,'Bar Simples',0x10)
    else:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        try:messagebox.showerror('Bar Simples',message,parent=root)
        finally:root.destroy()


def find_pythonw(executable=None):
    executable=Path(executable or sys.executable).resolve()
    candidate=executable.with_name('pythonw.exe')
    if not candidate.is_file():
        raise BusinessError('O Python sem console não foi encontrado. Repare a instalação do Python3.12 ou superior com Tcl/Tk pelo instalador oficial.')
    return candidate


def _record_failure(error):
    # O conteúdo da exceção não entra no log: pode incluir dados da operação.
    try:
        log=Path.home()/'SalvaAiHeadshopV2'/'logs'/'inicializacao.log'
        log.parent.mkdir(parents=True,exist_ok=True)
        if log.exists() and log.stat().st_size>65536:
            log.replace(log.with_name('inicializacao-anterior.log'))
        with log.open('a',encoding='utf-8') as stream:
            stream.write(datetime.now(timezone.utc).isoformat()+' '+type(error).__name__+'\n')
    except OSError:
        pass


def launch(root,*,check_only=False):
    try:
        root=Path(root).resolve();entry=root/'Bar_Simples.pyw'
        if not entry.is_file():raise BusinessError('Extraia todo o ZIP antes de abrir o Bar Simples. O arquivo Bar_Simples.pyw está ausente.')
        if sys.version_info<(3,12):raise BusinessError('Instale Python3.12 ou superior com Tcl/Tk para abrir o Bar Simples.')
        import tkinter  # Confirma a biblioteca obrigatória antes de criar o atalho.
        pythonw=find_pythonw()
        if not check_only:
            subprocess.Popen([str(pythonw),str(entry)],cwd=root,creationflags=0x08000000,
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
        return 0
    except Exception as error:
        _record_failure(error)
        message=str(error) if isinstance(error,BusinessError) else 'Não foi possível abrir o Bar Simples. Confira a instalação do Python com Tcl/Tk e extraia todo o pacote novamente.'
        notify_error(message);return 1


def run_program():
    try:
        from .bootstrap import build_application
        app=build_application()
        try:app.run()
        finally:app.close()
        return 0
    except Exception as error:
        _record_failure(error)
        message=str(error) if isinstance(error,BusinessError) else 'Não foi possível abrir o Bar Simples. Seus dados foram mantidos. Tente INICIAR_V2.bat para diagnóstico; o registro fica em SalvaAiHeadshopV2/logs/inicializacao.log na sua pasta de usuário.'
        notify_error(message);return 1
