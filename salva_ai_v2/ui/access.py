"""Entrada offline: nenhum controle de operação antes da autenticação."""
import sqlite3
import tkinter as tk
from tkinter import ttk,messagebox
from ..common.errors import BusinessError


class AccessView(ttk.Frame):
    def __init__(self,parent,accounts,security,on_authenticated,on_cancel,*,emails=None):
        super().__init__(parent,padding=(30,18))
        self.accounts,self.security=accounts,security
        self.emails=emails
        self.on_authenticated,self.on_cancel=on_authenticated,on_cancel
        self._focus_job=None;self.busy=False;self.inputs={}
        self.mode=accounts.mode
        self.error=tk.StringVar();self.show_password=tk.BooleanVar();self.proof_kind=tk.StringVar(value='PIN atual')
        self.columnconfigure(0,weight=4);self.columnconfigure(1,weight=6);self.rowconfigure(0,weight=1)
        self.brand=ttk.Frame(self,padding=(20,30));self.brand.grid(row=0,column=0,sticky='nsew',padx=(0,36))
        from .branding import load_logo
        self.logo=load_logo(self,280)
        self.logo_label=ttk.Label(self.brand,image=self.logo)
        self.logo_label.pack(anchor='w',pady=(12,20))
        ttk.Label(self.brand,text='Seu bar, organizado.',style='Title.TLabel',foreground='#a34728').pack(anchor='w',pady=(0,12))
        ttk.Label(self.brand,text='Vendas, comandas e entregas\nno mesmo lugar.',justify='left',wraplength=300).pack(anchor='w')
        ttk.Label(self.brand,text='Funciona sem internet.',style='Muted.TLabel').pack(anchor='w',pady=24)
        self.form=ttk.Frame(self,padding=(12,0));self.form.grid(row=0,column=1,sticky='nsew');self.form.columnconfigure(0,weight=1)
        self.set_mode(self.mode)

    def set_mode(self,mode):
        if self._focus_job:self.after_cancel(self._focus_job);self._focus_job=None
        self.mode=mode if mode in ('RECOVERY','ENROLL') else self.accounts.mode
        for child in self.form.winfo_children():child.destroy()
        self.inputs={};self.error.set('');self.show_password.set(False)
        if self.mode!='LOGIN':
            from .email_access import EmailAccessWizard
            self.wizard=EmailAccessWizard(self.form,self.accounts,self.emails,self.security,
                mode='RECOVER' if self.mode=='RECOVERY' else self.mode,on_completed=self.email_completed,
                on_cancel=lambda:self.set_mode('LOGIN') if self.accounts.configured else self.on_cancel())
            self.wizard.grid(row=0,column=0,sticky='nsew')
            self.primary_button=self.wizard.primary_button
            return
        ttk.Label(self.form,text='Entrar no seu bar',style='Title.TLabel').grid(row=0,column=0,sticky='w',pady=(4,8))
        ttk.Label(self.form,text='Informe o usuário e a senha do estabelecimento.\nO login e o atendimento funcionam sem internet.').grid(row=1,column=0,sticky='w',pady=(0,12))
        for index,(name,label) in enumerate((('username','Usuário'),('password','Senha'))):
            ttk.Label(self.form,text=label).grid(row=3+index*2,column=0,sticky='w',pady=(6,2))
            entry=ttk.Entry(self.form,width=44,show='*' if name=='password' else '')
            entry.grid(row=4+index*2,column=0,sticky='ew');self.inputs[name]=entry
            entry.bind('<Return>',lambda event,i=index:self.advance(i))
        ttk.Checkbutton(self.form,text='Mostrar senha',variable=self.show_password,command=self.toggle_password).grid(row=7,column=0,sticky='w',pady=6)
        ttk.Label(self.form,textvariable=self.error,foreground='#a52525',wraplength=510).grid(row=8,column=0,sticky='w',pady=6)
        self.primary_button=ttk.Button(self.form,text='Entrar',style='Primary.TButton',command=self.submit)
        self.primary_button.grid(row=9,column=0,sticky='ew');self.primary_button.bind('<Return>',lambda event:self.submit_key())
        actions=ttk.Frame(self.form);actions.grid(row=10,column=0,sticky='ew',pady=8)
        ttk.Button(actions,text='Recuperar acesso',command=lambda:self.set_mode('RECOVERY')).pack(side='left')
        if self.emails and not self.emails.bound:ttk.Button(actions,text='Refazer cadastro',command=lambda:self.set_mode('ENROLL')).pack(side='left',padx=8)
        ttk.Button(actions,text='Fechar',command=self.on_cancel).pack(side='right')
        self._focus_job=self.after_idle(self.inputs['username'].focus_set)

    def email_completed(self,username):
        self.set_mode('LOGIN');self.inputs['username'].insert(0,username)
        self.error.set('Acesso salvo. Entre com sua nova senha.')

    def advance(self,index):
        entries=list(self.inputs.values())
        if not entries[index].get():self.error.set('Preencha este campo para continuar.');return 'break'
        (entries[index+1] if index+1<len(entries) else self.primary_button).focus_set();return 'break'

    def toggle_password(self):
        value='' if self.show_password.get() else '*'
        if not self.show_password.get() and self.inputs['password'].cget('show')=='*':self.show_password.set(True);value=''
        self.inputs['password'].configure(show=value)

    def submit_key(self):self.submit();return 'break'

    def submit(self):
        if self.mode!='LOGIN':return self.wizard.submit()
        if self.busy:return False
        self.busy=True
        try:
            session=self.accounts.login(self.inputs['username'].get(),self.inputs['password'].get())
            self.on_authenticated(session);return True
        except (BusinessError,sqlite3.Error,OSError) as error:
            self.error.set(str(error));return False
        finally:self.busy=False

    def destroy(self):
        if self._focus_job:self.after_cancel(self._focus_job);self._focus_job=None
        super().destroy()
