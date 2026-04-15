# modules/jupyter_ui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class JupyterUI:
    """Jupyter tab UI component with integrated port selection"""
    
    def __init__(self, parent, launch_callback, stop_callback, port_manager=None, workspace_manager=None):
        self.parent = parent
        self.launch_callback = launch_callback
        self.stop_callback = stop_callback
        self.port_manager = port_manager
        self.workspace_manager = workspace_manager
        self.create_widgets()
        self.refresh_port_display()
    
    def create_widgets(self):
        """Create all Jupyter tab widgets"""
        # Main container
        main_frame = tk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ========== Configuration Section ==========
        config_frame = tk.LabelFrame(main_frame, text=" Configuration ", padx=10, pady=10, font=("Arial", 10, "bold"))
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Workspace row
        workspace_frame = tk.Frame(config_frame)
        workspace_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(workspace_frame, text="Workspace:", width=12, anchor="w").pack(side=tk.LEFT)
        self.workspace_label = tk.Label(workspace_frame, text="", fg="blue", anchor="w")
        self.workspace_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Button(workspace_frame, text="Change", command=self.change_workspace, bg="#607D8B", fg="white", padx=10).pack(side=tk.RIGHT)
        
        # Port row
        port_frame = tk.Frame(config_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(port_frame, text="Jupyter Port:", width=12, anchor="w").pack(side=tk.LEFT)
        
        self.port_var = tk.StringVar()
        self.port_entry = tk.Entry(port_frame, textvariable=self.port_var, width=10)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.port_status = tk.Label(port_frame, text="", font=("Arial", 9))
        self.port_status.pack(side=tk.LEFT, padx=10)
        
        # Port buttons
        self.check_port_btn = tk.Button(
            port_frame, text="Check", command=self.check_port,
            bg="#FF9800", fg="white", padx=10, width=6
        )
        self.check_port_btn.pack(side=tk.LEFT, padx=2)
        
        self.suggest_port_btn = tk.Button(
            port_frame, text="Suggest", command=self.suggest_port,
            bg="#4CAF50", fg="white", padx=10, width=6
        )
        self.suggest_port_btn.pack(side=tk.LEFT, padx=2)
        
        self.apply_port_btn = tk.Button(
            port_frame, text="Apply", command=self.apply_port,
            bg="#2196F3", fg="white", padx=10, width=6
        )
        self.apply_port_btn.pack(side=tk.LEFT, padx=2)
        
        # ========== Control Section ==========
        control_frame = tk.Frame(main_frame)
        control_frame.pack(pady=10, fill=tk.X)
        
        self.launch_btn = tk.Button(
            control_frame, text="▶ Launch Jupyter", command=self.launch_callback,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20, pady=10
        )
        self.launch_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(
            control_frame, text="⏹ Stop Server", command=self.stop_callback,
            bg="#f44336", fg="white", state=tk.DISABLED,
            font=("Arial", 10, "bold"), padx=20, pady=10
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # ========== Log Section ==========
        log_frame = tk.LabelFrame(main_frame, text=" Jupyter Log ", font=("Arial", 10, "bold"))
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(
            log_frame, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10)
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def refresh_port_display(self):
        """Refresh port display with current saved port"""
        if self.port_manager:
            saved_port = self.port_manager.get_saved_port()
            self.port_var.set(str(saved_port))
            self.update_port_status()
    
    def update_port_status(self):
        """Update port status indicator"""
        if self.port_manager:
            try:
                port = int(self.port_var.get().strip())
                validation = self.port_manager.validate_port(port)
                if validation['safe']:
                    self.port_status.config(text="✓ Available", fg="green")
                else:
                    self.port_status.config(text="✗ In Use", fg="red")
            except:
                self.port_status.config(text="Invalid", fg="red")
    
    def check_port(self):
        """Check current port status"""
        if not self.port_manager:
            return
        
        try:
            port = int(self.port_var.get().strip())
            info = self.port_manager.get_port_info(port)
            
            status_text = f"Port {port} Status:\n"
            status_text += "=" * 40 + "\n\n"
            
            if info['available']:
                status_text += "✓ Port is AVAILABLE\n"
                status_text += "   This port is free to use."
            else:
                status_text += "✗ Port is IN USE\n\n"
                
                if info['containers']:
                    status_text += "Docker Containers using this port:\n"
                    for c in info['containers']:
                        status_text += f"  • {c['name']}: {c['ports']}\n"
                
                if info['processes']:
                    status_text += "\nSystem Processes using this port:\n"
                    for p in info['processes']:
                        status_text += f"  • PID: {p['pid']}, Name: {p['name']}\n"
                
                status_text += f"\n💡 Suggested port: {info['suggested']}"
            
            messagebox.showinfo("Port Check", status_text)
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")
    
    def suggest_port(self):
        """Suggest an available port"""
        if not self.port_manager:
            return
        
        suggested = self.port_manager.get_suggested_port()
        self.port_var.set(str(suggested))
        self.update_port_status()
        messagebox.showinfo("Suggested Port", f"Suggested available port: {suggested}\n\nClick 'Apply' to use this port.")
    
    def apply_port(self):
        """Apply the selected port"""
        if not self.port_manager:
            return
        
        try:
            new_port = int(self.port_var.get().strip())
            validation = self.port_manager.validate_port(new_port)
            
            if validation['valid']:
                self.port_manager.set_port(new_port)
                self.update_port_status()
                messagebox.showinfo("Success", f"Port changed to {new_port}")
            else:
                messagebox.showerror("Port Error", validation['message'])
                # Suggest using the suggested port
                if validation.get('suggested_port'):
                    result = messagebox.askyesno("Use Suggested", f"Suggested port: {validation['suggested_port']}\n\nDo you want to use this port?")
                    if result:
                        self.port_var.set(str(validation['suggested_port']))
                        self.port_manager.set_port(validation['suggested_port'])
                        self.update_port_status()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")
    
    def change_workspace(self):
        """Open dialog to change workspace"""
        if not self.workspace_manager:
            return
        
        from tkinter import filedialog
        current = self.workspace_manager.get_workspace_path()
        new_path = filedialog.askdirectory(title="Select Jupyter Workspace", initialdir=current)
        
        if new_path:
            success = self.workspace_manager.set_workspace_path(new_path, create_if_not_exist=True)
            if success:
                self.workspace_label.config(text=new_path[:60] + "..." if len(new_path) > 60 else new_path)
                messagebox.showinfo("Success", f"Workspace changed to:\n{new_path}")
            else:
                messagebox.showerror("Error", "Failed to set workspace")
    
    def update_workspace_display(self):
        """Update workspace display"""
        if self.workspace_manager:
            workspace = self.workspace_manager.get_workspace_path()
            display_path = workspace[:60] + "..." if len(workspace) > 60 else workspace
            self.workspace_label.config(text=display_path)
    
    def update_log(self, text):
        """Update log area"""
        def update():
            self.log_area.insert(tk.END, text)
            self.log_area.see(tk.END)
        self.log_area.master.after(0, update)
    
    def set_running_state(self, is_running):
        """Update button states"""
        def update():
            if is_running:
                self.launch_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)
            else:
                self.launch_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
        self.log_area.master.after(0, update)