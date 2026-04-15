import tkinter as tk
from tkinter import ttk, scrolledtext


class LogTextArea:
    """Reusable log text area component"""
    
    def __init__(self, parent, bg="#1e1e1e", fg="#d4d4d4", height=20):
        self.text_area = scrolledtext.ScrolledText(
            parent, bg=bg, fg=fg, font=("Consolas", 10), height=height
        )
    
    def pack(self, **kwargs):
        self.text_area.pack(**kwargs)
    
    def insert(self, text):
        self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)
    
    def clear(self):
        self.text_area.delete(1.0, tk.END)
    
    def get_widget(self):
        return self.text_area


class ControlButton:
    """Reusable button with consistent styling"""
    
    def __init__(self, parent, text, command, bg_color, state=tk.NORMAL):
        self.button = tk.Button(
            parent, text=text, command=command,
            bg=bg_color, fg="white", font=("Arial", 10, "bold"),
            padx=20, pady=10, state=state
        )
    
    def pack(self, **kwargs):
        self.button.pack(**kwargs)
    
    def config(self, **kwargs):
        self.button.config(**kwargs)
    
    def get_widget(self):
        return self.button


class ConfigPanel:
    """Reusable configuration panel for Git settings"""
    
    def __init__(self, parent, title=" Configuration "):
        self.frame = tk.LabelFrame(parent, text=title, padx=10, pady=10)
        self.repo_entry = None
        self.branch_combo = None
        self.new_branch_entry = None
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def create_widgets(self, save_callback, sync_callback, switch_callback, create_callback):
        """Create all widgets in the config panel"""
        # URL row
        url_row = tk.Frame(self.frame)
        url_row.pack(fill=tk.X, pady=2)
        tk.Label(url_row, text="Repo URL:", width=10, anchor="w").pack(side=tk.LEFT)
        self.repo_entry = tk.Entry(url_row)
        self.repo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(url_row, text="Save", command=save_callback).pack(side=tk.LEFT)
        
        # Branch row
        branch_row = tk.Frame(self.frame)
        branch_row.pack(fill=tk.X, pady=10)
        self.branch_combo = ttk.Combobox(branch_row, width=25, state="readonly")
        self.branch_combo.pack(side=tk.LEFT, padx=5)
        tk.Button(branch_row, text="🔄 Sync Tree", command=sync_callback,
                 bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        self.new_branch_entry = tk.Entry(branch_row, width=15)
        self.new_branch_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(branch_row, text="Switch", bg="#2196F3", fg="white",
                 command=switch_callback).pack(side=tk.LEFT, padx=2)
        tk.Button(branch_row, text="Create", bg="#388E3C", fg="white",
                 command=create_callback).pack(side=tk.LEFT, padx=2)
        
        return self.repo_entry, self.branch_combo, self.new_branch_entry
    
    def get_widget(self):
        return self.frame


class GitTreeView:
    """Reusable Git tree view component"""
    
    def __init__(self, parent):
        self.tree = ttk.Treeview(
            parent,
            columns=("SHA", "REFS", "AUTHOR", "DATE", "MESSAGE"),
            selectmode="browse"
        )
        self._setup_columns()
        self._setup_tags()
    
    def _setup_columns(self):
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
        self.tree.tag_configure("graph_style", font=("Consolas", 10))
        self.tree.tag_configure("head_row", background="#e3f2fd")
    
    def pack(self, **kwargs):
        self.tree.pack(**kwargs)
    
    def insert(self, **kwargs):
        return self.tree.insert(**kwargs)
    
    def delete(self, *args):
        self.tree.delete(*args)
    
    def get_selection(self):
        return self.tree.selection()
    
    def item(self, *args, **kwargs):
        return self.tree.item(*args, **kwargs)
    
    def bind(self, *args, **kwargs):
        self.tree.bind(*args, **kwargs)
    
    def get_widget(self):
        return self.tree


class HierarchyCanvas:
    """Reusable hierarchy visualization canvas"""
    
    def __init__(self, parent, height=150):
        self.canvas = tk.Canvas(parent, height=height, bg="#ffffff", highlightthickness=0)
    
    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)
    
    def clear(self):
        self.canvas.delete("all")
    
    def draw_branch_link(self, x_start, y, local_name, remote_name, is_active=False):
        """Draw a single branch link"""
        # Local node
        color = "#2196F3" if is_active else "#607D8B"
        width = 3 if is_active else 1
        self.canvas.create_text(
            x_start, y, text=f" {local_name} ", anchor="w",
            font=("Arial", 10, "bold"), fill=color
        )
        
        # Arrow
        dash_start = x_start + 110
        arrow_end = dash_start + 160
        line_color = "#4CAF50" if remote_name != "NO_UPSTREAM" else "#f44336"
        dash_pattern = None if remote_name != "NO_UPSTREAM" else (5, 5)
        
        self.canvas.create_line(
            dash_start, y, arrow_end, y,
            arrow=tk.LAST, fill=line_color, dash=dash_pattern, width=width
        )
        
        # Remote node
        remote_text = remote_name if remote_name != "NO_UPSTREAM" else "⚠️ Disconnected"
        self.canvas.create_text(
            arrow_end + 10, y, text=remote_text,
            anchor="w", font=("Consolas", 9), fill=line_color
        )
    
    def get_widget(self):
        return self.canvas