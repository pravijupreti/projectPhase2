#!/usr/bin/env python3
import os
import platform
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import sys
import threading
import time
import tempfile


class SafeJupyterLauncher:

    def __init__(self, root):
        self.root = root
        self.root.title("Safe Jupyter Notebook Launcher")
        self.root.geometry("750x550")

        self.process = None
        self.running = False
        self.fix_script_path = None

        # Project root = folder where app.py lives
        self.project_root = os.path.dirname(os.path.abspath(__file__))

        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)

        self.create_widgets()
        self.show_warning()

    def show_warning(self):
        warning = (
            "⚠️ SAFETY NOTICE ⚠️\n"
            "Use STOP button to terminate scripts safely.\n"
            + "=" * 50 + "\n"
        )
        self.update_output(warning)

    def create_widgets(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        self.launch_btn = tk.Button(
            control_frame,
            text="▶ Launch Jupyter Notebook",
            command=self.launch_safe,
            padx=15,
            pady=8,
            bg="#4CAF50",
            fg="white"
        )
        self.launch_btn.pack(side=tk.LEFT, padx=5)

        self.fix_btn = tk.Button(
            control_frame,
            text="🔧 Fix Docker Daemon",
            command=self.fix_docker_daemon,
            padx=15,
            pady=8,
            bg="#FF9800",
            fg="white"
        )
        self.fix_btn.pack(side=tk.LEFT, padx=5)

        self.gpu_btn = tk.Button(
            control_frame,
            text="🖥 Check GPU",
            command=self.check_gpu_thread,
            padx=15,
            pady=8,
            bg="#2196F3",
            fg="white"
        )
        self.gpu_btn.pack(side=tk.LEFT, padx=5)

        # Configure Git button (UI for git config)
        self.git_config_btn = tk.Button(
            control_frame,
            text="Configure Git",
            command=self.configure_git,
            padx=15,
            pady=8,
            bg="#9C27B0",
            fg="white"
        )
        self.git_config_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            control_frame,
            text="⏹ Stop Script",
            command=self.stop_safe,
            padx=15,
            pady=8,
            bg="#f44336",
            fg="white",
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(
            self.root,
            text="Status: Ready",
            fg="blue"
        )
        self.status_label.pack(pady=5)

        self.output_text = scrolledtext.ScrolledText(
            self.root,
            width=85,
            height=25,
            font=("Consolas", 10)
        )
        self.output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def update_output(self, text):
        def update():
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)

        if threading.current_thread() is threading.main_thread():
            update()
        else:
            self.root.after(0, update)

    def update_status(self, status, color="blue"):
        def update():
            self.status_label.config(text=f"Status: {status}", fg=color)

        if threading.current_thread() is threading.main_thread():
            update()
        else:
            self.root.after(0, update)

    # ---------- Git config UI ----------

    def configure_git(self):
        """Small dialog to store GitHub repo + branch into ~/.jupyter_git_config.ps1."""
        cfg_win = tk.Toplevel(self.root)
        cfg_win.title("Git Auto-Push Configuration")

        tk.Label(cfg_win, text="GitHub repository URL:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        repo_entry = tk.Entry(cfg_win, width=60)
        repo_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(cfg_win, text="Branch name:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )
        branch_entry = tk.Entry(cfg_win, width=20)
        branch_entry.insert(0, "main")
        branch_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        def save_cfg():
            repo = repo_entry.get().strip()
            branch = branch_entry.get().strip() or "main"
            if not repo:
                messagebox.showerror("Error", "Repository URL is required.")
                return

            cfg_path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
            content = (
                "# Jupyter Git Auto-Push Configuration\n"
                f"# Created: {time.ctime()}\n"
                f'$GITHUB_REPO="{repo}"\n'
                f'$CURRENT_BRANCH="{branch}"\n'
            )
            try:
                with open(cfg_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.update_output(f"\nSaved Git config to: {cfg_path}\n")
                messagebox.showinfo("Saved", "Git auto-push configuration saved.")
                cfg_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save config:\n{e}")

        tk.Button(cfg_win, text="Save", command=save_cfg).grid(
            row=2, column=0, columnspan=2, pady=10
        )

    # ---------- existing logic ----------

    def check_gpu_thread(self):
        thread = threading.Thread(target=self.check_gpu)
        thread.daemon = True
        thread.start()

    def check_gpu(self):
        self.update_output("\n🔍 Checking GPU...\n")
        self.update_output("=" * 40 + "\n")

        system = platform.system()

        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.update_output("✅ NVIDIA GPU detected\n\n")
                self.update_output(result.stdout + "\n")
                return
        except FileNotFoundError:
            pass

        try:
            if system == "Windows":
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True,
                    text=True
                )
                self.update_output("Detected GPUs:\n")
                self.update_output(result.stdout + "\n")

            elif system == "Linux":
                result = subprocess.run(
                    ["lspci"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.splitlines():
                    if "VGA" in line or "3D" in line:
                        self.update_output(line + "\n")

            else:
                self.update_output("Unsupported OS\n")

        except Exception as e:
            self.update_output(f"GPU detection failed: {e}\n")

        self.update_output("=" * 40 + "\n")

    def create_fix_script(self):
        content = '''
Write-Host "Fixing Docker Daemon..."

Get-Process "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force

Stop-Service com.docker.service -ErrorAction SilentlyContinue

wsl --unregister docker-desktop 2>$null
wsl --unregister docker-desktop-data 2>$null

Start-Process "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"

Start-Sleep 20

docker version
'''
        path = os.path.join(tempfile.gettempdir(), "fix_docker.ps1")
        with open(path, "w") as f:
            f.write(content)
        return path

    def fix_docker_daemon(self):
        if self.running:
            messagebox.showwarning("Busy", "Wait for script to finish")
            return

        if not messagebox.askyesno("Confirm", "Restart Docker completely?"):
            return

        script = self.create_fix_script()

        thread = threading.Thread(target=self.run_fix_script, args=(script,))
        thread.daemon = True
        thread.start()

    def run_fix_script(self, script):
        self.running = True

        self.launch_btn.config(state=tk.DISABLED)
        self.fix_btn.config(state=tk.DISABLED)
        self.git_config_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        cmd = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in self.process.stdout:
                self.update_output(line)

        except Exception as e:
            self.update_output(str(e))

        finally:
            self.cleanup()

    def launch_safe(self):
        if self.running:
            return

        thread = threading.Thread(target=self.run_script)
        thread.daemon = True
        thread.start()

    def run_script(self):
        self.running = True

        self.launch_btn.config(state=tk.DISABLED)
        self.fix_btn.config(state=tk.DISABLED)
        self.git_config_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        system = platform.system()

        try:
            if system == "Windows":
                script = os.path.join(self.project_root, "Windows", "jupyter_notebook.ps1")
                cmd = [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script
                ]
            else:
                script = os.path.join(self.project_root, "Linux", "jupyter_notebook.sh")
                cmd = ["bash", script]

            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,  # current working dir = project root
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in self.process.stdout:
                self.update_output(line)

        except Exception as e:
            self.update_output(str(e))

        finally:
            self.cleanup()

    def stop_safe(self):
        if not self.process:
            return

        try:
            if platform.system() == "Windows":
                subprocess.run([
                    "taskkill",
                    "/F",
                    "/T",
                    "/PID",
                    str(self.process.pid)
                ])
            else:
                self.process.terminate()
        except Exception:
            pass

        self.cleanup()

    def cleanup(self):
        self.running = False
        self.process = None

        self.launch_btn.config(state=tk.NORMAL)
        self.fix_btn.config(state=tk.NORMAL)
        self.git_config_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        self.update_status("Ready")

    def safe_exit(self):
        if self.running:
            if messagebox.askyesno("Exit", "Stop running script first?"):
                self.stop_safe()

        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = SafeJupyterLauncher(root)
    root.mainloop()
