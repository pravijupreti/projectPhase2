import tkinter as tk
from tkinter import ttk
import uuid


class TreeView:
    """Git tree view component"""
    
    def __init__(self, parent):
        self.parent = parent
        self.create_widgets()
    
    def create_widgets(self):
        """Create tree view widgets"""
        self.tree = ttk.Treeview(
            self.parent,
            columns=("SHA", "REFS", "AUTHOR", "DATE", "MESSAGE"),
            selectmode="browse"
        )
        self._setup_columns()
        self._setup_tags()
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _setup_columns(self):
        """Setup tree columns"""
        self.tree.heading("#0", text="Graph")
        self.tree.heading("SHA", text="SHA")
        self.tree.heading("REFS", text="Refs")
        self.tree.heading("AUTHOR", text="Author")
        self.tree.heading("DATE", text="Date")
        self.tree.heading("MESSAGE", text="Message")
        
        self.tree.column("#0", width=150)
        self.tree.column("SHA", width=90)
        self.tree.column("REFS", width=150)
    
    def _setup_tags(self):
        """Setup tree tags"""
        self.tree.tag_configure("graph_style", font=("Consolas", 10))
        self.tree.tag_configure("head_row", background="#e3f2fd")
    
    def handle_tree_data(self, data):
        """Handle incoming tree data"""
        if data == "CLEAR_TREE":
            self.tree.delete(*self.tree.get_children())
            return
        
        p = data.split('::')
        while len(p) < 6:
            p.append("")
        
        row_id = str(uuid.uuid4())
        tags = ("graph_style",)
        if "HEAD" in p[2]:
            tags = ("graph_style", "head_row")
        
        self.tree.insert("", "end", iid=row_id, text=p[0],
                        values=(p[1][:8] if p[1].strip() else "", p[2], p[3], p[4], p[5]),
                        tags=tags)
    
    def get_widget(self):
        return self.tree
    
    def bind(self, event, callback):
        self.tree.bind(event, callback)
    
    def get_selected_item(self, event_y):
        return self.tree.identify_row(event_y)
    
    def select_item(self, item):
        self.tree.selection_set(item)
    
    def get_item_values(self, item):
        return self.tree.item(item, "values")