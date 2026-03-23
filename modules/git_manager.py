import os
import subprocess
import threading


class GitManager:
    """Handles all Git operations"""
    
    def __init__(self, project_root, update_output_callback):
        self.project_root = project_root
        self.update_output = update_output_callback
        self.found_branches = []
        self.branch_links = []
        self.git_script = os.path.join(project_root, "Windows", "manage_branch.ps1")
    
    def parse_git_stream(self, line, branch_callback=None, tree_callback=None, link_callback=None):
        """Parse Git script output"""
        line = line.strip()
        if not line:
            return
        
        if line.startswith("[LINK]"):
            raw = line.replace("[LINK]", "").strip().split("::")
            if len(raw) == 2:
                link = (raw[0], raw[1])
                self.branch_links.append(link)
                if link_callback:
                    link_callback(raw[0], raw[1])
        
        elif line.startswith("[BRANCH]"):
            b = line.replace("[BRANCH]", "").strip()
            if b not in self.found_branches:
                self.found_branches.append(b)
                if branch_callback:
                    branch_callback(b)
        
        elif line.startswith("[TREE]"):
            data = line[6:]
            if tree_callback:
                tree_callback(data)
        
        elif line.startswith("[ERROR]"):
            self.update_output(f"❌ {line[7:]}\n")
        
        else:
            self.update_output(line + "\n")
    
    def sync_git_data(self, branch_callback=None, tree_callback=None, link_callback=None):
        """Sync Git data"""
        def task():
            self.found_branches = []
            self.branch_links = []
            
            process = subprocess.Popen(
                ["powershell", "-File", self.git_script, "-TargetBranch", "LIST", "-ListOnly"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                self.parse_git_stream(line, branch_callback, tree_callback, link_callback)
            process.wait()
        
        threading.Thread(target=task, daemon=True).start()
    
    def run_branch_operation(self, branch_name, create_new=False, base_point=None, 
                            branch_callback=None, tree_callback=None, link_callback=None):
        """Run branch operation"""
        def task():
            cmd = ["powershell", "-File", self.git_script, "-TargetBranch", branch_name]
            if create_new:
                cmd.append("-CreateNew")
            if base_point:
                cmd.extend(["-BaseCommit", base_point])
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                self.parse_git_stream(line, branch_callback, tree_callback, link_callback)
            process.wait()
        
        threading.Thread(target=task, daemon=True).start()
    
    def save_repo_config(self, repo_url, branch_name):
        """Save repo config"""
        path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
        with open(path, "w") as f:
            f.write(f'$GITHUB_REPO="{repo_url}"\n')
            f.write(f'$CURRENT_BRANCH="{branch_name}"')
    
    def load_repo_config(self):
        """Load repo config"""
        path = os.path.join(os.path.expanduser("~"), ".jupyter_git_config.ps1")
        repo_url = ""
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        if "GITHUB_REPO" in line:
                            repo_url = line.split('"')[1]
                            break
            except:
                pass
        return repo_url