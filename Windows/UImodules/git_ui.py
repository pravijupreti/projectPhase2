import tkinter as tk
from tkinter import ttk, scrolledtext
from .workspace.terminal_widget import TerminalWidget


class GitUI:
    """
    Git tab UI with real terminal.
    """

    def __init__(self, parent, save_cb, sync_cb,
                 switch_cb, create_cb, push_cb, workspace_manager):  # ADD workspace_manager
        self.parent = parent
        self.save_cb = save_cb
        self.sync_cb = sync_cb
        self.switch_cb = switch_cb
        self.create_cb = create_cb
        self.push_cb = push_cb
        self.workspace_manager = workspace_manager  # ADD THIS
        self._build()

    def _build(self):

        # ── Config panel ──────────────────────────────────────────
        cfg = tk.LabelFrame(self.parent, text=" Configuration ",
                            padx=10, pady=10)
        cfg.pack(fill=tk.X, padx=15, pady=10)

        # repo URL
        url_row = tk.Frame(cfg)
        url_row.pack(fill=tk.X, pady=2)
        tk.Label(url_row, text="Repo URL:", width=10, anchor="w").pack(side=tk.LEFT)
        self.repo_entry = tk.Entry(url_row)
        self.repo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(url_row, text="Save",
                  command=self.save_cb).pack(side=tk.LEFT)

        # branch row
        br = tk.Frame(cfg)
        br.pack(fill=tk.X, pady=6)

        self.branch_combo = ttk.Combobox(br, width=22, state="readonly")
        self.branch_combo.pack(side=tk.LEFT, padx=5)

        tk.Button(br, text="🔄 Sync Tree",
                  command=self.sync_cb,
                  bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=4)

        self.new_branch_entry = tk.Entry(br, width=20, fg="gray")
        self.new_branch_entry.insert(0, "new-branch-name")
        self.new_branch_entry.pack(side=tk.LEFT, padx=4)
        self.new_branch_entry.bind("<FocusIn>",  self._ph_clear)
        self.new_branch_entry.bind("<FocusOut>", self._ph_restore)

        tk.Button(br, text="Switch",
                  bg="#2196F3", fg="white",
                  command=self.switch_cb).pack(side=tk.LEFT, padx=2)
        tk.Button(br, text="Create",
                  bg="#388E3C", fg="white",
                  command=self.create_cb).pack(side=tk.LEFT, padx=2)

        # ── Push panel ────────────────────────────────────────────
        push_panel = tk.LabelFrame(self.parent, text=" Push to GitHub ",
                                   padx=10, pady=8)
        push_panel.pack(fill=tk.X, padx=15, pady=(0, 6))

        push_row = tk.Frame(push_panel)
        push_row.pack(fill=tk.X)

        self.push_btn = tk.Button(
            push_row,
            text="⬆  Push Changes",
            bg="#1565C0", fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=16, pady=6,
            command=self.push_cb,
        )
        self.push_btn.pack(side=tk.LEFT, padx=(0, 12))

        self.push_status_var = tk.StringVar(value="Ready")
        self.push_status_lbl = tk.Label(
            push_row,
            textvariable=self.push_status_var,
            fg="#555555", font=("Segoe UI", 9),
        )
        self.push_status_lbl.pack(side=tk.LEFT)

        # ── Paned: commit graph + terminal ─────────────────────────
        paned = ttk.Panedwindow(self.parent, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.tree_frame = tk.LabelFrame(paned, text=" Commit Graph ",
                                        padx=2, pady=2)
        paned.add(self.tree_frame, weight=3)

        # REPLACE log_area with TerminalWidget
        self.terminal_widget = TerminalWidget(paned, self.workspace_manager, height=8)
        paned.add(self.terminal_widget.get_frame(), weight=1)

        # ── Branch hierarchy with buttons (bottom) ─────────────────
        hierarchy_container = tk.Frame(self.parent)
        hierarchy_container.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=10)
        
        # Button frame for hierarchy
        button_frame = tk.Frame(hierarchy_container)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.show_hierarchy_btn = tk.Button(
            button_frame,
            text="📊 Show Hierarchy",
            bg="#FF9800", fg="white",
            command=self._show_hierarchy
        )
        self.show_hierarchy_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_terminal_btn = tk.Button(
            button_frame,
            text="🗑️ Clear Terminal",
            bg="#f44336", fg="white",
            command=self._clear_terminal
        )
        self.clear_terminal_btn.pack(side=tk.LEFT, padx=5)
        
        # Hierarchy frame
        self.hierarchy_frame = tk.LabelFrame(
            hierarchy_container,
            text=" Branch Linkage Hierarchy ",
            padx=5, pady=5,
        )
        self.hierarchy_frame.pack(fill=tk.X)
    
    def _show_hierarchy(self):
        """Show branch hierarchy - can be called from app"""
        # This will be connected to the draw method
        if hasattr(self, 'on_show_hierarchy'):
            self.on_show_hierarchy()
    
    def _clear_terminal(self):
        """Clear terminal output"""
        self.terminal_widget.clear()

    # ── placeholder ───────────────────────────────────────────────

    def _ph_clear(self, _e):
        if self.new_branch_entry.get() == "new-branch-name":
            self.new_branch_entry.delete(0, tk.END)
            self.new_branch_entry.config(fg="black")

    def _ph_restore(self, _e):
        if not self.new_branch_entry.get().strip():
            self.new_branch_entry.insert(0, "new-branch-name")
            self.new_branch_entry.config(fg="gray")

    # ── push state ────────────────────────────────────────────────

    def set_push_busy(self, busy: bool):
        def _u():
            self.push_btn.config(
                state=tk.DISABLED if busy else tk.NORMAL,
                text="⏳ Pushing…" if busy else "⬆  Push Changes",
            )
        self.push_btn.after(0, _u)

    def set_push_status(self, text: str, color: str = "#555555"):
        def _u():
            self.push_status_var.set(text)
            self.push_status_lbl.config(fg=color)
        self.push_status_lbl.after(0, _u)

    # ── getters ───────────────────────────────────────────────────

    def get_repo_entry(self):       return self.repo_entry
    def get_branch_combo(self):     return self.branch_combo
    def get_new_branch_entry(self): return self.new_branch_entry
    def get_tree_frame(self):       return self.tree_frame
    def get_hierarchy_frame(self):  return self.hierarchy_frame

    # ── updaters (thread-safe) ────────────────────────────────────

    def update_log(self, text: str):
        """For compatibility - sends to terminal"""
        self.terminal_widget._append_output(text.rstrip(), "output")

    def update_branches(self, branches: list):
        def _u():
            cur = self.branch_combo.get()
            self.branch_combo.config(values=sorted(branches))
            if cur in branches:
                self.branch_combo.set(cur)
        self.branch_combo.after(0, _u)

    def set_repo_url(self, url: str):
        self.repo_entry.delete(0, tk.END)
        self.repo_entry.insert(0, url)