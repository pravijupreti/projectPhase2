import os
import subprocess
import threading


class GitManager:
    """
    Handles all Git operations via PowerShell scripts.
    No Tkinter. Pure subprocess + threading.

    Scripts:
        manage_branch.ps1  — branch ops + tree listing
        git_auto_push.ps1  — stage / commit / push
                             requires -WorkspacePath (Docker volume path)
    """

    def __init__(self, project_root: str, update_output_callback):
        self.project_root  = project_root
        self.update_output = update_output_callback
        self.found_branches: list[str] = []
        self.branch_links:   list[tuple] = []
        self.git_script  = os.path.join(project_root, "Windows", "manage_branch.ps1")
        self.push_script = os.path.join(project_root, "Windows", "git_auto_push.ps1")

    # ── internal: run powershell in thread ────────────────────────

    def _powershell(self, args: list, on_line=None, on_done=None):
        """
        Run powershell in a daemon thread.
        on_line(str) called for each stdout line.
        on_done()    called when process exits.
        """
        def _task():
            try:
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                proc = subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass"] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=flags,
                )
                for line in proc.stdout:
                    if on_line:
                        on_line(line)
                    else:
                        self.update_output(line)
                proc.wait()
            except FileNotFoundError:
                self.update_output("❌ PowerShell not found.\n")
            except Exception as exc:
                self.update_output(f"❌ Subprocess error: {exc}\n")
            finally:
                if on_done:
                    on_done()

        threading.Thread(target=_task, daemon=True).start()

    # ── manage_branch.ps1 stream parser ──────────────────────────

    def _parse_stream(self, line: str,
                      branch_cb=None, tree_cb=None, link_cb=None, error_cb=None):  # ← ADD error_cb
        """
        Protocol from manage_branch.ps1:
            [BRANCH] name
            [TREE]   sha::subject::branch::parent[,parent]
            [LINK]   local::remote
            [ERROR]  message
            else     → plain log
        """
        line = line.strip()
        if not line:
            return

        if line.startswith("[BRANCH]"):
            b = line[8:].strip()
            if b and b not in self.found_branches:
                self.found_branches.append(b)
                if branch_cb:
                    branch_cb(b)

        elif line.startswith("[TREE]"):
            if tree_cb:
                tree_cb(line[6:])

        elif line.startswith("[LINK]"):
            parts = line[6:].strip().split("::")
            if len(parts) == 2:
                local, remote = parts[0].strip(), parts[1].strip()
                self.branch_links.append((local, remote))
                if link_cb:
                    link_cb(local, remote)

        elif line.startswith("[ERROR]"):
            self.update_output(f"❌ {line[7:].strip()}\n")
            if error_cb:  # ← ADD THIS
                error_cb(line[7:].strip())

        else:
            self.update_output(line + "\n")

    # ── public: branch / tree ─────────────────────────────────────

    def sync_git_data(self, workspace_path: str,
                      branch_cb=None, tree_cb=None, link_cb=None, error_cb=None):  # ← ADD error_cb
        """
        List all branches and commit tree from workspace_path.
        workspace_path = Docker volume path, e.g. C:/workspace
        """
        self.found_branches.clear()
        self.branch_links.clear()

        def _on_line(line):
            self._parse_stream(line, branch_cb, tree_cb, link_cb, error_cb)  # ← ADD error_cb

        self._powershell(
            [
                "-File", self.git_script,
                "-TargetBranch", "LIST",
                "-ListOnly",
                "-WorkspacePath", workspace_path,
            ],
            on_line=_on_line,
        )

    def run_branch_operation(self, workspace_path: str,
                             branch_name: str,
                             create_new: bool = False,
                             base_commit: str = None,
                             branch_cb=None, tree_cb=None, link_cb=None, error_cb=None):  # ← ADD error_cb
        """Switch to or create a branch inside workspace_path."""
        cmd = [
            "-File", self.git_script,
            "-TargetBranch", branch_name,
            "-WorkspacePath", workspace_path,
        ]
        if create_new:
            cmd.append("-CreateNew")
        if base_commit:
            cmd.extend(["-BaseCommit", base_commit])

        def _on_line(line):
            self._parse_stream(line, branch_cb, tree_cb, link_cb, error_cb)  # ← ADD error_cb

        self._powershell(cmd, on_line=_on_line)

    # ── public: push ──────────────────────────────────────────────

    def push_to_github(self, workspace_path: str, done_callback=None):
        """
        Run git_auto_push.ps1 -WorkspacePath <workspace_path>.
        The script handles init / remote update / commit / push.
        All output streams to the git log panel.
        """
        if not os.path.exists(self.push_script):
            self.update_output(
                f"❌ Push script not found:\n   {self.push_script}\n"
            )
            return

        self.update_output(f"🚀 Pushing from: {workspace_path}\n")

        self._powershell(
            ["-File", self.push_script, "-WorkspacePath", workspace_path],
            on_line=self.update_output,
            on_done=done_callback,
        )

    # ── config ────────────────────────────────────────────────────

    def save_repo_config(self, repo_url: str, branch_name: str):
        """
        Write ~/.jupyter_git_config.ps1
        Format matches what git_auto_push.ps1 dot-sources.
        """
        path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
        try:
            with open(path, "w") as f:
                f.write(f"$GITHUB_REPO = '{repo_url}'\n")
                f.write(f"$CURRENT_BRANCH = '{branch_name}'\n")
            self.update_output(f"✅ Config saved → {path}\n")
        except OSError as exc:
            self.update_output(f"❌ Could not save config: {exc}\n")

    def load_repo_config(self) -> str:
        """Return saved repo URL or empty string."""
        path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r") as f:
                for line in f:
                    if "GITHUB_REPO" in line:
                        parts = line.split("'")
                        if len(parts) >= 2:
                            return parts[1]
        except OSError:
            pass
        return ""