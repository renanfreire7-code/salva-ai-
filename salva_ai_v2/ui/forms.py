from dataclasses import dataclass
from decimal import InvalidOperation
import sqlite3
import tkinter as tk
from tkinter import ttk
from ..common.errors import BusinessError


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    initial: object = ''
    kind: str = 'text'
    choices: tuple = ()
    required: bool = False
    validator: object = None


class FormDialog(tk.Toplevel):
    def __init__(self,parent,title,fields,*,on_submit=None):
        super().__init__(parent)
        self.title(title);self.transient(parent.winfo_toplevel())
        self.result=None;self.on_submit=on_submit;self.busy=False;self._focus_job=None
        self.fields=[f if isinstance(f,FieldSpec) else FieldSpec(*f) for f in fields]
        self.inputs={};self.field_errors={};self.error=tk.StringVar()
        body=ttk.Frame(self,padding=20);body.pack(fill='both',expand=True)
        body.columnconfigure(0,weight=1)
        for row,field in enumerate(self.fields):
            ttk.Label(body,text=field.label+(' *' if field.required else '')).grid(row=row*3,column=0,sticky='w',pady=(6,3))
            if field.kind=='choice':
                entry=ttk.Combobox(body,values=field.choices,state='readonly',width=44)
                entry.set(str(field.initial))
            elif field.kind=='multiline':
                entry=tk.Text(body,height=3,width=44,wrap='word');entry.insert('1.0',str(field.initial))
            else:
                entry=ttk.Entry(body,width=46);entry.insert(0,str(field.initial))
            entry.grid(row=row*3+1,column=0,sticky='ew')
            self.inputs[field.name]=entry
            error=tk.StringVar();self.field_errors[field.name]=error
            ttk.Label(body,textvariable=error,foreground='#a52525',wraplength=460).grid(row=row*3+2,column=0,sticky='w')
            if field.kind!='multiline':
                entry.bind('<Return>',lambda event,w=entry:self.advance(w))
                entry.bind('<KP_Enter>',lambda event,w=entry:self.advance(w))
        ttk.Label(body,textvariable=self.error,foreground='#a52525',wraplength=460).grid(row=len(fields)*3,column=0,sticky='w',pady=4)
        buttons=ttk.Frame(body);buttons.grid(row=len(fields)*3+1,column=0,sticky='e',pady=(12,0))
        ttk.Button(buttons,text='Cancelar',command=self.destroy).pack(side='left',padx=8)
        self.save_button=ttk.Button(buttons,text='Salvar',style='Primary.TButton',command=self.submit)
        self.save_button.pack(side='left')
        self.save_button.bind('<Return>',lambda event:self._submit_key())
        self.bind('<Escape>',lambda event:self.destroy())
        self.protocol('WM_DELETE_WINDOW',self.destroy)
        self.resizable(False,False)
        if self.inputs:
            self._focus_job=self.after_idle(next(iter(self.inputs.values())).focus_set)

    def destroy(self):
        if self._focus_job is not None:
            self.after_cancel(self._focus_job);self._focus_job=None
        super().destroy()

    def values(self):
        return {name:(widget.get('1.0','end-1c') if isinstance(widget,tk.Text) else widget.get()).strip() for name,widget in self.inputs.items()}

    def validate_field(self,field):
        widget=self.inputs[field.name]
        if str(widget.cget('state'))=='disabled':
            return True
        value=self.values()[field.name]
        try:
            if field.required and not value:
                raise BusinessError('Preencha este campo.')
            if field.kind=='choice' and value not in field.choices:
                raise BusinessError('Escolha uma opção da lista.')
            if field.validator:
                field.validator(value)
        except (BusinessError,ValueError,InvalidOperation) as error:
            self.field_errors[field.name].set(str(error));widget.focus_set();return False
        self.field_errors[field.name].set('')
        return True

    def advance(self,widget):
        field=next(f for f in self.fields if self.inputs[f.name]==widget)
        if not self.validate_field(field):
            return 'break'
        widgets=[self.inputs[f.name] for f in self.fields]
        for candidate in widgets[widgets.index(widget)+1:]+[self.save_button]:
            if str(candidate.cget('state'))!='disabled':
                candidate.focus_set();break
        return 'break'

    def _submit_key(self):
        self.submit();return 'break'

    def submit(self):
        if self.busy:
            return False
        for field in self.fields:
            if not self.validate_field(field):
                return False
        self.busy=True
        try:
            values=self.values()
            result=self.on_submit(values) if self.on_submit else values
        except (BusinessError,ValueError,InvalidOperation,OSError,sqlite3.Error) as error:
            self.error.set(str(error));return False
        else:
            self.result=result;self.destroy();return True
        finally:
            self.busy=False

    def show(self):
        self.wait_visibility();self.grab_set();self.wait_window()
        return self.result


def ask_fields(parent,title,fields,*,on_submit=None):
    return FormDialog(parent,title,fields,on_submit=on_submit).show()
