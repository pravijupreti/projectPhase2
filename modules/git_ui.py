import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext


class GitUI:
    """Git tab UI component"""
    
    def __init__(self, parent, save_callback, sync_callback, switch_callback, create_callback):
        self.parent = parent
        self.save_callback = save_callback
        self.sync_callback = sync_callback
        self.switch_callback = switch_callback
        self.create_callback = create_callback
        self.create_widgets()
    
    def create_widgets(self):
        """Create all Git tab widgets"""
        # Configuration Panel
        config_panel = tk.LabelFrame(self.parent, text=" Configuration ", padx=10, pady=10)
        config_panel.pack(fill=tk.X, padx=15, pady=10)
        
        url_row = tk.Frame(config_panel)
        url_row.pack(fill=tk.X, pady=2)
        tk.Label(url_row, text="Repo URL:", width=10, anchor="w").pack(side=tk.LEFT)
        self.repo_entry = tk.Entry(url_row)
        self.repo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(url_row, text="Save", command=self.save_callback).pack(side=tk.LEFT)
        
        branch_row = tk.Frame(config_panel)
        branch_row.pack(fill=tk.X, pady=10)
        self.branch_combo = ttk.Combobox(branch_row, width=25, state="readonly")
        self.branch_combo.pack(side=tk.LEFT, padx=5)
        tk.Button(branch_row, text="🔄 Sync Tree", command=self.sync_callback,
                 bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        self.new_branch_entry = tk.Entry(branch_row, width=15)
        self.new_branch_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(branch_row, text="Switch", bg="#2196F3", fg="white",
                 command=self.switch_callback).pack(side=tk.LEFT, padx=2)
        tk.Button(branch_row, text="Create", bg="#388E3C", fg="white",
                 command=self.create_callback).pack(side=tk.LEFT, padx=2)
        
        # Paned window for tree and log
        self.paned = ttk.Panedwindow(self.parent, orient=tk.VERTICAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Tree frame (will be filled by TreeView component)
        self.tree_frame = tk.Frame(self.paned)
        self.paned.add(self.tree_frame, weight=3)
        
        # Log area
        self.log_area = scrolledtext.ScrolledText(
            self.paned, height=6, font=("Consolas", 10), bg="#f8f9fa"
        )
        self.paned.add(self.log_area, weight=1)
        
        # Hierarchy frame (will be filled by HierarchyDrawer)
        self.hierarchy_frame = tk.LabelFrame(self.parent, text=" Branch Linkage Hierarchy ", padx=5, pady=5)
        self.hierarchy_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=10)
    
    def get_repo_entry(self):
        return self.repo_entry
    
    def get_branch_combo(self):
        return self.branch_combo
    
    def get_new_branch_entry(self):
        return self.new_branch_entry
    
    def get_tree_frame(self):
        return self.tree_frame
    
    def get_hierarchy_frame(self):
        return self.hierarchy_frame
    
    def get_log_area(self):
        return self.log_area
    
    def update_log(self, text):
        """Update log area"""
        def update():
            self.log_area.insert(tk.END, text)
            self.log_area.see(tk.END)
        self.log_area.master.after(0, update)
    
    def update_branches(self, branches):
        """Update branch combo box"""
        def update():
            self.branch_combo.config(values=sorted(branches))
        self.branch_combo.master.after(0, update)