import subprocess
import threading


class ProcessManager:
    """Manages all process-related operations"""
    
    def __init__(self, update_output_callback, update_status_callback=None):
        self.process = None
        self.running = False
        self.update_output = update_output_callback
        self.update_status = update_status_callback
    
    def run_jupyter_script(self, script_path, cwd):
        """Run Jupyter script"""
        self.running = True
        if self.update_status:
            self.update_status(True)
        
        def task():
            try:
                self.process = subprocess.Popen(
                    ["powershell", "-File", script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd
                )
                for line in self.process.stdout:
                    self.update_output(line)
                self.process.wait()
            except Exception as e:
                self.update_output(str(e))
            finally:
                self.cleanup()
        
        thread = threading.Thread(target=task, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop running process"""
        if self.process:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)], 
                         capture_output=True)
            self.cleanup()
    
    def cleanup(self):
        """Clean up after process"""
        self.running = False
        self.process = None
        if self.update_status:
            self.update_status(False)
    
    def is_running(self):
        return self.running