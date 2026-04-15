# modules/systemcheck/system_check_ui.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading


class SystemCheckUI:
    """System Compatibility Check UI Component"""
    
    def __init__(self, parent, system_checker):
        self.parent = parent
        self.checker = system_checker
        self.create_widgets()
    
    def create_widgets(self):
        """Create system check UI widgets"""
        # Main frame
        self.main_frame = tk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = tk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(header_frame, text="System Compatibility Check", 
                font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        self.status_label = tk.Label(header_frame, text="", font=("Arial", 10))
        self.status_label.pack(side=tk.RIGHT)
        
        # Check button
        self.check_btn = tk.Button(
            header_frame,
            text="🔄 Run System Check",
            command=self.run_check,
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=5
        )
        self.check_btn.pack(side=tk.RIGHT, padx=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_status_tab()
        self.create_docker_tab()
        self.create_gpu_tab()
        self.create_requirements_tab()
        self.create_log_tab()
        
        # Initial check
        self.run_check()
    
    def create_status_tab(self):
        """Create Status Summary tab"""
        self.status_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.status_tab, text="📊 Status Summary")
        
        self.status_text = scrolledtext.ScrolledText(
            self.status_tab, font=("Consolas", 10), wrap=tk.WORD
        )
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_docker_tab(self):
        """Create Docker tab"""
        self.docker_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.docker_tab, text="🐳 Docker")
        
        self.docker_text = scrolledtext.ScrolledText(
            self.docker_tab, font=("Consolas", 10), wrap=tk.WORD
        )
        self.docker_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_gpu_tab(self):
        """Create GPU tab"""
        self.gpu_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.gpu_tab, text="🎮 GPU & CUDA")
        
        self.gpu_text = scrolledtext.ScrolledText(
            self.gpu_tab, font=("Consolas", 10), wrap=tk.WORD
        )
        self.gpu_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_requirements_tab(self):
        """Create Requirements tab"""
        self.req_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.req_tab, text="📋 Requirements")
        
        self.req_text = scrolledtext.ScrolledText(
            self.req_tab, font=("Consolas", 10), wrap=tk.WORD
        )
        self.req_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_log_tab(self):
        """Create Log tab"""
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="📝 Check Log")
        
        self.log_text = scrolledtext.ScrolledText(
            self.log_tab, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def log(self, message):
        """Add message to log"""
        def update():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.log_text.master.after(0, update)
    
    def run_check(self):
        """Run system check in background thread"""
        self.check_btn.config(state=tk.DISABLED, text="⏳ Checking...")
        self.status_label.config(text="Running checks...", fg="orange")
        
        def check_task():
            try:
                self.log("Starting system compatibility check...")
                self.log("=" * 50)
                
                info = self.checker.get_all_info()
                
                # Update UI
                self.parent.after(0, lambda: self.update_status_tab(info))
                self.parent.after(0, lambda: self.update_docker_tab(info))
                self.parent.after(0, lambda: self.update_gpu_tab(info))
                self.parent.after(0, lambda: self.update_requirements_tab(info))
                
                self.log("System check completed successfully")
                self.log("=" * 50)
                
                self.parent.after(0, lambda: self.status_label.config(text="✓ Check Complete", fg="green"))
                self.parent.after(0, lambda: self.check_btn.config(state=tk.NORMAL, text="🔄 Run System Check"))
                
            except Exception as e:
                self.log(f"Error during check: {e}")
                self.parent.after(0, lambda: self.status_label.config(text="✗ Check Failed", fg="red"))
                self.parent.after(0, lambda: self.check_btn.config(state=tk.NORMAL, text="🔄 Run System Check"))
        
        threading.Thread(target=check_task, daemon=True).start()
    
    def update_status_tab(self, info):
        """Update status summary tab"""
        self.status_text.delete(1.0, tk.END)
        
        status = info.get('status', {})
        
        # Overall Status
        self.status_text.insert(tk.END, "╔══════════════════════════════════════════════════════════╗\n")
        self.status_text.insert(tk.END, "║                    SYSTEM STATUS                         ║\n")
        self.status_text.insert(tk.END, "╚══════════════════════════════════════════════════════════╝\n\n")
        
        if status.get('overall'):
            self.status_text.insert(tk.END, "✓ SYSTEM IS READY\n", "good")
            self.status_text.insert(tk.END, "  All requirements are met. You can run Jupyter with GPU support.\n\n")
        else:
            self.status_text.insert(tk.END, "⚠ SYSTEM NEEDS ATTENTION\n", "warning")
            for issue in status.get('issues', []):
                self.status_text.insert(tk.END, f"  • {issue}\n")
            self.status_text.insert(tk.END, "\n")
        
        # Docker Status
        self.status_text.insert(tk.END, "┌──────────────────────────────────────────────────────────┐\n")
        self.status_text.insert(tk.END, "│ DOCKER STATUS                                              │\n")
        self.status_text.insert(tk.END, "└──────────────────────────────────────────────────────────┘\n")
        docker = info.get('docker', {})
        if docker.get('installed') and docker.get('running'):
            self.status_text.insert(tk.END, f"  ✓ Docker: Running (v{docker.get('version', 'Unknown')})\n")
        elif docker.get('installed'):
            self.status_text.insert(tk.END, f"  ⚠ Docker: Installed but not running\n")
        else:
            self.status_text.insert(tk.END, f"  ✗ Docker: Not installed\n")
        self.status_text.insert(tk.END, "\n")
        
        # GPU Status
        self.status_text.insert(tk.END, "┌──────────────────────────────────────────────────────────┐\n")
        self.status_text.insert(tk.END, "│ GPU STATUS                                                 │\n")
        self.status_text.insert(tk.END, "└──────────────────────────────────────────────────────────┘\n")
        gpu = info.get('gpu', {})
        if gpu.get('has_nvidia'):
            self.status_text.insert(tk.END, f"  ✓ NVIDIA GPU detected\n")
            for g in gpu.get('gpus', []):
                if g['type'] == 'NVIDIA':
                    self.status_text.insert(tk.END, f"    • {g['name']}\n")
            if gpu.get('nvidia_driver'):
                self.status_text.insert(tk.END, f"  ✓ Driver: {gpu['nvidia_driver']}\n")
            if gpu.get('cuda_version'):
                self.status_text.insert(tk.END, f"  ✓ CUDA: {gpu['cuda_version']}\n")
            if gpu.get('cudnn_version'):
                self.status_text.insert(tk.END, f"  ✓ cuDNN: {gpu['cudnn_version']}\n")
        else:
            self.status_text.insert(tk.END, f"  ⚠ No NVIDIA GPU detected (will use CPU mode)\n")
        self.status_text.insert(tk.END, "\n")
    
    def update_docker_tab(self, info):
        """Update Docker tab"""
        self.docker_text.delete(1.0, tk.END)
        
        docker = info.get('docker', {})
        
        self.docker_text.insert(tk.END, "DOCKER INFORMATION\n")
        self.docker_text.insert(tk.END, "=" * 50 + "\n\n")
        
        if docker.get('installed'):
            self.docker_text.insert(tk.END, f"Status: ✓ Installed\n")
            self.docker_text.insert(tk.END, f"Path: {docker.get('path', 'Unknown')}\n")
            if docker.get('version'):
                self.docker_text.insert(tk.END, f"Server Version: {docker['version']}\n")
            if docker.get('client_version'):
                self.docker_text.insert(tk.END, f"Client Version: {docker['client_version']}\n")
            if docker.get('compose_version'):
                self.docker_text.insert(tk.END, f"Compose Version: {docker['compose_version']}\n")
            if docker.get('running'):
                self.docker_text.insert(tk.END, f"\n✓ Docker daemon is running\n")
            else:
                self.docker_text.insert(tk.END, f"\n⚠ Docker daemon is NOT running\n")
                self.docker_text.insert(tk.END, f"  Please start Docker Desktop\n")
        else:
            self.docker_text.insert(tk.END, f"Status: ✗ Not Installed\n")
            self.docker_text.insert(tk.END, f"Error: {docker.get('error', 'Docker not found')}\n")
            self.docker_text.insert(tk.END, f"\n📥 Download Docker Desktop from:\n")
            self.docker_text.insert(tk.END, f"  https://www.docker.com/products/docker-desktop/\n")
    
    def update_gpu_tab(self, info):
        """Update GPU tab"""
        self.gpu_text.delete(1.0, tk.END)
        
        gpu = info.get('gpu', {})
        
        self.gpu_text.insert(tk.END, "GPU & CUDA INFORMATION\n")
        self.gpu_text.insert(tk.END, "=" * 50 + "\n\n")
        
        if gpu.get('gpus'):
            self.gpu_text.insert(tk.END, "Detected GPUs:\n")
            for g in gpu['gpus']:
                self.gpu_text.insert(tk.END, f"  • {g['type']}: {g['name']}\n")
            self.gpu_text.insert(tk.END, "\n")
        
        if gpu.get('nvidia_driver'):
            self.gpu_text.insert(tk.END, f"NVIDIA Driver: {gpu['nvidia_driver']}\n")
        
        if gpu.get('cuda_version'):
            self.gpu_text.insert(tk.END, f"CUDA Version: {gpu['cuda_version']}\n")
        
        if gpu.get('cuda_toolkit'):
            self.gpu_text.insert(tk.END, f"CUDA Toolkit: {gpu['cuda_toolkit']}\n")
        
        if gpu.get('cudnn_version'):
            self.gpu_text.insert(tk.END, f"cuDNN Version: {gpu['cudnn_version']}\n")
        
        if not gpu.get('has_nvidia'):
            self.gpu_text.insert(tk.END, "\n⚠ No NVIDIA GPU detected\n")
            self.gpu_text.insert(tk.END, "  Jupyter will run in CPU mode\n")
    
    def update_requirements_tab(self, info):
        """Update Requirements tab"""
        self.req_text.delete(1.0, tk.END)
        
        req = info.get('requirements', {})
        
        self.req_text.insert(tk.END, "DOCKER IMAGE REQUIREMENTS\n")
        self.req_text.insert(tk.END, "=" * 50 + "\n")
        self.req_text.insert(tk.END, f"Image: {req.get('docker_image', 'Unknown')}\n\n")
        
        self.req_text.insert(tk.END, "System Requirements:\n")
        self.req_text.insert(tk.END, "-" * 40 + "\n")
        requirements = req.get('requirements', {})
        for key, value in requirements.items():
            self.req_text.insert(tk.END, f"  • {key.upper()}: {value}\n")
        
        self.req_text.insert(tk.END, "\nDocker Commands:\n")
        self.req_text.insert(tk.END, "-" * 40 + "\n")
        commands = req.get('docker_commands', {})
        for key, value in commands.items():
            self.req_text.insert(tk.END, f"  • {key}: {value}\n")
        
        self.req_text.insert(tk.END, "\nCurrent System Status:\n")
        self.req_text.insert(tk.END, "-" * 40 + "\n")
        status = info.get('status', {})
        if status.get('docker_ready'):
            self.req_text.insert(tk.END, "  ✓ Docker: Ready\n")
        else:
            self.req_text.insert(tk.END, "  ✗ Docker: Not ready\n")
        
        gpu = info.get('gpu', {})
        if gpu.get('has_nvidia') and gpu.get('cuda_version'):
            self.req_text.insert(tk.END, "  ✓ GPU: Ready with CUDA support\n")
        elif gpu.get('has_nvidia'):
            self.req_text.insert(tk.END, "  ⚠ GPU: Detected but CUDA not configured\n")
        else:
            self.req_text.insert(tk.END, "  ⚠ GPU: CPU mode only\n")