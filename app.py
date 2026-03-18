#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import subprocess
import threading
import uuid 

class SafeJupyterLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Control Center")
        self.root.geometry("1100x950") # Increased height for hierarchy view
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.process = None
        self.running = False
        self.found_branches = []
        self.branch_links = [] # Stores (local, remote) pairs

        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_jupyter = ttk.Frame(self.notebook)
        self.tab_git = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_jupyter, text=" 🚀 Jupyter Dashboard ")
        self.notebook.add(self.tab_git, text=" 🌿 Git & Branch Manager ")

        self.setup_jupyter_tab()
        self.setup_git_tab()

    def setup_jupyter_tab(self):
        ctrl_frame = tk.Frame(self.tab_jupyter); ctrl_frame.pack(pady=15, fill=tk.X)
        self.launch_btn = tk.Button(ctrl_frame, text="▶ Launch Jupyter", command=self.launch_safe, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20, pady=10)
        self.launch_btn.pack(side=tk.LEFT, padx=20)
        self.stop_btn = tk.Button(ctrl_frame, text="⏹ Stop Server", command=self.stop_safe, bg="#f44336", fg="white", state=tk.DISABLED, font=("Arial", 10, "bold"), padx=20, pady=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.jupyter_log = scrolledtext.ScrolledText(self.tab_jupyter, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10))
        self.jupyter_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 20))

    def setup_git_tab(self):
        # 1. Configuration Panel
        config_panel = tk.LabelFrame(self.tab_git, text=" Configuration ", padx=10, pady=10)
        config_panel.pack(fill=tk.X, padx=15, pady=10)

        url_row = tk.Frame(config_panel); url_row.pack(fill=tk.X, pady=2)
        tk.Label(url_row, text="Repo URL:", width=10, anchor="w").pack(side=tk.LEFT)
        self.repo_entry = tk.Entry(url_row); self.repo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(url_row, text="Save", command=self.save_repo_url).pack(side=tk.LEFT)

        branch_row = tk.Frame(config_panel); branch_row.pack(fill=tk.X, pady=10)
        self.branch_combo = ttk.Combobox(branch_row, width=25, state="readonly"); self.branch_combo.pack(side=tk.LEFT, padx=5)
        tk.Button(branch_row, text="🔄 Sync Tree", command=self.sync_git_data, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        self.new_branch_entry = tk.Entry(branch_row, width=15); self.new_branch_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(branch_row, text="Switch", bg="#2196F3", fg="white", command=lambda: self.start_git_op(False)).pack(side=tk.LEFT, padx=2)
        tk.Button(branch_row, text="Create", bg="#388E3C", fg="white", command=lambda: self.start_git_op(True)).pack(side=tk.LEFT, padx=2)

        # 2. Main Git Display Area (Tree & Log)
        self.git_paned = ttk.Panedwindow(self.tab_git, orient=tk.VERTICAL)
        self.git_paned.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.tree_frame = tk.Frame(self.git_paned)
        self.tree = ttk.Treeview(self.tree_frame, columns=("SHA", "REFS", "AUTHOR", "DATE", "MESSAGE"), selectmode="browse")
        self.tree.heading("#0", text="Graph"); self.tree.heading("SHA", text="SHA"); self.tree.heading("REFS", text="Refs")
        self.tree.heading("AUTHOR", text="Author"); self.tree.heading("DATE", text="Date"); self.tree.heading("MESSAGE", text="Message")
        self.tree.column("#0", width=150); self.tree.column("SHA", width=90); self.tree.column("REFS", width=150)
        
        self.tree.tag_configure("graph_style", font=("Consolas", 10))
        self.tree.tag_configure("head_row", background="#e3f2fd")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.git_log = scrolledtext.ScrolledText(self.git_paned, height=6, font=("Consolas", 10), bg="#f8f9fa")
        self.git_paned.add(self.tree_frame, weight=3)
        self.git_paned.add(self.git_log, weight=1)

        # 3. Hierarchy Section (Bottom)
        self.status_frame = tk.LabelFrame(self.tab_git, text=" Branch Linkage Hierarchy ", padx=5, pady=5)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=10)
        
        self.hierarchy_canvas = tk.Canvas(self.status_frame, height=150, bg="#ffffff", highlightthickness=0)
        self.hierarchy_canvas.pack(fill=tk.X, expand=True)

        self.tree.bind("<Button-3>", self.show_tree_context_menu)
        self.load_repo_url()

    # --- REPO URL LOGIC ---
    def save_repo_url(self):
        path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
        repo = self.repo_entry.get().strip()
        branch = self.branch_combo.get() or "main"
        with open(path, "w") as f: 
            f.write(f'$GITHUB_REPO="{repo}"\n')
            f.write(f'$CURRENT_BRANCH="{branch}"')
        messagebox.showinfo("Success", f"Configuration Saved (Target: {branch})")

    def load_repo_url(self):
        path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        if "GITHUB_REPO" in line:
                            url = line.split('"')[1]
                            self.repo_entry.delete(0, tk.END)
                            self.repo_entry.insert(0, url)
            except: pass

    # --- HIERARCHY DRAWING ---
    def draw_hierarchy(self):
        self.hierarchy_canvas.delete("all")
        x_start = 20
        y_start = 30
        spacing = 35

        for i, (local, remote) in enumerate(self.branch_links):
            y = y_start + (i * spacing)
            is_active = (local == self.branch_combo.get())
            
            # Local Node
            color = "#2196F3" if is_active else "#607D8B"
            width = 3 if is_active else 1
            self.hierarchy_canvas.create_text(x_start, y, text=f" {local} ", anchor="w", 
                                             font=("Arial", 10, "bold"), fill=color)
            
            # Link Arrow (Dash if disconnected)
            dash_start = x_start + 110
            arrow_end = dash_start + 160
            line_color = "#4CAF50" if remote != "NO_UPSTREAM" else "#f44336"
            dash_pattern = None if remote != "NO_UPSTREAM" else (5, 5)
            
            self.hierarchy_canvas.create_line(dash_start, y, arrow_end, y, 
                                             arrow=tk.LAST, fill=line_color, 
                                             dash=dash_pattern, width=width)
            
            # Remote Node
            remote_text = remote if remote != "NO_UPSTREAM" else "⚠️ Disconnected"
            self.hierarchy_canvas.create_text(arrow_end + 10, y, text=remote_text, 
                                             anchor="w", font=("Consolas", 9), fill=line_color)

    # --- GIT STREAM LOGIC ---
    def parse_git_stream(self, line):
        line = line.strip()
        if not line: return
        
        if line.startswith("[LINK]"):
            raw = line.replace("[LINK]", "").strip().split("::")
            if len(raw) == 2: self.branch_links.append((raw[0], raw[1]))
        elif line.startswith("[BRANCH]"):
            b = line.replace("[BRANCH]", "").strip()
            if b not in self.found_branches: self.found_branches.append(b)
        elif line.startswith("[TREE]"):
            self.root.after(0, lambda: self.handle_tree_data(line[6:]))
        elif line.startswith("[ERROR]"):
            self.update_git_log(f"❌ {line[7:]}\n")
        else:
            self.update_git_log(line + "\n")

    def handle_tree_data(self, data):
        if data == "CLEAR_TREE":
            self.tree.delete(*self.tree.get_children())
            return
        p = data.split('::')
        while len(p) < 6: p.append("")
        row_id = str(uuid.uuid4())
        tags = ("graph_style",)
        if "HEAD" in p[2]: tags = ("graph_style", "head_row")
        self.tree.insert("", "end", iid=row_id, text=p[0], 
                         values=(p[1][:8] if p[1].strip() else "", p[2], p[3], p[4], p[5]), 
                         tags=tags)

    def sync_git_data(self):
        def task():
            self.found_branches = []
            self.branch_links = [] # Reset links for fresh draw
            script = os.path.join(self.project_root, "Windows", "manage_branch.ps1")
            proc = subprocess.Popen(["powershell", "-File", script, "-TargetBranch", "LIST", "-ListOnly"], 
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout: self.parse_git_stream(line)
            proc.wait()
            self.root.after(0, lambda: (
                self.branch_combo.config(values=sorted(self.found_branches)),
                self.draw_hierarchy()
            ))
        threading.Thread(target=task, daemon=True).start()

    def start_git_op(self, is_new):
        name = self.new_branch_entry.get().strip() if is_new else self.branch_combo.get()
        if not name: 
            messagebox.showwarning("Warning", "Select or enter a branch name.")
            return
        # Save selection to config so auto-push knows where to go
        self.save_repo_url()
        threading.Thread(target=self.run_branch_script, args=(name, is_new), daemon=True).start()

    def run_branch_script(self, branch_name, create_new, base_point=None):
        script = os.path.join(self.project_root, "Windows", "manage_branch.ps1")
        cmd = ["powershell", "-File", script, "-TargetBranch", branch_name]
        if create_new: cmd.append("-CreateNew")
        if base_point: cmd.extend(["-BaseCommit", base_point])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout: self.parse_git_stream(line)
        proc.wait()
        self.sync_git_data()

    def show_tree_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        self.tree.selection_set(item)
        sha = self.tree.item(item, "values")[0]
        if not sha: return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"🌿 New Branch from {sha}", command=lambda: self.prompt_new_branch(sha))
        menu.post(event.x_root, event.y_root)

    def prompt_new_branch(self, base_sha):
        name = simpledialog.askstring("New Branch", f"Name for branch starting at {base_sha}:")
        if name: threading.Thread(target=self.run_branch_script, args=(name, True, base_sha), daemon=True).start()

    def update_git_log(self, text): self.root.after(0, lambda: (self.git_log.insert(tk.END, text), self.git_log.see(tk.END)))
    
    def launch_safe(self): threading.Thread(target=self.run_jupyter_script, daemon=True).start()
    def run_jupyter_script(self):
        self.running = True
        self.root.after(0, lambda: (self.launch_btn.config(state=tk.DISABLED), self.stop_btn.config(state=tk.NORMAL)))
        script = os.path.join(self.project_root, "Windows", "jupyter_notebook.ps1")
        self.process = subprocess.Popen(["powershell", "-File", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in self.process.stdout: self.root.after(0, lambda l=line: (self.jupyter_log.insert(tk.END, l), self.jupyter_log.see(tk.END)))
        self.cleanup()

    def stop_safe(self):
        if self.process: subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)], capture_output=True)
        self.cleanup()

    def cleanup(self):
        self.running = False
        self.root.after(0, lambda: (self.launch_btn.config(state=tk.NORMAL), self.stop_btn.config(state=tk.DISABLED)))

    def safe_exit(self):
        if self.running: self.stop_safe()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = SafeJupyterLauncher(root); root.mainloop()