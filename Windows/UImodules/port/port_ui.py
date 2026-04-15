# modules/port/port_ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time


class PortUI:
    """Port configuration UI component with auto-refresh"""
    
    def __init__(self, parent, port_manager, on_port_changed=None):
        self.parent = parent
        self.port_manager = port_manager
        self.on_port_changed = on_port_changed
        self.refresh_enabled = True
        self.refresh_interval = 2000  # milliseconds (2 seconds)
        self.after_id = None
        self.create_widgets()
        self.refresh_display()
        self.start_auto_refresh()
        
        # Bind cleanup when tab is hidden
        parent.bind("<Visibility>", self.on_tab_visible)
        parent.bind("<Unmap>", self.on_tab_hidden)
    
    def create_widgets(self):
        """Create port UI widgets"""
        # Main frame
        self.frame = tk.LabelFrame(
            self.parent,
            text=" Port Configuration ",
            padx=10,
            pady=10,
            font=("Arial", 10, "bold")
        )
        self.frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Description
        desc_label = tk.Label(
            self.frame,
            text="Jupyter Notebook will run on this port.\nAuto-refreshes every 2 seconds.",
            fg="gray",
            justify=tk.LEFT
        )
        desc_label.pack(fill=tk.X, pady=(0, 10))
        
        # Port display frame
        port_frame = tk.Frame(self.frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(port_frame, text="Current Port:", width=12, anchor="w", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.port_label = tk.Label(port_frame, text="", fg="blue", font=("Arial", 10, "bold"))
        self.port_label.pack(side=tk.LEFT, padx=5)
        
        # Status indicator with animation
        self.status_label = tk.Label(port_frame, text="", font=("Arial", 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Refresh indicator (small dot)
        self.refresh_indicator = tk.Label(port_frame, text="●", fg="gray", font=("Arial", 8))
        self.refresh_indicator.pack(side=tk.RIGHT, padx=5)
        
        # Buttons frame
        buttons_frame = tk.Frame(self.frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Change button
        self.change_btn = tk.Button(
            buttons_frame,
            text="Change Port",
            command=self.change_port,
            bg="#2196F3",
            fg="white",
            padx=15,
            pady=5
        )
        self.change_btn.pack(side=tk.LEFT, padx=5)
        
        # Check button (manual check)
        self.check_btn = tk.Button(
            buttons_frame,
            text="Check Now",
            command=self.check_port,
            bg="#FF9800",
            fg="white",
            padx=15,
            pady=5
        )
        self.check_btn.pack(side=tk.LEFT, padx=5)
        
        # Suggest button
        self.suggest_btn = tk.Button(
            buttons_frame,
            text="Suggest Port",
            command=self.suggest_port,
            bg="#4CAF50",
            fg="white",
            padx=15,
            pady=5
        )
        self.suggest_btn.pack(side=tk.LEFT, padx=5)
        
        # Auto-refresh toggle
        self.refresh_toggle = tk.Button(
            buttons_frame,
            text="⏸ Pause Refresh",
            command=self.toggle_refresh,
            bg="#607D8B",
            fg="white",
            padx=10,
            pady=5
        )
        self.refresh_toggle.pack(side=tk.RIGHT, padx=5)
    
    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        if self.refresh_enabled and self.after_id is None:
            self._schedule_refresh()
    
    def _schedule_refresh(self):
        """Schedule the next refresh"""
        if self.refresh_enabled:
            self.after_id = self.frame.after(self.refresh_interval, self._do_refresh)
    
    def _do_refresh(self):
        """Perform the refresh in a background thread"""
        self.after_id = None
        
        # Update indicator
        self.refresh_indicator.config(fg="green")
        
        # Perform refresh in background thread
        def refresh_task():
            try:
                # Get current port
                port = self.port_manager.get_saved_port()
                validation = self.port_manager.validate_port(port)
                
                # Update UI on main thread
                self.frame.after(0, lambda: self._update_display(port, validation))
                self.frame.after(0, lambda: self.refresh_indicator.config(fg="gray"))
            except Exception as e:
                self.frame.after(0, lambda: self.refresh_indicator.config(fg="red"))
        
        threading.Thread(target=refresh_task, daemon=True).start()
        
        # Schedule next refresh
        self._schedule_refresh()
    
    def _update_display(self, port, validation):
        """Update the display with new data"""
        self.port_label.config(text=str(port))
        
        if validation['safe']:
            self.status_label.config(text="✓ Available", fg="green")
        else:
            self.status_label.config(text="⚠ In Use", fg="red")
    
    def refresh_display(self):
        """Manual refresh display (called from outside)"""
        port = self.port_manager.get_saved_port()
        validation = self.port_manager.validate_port(port)
        self._update_display(port, validation)
    
    def toggle_refresh(self):
        """Toggle auto-refresh on/off"""
        self.refresh_enabled = not self.refresh_enabled
        
        if self.refresh_enabled:
            self.refresh_toggle.config(text="⏸ Pause Refresh", bg="#607D8B")
            self.refresh_indicator.config(fg="gray")
            self.start_auto_refresh()
        else:
            self.refresh_toggle.config(text="▶ Resume Refresh", bg="#4CAF50")
            if self.after_id:
                self.frame.after_cancel(self.after_id)
                self.after_id = None
            self.refresh_indicator.config(fg="red")
    
    def on_tab_visible(self, event):
        """Resume refresh when tab becomes visible"""
        if self.refresh_enabled:
            self.start_auto_refresh()
    
    def on_tab_hidden(self, event):
        """Pause refresh when tab is hidden to save resources"""
        if self.after_id:
            self.frame.after_cancel(self.after_id)
            self.after_id = None
    
    def change_port(self):
        """Open dialog to change port"""
        # Pause auto-refresh while dialog is open
        was_enabled = self.refresh_enabled
        if was_enabled:
            self.toggle_refresh()
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Change Port")
        dialog.geometry("550x500")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (550 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (500 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Current port display
        current_port = self.port_manager.get_saved_port()
        tk.Label(dialog, text="Current Port:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
        tk.Label(dialog, text=str(current_port), fg="blue", font=("Arial", 12)).pack()
        
        # New port entry
        tk.Label(dialog, text="New Port (1024-65535):", font=("Arial", 10)).pack(pady=(20, 5))
        port_entry = tk.Entry(dialog, font=("Arial", 12), width=15)
        port_entry.insert(0, str(current_port))
        port_entry.pack()
        
        # Status label
        status_label = tk.Label(dialog, text="", fg="red", wraplength=500, justify=tk.LEFT)
        status_label.pack(pady=10, padx=20)
        
        # Info text area (live updates)
        info_text = tk.Text(dialog, height=10, width=65, font=("Consolas", 9), bg="#f8f9fa")
        info_text.pack(pady=10, padx=20)
        
        def update_info():
            """Update info text with current port status"""
            try:
                port = int(port_entry.get().strip())
                info = self.port_manager.get_port_info(port)
                info_text.delete(1.0, tk.END)
                
                if info['available']:
                    info_text.insert(tk.END, f"Port {port} is AVAILABLE\n")
                    info_text.insert(tk.END, "=" * 50 + "\n")
                    info_text.insert(tk.END, "✓ This port is free to use.\n")
                else:
                    info_text.insert(tk.END, f"Port {port} is IN USE\n")
                    info_text.insert(tk.END, "=" * 50 + "\n")
                    
                    if info['containers']:
                        info_text.insert(tk.END, "\n🐳 Docker Containers:\n")
                        for c in info['containers']:
                            info_text.insert(tk.END, f"  • {c['name']} ({c['status']})\n")
                            info_text.insert(tk.END, f"    Ports: {c['ports']}\n")
                    
                    if info['processes']:
                        info_text.insert(tk.END, "\n🪟 Windows Processes:\n")
                        for p in info['processes']:
                            info_text.insert(tk.END, f"  • {p['name']} (PID: {p['pid']})\n")
                    
                    if info['suggested']:
                        info_text.insert(tk.END, f"\n💡 Suggested port: {info['suggested']}\n")
                
                # Update status label
                if info['available']:
                    status_label.config(text="✓ Port is available", fg="green")
                else:
                    status_label.config(text="⚠ Port is in use", fg="red")
                    
            except ValueError:
                info_text.delete(1.0, tk.END)
                info_text.insert(tk.END, "Please enter a valid port number")
                status_label.config(text="Invalid port number", fg="red")
        
        # Bind live update to key release
        def on_port_change(*args):
            update_info()
        
        port_entry.bind('<KeyRelease>', on_port_change)
        update_info()
        
        def apply_port():
            try:
                new_port = int(port_entry.get().strip())
                validation = self.port_manager.validate_port(new_port)
                
                if validation['valid']:
                    self.port_manager.set_port(new_port)
                    self.refresh_display()
                    if self.on_port_changed:
                        self.on_port_changed(new_port)
                    messagebox.showinfo("Success", f"Port changed to {new_port}")
                    dialog.destroy()
                else:
                    status_label.config(text=validation['message'])
            except ValueError:
                status_label.config(text="Please enter a valid number")
        
        def use_suggested():
            try:
                current = int(port_entry.get().strip())
                suggested = self.port_manager.get_suggested_port(start_port=current)
            except:
                suggested = self.port_manager.get_suggested_port()
            port_entry.delete(0, tk.END)
            port_entry.insert(0, str(suggested))
            update_info()
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Apply", command=apply_port, bg="#4CAF50", fg="white", padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Use Suggested", command=use_suggested, bg="#FF9800", fg="white", padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#f44336", fg="white", padx=20).pack(side=tk.LEFT, padx=5)
        
        # Resume auto-refresh when dialog closes
        def on_dialog_close():
            if was_enabled and not self.refresh_enabled:
                self.toggle_refresh()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
    
    def check_port(self):
        """Check current port status with detailed info"""
        port = self.port_manager.get_saved_port()
        info = self.port_manager.get_port_info(port)
        
        status_text = f"Port {port} Status:\n"
        status_text += "=" * 50 + "\n\n"
        
        if info['available']:
            status_text += "✓ Port is AVAILABLE\n"
            status_text += "This port is free to use."
        else:
            status_text += "✗ Port is IN USE\n\n"
            
            if info['containers']:
                status_text += "\n🐳 Docker containers using this port:\n"
                for c in info['containers']:
                    status_text += f"  • {c['name']} ({c['status']})\n"
                    status_text += f"    Ports: {c['ports']}\n"
            
            if info['processes']:
                status_text += "\n🪟 Windows processes using this port:\n"
                for p in info['processes']:
                    status_text += f"  • {p['name']} (PID: {p['pid']})\n"
            
            status_text += f"\n💡 Suggested port: {info['suggested']}"
        
        messagebox.showinfo("Port Check", status_text)
    
    def suggest_port(self):
        """Suggest and optionally use an available port"""
        suggested = self.port_manager.get_suggested_port()
        
        result = messagebox.askyesno(
            "Suggested Port",
            f"Suggested available port: {suggested}\n\nDo you want to use this port?"
        )
        
        if result:
            self.port_manager.set_port(suggested)
            self.refresh_display()
            if self.on_port_changed:
                self.on_port_changed(suggested)
            messagebox.showinfo("Success", f"Port changed to {suggested}")