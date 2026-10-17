class ShortcutRouter:
    def __init__(self,root,current_picker):
        self.root,self.current_picker=root,current_picker
        self.editors={}
        for key in range(1,13):
            root.bind_all(f'<F{key}>',lambda event,k=key:self.route(k))

    def register(self,window,picker):
        self.editors[str(window)]=picker
        window.bind('<Destroy>',lambda event:self.editors.pop(str(window),None) if event.widget==window else None,add='+')

    def route(self,key):
        focus=self.root.focus_get()
        if not focus:
            return 'break'
        top=focus.winfo_toplevel();grab=self.root.grab_current()
        if grab is not None and str(grab) not in self.editors:
            return 'break'
        if str(top) in self.editors:
            picker=self.editors[str(top)]
        elif top==self.root:
            picker=self.current_picker()
        else:
            return 'break'
        if picker is not None and hasattr(picker,'select_shortcut'):
            picker.select_shortcut(key)
        return 'break'
