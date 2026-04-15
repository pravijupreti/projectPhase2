# helper/workspace_helper.py
import os
import tkinter as tk
from tkinter import filedialog, messagebox

class WorkspaceHelper:
    """Helper class to handle workspace selection only when needed"""
    
    def __init__(self, workspace_manager, log_callback=None):
        self.workspace_manager = workspace_manager
        self.log_callback = log_callback
    
    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)
    
    def ensure_workspace(self, parent=None):
        """Check if workspace exists, if not ask user to select one.
        Returns True if workspace is available, False otherwise."""
        
        workspace = self.workspace_manager.get_workspace_path()
        
        # Check if workspace is valid
        if workspace and workspace != self.workspace_manager._get_default_workspace():
            return True
        
        # No valid workspace - ask user
        response = messagebox.askyesno(
            "Workspace Required",
            "No working directory selected.\n\n"
            "This operation requires a workspace folder.\n"
            "Would you like to select a folder now?"
        )
        
        if not response:
            return False
        
        # Let user select folder
        workspace = filedialog.askdirectory(
            title="Select Workspace Directory",
            initialdir=os.path.expanduser("~/Desktop")
        )
        
        if not workspace:
            messagebox.showwarning("No Selection", "Workspace not selected. Operation cancelled.")
            return False
        
        # Save the selected workspace
        self.workspace_manager.set_workspace_path(workspace)
        self._log(f"✅ Workspace set to: {workspace}")
        return True
    
    def get_workspace(self):
        """Get workspace path, returns None if no valid workspace"""
        workspace = self.workspace_manager.get_workspace_path()
        if workspace and workspace != self.workspace_manager._get_default_workspace():
            return workspace
        return None