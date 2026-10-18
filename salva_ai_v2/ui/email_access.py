"""Confirmação de e-mail em etapas; senhas e PIN nunca saem do computador."""
import sqlite3
import tkinter as tk
from tkinter import ttk,messagebox
from ..common.errors import BusinessError


class EmailAccessWizard(ttk.Frame):
    def __init__(self,parent,accounts,emails,security,*,mode,on_completed,on_cancel):
        super().__init__(parent)
        self.accounts,self.emails,self.security=accounts,emails,security
        self.mode,self.on_completed,self.on_cancel=mode,on_completed,on_cancel
        self.stage='EMAIL';self.busy=False;self.alive=True;self.challenge=None;self.proof=None;self.inputs={}
        self.address='';self.error=tk.StringVar();self.wait=tk.StringVar();self.show=tk.BooleanVar();self.timer=None;self.focus_job=None
        self.columnconfigure(0,weight=1);self.render()
        self.timer=self.after(1000,self.tick)

    def render(self):
        if self.focus_job:self.after_cancel(self.focus_job);self.focus_job=None
        for child in self.winfo_children():child.destroy()
        self.inputs={}
        title={'SETUP':'Configure seu acesso','TRANSITION':'Atualize seu acesso','ENROLL':'Refazer cadastro','RECOVER':'Recuperar acesso'}[self.mode]
        ttk.Label(self,text=title,style='Title.TLabel').grid(row=0,column=0,sticky='w',pady=(4,8))
        note={'EMAIL':'1 de 3 · Confirme seu e-mail. Esta etapa precisa de internet.','CODE':'2 de 3 · Digite os seis dígitos recebidos no e-mail.','CREDENTIALS':'3 de 3 · Defina o usuário e a senha deste estabelecimento.'}[self.stage]
        ttk.Label(self,text=note,wraplength=510).grid(row=1,column=0,sticky='w',pady=(0,8))
        if self.stage=='EMAIL':fields=[('email','E-mail cadastrado' if self.mode=='RECOVER' else 'Seu e-mail')]
        elif self.stage=='CODE':
            ttk.Label(self,text=self.address,wraplength=510).grid(row=2,column=0,sticky='w')
            fields=[('code','Código de confirmação')]
        else:
            fields=[('username','Novo usuário'),('password','Senha (mínimo oito caracteres)'),('password_confirm','Confirme a senha')]
            if self.mode=='ENROLL':fields.append(('pin','PIN administrativo atual (será mantido)'))
            if self.mode in ('SETUP','TRANSITION'):fields.extend([('pin','Novo PIN de três dígitos'),('pin_confirm','Confirme o PIN')])
            if self.mode=='TRANSITION':fields.append(('legacy_pin',f'PIN atual de {self.security.pin_length} dígitos'))
        for index,(name,label) in enumerate(fields):
            row=3+index*2
            ttk.Label(self,text=label).grid(row=row,column=0,sticky='w',pady=(3,1))
            entry=ttk.Entry(self,show='*' if name in ('password','password_confirm','pin','pin_confirm','legacy_pin') else '',width=44)
            entry.grid(row=row+1,column=0,sticky='ew');entry.bind('<Return>',lambda event,i=index:self.advance(i));self.inputs[name]=entry
        row=3+2*len(fields)
        if self.stage=='CREDENTIALS':ttk.Checkbutton(self,text='Mostrar senha',variable=self.show,command=self.toggle).grid(row=row,column=0,sticky='w')
        if self.stage=='CODE':
            self.resend_button=ttk.Button(self,text='Reenviar código',command=self.resend);self.resend_button.grid(row=row,column=0,sticky='w')
            ttk.Label(self,textvariable=self.wait,style='Muted.TLabel').grid(row=row+1,column=0,sticky='w')
        ttk.Label(self,textvariable=self.error,foreground='#a52525',wraplength=510).grid(row=row+2,column=0,sticky='w',pady=6)
        self.primary_button=ttk.Button(self,text={'EMAIL':'Enviar código','CODE':'Confirmar código','CREDENTIALS':'Salvar acesso'}[self.stage],style='Primary.TButton',command=self.submit)
        self.primary_button.grid(row=row+3,column=0,sticky='ew');self.primary_button.bind('<Return>',lambda event:self.submit_key())
        actions=ttk.Frame(self);actions.grid(row=row+4,column=0,sticky='ew',pady=8)
        self.back_button=ttk.Button(actions,text='Voltar',command=self.cancel);self.back_button.pack(side='left')
        ttk.Label(actions,text='Seus dados e seu histórico serão mantidos.',style='Muted.TLabel').pack(side='right')
        self.focus_job=self.after_idle(next(iter(self.inputs.values())).focus_set)
        self.update_busy()

    def advance(self,index):
        entries=list(self.inputs.values())
        if not entries[index].get():self.error.set('Preencha este campo para continuar.');return 'break'
        (entries[index+1] if index+1<len(entries) else self.primary_button).focus_set();return 'break'

    def submit_key(self):self.submit();return 'break'
    def toggle(self):
        for name in ('password','password_confirm'):
            if name in self.inputs:self.inputs[name].configure(show='' if self.show.get() else '*')

    def update_busy(self):
        self.primary_button.configure(state='disabled' if self.busy else 'normal')
        for entry in self.inputs.values():entry.configure(state='disabled' if self.busy else 'normal')
        if self.stage=='CODE':
            seconds=self.emails.remaining_wait(self.address) if self.emails else 0
            self.wait.set(f'Reenvio disponível em {seconds}s.' if seconds else 'Você pode solicitar outro código.')
            self.resend_button.configure(state='disabled' if self.busy or seconds else 'normal')

    def tick(self):
        if self.alive:self.update_busy();self.timer=self.after(1000,self.tick)

    def fail(self,error):
        if not self.alive:return
        self.busy=False
        self.error.set(str(error) if isinstance(error,BusinessError) else 'Não foi possível salvar. Seus dados anteriores foram mantidos. Tente novamente.')
        self.update_busy()

    def sent(self,challenge):
        if not self.alive:return
        self.challenge=challenge;self.stage='CODE';self.busy=False;self.render()

    def verified(self,proof):
        if not self.alive:return
        self.proof=proof;self.stage='CREDENTIALS';self.busy=False;self.error.set('');self.render()

    def resend(self):
        if self.busy:return
        try:
            self.busy=True;self.error.set('');self.update_busy()
            self.emails.request_code(self.address,'SETUP' if self.mode=='TRANSITION' else self.mode,self.sent,self.fail)
        except (BusinessError,sqlite3.Error,OSError) as error:self.fail(error)

    def submit(self):
        if self.busy or not self.alive:return False
        values={name:entry.get() for name,entry in self.inputs.items()}
        try:
            self.error.set('')
            if self.stage=='EMAIL':
                if self.emails is None:raise BusinessError('Configure o serviço de e-mail antes de continuar.')
                self.address=values['email'].strip().casefold();self.resend();return self.busy
            if self.stage=='CODE':
                self.busy=True;self.update_busy();self.emails.verify_code(self.challenge,values['code'],self.verified,self.fail);return True
            if values['password']!=values['password_confirm']:raise BusinessError('As senhas não coincidem.')
            if self.mode in ('SETUP','TRANSITION') and values['pin']!=values['pin_confirm']:raise BusinessError('Os PINs não coincidem.')
            self.busy=True;self.update_busy()
            if self.mode=='ENROLL':self.accounts.reenroll_with_email(self.proof,values['username'],values['password'],values['pin'])
            elif self.mode=='RECOVER':self.accounts.recover_with_email(self.proof,values['username'],values['password'])
            else:
                legacy=self.security.authorize(values['legacy_pin'],'access.configure') if self.mode=='TRANSITION' else None
                key=self.accounts.create_with_email(self.proof,values['username'],values['password'],values['pin'],legacy)
                messagebox.showinfo('Guarde a chave administrativa','A recuperação de usuário e senha será por e-mail. Guarde esta chave separadamente para emergências do PIN administrativo:\n\n'+key,parent=self)
            self.on_completed(values['username'].strip().casefold());return True
        except (BusinessError,sqlite3.Error,OSError) as error:self.fail(error);return False

    def cancel(self):
        if self.emails:self.emails.invalidate_all()
        self.on_cancel()

    def destroy(self):
        if not self.alive:return
        self.alive=False
        for job in (self.timer,self.focus_job):
            if job:self.after_cancel(job)
        if self.emails:self.emails.invalidate_all()
        super().destroy()
