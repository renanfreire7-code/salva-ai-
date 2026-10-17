import tkinter as tk
from tkinter import ttk
import unittest
from salva_ai_v2.common.errors import BusinessError


class FormKeyboardTest(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.geometry('900x650');self.root.update()
        self.addCleanup(self.root.destroy)

    def test_enter_advances_and_last_field_only_focuses_save(self):
        from salva_ai_v2.ui.forms import FormDialog,FieldSpec
        calls=[]
        dialog=FormDialog(self.root,'Cadastro',[FieldSpec('name','Nome',required=True),FieldSpec('price','Preço','5,00')],on_submit=lambda values:calls.append(values) or values)
        dialog.update();dialog.inputs['name'].focus_force();dialog.inputs['name'].insert(0,'Produto')
        dialog.inputs['name'].event_generate('<Return>');dialog.update()
        self.assertEqual(dialog.focus_get(),dialog.inputs['price'])
        dialog.inputs['price'].event_generate('<Return>');dialog.update()
        self.assertEqual(dialog.focus_get(),dialog.save_button)
        self.assertEqual(calls,[])
        dialog.save_button.event_generate('<Return>');self.root.update()
        self.assertEqual(len(calls),1)

    def test_callback_error_preserves_fields_and_selectors_are_real(self):
        from salva_ai_v2.ui.forms import FormDialog,FieldSpec
        def fail(values):
            raise BusinessError('Confira o valor informado.')
        dialog=FormDialog(self.root,'Pagamento',[FieldSpec('name','Nome','Cliente'),FieldSpec('method','Forma','Pix',kind='choice',choices=('Dinheiro','Pix'))],on_submit=fail)
        self.assertIsInstance(dialog.inputs['method'],ttk.Combobox)
        self.assertFalse(dialog.submit())
        self.assertTrue(dialog.winfo_exists())
        self.assertEqual(dialog.inputs['name'].get(),'Cliente')
        self.assertIn('Confira',dialog.error.get())
        dialog.destroy()

    def test_required_validation_disabled_and_multiline(self):
        from salva_ai_v2.ui.forms import FormDialog,FieldSpec
        dialog=FormDialog(self.root,'Dados',[FieldSpec('name','Nome',required=True),FieldSpec('skip','Pular'),FieldSpec('note','Observação',kind='multiline')])
        dialog.update();dialog.inputs['skip'].configure(state='disabled')
        dialog.inputs['name'].focus_force();dialog.inputs['name'].event_generate('<Return>');dialog.update()
        self.assertEqual(dialog.focus_get(),dialog.inputs['name'])
        dialog.inputs['name'].insert(0,'Nome');dialog.inputs['name'].event_generate('<Return>');dialog.update()
        self.assertEqual(dialog.focus_get(),dialog.inputs['note'])
        dialog.inputs['note'].event_generate('<Return>');dialog.update()
        self.assertIn('\n',dialog.inputs['note'].get('1.0','end-1c'))
        dialog.destroy()

    def test_shortcuts_follow_editor_focus_and_block_administrative_grab(self):
        from salva_ai_v2.ui.keyboard import ShortcutRouter
        class Picker:
            def __init__(self):self.selected=[]
            def select_shortcut(self,key):self.selected.append(key)
        background=Picker();editor=Picker()
        router=ShortcutRouter(self.root,lambda:background)
        window=tk.Toplevel(self.root);entry=ttk.Entry(window);entry.pack()
        router.register(window,editor)
        self.root.update();entry.focus_force();entry.event_generate('<F1>');self.root.update()
        self.assertEqual(editor.selected,[1]);self.assertEqual(background.selected,[])
        admin=tk.Toplevel(self.root);pin=ttk.Entry(admin);pin.pack();admin.grab_set()
        self.root.update();pin.focus_force();pin.event_generate('<F2>');self.root.update()
        self.assertEqual(editor.selected,[1]);self.assertEqual(background.selected,[])
        admin.destroy();window.destroy()

    def test_closed_form_has_no_pending_focus_callback(self):
        from salva_ai_v2.ui.forms import FormDialog
        dialog=FormDialog(self.root,'Dados',[('name','Nome','')])
        pending=set(self.root.tk.call('after','info'))
        dialog.destroy()
        self.assertFalse(pending.intersection(self.root.tk.call('after','info')))

    def test_picker_enter_selects_then_adds_once_and_returns_to_search(self):
        from types import SimpleNamespace
        from salva_ai_v2.ui.shared import View,ProductPicker
        class Picker(View,ProductPicker):
            def __init__(self,parent):
                inventory=SimpleNamespace(products=lambda:[{'id':1,'name':'Cerveja Heineken Latão','price_cents':500}],position=lambda id:SimpleNamespace(available=20))
                super().__init__(parent,SimpleNamespace(inventory=inventory,application=SimpleNamespace(refresh=lambda:None)))
                self.added=[];self.build_picker(self,self.add)
            def add(self):self.added.append((self.selected_product(),int(self.qty.get())))
        picker=Picker(self.root);picker.pack();self.root.update()
        picker.search.set('CHL');picker.filter_products();picker.picker.focus_force()
        picker.picker.event_generate('<Return>');self.root.update()
        self.assertEqual(self.root.focus_get(),picker.qty)
        self.assertEqual(picker.added,[])
        picker.qty.event_generate('<Return>');self.root.update()
        self.assertEqual(picker.added,[(1,1)])
        self.assertEqual(self.root.focus_get(),picker.picker)
