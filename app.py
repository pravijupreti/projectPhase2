#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from modules import (
    ProcessManager,
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


class SafeJupyterLauncher:
    """
    Main application — coordinates all modules.

    Push flow:
        "Push Changes" button
            → _push_to_github()          [saves config so script has latest URL]
                → GitManager.push_to_github(done_cb)
                    → runs git_auto_push.ps1 in daemon thread
                      (script owns workspace via Docker volume / Get-Location)
                    → stdout lines stream → GitUI log panel
                → _on_push_done()        [re-enables button, syncs tree]
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Project Control Center")
        self.root.geometry("1100x950")
        self.project_root = os.path.dirname(os.path.abspath(__file__))

        # ── managers ──────────────────────────────────────────────
        self.workspace_manager = WorkspaceManager(self.update_log)
        self.port_manager      = PortManager(self.update_log)
        self.process_manager   = ProcessManager(
            self.update_jupyter_log, self.update_jupyter_state
        )
        self.git_manager    = GitManager(self.project_root, self.update_git_log)
        self.system_checker = SystemChecker(self.update_log)

        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)

        # ── notebook ──────────────────────────────────────────────
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_jupyter   = ttk.Frame(self.notebook)
        self.tab_git       = ttk.Frame(self.notebook)
        self.tab_workspace = ttk.Frame(self.notebook)
        self.tab_system    = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_jupyter,   text=" 🚀 Jupyter Dashboard ")
        self.notebook.add(self.tab_git,       text=" 🌿 Git & Branch Manager ")
        self.notebook.add(self.tab_workspace, text=" 📁 Workspace Advanced ")
        self.notebook.add(self.tab_system,    text=" 🔧 System Check ")

        # ── UI components ─────────────────────────────────────────
        self._setup_jupyter_tab()
        self._setup_git_tab()
        self._setup_workspace_tab()
        self._setup_system_tab()

        self._load_repo_config()

    # ══════════════════════════════════════════════════════════════
    # TAB SETUP
    # ══════════════════════════════════════════════════════════════

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
        """Handle Git errors (no repo, no branches, etc.)"""
        self.root.after(0, lambda: messagebox.showerror("Git Error", error_msg))
        self.root.after(0, lambda: self.git_ui.update_log(f"❌ {error_msg}\n"))
    
    def _setup_git_tab(self):
        self.git_ui = GitUI(
            self.tab_git,
            save_cb   = self._save_repo,
            sync_cb   = self._sync_git,
            switch_cb = self._switch_branch,
            create_cb = self._create_branch,
            push_cb   = self._push_to_github,
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
            self.tab_workspace, text=" ℹ️ Information ", padx=10, pady=10
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
        workspace  = self.workspace_manager.get_workspace_path()
        port       = self.port_manager.get_saved_port()
        validation = self.port_manager.validate_port(port)

        if not validation["valid"]:
            messagebox.showerror(
                "Port Error",
                f"Cannot launch Jupyter:\n\n{validation['message']}\n\n"
                "Please change the port in the Jupyter Dashboard tab.",
            )
            return

        self.update_log(f"Launching Jupyter — workspace: {workspace}  port: {port}")
        script = os.path.join(self.project_root, "Windows", "jupyter_notebook.ps1")
        self.process_manager.run_jupyter_script(script, self.project_root)

    def stop_jupyter(self):
        self.process_manager.stop()

    # ══════════════════════════════════════════════════════════════
    # GIT ACTIONS
    # ══════════════════════════════════════════════════════════════

    def _save_repo(self):
        repo   = self.git_ui.get_repo_entry().get().strip()
        branch = self.git_ui.get_branch_combo().get() or "main"
        self.git_manager.save_repo_config(repo, branch)
        messagebox.showinfo("Saved", f"Config saved  (branch: {branch})")

    def _load_repo_config(self):
        url = self.git_manager.load_repo_config()
        if url:
            self.git_ui.set_repo_url(url)

    def _sync_git(self):
        self.tree_view.clear()
        workspace_path = self.workspace_manager.get_workspace_path()
    
        self.git_manager.sync_git_data(
            workspace_path,
            branch_cb = self._on_branch_found,
            tree_cb   = self._on_tree_line,
            link_cb   = self._on_link_found,
            error_cb  = self._on_git_error
        )

    def _switch_branch(self):
        branch = self.git_ui.get_branch_combo().get()
        if not branch:
            messagebox.showwarning("Warning", "Select a branch to switch to.")
            return
        self._save_repo()
        self._run_branch_op(branch, create_new=False)

    def _create_branch(self):
        branch = self.git_ui.get_new_branch_entry().get().strip()
        if not branch or branch == "new-branch-name":
            messagebox.showwarning("Warning", "Enter a branch name.")
            return
        self._save_repo()
        self._run_branch_op(branch, create_new=True)
        self.git_ui.get_new_branch_entry().delete(0, tk.END)

    def _run_branch_op(self, branch_name: str, create_new: bool,
                       base_commit: str = None):
        workspace_path = self.workspace_manager.get_workspace_path()
    
        self.git_manager.run_branch_operation(
            workspace_path,
            branch_name,
            create_new      = create_new,
            base_commit     = base_commit,
            branch_cb       = self._on_branch_found,
            tree_cb         = self._on_tree_line,
            link_cb         = self._on_link_found,
            error_cb        = self._on_git_error,
        )

    # ── push ──────────────────────────────────────────────────────

    def _push_to_github(self):
        """
        Only responsibility: ensure config is written so the script
        has the latest repo URL + branch, then hand off entirely to
        git_auto_push.ps1.  Workspace comes from the Docker volume
        inside the script (Get-Location) — Python passes nothing extra.
        """
        repo = self.git_ui.get_repo_entry().get().strip()
        if not repo:
            messagebox.showwarning(
                "No Repo URL",
                "Enter a GitHub repository URL and press Save before pushing."
            )
            return

        # write config so git_auto_push.ps1 picks up the current values
        branch = self.git_ui.get_branch_combo().get() or "main"
        self.git_manager.save_repo_config(repo, branch)

        self.git_ui.set_push_busy(True)
        self.git_ui.set_push_status("Pushing…", "#1565C0")

        workspace_path = self.workspace_manager.get_workspace_path()
        self.git_manager.push_to_github(workspace_path, done_callback=self._on_push_done)

    def _on_push_done(self):
        """Worker thread calls this when git_auto_push.ps1 exits."""
        self.root.after(0, self._push_finished)

    def _push_finished(self):
        self.git_ui.set_push_busy(False)
        self.git_ui.set_push_status("✅ Push complete", "#2E7D32")
        # refresh tree so the new auto-backup commit appears
        self._sync_git()

    # ── context menu ──────────────────────────────────────────────

    def _on_tree_right_click(self, event):
        sha = self.tree_view.get_selected_sha(event.y)
        if not sha:
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=f"🌿 New branch from {sha}",
            command=lambda: self._prompt_new_branch(sha),
        )
        menu.post(event.x_root, event.y_root)

    def _prompt_new_branch(self, base_sha: str):
        name = simpledialog.askstring(
            "New Branch", f"Name for branch starting at commit {base_sha}:"
        )
        if name:
            self._run_branch_op(name, create_new=True, base_commit=base_sha)

    # ══════════════════════════════════════════════════════════════
    # GIT CALLBACKS  (GitManager worker threads → main thread)
    # ══════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════
    # GENERIC CALLBACKS
    # ══════════════════════════════════════════════════════════════

    def update_log(self, text: str):
        pass  # extend to write to a status bar if desired

    def update_jupyter_log(self, text: str):
        self.jupyter_ui.update_log(text)

    def update_jupyter_state(self, is_running: bool):
        self.jupyter_ui.set_running_state(is_running)

    def update_git_log(self, text: str):
        self.git_ui.update_log(text)

    def _on_workspace_changed(self):
        self.update_log(f"Workspace → {self.workspace_manager.get_workspace_path()}")
        self.jupyter_ui.update_workspace_display()

    # ══════════════════════════════════════════════════════════════
    # EXIT
    # ══════════════════════════════════════════════════════════════

    def safe_exit(self):
        if self.process_manager.is_running():
            self.stop_jupyter()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app  = SafeJupyterLauncher(root)
    root.mainloop()