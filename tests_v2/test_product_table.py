import tkinter as tk
import unittest,importlib.util


class ProductTableTest(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.geometry('520x420');self.addCleanup(self.root.destroy)
        self.assertIsNotNone(importlib.util.find_spec('salva_ai_v2.ui.product_table'),'Tabela de nomes completos ainda não existe')
        from salva_ai_v2.ui.product_table import ProductTable
        self.table=ProductTable(self.root,['Produto','Quantidade','Total'],height=5);self.table.pack(fill='both',expand=True)

    def test_wrap_long_and_unbroken_names_without_loss(self):
        names=['Cerveja Heineken edição especial '+('nome completo '*15),'Á'+('x'*100)]
        for index,name in enumerate(names):self.table.insert('','end',iid=str(index),values=(name,2,'R$ 10,00'))
        self.root.update()
        for index,name in enumerate(names):
            cell=self.table.cell(str(index),'Produto')
            self.assertEqual(cell.cget('text'),name)
            self.assertGreater(cell.winfo_reqheight(),35)
            self.assertGreaterEqual(cell.winfo_height(),cell.winfo_reqheight())
            self.assertEqual(self.table.item(str(index),'values'),(name,2,'R$ 10,00'))
        self.root.geometry('390x420');self.root.update()
        self.assertLessEqual(self.table.cell('0','Produto').winfo_width(),390)

    def test_keyboard_selection_refresh_and_duplicate_names(self):
        from salva_ai_v2.ui.shared import fill
        rows=[(str(i),('Mesmo nome',i,'R$ 10,00')) for i in range(20)]
        fill(self.table,rows);self.root.update();self.table.focus_force()
        self.table.event_generate('<Down>');self.root.update();self.assertEqual(self.table.selection(),('0',))
        self.table.event_generate('<Down>');self.root.update();self.assertEqual(self.table.selection(),('1',))
        fill(self.table,rows);self.root.update();self.assertEqual(self.table.selection(),('1',))
        self.table.event_generate('<End>');self.root.update();self.assertEqual(self.table.selection(),('19',))
        self.assertGreater(self.table.canvas.yview()[0],0)
        self.table.event_generate('<Home>');self.root.update();self.assertEqual(self.table.selection(),('0',))
        calls=[];self.table.bind('<Return>',lambda event:calls.append(self.table.selection()))
        self.table.event_generate('<Return>');self.root.update();self.assertEqual(calls,[('0',)])
