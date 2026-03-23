#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from modules import (
    ProcessManager, GitManager, JupyterUI, GitUI, 
    HierarchyDrawer, TreeView, WorkspaceManager, WorkspaceUI,
    PortManager, PortUI, SystemChecker, SystemCheckUI
)


class SafeJupyterLauncher:
    """Main application class - coordinates all modules"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Project Control Center")
        self.root.geometry("1100x950")
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        
        # Initialize managers
        self.workspace_manager = WorkspaceManager(self.update_log)
        self.port_manager = PortManager(self.update_log)
        self.process_manager = ProcessManager(self.update_jupyter_log, self.update_jupyter_state)
        self.git_manager = GitManager(self.project_root, self.update_git_log)
        self.system_checker = SystemChecker(self.update_log)
        
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
        
        # Create notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.tab_jupyter = ttk.Frame(self.notebook)
        self.tab_git = ttk.Frame(self.notebook)
        self.tab_workspace = ttk.Frame(self.notebook)
        self.tab_system = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_jupyter, text=" 🚀 Jupyter Dashboard ")
        self.notebook.add(self.tab_git, text=" 🌿 Git & Branch Manager ")
        self.notebook.add(self.tab_workspace, text=" 📁 Workspace Advanced ")
        self.notebook.add(self.tab_system, text=" 🔧 System Check ")
        
        # Initialize UI components
        self.setup_jupyter_tab()
        self.setup_git_tab()
        self.setup_workspace_tab()
        self.setup_system_tab()
        
        # Load saved configs
        self.load_repo_config()
    
    # ==================== UI SETUP METHODS ====================
    def setup_jupyter_tab(self):
        """Setup Jupyter tab with integrated port and workspace"""
        self.jupyter_ui = JupyterUI(
            self.tab_jupyter, 
            self.launch_jupyter, 
            self.stop_jupyter,
            self.port_manager,
            self.workspace_manager
        )
        # Update workspace display
        self.jupyter_ui.update_workspace_display()
    
    def setup_git_tab(self):
        """Setup Git tab"""
        self.git_ui = GitUI(self.tab_git, self.save_repo, self.sync_git, self.switch_branch, self.create_branch)
        
        # Initialize specialized UI components
        self.tree_view = TreeView(self.git_ui.get_tree_frame())
        self.hierarchy_drawer = HierarchyDrawer(self.git_ui.get_hierarchy_frame())
        
        # Bind context menu
        self.tree_view.bind("<Button-3>", self.show_context_menu)
    
    def setup_workspace_tab(self):
        """Setup Workspace Advanced Configuration tab"""
        self.workspace_ui = WorkspaceUI(
            self.tab_workspace,
            self.workspace_manager,
            self.on_workspace_changed
        )
        
        # Add info frame
        info_frame = tk.LabelFrame(self.tab_workspace, text=" ℹ️ Information ", padx=10, pady=10)
        info_frame.pack(fill=tk.X, padx=15, pady=10)
        
        info_text = """
You can also change workspace from the Jupyter Dashboard tab.
This tab provides additional workspace management options.
        """
        
        tk.Label(info_frame, text=info_text, justify=tk.LEFT, fg="gray").pack(anchor=tk.W)
    
    def setup_system_tab(self):
        """Setup System Check tab"""
        self.system_ui = SystemCheckUI(self.tab_system, self.system_checker)
    
    # ==================== JUPYTER METHODS ====================
    def launch_jupyter(self):
        """Launch Jupyter notebook with current workspace and port"""
        workspace = self.workspace_manager.get_workspace_path()
        port = self.port_manager.get_saved_port()
        
        # Validate port before launching
        validation = self.port_manager.validate_port(port)
        if not validation['valid']:
            messagebox.showerror(
                "Port Error",
                f"Cannot launch Jupyter:\n\n{validation['message']}\n\nPlease change the port in the Jupyter Dashboard tab."
            )
            return
        
        self.update_log(f"Launching Jupyter with workspace: {workspace}, port: {port}")
        
        # Call jupyter_notebook.ps1 (main entry point with Docker check)
        script = os.path.join(self.project_root, "Windows", "jupyter_notebook.ps1")
        self.process_manager.run_jupyter_script(script, self.project_root)
    
    def stop_jupyter(self):
        """Stop Jupyter"""
        self.process_manager.stop()
    
    # ==================== GIT METHODS ====================
    def save_repo(self):
        """Save repository configuration"""
        repo = self.git_ui.get_repo_entry().get().strip()
        branch = self.git_ui.get_branch_combo().get() or "main"
        self.git_manager.save_repo_config(repo, branch)
        messagebox.showinfo("Success", f"Configuration Saved (Target: {branch})")
    
    def load_repo_config(self):
        """Load saved repository configuration"""
        repo = self.git_manager.load_repo_config()
        if repo:
            self.git_ui.get_repo_entry().delete(0, tk.END)
            self.git_ui.get_repo_entry().insert(0, repo)
    
    def sync_git(self):
        """Sync Git data"""
        def on_branch(branch):
            self.git_ui.update_branches(self.git_manager.found_branches)
        
        def on_tree(data):
            self.tree_view.handle_tree_data(data)
        
        def on_link(local, remote):
            current_branch = self.git_ui.get_branch_combo().get()
            self.hierarchy_drawer.draw(self.git_manager.branch_links, current_branch)
        
        self.git_manager.sync_git_data(on_branch, on_tree, on_link)
    
    def switch_branch(self):
        """Switch to selected branch"""
        branch = self.git_ui.get_branch_combo().get()
        if not branch:
            messagebox.showwarning("Warning", "Select a branch to switch to.")
            return
        
        self.save_repo()
        self._run_branch_operation(branch, False)
    
    def create_branch(self):
        """Create new branch"""
        branch = self.git_ui.get_new_branch_entry().get().strip()
        if not branch:
            messagebox.showwarning("Warning", "Enter a branch name.")
            return
        
        self.save_repo()
        self._run_branch_operation(branch, True)
        self.git_ui.get_new_branch_entry().delete(0, tk.END)
    
    def _run_branch_operation(self, branch_name, create_new):
        """Run branch operation with callbacks"""
        def on_branch(branch):
            self.git_ui.update_branches(self.git_manager.found_branches)
        
        def on_tree(data):
            self.tree_view.handle_tree_data(data)
        
        def on_link(local, remote):
            current_branch = self.git_ui.get_branch_combo().get()
            self.hierarchy_drawer.draw(self.git_manager.branch_links, current_branch)
        
        self.git_manager.run_branch_operation(branch_name, create_new, None, on_branch, on_tree, on_link)
    
    def show_context_menu(self, event):
        """Show context menu for tree view"""
        item = self.tree_view.get_selected_item(event.y)
        if not item:
            return
        
        self.tree_view.select_item(item)
        values = self.tree_view.get_item_values(item)
        sha = values[0] if values else ""
        
        if not sha:
            return
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"🌿 New Branch from {sha}",
                        command=lambda: self.prompt_new_branch(sha))
        menu.post(event.x_root, event.y_root)
    
    def prompt_new_branch(self, base_sha):
        """Prompt for new branch from commit"""
        name = simpledialog.askstring("New Branch", f"Name for branch starting at {base_sha}:")
        if name:
            def on_branch(branch):
                self.git_ui.update_branches(self.git_manager.found_branches)
            
            def on_tree(data):
                self.tree_view.handle_tree_data(data)
            
            def on_link(local, remote):
                current_branch = self.git_ui.get_branch_combo().get()
                self.hierarchy_drawer.draw(self.git_manager.branch_links, current_branch)
            
            self.git_manager.run_branch_operation(name, True, base_sha, on_branch, on_tree, on_link)
    
    # ==================== CALLBACK METHODS ====================
    def update_log(self, text):
        """Update general log"""
        pass
    
    def update_jupyter_log(self, text):
        """Forward log to Jupyter UI"""
        self.jupyter_ui.update_log(text)
    
    def update_jupyter_state(self, is_running):
        """Forward state to Jupyter UI"""
        self.jupyter_ui.set_running_state(is_running)
    
    def update_git_log(self, text):
        """Forward log to Git UI"""
        self.git_ui.update_log(text)
    
    def on_workspace_changed(self):
        """Callback when workspace is changed"""
        workspace = self.workspace_manager.get_workspace_path()
        self.update_log(f"Workspace changed to: {workspace}")
        # Update the display in Jupyter tab
        self.jupyter_ui.update_workspace_display()
    
    # ==================== EXIT METHOD ====================
    def safe_exit(self):
        """Safe application exit"""
        if self.process_manager.is_running():
            self.stop_jupyter()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SafeJupyterLauncher(root)
    root.mainloop()