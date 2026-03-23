# modules/workspace_manager.py
import os
import json


class WorkspaceManager:
    """Manages user workspace directory for Jupyter notebooks (Docker volume)"""
    
    def __init__(self, update_log_callback=None):
        self.config_file = os.path.join(os.path.expanduser("~"), ".jupyter_workspace_config.json")
        self.config = {}
        self.update_log = update_log_callback
        self.load_config()
    
    def load_config(self):
        """Load workspace configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                self._log("✅ Loaded workspace config")
            except Exception as e:
                self._log(f"⚠️ Failed to load config: {e}")
                self.config = {}
        else:
            self.config = {}
            self._log("✨ No existing workspace config, will create on first save")
    
    def save_config(self):
        """Save workspace configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self._log(f"💾 Workspace config saved to: {self.config_file}")
            return True
        except Exception as e:
            self._log(f"❌ Failed to save config: {e}")
            return False
    
    def get_workspace_path(self):
        """Get current workspace path with fallback to default"""
        # Check if config has saved path and it exists
        if self.config.get('workspace_path') and os.path.exists(self.config['workspace_path']):
            return self.config['workspace_path']
        elif self.config.get('workspace_path'):
            self._log(f"⚠️ Saved workspace not found: {self.config['workspace_path']}")
            self._log("   Using default workspace instead.")
            return self._get_default_workspace()
        else:
            return self._get_default_workspace()
    
    def _get_default_workspace(self):
        """Get default workspace path (Documents/JupyterWorkspace)"""
        default_path = os.path.join(os.path.expanduser("~"), "Documents", "JupyterWorkspace")
        if not os.path.exists(default_path):
            try:
                os.makedirs(default_path, exist_ok=True)
                self._log(f"✅ Created default workspace: {default_path}")
            except:
                pass
        return default_path
    
    def set_workspace_path(self, path, create_if_not_exist=True):
        """Set new workspace path"""
        if not path:
            self._log("❌ No path provided")
            return False
        
        # Expand user path if needed
        expanded_path = os.path.expanduser(path)
        
        # Check if path exists
        if not os.path.exists(expanded_path):
            if create_if_not_exist:
                try:
                    os.makedirs(expanded_path, exist_ok=True)
                    self._log(f"📁 Created workspace directory: {expanded_path}")
                except Exception as e:
                    self._log(f"❌ Failed to create directory: {e}")
                    return False
            else:
                self._log(f"❌ Path does not exist: {expanded_path}")
                return False
        
        # Check if directory is writable
        test_file = os.path.join(expanded_path, ".workspace_test.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except:
            self._log(f"❌ Workspace is not writable: {expanded_path}")
            return False
        
        # Save to config
        self.config['workspace_path'] = expanded_path
        self.save_config()
        
        self._log(f"✅ Workspace path set to: {expanded_path}")
        return True
    
    def get_workspace_info(self):
        """Get workspace information for display"""
        path = self.get_workspace_path()
        exists = os.path.exists(path)
        writable = False
        
        if exists:
            # Check if writable
            test_file = os.path.join(path, ".workspace_test.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                writable = True
            except:
                writable = False
        
        return {
            'path': path,
            'exists': exists,
            'writable': writable
        }
    
    def _log(self, message):
        """Log message if callback provided"""
        if self.update_log:
            self.update_log(message + "\n")