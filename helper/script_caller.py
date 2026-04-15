import os
import subprocess
import threading
import sys
from tkinter import filedialog, messagebox

class ScriptCaller:
    """Centralized script calling - all script execution happens here"""
    
    def __init__(self, project_root, workspace_manager, log_callback=None):
        self.project_root = project_root
        self.workspace_manager = workspace_manager
        self.log_callback = log_callback
        self.process = None
        self.running = False
    
    def _log(self, message):
        """Log message to both callback AND console"""
        print(f"[SCRIPT_CALLER] {message}")
        if self.log_callback:
            self.log_callback(message)
    
    def _log_error(self, message):
        """Log error messages prominently"""
        error_msg = f"❌ ERROR: {message}"
        print(f"[ERROR] {error_msg}")
        if self.log_callback:
            self.log_callback(error_msg)
    
    def _ensure_workspace(self) -> str:
        """Get workspace path, ask user if not set"""
        if not self.workspace_manager:
            self._log_error("Workspace manager not available")
            return None
            
        workspace = self.workspace_manager.get_workspace_path()
        
        # Check if workspace is valid
        if workspace and workspace != self.workspace_manager._get_default_workspace():
            if os.path.exists(workspace):
                return workspace
        
        # No valid workspace - ask user
        response = messagebox.askyesno(
            "Workspace Required",
            "No working directory selected.\n\n"
            "This operation requires a workspace folder.\n"
            "Would you like to select a folder now?"
        )
        
        if not response:
            return None
        
        # Let user select folder
        workspace = filedialog.askdirectory(
            title="Select Workspace Directory",
            initialdir=os.path.expanduser("~/Desktop")
        )
        
        if not workspace:
            messagebox.showwarning("No Selection", "Workspace not selected. Operation cancelled.")
            return None
        
        # Save the selected workspace
        self.workspace_manager.set_workspace_path(workspace)
        self._log(f"✅ Workspace set to: {workspace}")
        return workspace
    
    def jupyter_script(self, port, status_callback=None):
        """Call Jupyter notebook script - workspace auto-detected"""
        workspace_path = self._ensure_workspace()
        if not workspace_path:
            if status_callback:
                status_callback(False)
            return
        
        script_path = os.path.join(self.project_root, "Windows", "jupyter_notebook.ps1")
        
        if not os.path.exists(script_path):
            self._log_error(f"Script not found: {script_path}")
            if status_callback:
                status_callback(False)
            return
        
        self._log(f"Calling Jupyter script: {script_path}")
        self._log(f"Workspace: {workspace_path}")
        self._log(f"Port: {port}")
        
        self.running = True
        if status_callback:
            status_callback(True)
        
        def task():
            try:
                self._log("Starting subprocess...")
                self.process = subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, "-Port", str(port)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=workspace_path
                )
                
                for line in self.process.stdout:
                    self._log(f"[JUPYTER] {line.strip()}")
                
                for line in self.process.stderr:
                    self._log_error(f"{line.strip()}")
                
                self.process.wait()
                self._log(f"Process finished with exit code: {self.process.returncode}")
                
            except FileNotFoundError as e:
                self._log_error(f"PowerShell not found: {str(e)}")
            except Exception as e:
                self._log_error(f"Unexpected error: {str(e)}")
            finally:
                self.running = False
                if status_callback:
                    status_callback(False)
                self.process = None
        
        threading.Thread(target=task, daemon=True).start()
    
    def git_push_script(self, done_callback=None):
        """Call git auto push script - workspace auto-detected"""
        workspace_path = self._ensure_workspace()
        if not workspace_path:
            if done_callback:
                done_callback()
            return
        
        script_path = os.path.join(self.project_root, "Windows", "git_auto_push.ps1")
        
        if not os.path.exists(script_path):
            self._log_error(f"Script not found: {script_path}")
            if done_callback:
                done_callback()
            return
        
        self._log(f"Calling Git push script: {script_path}")
        self._log(f"Workspace: {workspace_path}")
        
        def task():
            try:
                self._log("Starting git push subprocess...")
                process = subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, 
                     "-WorkspacePath", workspace_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=workspace_path
                )
                
                for line in process.stdout:
                    self._log(f"[GIT] {line.strip()}")
                
                for line in process.stderr:
                    self._log_error(f"{line.strip()}")
                
                process.wait()
                self._log(f"Git push finished with exit code: {process.returncode}")
                
                if done_callback:
                    done_callback()
                    
            except FileNotFoundError as e:
                self._log_error(f"PowerShell not found: {str(e)}")
            except Exception as e:
                self._log_error(f"Unexpected error: {str(e)}")
        
        threading.Thread(target=task, daemon=True).start()
    
    def git_branch_script(self, branch_name, create_new=False, base_commit=None):
        """Call git branch management script - workspace auto-detected"""
        workspace_path = self._ensure_workspace()
        if not workspace_path:
            return
        
        script_path = os.path.join(self.project_root, "Windows", "manage_branch.ps1")
        
        if not os.path.exists(script_path):
            self._log_error(f"Script not found: {script_path}")
            return
        
        # FIXED: Use -TargetBranch instead of -BranchName
        args = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, 
                "-WorkspacePath", workspace_path, "-TargetBranch", branch_name]
        
        if create_new:
            args.append("-CreateNew")
        if base_commit:
            args.extend(["-BaseCommit", base_commit])
        
        self._log(f"Calling Git branch script: {' '.join(args)}")
        self._log(f"Workspace: {workspace_path}")
        
        def task():
            try:
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=workspace_path
                )
                
                for line in process.stdout:
                    self._log(f"[BRANCH] {line.strip()}")
                
                for line in process.stderr:
                    self._log_error(f"{line.strip()}")
                
                process.wait()
                self._log(f"Branch operation finished with exit code: {process.returncode}")
                
            except Exception as e:
                self._log_error(f"Error: {str(e)}")
        
        threading.Thread(target=task, daemon=True).start()
    
    def stop_jupyter(self):
        """Stop running Jupyter process"""
        if self.process:
            self._log("Stopping Jupyter process...")
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)], 
                         capture_output=True)
            self.running = False
            self.process = None
            self._log("Jupyter process stopped")
        else:
            self._log("No Jupyter process running")
    
    def is_running(self):
        return self.running