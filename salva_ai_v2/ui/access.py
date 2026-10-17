"""Entrada offline: nenhum controle de operação antes da autenticação."""
import sqlite3
import tkinter as tk
from tkinter import ttk,messagebox
from ..common.errors import BusinessError


class AccessView(ttk.Frame):
    def __init__(self,parent,accounts,security,on_authenticated,on_cancel):
        super().__init__(parent,padding=(30,18))
        self.accounts,self.security=accounts,security
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
        self.mode=mode if mode=='RECOVERY' else self.accounts.mode
        for child in self.form.winfo_children():child.destroy()
        self.inputs={};self.error.set('');self.show_password.set(False)
        title={'LOGIN':'Entrar no seu bar','SETUP':'Configure seu acesso','TRANSITION':'Atualize seu acesso','RECOVERY':'Recuperar acesso'}[self.mode]
        ttk.Label(self.form,text=title,style='Title.TLabel').grid(row=0,column=0,sticky='w',pady=(4,6))
        note={'LOGIN':'Informe o usuário e a senha do estabelecimento.','SETUP':'Crie uma conta e um PIN de três dígitos.','TRANSITION':'Confirme o acesso atual e crie a conta. Seus dados serão preservados.','RECOVERY':'Use a chave guardada para definir nova senha e PIN.'}[self.mode]
        ttk.Label(self.form,text=note,wraplength=510).grid(row=1,column=0,sticky='w',pady=(0,8))
        fields=[]
        if self.mode!='RECOVERY':fields.append(('username','Usuário'))
        else:fields.append(('key','Chave de recuperação'))
        fields.append(('password','Senha' if self.mode=='LOGIN' else 'Senha (mínimo oito caracteres)'))
        if self.mode!='LOGIN':fields.extend([('password_confirm','Confirme a senha'),('pin','PIN de três dígitos'),('pin_confirm','Confirme o PIN')])
        if self.mode=='TRANSITION':
            proof=ttk.Combobox(self.form,textvariable=self.proof_kind,values=('PIN atual','Chave de recuperação'),state='readonly',width=32)
            fields.append(('proof','Confirme o acesso atual'))
        for index,(name,label) in enumerate(fields):
            row=index*2+3
            if name=='proof':proof.grid(row=row,column=0,sticky='e')
            ttk.Label(self.form,text=label).grid(row=row,column=0,sticky='w',pady=(4,2))
            entry=ttk.Entry(self.form,width=44,show='*' if name!='username' else '')
            entry.grid(row=row+1,column=0,sticky='ew');self.inputs[name]=entry
            entry.bind('<Return>',lambda event,i=index:self.advance(i))
        row=len(fields)*2+3
        ttk.Checkbutton(self.form,text='Mostrar senha',variable=self.show_password,command=self.toggle_password).grid(row=row,column=0,sticky='w',pady=(6,0))
        ttk.Label(self.form,textvariable=self.error,foreground='#a52525',wraplength=510).grid(row=row+1,column=0,sticky='w',pady=6)
        self.primary_button=ttk.Button(self.form,text='Entrar' if self.mode=='LOGIN' else 'Recuperar acesso' if self.mode=='RECOVERY' else 'Salvar e entrar',style='Primary.TButton',command=self.submit)
        self.primary_button.grid(row=row+2,column=0,sticky='ew');self.primary_button.bind('<Return>',lambda event:self.submit_key())
        actions=ttk.Frame(self.form);actions.grid(row=row+3,column=0,sticky='ew',pady=8)
        if self.mode=='LOGIN':ttk.Button(actions,text='Recuperar acesso',command=lambda:self.set_mode('RECOVERY')).pack(side='left')
        elif self.mode=='RECOVERY':ttk.Button(actions,text='Voltar',command=lambda:self.set_mode('LOGIN')).pack(side='left')
        ttk.Button(actions,text='Fechar',command=self.on_cancel).pack(side='right')
        self._focus_job=self.after_idle(next(iter(self.inputs.values())).focus_set)

    def advance(self,index):
        entries=list(self.inputs.values());current=entries[index]
        if not current.get():self.error.set('Preencha este campo para continuar.');return 'break'
        (entries[index+1] if index+1<len(entries) else self.primary_button).focus_set();return 'break'

    def toggle_password(self):
        # Can be called by the checkbutton or directly by keyboard/test automation.
        value='' if self.show_password.get() else '*'
        if not self.show_password.get() and self.inputs['password'].cget('show')=='*':
            self.show_password.set(True);value=''
        for name in ('password','password_confirm'):
            if name in self.inputs:self.inputs[name].configure(show=value)

    def submit_key(self):
        self.submit();return 'break'

    def submit(self):
        if self.busy:return False
        self.busy=True
        try:
            values={name:entry.get() for name,entry in self.inputs.items()}
            if self.mode=='LOGIN':
                session=self.accounts.login(values['username'],values['password'])
            else:
                if values['password']!=values['password_confirm']:raise BusinessError('As senhas não coincidem.')
                if values['pin']!=values['pin_confirm']:raise BusinessError('Os PINs não coincidem.')
                if self.mode=='RECOVERY':
                    key=self.accounts.recover(values['key'],values['password'],values['pin'])
                    messagebox.showinfo('Guarde a nova chave','A chave anterior não funciona mais. Guarde fora do computador:\n\n'+key,parent=self)
                    self.set_mode('LOGIN');return True
                proof=None
                if self.mode=='TRANSITION':
                    proof=(self.security.authorize_recovery(values['proof'],'access.configure') if self.proof_kind.get()=='Chave de recuperação' else self.security.authorize(values['proof'],'access.configure'))
                key=self.accounts.create(values['username'],values['password'],values['pin'],proof)
                messagebox.showinfo('Guarde sua chave de recuperação','Guarde esta chave fora do computador. Ela recupera senha e PIN e não será exibida novamente:\n\n'+key,parent=self)
                session=self.accounts.login(values['username'],values['password'])
            self.on_authenticated(session);return True
        except (BusinessError,sqlite3.Error,OSError) as error:
            wait=max(self.accounts.remaining_wait(),self.security.remaining_wait())
            self.error.set(str(error)+(f' Aguarde {wait} segundos.' if wait else ''));return False
        finally:self.busy=False

    def destroy(self):
        if self._focus_job:self.after_cancel(self._focus_job);self._focus_job=None
        super().destroy()
