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
        self._lock = threading.Lock()

    # ─────────────────────────────
    # LOGGING
    # ─────────────────────────────

    def _log(self, message):
        print(f"[SCRIPT_CALLER] {message}")
        if self.log_callback:
            self.log_callback(message)

    def _log_error(self, message):
        msg = f"ERROR: {message}"
        print(f"[SCRIPT_CALLER] {msg}")
        if self.log_callback:
            self.log_callback(msg)

    # ─────────────────────────────
    # WORKSPACE
    # ─────────────────────────────

    def _ensure_workspace(self) -> str:
        if not self.workspace_manager:
            self._log_error("Workspace manager not available")
            return None

        workspace = self.workspace_manager.get_workspace_path()

        if workspace and os.path.exists(workspace):
            return workspace

        response = messagebox.askyesno(
            "Workspace Required",
            "No working directory selected.\n\nSelect one now?"
        )

        if not response:
            return None

        workspace = filedialog.askdirectory(
            title="Select Workspace",
            initialdir=os.path.expanduser("~/Desktop")
        )

        if not workspace:
            return None

        self.workspace_manager.set_workspace_path(workspace)
        self._log(f"Workspace set: {workspace}")
        return workspace

    # ─────────────────────────────
    # JUPYTER
    # ─────────────────────────────

    def jupyter_script(self, port, status_callback=None):
        workspace_path = self._ensure_workspace()
        if not workspace_path:
            if status_callback:
                status_callback(False)
            return

        script_path = os.path.join(self.project_root, "Windows", "jupyter_notebook.ps1")

        if not os.path.exists(script_path):
            self._log_error(f"Script not found: {script_path}")
            return

        self._log(f"Launching Jupyter on port {port}")
        self.running = True

        if status_callback:
            status_callback(True)

        def task():
            proc = None

            try:
                proc = subprocess.Popen(
                    [
                        "powershell",
                        "-ExecutionPolicy", "Bypass",
                        "-File", script_path,
                        "-Port", str(port)
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=workspace_path
                )

                with self._lock:
                    self.process = proc

                for line in proc.stdout:
                    if line:
                        self._log(f"[JUPYTER] {line.strip()}")

                for line in proc.stderr:
                    if line:
                        self._log_error(line.strip())

                proc.wait()

                return_code = proc.returncode if proc else -1
                self._log(f"Process finished with exit code: {return_code}")

            except FileNotFoundError:
                self._log_error("PowerShell not found")
            except Exception as e:
                self._log_error(f"Unexpected error: {e}")

            finally:
                with self._lock:
                    self.process = None
                    self.running = False

                if status_callback:
                    status_callback(False)

        threading.Thread(target=task, daemon=True).start()

    # ─────────────────────────────
    # GIT PUSH
    # ─────────────────────────────

    def git_push_script(self, done_callback=None):
        workspace_path = self._ensure_workspace()
        if not workspace_path:
            return

        script_path = os.path.join(self.project_root, "Windows", "git_auto_push.ps1")

        if not os.path.exists(script_path):
            self._log_error("Git script not found")
            return

        def task():
            try:
                proc = subprocess.Popen(
                    [
                        "powershell",
                        "-ExecutionPolicy", "Bypass",
                        "-File", script_path,
                        "-WorkspacePath", workspace_path
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=workspace_path
                )

                for line in proc.stdout:
                    self._log(f"[GIT] {line.strip()}")

                for line in proc.stderr:
                    self._log_error(line.strip())

                proc.wait()
                self._log(f"Git finished: {proc.returncode}")

                if done_callback:
                    done_callback()

            except Exception as e:
                self._log_error(str(e))

        threading.Thread(target=task, daemon=True).start()

    # ─────────────────────────────
    # BRANCH
    # ─────────────────────────────

    def git_branch_script(self, branch_name, create_new=False, base_commit=None):
        workspace_path = self._ensure_workspace()
        if not workspace_path:
            return

        script_path = os.path.join(self.project_root, "Windows", "manage_branch.ps1")

        if not os.path.exists(script_path):
            self._log_error("Branch script not found")
            return

        args = [
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
            "-WorkspacePath", workspace_path,
            "-TargetBranch", branch_name
        ]

        if create_new:
            args.append("-CreateNew")
        if base_commit:
            args += ["-BaseCommit", base_commit]

        def task():
            try:
                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=workspace_path
                )

                for line in proc.stdout:
                    self._log(f"[BRANCH] {line.strip()}")

                for line in proc.stderr:
                    self._log_error(line.strip())

                proc.wait()
                self._log(f"Branch finished: {proc.returncode}")

            except Exception as e:
                self._log_error(str(e))

        threading.Thread(target=task, daemon=True).start()

    # ─────────────────────────────
    # STOP SAFE
    # ─────────────────────────────

    def stop_jupyter(self):
        with self._lock:
            proc = self.process

        if proc and proc.poll() is None:
            self._log("Stopping Jupyter...")

            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True
            )

            self._log("Jupyter stopped")
        else:
            self._log("No running process")

        with self._lock:
            self.process = None
            self.running = False

    def is_running(self):
        return self.running