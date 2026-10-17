"""Linhas de altura variável; nomes e valores originais nunca são truncados."""
from collections import OrderedDict
import tkinter as tk
from tkinter import ttk,font


class ProductTable(ttk.Frame):
    def __init__(self,parent,columns,height=12):
        super().__init__(parent,takefocus=True)
        self.columns=tuple(columns);self._rows=OrderedDict();self._selected='';self._focus='';self._layout_width=0
        self._spec={name:{'width':110,'anchor':'w' if name=='Produto' else 'e'} for name in self.columns}
        self._font=font.Font(self,font=ttk.Style(self).lookup('Treeview','font') or 'TkDefaultFont')
        self._header_font=font.Font(self,font=self._font);self._header_font.configure(weight='bold')
        self.header=ttk.Frame(self);self.header.pack(fill='x')
        self._headers={}
        for index,name in enumerate(self.columns):
            label=tk.Label(self.header,text={'Quantidade':'Qtd.','Faturamento':'Vendas','Contribuição':'Contrib.','Preço normal':'Preço unit.'}.get(name,name),font=self._header_font,bg='#eaf0ed',fg='#233c3e',padx=5,pady=6,anchor='w',justify='left')
            label.grid(row=0,column=index,sticky='nsew');self._headers[name]=label
        body=ttk.Frame(self);body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,height=height*28,background='#ffffff',highlightthickness=0)
        scroll=ttk.Scrollbar(body,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set);self.canvas.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.inner=ttk.Frame(self.canvas);self.inner.columnconfigure(0,weight=1)
        self._window=self.canvas.create_window(0,0,window=self.inner,anchor='nw')
        self.inner.bind('<Configure>',lambda event:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda event:self._layout(event.width))
        for key in ('Up','Down','Home','End'):super().bind('<'+key+'>',lambda event,k=key:self._navigate(k))
        for widget in (self,self.canvas,self.inner):self._wheel_bind(widget)

    def __getitem__(self,key):
        return self.columns if key=='columns' else super().__getitem__(key)

    def bind(self,sequence=None,func=None,add=None):
        if sequence=='<Double-1>':sequence='<<ProductDoubleClick>>'
        return super().bind(sequence,func,add)

    def _wheel_bind(self,widget):
        widget.bind('<MouseWheel>',lambda event:self._wheel(-1 if event.delta>0 else 1))
        widget.bind('<Button-4>',lambda event:self._wheel(-1));widget.bind('<Button-5>',lambda event:self._wheel(1))

    def _wheel(self,delta):
        self.canvas.yview_scroll(delta*2,'units');return 'break'

    def _layout(self,width=None):
        width=width or self.canvas.winfo_width()
        if width<20:return
        self._layout_width=width;self.canvas.itemconfigure(self._window,width=width)
        others=[name for name in self.columns if name!='Produto']
        requested=sum(self._spec[name]['width'] for name in others)
        budget=max(len(others)*45,width-max(160,int(width*.34)))
        scale=min(1,budget/max(1,requested))
        widths={name:max(45,int(self._spec[name]['width']*scale)) for name in others}
        widths['Produto']=max(80,width-sum(widths.values()))
        for index,name in enumerate(self.columns):
            size=widths[name];self.header.columnconfigure(index,minsize=size,weight=0)
            self._headers[name].configure(wraplength=max(20,size-12))
        # Reserve the scrollbar's width beside the header as well.
        self.header.configure(padding=(0,0,max(0,self.winfo_width()-width),0))
        for data in self._rows.values():
            for index,name in enumerate(self.columns):
                size=widths[name];data['frame'].columnconfigure(index,minsize=size,weight=0)
                data['labels'][name].configure(wraplength=max(20,size-12))
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def insert(self,parent,index,iid=None,values=(),**kwargs):
        id=str(iid if iid is not None else len(self._rows)+1)
        if id in self._rows:raise tk.TclError('Identificação repetida: '+id)
        frame=ttk.Frame(self.inner);labels={}
        data=dict(values=tuple(values),tags=kwargs.get('tags',()),frame=frame,labels=labels)
        self._rows[id]=data
        for col,name in enumerate(self.columns):
            label=tk.Label(frame,text=values[col] if col<len(values) else '',font=self._font,bg='#ffffff',fg='#233c3e',padx=5,pady=7,
                justify='left',anchor='w' if self._spec[name]['anchor']=='w' else 'e')
            label.grid(row=0,column=col,sticky='nsew');labels[name]=label
            label.bind('<Button-1>',lambda event,i=id:self._click(i))
            label.bind('<Double-1>',lambda event,i=id:self._double(i));self._wheel_bind(label)
        if index!='end':
            items=list(self._rows.items());new=items.pop();items.insert(int(index),new);self._rows=OrderedDict(items)
        self._place_rows();self._layout();return id

    def _place_rows(self):
        for index,data in enumerate(self._rows.values()):data['frame'].grid(row=index,column=0,sticky='ew')

    def cell(self,id,column):
        return self._rows[str(id)]['labels'][column]

    def item(self,id,option=None,**kwargs):
        data=self._rows[str(id)]
        if 'values' in kwargs:
            data['values']=tuple(kwargs['values'])
            for index,name in enumerate(self.columns):data['labels'][name].configure(text=data['values'][index])
        if 'tags' in kwargs:data['tags']=kwargs['tags']
        result={'values':data['values'],'tags':data['tags']}
        return result.get(option) if option else result

    def column(self,name,**kwargs):
        if kwargs:self._spec[name].update(kwargs);self._layout()
        return self._spec[name].copy()

    def heading(self,name,**kwargs):
        if 'text' in kwargs:self._headers[name].configure(text=kwargs['text'])
        return {'text':self._headers[name].cget('text')}

    def get_children(self,item=None):
        return tuple(self._rows)

    def exists(self,id):
        return str(id) in self._rows

    def delete(self,*ids):
        removed=False
        for id in ids:
            id=str(id)
            if id in self._rows:self._rows.pop(id)['frame'].destroy()
            if id==self._selected:self._selected='';removed=True
            if id==self._focus:self._focus=''
        self._place_rows()
        if removed:self.event_generate('<<TreeviewSelect>>',when='tail')

    def selection(self):
        return (self._selected,) if self._selected else ()

    def selection_set(self,id):
        if isinstance(id,(tuple,list)):id=id[0] if id else ''
        id=str(id)
        if id and id not in self._rows:raise tk.TclError('Item inexistente: '+id)
        previous=self._selected;self._selected=id;self._focus=id
        for key in (previous,id):
            if key in self._rows:
                for label in self._rows[key]['labels'].values():label.configure(bg='#d8e9df' if key==id else '#ffffff')
        if previous!=id:self.event_generate('<<TreeviewSelect>>',when='tail')

    def focus(self,id=None):
        if id is not None:self._focus=str(id)
        return self._focus

    def _click(self,id):
        self.selection_set(id);self.focus_set();return 'break'

    def _double(self,id):
        self._click(id);self.event_generate('<<ProductDoubleClick>>',when='tail');return 'break'

    def _navigate(self,key):
        ids=list(self._rows)
        if not ids:return 'break'
        index=ids.index(self._selected) if self._selected in ids else -1
        index=0 if key=='Home' else len(ids)-1 if key=='End' else max(0,min(len(ids)-1,index+(1 if key=='Down' else -1)))
        self.selection_set(ids[index]);self.see(ids[index]);return 'break'

    def see(self,id):
        if str(id) not in self._rows:return
        self.update_idletasks();row=self._rows[str(id)]['frame'];top=row.winfo_y();bottom=top+row.winfo_height()
        total=max(1,self.inner.winfo_height());current=self.canvas.canvasy(0);height=self.canvas.winfo_height()
        if top<current:self.canvas.yview_moveto(top/total)
        elif bottom>current+height:self.canvas.yview_moveto(max(0,bottom-height)/total)
