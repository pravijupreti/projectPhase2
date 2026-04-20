#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import traceback
from datetime import datetime

from Windows.UImodules import (
    GitManager,
    JupyterUI,
    GitUI,
    HierarchyDrawer,
    TreeView,
    WorkspaceManager,
    WorkspaceUI,
    PortManager,
    PortUI,
    SystemChecker,
    SystemCheckUI,
)

from helper.script_caller import ScriptCaller


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)

LOG_FILE = os.path.join(BASE_DIR, "runtime_log.txt")


def log_runtime(message: str):
    """Write normal runtime logs"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")


def install_exception_logger():
    def handle_exception(exc_type, exc_value, exc_traceback):
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"[{datetime.now()}] UNCAUGHT EXCEPTION\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write("=" * 80 + "\n")

    sys.excepthook = handle_exception



class SafeJupyterLauncher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Project Control Center")
        self.root.geometry("1100x950")
        self.project_root = os.path.dirname(os.path.abspath(__file__))

        # ── managers ──────────────────────────────────────────────
        self.workspace_manager = WorkspaceManager(self.update_log)
        self.port_manager      = PortManager(self.update_log)
        self.git_manager       = GitManager(self.project_root, self.update_git_log, self.workspace_manager)
        self.system_checker    = SystemChecker(self.update_log)

        # ── Script caller (centralized) ──────────────────────────
        self.script_caller = ScriptCaller(self.project_root, self.workspace_manager, self.update_log)

        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)

        # ── notebook ──────────────────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_jupyter   = ttk.Frame(self.notebook)
        self.tab_git       = ttk.Frame(self.notebook)
        self.tab_workspace = ttk.Frame(self.notebook)
        self.tab_system    = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_jupyter,   text=" Jupyter Dashboard ")
        self.notebook.add(self.tab_git,       text=" Git & Branch Manager ")
        self.notebook.add(self.tab_workspace, text=" Workspace Advanced ")
        self.notebook.add(self.tab_system,    text=" System Check ")

        # ── UI components ─────────────────────────────────────────
        self._setup_jupyter_tab()
        self._setup_git_tab()
        self._setup_workspace_tab()
        self._setup_system_tab()

        self._load_repo_config()

    def _setup_jupyter_tab(self):
        self.jupyter_ui = JupyterUI(
            self.tab_jupyter,
            self.launch_jupyter,
            self.stop_jupyter,
            self.port_manager,
            self.workspace_manager,
        )
        self.jupyter_ui.update_workspace_display()

    def _on_git_error(self, error_msg: str):
        self.root.after(0, lambda: messagebox.showerror("Git Error", error_msg))
        self.root.after(0, lambda: self.git_ui.update_log(f"{error_msg}\n"))
    
    def _setup_git_tab(self):
        self.git_ui = GitUI(
            self.tab_git,
            save_cb   = self._save_repo,
            sync_cb   = self._sync_git,
            switch_cb = self._switch_branch,
            create_cb = self._create_branch,
            push_cb   = self._push_to_github,
            workspace_manager = self.workspace_manager,
        )
        self.tree_view        = TreeView(self.git_ui.get_tree_frame())
        self.hierarchy_drawer = HierarchyDrawer(self.git_ui.get_hierarchy_frame())
        self.tree_view.bind("<Button-3>", self._on_tree_right_click)

    def _setup_workspace_tab(self):
        self.workspace_ui = WorkspaceUI(
            self.tab_workspace,
            self.workspace_manager,
            self._on_workspace_changed,
        )
        info_frame = tk.LabelFrame(
            self.tab_workspace, text=" ℹInformation ", padx=10, pady=10
        )
        info_frame.pack(fill=tk.X, padx=15, pady=10)
        tk.Label(
            info_frame,
            text=(
                "You can also change workspace from the Jupyter Dashboard tab.\n"
                "This tab provides additional workspace management options."
            ),
            justify=tk.LEFT,
            fg="gray",
        ).pack(anchor=tk.W)

    def _setup_system_tab(self):
        self.system_ui = SystemCheckUI(self.tab_system, self.system_checker)

    # ══════════════════════════════════════════════════════════════
    # JUPYTER ACTIONS
    # ══════════════════════════════════════════════════════════════

    def launch_jupyter(self):
        port = self.port_manager.get_saved_port()
        validation = self.port_manager.validate_port(port)

        if not validation["valid"]:
            messagebox.showerror(
                "Port Error",
                f"Cannot launch Jupyter:\n\n{validation['message']}\n\n"
                "Please change the port in the Jupyter Dashboard tab.",
            )
            return

        self.update_log(f"Launching Jupyter on port: {port}")
        
        try:
            self.script_caller.jupyter_script(port, self.update_jupyter_state)
            self.update_log("Jupyter launch initiated")
        except Exception as e:
            error_msg = f"Failed to launch Jupyter: {str(e)}"
            self.update_log(error_msg)
            messagebox.showerror("Launch Error", error_msg)

    def stop_jupyter(self):
        self.update_log("Stopping Jupyter...")
        self.script_caller.stop_jupyter()
        self.update_log("Jupyter stopped")

    # ══════════════════════════════════════════════════════════════
    # GIT ACTIONS
    # ══════════════════════════════════════════════════════════════

    def _save_repo(self):
        repo   = self.git_ui.get_repo_entry().get().strip()
        branch = self.git_ui.get_branch_combo().get() or "main"
        self.git_manager.save_repo_config(repo, branch)
        messagebox.showinfo("Saved", f"Config saved (branch: {branch})")
        self.update_log(f"Repo config saved: {repo} (branch: {branch})")

    def _load_repo_config(self):
        url = self.git_manager.load_repo_config()
        if url:
            self.git_ui.set_repo_url(url)
            self.update_log(f"Loaded repo config: {url}")

    def _sync_git(self):
        self.update_log("Syncing git data...")
        self.tree_view.clear()
        self.git_manager.sync_git_data(
            branch_cb=self._on_branch_found,
            tree_cb=self._on_tree_line,
            link_cb=self._on_link_found,
            error_cb=self._on_git_error
        )

    def _switch_branch(self):
        branch = self.git_ui.get_branch_combo().get()
        if not branch:
            messagebox.showwarning("Warning", "Select a branch to switch to.")
            return
        self.update_log(f"Switching to branch: {branch}")
        self._save_repo()
        self._run_branch_op(branch, create_new=False)

    def _create_branch(self):
        branch = self.git_ui.get_new_branch_entry().get().strip()
        if not branch or branch == "new-branch-name":
            messagebox.showwarning("Warning", "Enter a branch name.")
            return
        self.update_log(f"Creating new branch: {branch}")
        self._save_repo()
        self._run_branch_op(branch, create_new=True)
        self.git_ui.get_new_branch_entry().delete(0, tk.END)

    def _run_branch_op(self, branch_name: str, create_new: bool, base_commit: str = None):
        self.script_caller.git_branch_script(branch_name, create_new, base_commit)
        
        # Then refresh git data
        self.git_manager.sync_git_data(
            branch_cb=self._on_branch_found,
            tree_cb=self._on_tree_line,
            link_cb=self._on_link_found,
            error_cb=self._on_git_error,
        )

    def _push_to_github(self):
        repo = self.git_ui.get_repo_entry().get().strip()
        if not repo:
            messagebox.showwarning(
                "No Repo URL",
                "Enter a GitHub repository URL and press Save before pushing."
            )
            return

        branch = self.git_ui.get_branch_combo().get() or "main"
        self.git_manager.save_repo_config(repo, branch)

        self.git_ui.set_push_busy(True)
        self.git_ui.set_push_status("Pushing…", "#1565C0")
        self.update_log(f"Pushing to GitHub: {repo} (branch: {branch})")

        self.script_caller.git_push_script(self._on_push_done)

    def _on_push_done(self):
        self.root.after(0, self._push_finished)

    def _push_finished(self):
        self.git_ui.set_push_busy(False)
        self.git_ui.set_push_status("Push complete", "#2E7D32")
        self.update_log("Git push completed successfully")
        self._sync_git()

    def _on_tree_right_click(self, event):
        sha = self.tree_view.get_selected_sha(event.y)
        if not sha:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=f"New branch from {sha}",
            command=lambda: self._prompt_new_branch(sha),
        )
        menu.post(event.x_root, event.y_root)

    def _prompt_new_branch(self, base_sha: str):
        name = simpledialog.askstring(
            "New Branch", f"Name for branch starting at commit {base_sha}:"
        )
        if name:
            self._run_branch_op(name, create_new=True, base_commit=base_sha)

    def _on_branch_found(self, _branch: str):
        self.root.after(
            0, lambda: self.git_ui.update_branches(self.git_manager.found_branches)
        )

    def _on_tree_line(self, raw_line: str):
        self.root.after(0, lambda: self.tree_view.handle_tree_data(raw_line))

    def _on_link_found(self, _local: str, _remote: str):
        current = self.git_ui.get_branch_combo().get()
        self.root.after(
            0,
            lambda: self.hierarchy_drawer.draw(
                self.git_manager.branch_links, current
            ),
        )

    def update_log(self, text: str):
        """Show logs in the Jupyter UI log panel"""
        if hasattr(self, 'jupyter_ui'):
            self.jupyter_ui.update_log(text + "\n")
        print(text)

    def update_jupyter_log(self, text: str):
        self.jupyter_ui.update_log(text)

    def update_jupyter_state(self, is_running: bool):
        self.jupyter_ui.set_running_state(is_running)
        if is_running:
            self.update_log("Jupyter is now running")
        else:
            self.update_log("Jupyter has stopped")

    def update_git_log(self, text: str):
        self.git_ui.update_log(text)

    def _on_workspace_changed(self):
        self.update_log(f"Workspace changed → {self.workspace_manager.get_workspace_path()}")
        self.jupyter_ui.update_workspace_display()

    def safe_exit(self):
        if self.script_caller.is_running():
            self.stop_jupyter()
        self.root.destroy()


if __name__ == "__main__":
    try:
        install_exception_logger()
        log_runtime("Application starting")

        root = tk.Tk()
        app = SafeJupyterLauncher(root)
        root.mainloop()

        log_runtime("Application closed normally")

    except Exception:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\nFATAL STARTUP ERROR\n")
            traceback.print_exc(file=f)