# modules/workspace_ui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class WorkspaceUI:
    """Workspace configuration UI component for Docker volume"""
    
    def __init__(self, parent, workspace_manager, on_workspace_changed=None):
        self.parent = parent
        self.workspace_manager = workspace_manager
        self.on_workspace_changed = on_workspace_changed
        self.create_widgets()
        self.refresh_display()
    
    def create_widgets(self):
        """Create workspace UI widgets"""
        # Main frame
        self.frame = tk.LabelFrame(
            self.parent, 
            text=" 📁 Docker Volume - Workspace Directory ", 
            padx=10, 
            pady=10,
            font=("Arial", 10, "bold")
        )
        self.frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Description
        desc_label = tk.Label(
            self.frame,
            text="This directory will be mounted to the Docker container.\nAll Jupyter notebooks and files will be saved here.",
            fg="gray",
            justify=tk.LEFT
        )
        desc_label.pack(fill=tk.X, pady=(0, 10))
        
        # Current workspace display
        current_frame = tk.Frame(self.frame)
        current_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(current_frame, text="Current Workspace:", width=15, anchor="w", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.workspace_label = tk.Label(current_frame, text="", fg="blue", anchor="w")
        self.workspace_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Buttons frame
        buttons_frame = tk.Frame(self.frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Change button - opens folder dialog
        self.change_btn = tk.Button(
            buttons_frame, 
            text="📁 Change Workspace Directory",
            command=self.change_workspace,
            bg="#2196F3", 
            fg="white", 
            padx=15, 
            pady=5
        )
        self.change_btn.pack(side=tk.LEFT, padx=5)
        
        # Open button - opens in explorer
        self.open_btn = tk.Button(
            buttons_frame, 
            text="📂 Open in File Explorer",
            command=self.open_workspace,
            bg="#607D8B", 
            fg="white", 
            padx=15, 
            pady=5
        )
        self.open_btn.pack(side=tk.LEFT, padx=5)
        
        # Info button - shows details
        self.info_btn = tk.Button(
            buttons_frame, 
            text="ℹ️ Workspace Info",
            command=self.show_info,
            bg="#FF9800", 
            fg="white", 
            padx=15, 
            pady=5
        )
        self.info_btn.pack(side=tk.LEFT, padx=5)
        
        # Status indicator
        self.status_label = tk.Label(self.frame, text="", font=("Arial", 9))
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def refresh_display(self):
        """Refresh workspace display"""
        info = self.workspace_manager.get_workspace_info()
        
        # Update label with truncation if needed
        path = info['path']
        if len(path) > 60:
            path = "..." + path[-57:]
        self.workspace_label.config(text=path)
        
        # Update status indicator
        if info['exists'] and info['writable']:
            self.status_label.config(text="✅ Ready - Writable", fg="green")
        elif info['exists']:
            self.status_label.config(text="⚠️ Exists but Read Only", fg="orange")
        else:
            self.status_label.config(text="❌ Directory Not Found", fg="red")
    
    def change_workspace(self):
        """Open folder dialog to change workspace directory"""
        new_path = filedialog.askdirectory(
            title="Select Jupyter Workspace Directory",
            initialdir=self.workspace_manager.get_workspace_path()
        )
        
        if new_path:
            success = self.workspace_manager.set_workspace_path(new_path, create_if_not_exist=True)
            if success:
                self.refresh_display()
                messagebox.showinfo(
                    "Success", 
                    f"Workspace directory changed to:\n{new_path}\n\nThis directory will be mounted to the Docker container."
                )
                if self.on_workspace_changed:
                    self.on_workspace_changed()
            else:
                messagebox.showerror(
                    "Error", 
                    f"Failed to set workspace directory.\n\nMake sure you have write permissions."
                )
    
    def open_workspace(self):
        """Open workspace in file explorer"""
        path = self.workspace_manager.get_workspace_path()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning(
                "Warning", 
                f"Workspace directory does not exist:\n{path}\n\nPlease select a valid directory."
            )
    
    def show_info(self):
        """Show workspace information dialog"""
        info = self.workspace_manager.get_workspace_info()
        
        info_text = f"""
╔══════════════════════════════════════════════════════════╗
║                 WORKSPACE INFORMATION                    ║
╚══════════════════════════════════════════════════════════╝

📍 Path: {info['path']}

📁 Status:
   • Exists: {'✅ Yes' if info['exists'] else '❌ No'}
   • Writable: {'✅ Yes' if info['writable'] else '❌ No'}

📦 Docker Volume Mount:
   Windows Path: {info['path']}
   Container Path: /tf/notebooks

💡 Notes:
   • All Jupyter notebooks will be saved here
   • This directory is mounted to the Docker container
   • You can change this location anytime
   • The setting is saved in: ~/.jupyter_workspace_config.json
        """
        
        messagebox.showinfo("Workspace Information", info_text)