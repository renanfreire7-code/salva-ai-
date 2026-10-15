"""Restaurador offline: executar apenas com o programa fechado."""
from pathlib import Path
from datetime import datetime
import sqlite3
import tkinter as tk
from tkinter import filedialog,messagebox
ROOT=Path.home()/'SalvaAiHeadshop'
TARGET=ROOT/'dados'/'bar.sqlite3'
app=tk.Tk();app.withdraw()
messagebox.showinfo('Restauração segura','Feche o Salva ai headshop antes de continuar.\n\nEste assistente verificará o backup e guardará uma cópia do banco atual.')
source=filedialog.askopenfilename(title='Selecione o backup SQLite',initialdir=str(ROOT/'backups'),filetypes=[('Backups SQLite','*.sqlite3 *.db *.sqlite'),('Todos os arquivos','*.*')])
if source:
    try:
        con=sqlite3.connect(f'file:{Path(source).as_posix()}?mode=ro',uri=True)
        try:
            valid=con.execute('PRAGMA integrity_check').fetchone()[0]
            tables={r[0] for r in con.execute('SELECT name FROM sqlite_master WHERE type="table"')}
            if valid!='ok' or not {'products','tabs','sales','cash_sessions','stock_movements'}.issubset(tables): raise ValueError('Arquivo não é um backup válido do Salva ai headshop.')
        finally:con.close()
        if messagebox.askyesno('Confirmar restauração','O banco atual será preservado em uma pasta de segurança.\nDeseja restaurar o backup selecionado?'):
            TARGET.parent.mkdir(parents=True,exist_ok=True)
            safety=ROOT/'antes_da_restauracao';safety.mkdir(parents=True,exist_ok=True)
            timestamp=datetime.now().strftime('%Y%m%d_%H%M%S')
            # Backup consistente do banco atual, sem apagar nem substituir o original antes da validação.
            if TARGET.exists():
                a=sqlite3.connect(str(TARGET));b=sqlite3.connect(str(safety/f'banco_anterior_{timestamp}.sqlite3'))
                try:a.backup(b)
                finally:b.close();a.close()
            # Evita substituir arquivos de banco em uso pelo aplicativo.
            target=sqlite3.connect(str(TARGET),timeout=1)
            try:
                target.execute('BEGIN EXCLUSIVE');target.execute('ROLLBACK')
                restored=sqlite3.connect(f'file:{Path(source).as_posix()}?mode=ro',uri=True)
                try:restored.backup(target)
                finally:restored.close()
            finally:target.close()
            messagebox.showinfo('Restauração concluída','Dados restaurados. Agora abra novamente o sistema.\nCópia anterior em: '+str(safety))
    except Exception as e:messagebox.showerror('Não foi possível restaurar',str(e)+'\n\nSe o sistema estiver aberto, feche-o e tente novamente.')
app.destroy()
