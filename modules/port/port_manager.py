# modules/port/port_manager.py
import os
import json
import socket
import subprocess
import re


class PortManager:
    """Manages port configuration and safety checks"""
    
    def __init__(self, update_log_callback=None):
        self.config_file = os.path.join(os.path.expanduser("~"), ".jupyter_port_config.json")
        self.config = {}
        self.update_log = update_log_callback
        self.load_config()
    
    def load_config(self):
        """Load port configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                self._log("Loaded port config")
            except Exception as e:
                self._log(f"Failed to load port config: {e}")
                self.config = {}
        else:
            self.config = {}
            self._log("No existing port config, will use default")
    
    def save_config(self):
        """Save port configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self._log(f"Port config saved to: {self.config_file}")
            return True
        except Exception as e:
            self._log(f"Failed to save port config: {e}")
            return False
    
    def get_saved_port(self):
        """Get saved port from config"""
        return self.config.get('port', 8888)
    
    def set_port(self, port):
        """Set and save port"""
        self.config['port'] = port
        self.save_config()
        self._log(f"Port set to: {port}")
    
    def is_port_available(self, port):
        """Check if port is available using netstat (same as PowerShell)"""
        try:
            # Use netstat to check for LISTENING ports
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Look for the port in LISTENING state
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTENING' in line:
                    return False  # Port is in use
            
            # Also try to bind as fallback
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except socket.error:
            return False
        except Exception:
            return False
    
    def get_docker_containers_on_port(self, port):
        """Get Docker containers using the specified port"""
        containers = []
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}\t{{.Ports}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for line in result.stdout.splitlines():
                if f':{port}' in line:
                    parts = line.split('\t')
                    status = 'running' if 'Up' in parts[1] else 'stopped'
                    containers.append({
                        'name': parts[0],
                        'status': status,
                        'ports': parts[2] if len(parts) > 2 else ''
                    })
        except:
            pass
        return containers
    
    def get_windows_processes_on_port(self, port):
        """Get Windows processes using the specified port"""
        processes = []
        try:
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    try:
                        proc_result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if 'No tasks' not in proc_result.stdout:
                            lines = proc_result.stdout.splitlines()
                            if len(lines) > 1:
                                proc_parts = lines[1].split(',')
                                proc_name = proc_parts[0].strip('"')
                                processes.append({
                                    'pid': pid,
                                    'name': proc_name
                                })
                    except:
                        processes.append({'pid': pid, 'name': 'Unknown'})
        except:
            pass
        return processes
    
    def validate_port(self, port):
        """Validate port with safety checks (matching PowerShell logic)"""
        # Check range
        if port < 1024 or port > 65535:
            return {
                'valid': False,
                'safe': False,
                'message': f'Port {port} is outside valid range (1024-65535)',
                'suggested_port': self.get_suggested_port()
            }
        
        # Check availability using netstat (same as PowerShell)
        if not self.is_port_available(port):
            containers = self.get_docker_containers_on_port(port)
            processes = self.get_windows_processes_on_port(port)
            
            message = f'Port {port} is already in use'
            
            if containers:
                message += '\n\nDocker containers using this port:'
                for c in containers:
                    message += f'\n  • {c["name"]} ({c["status"]}): {c["ports"]}'
            
            if processes:
                message += '\n\nWindows processes using this port:'
                for p in processes:
                    message += f'\n  • {p["name"]} (PID: {p["pid"]})'
            
            return {
                'valid': False,
                'safe': False,
                'message': message,
                'suggested_port': self.get_suggested_port(start_port=port + 1)
            }
        
        return {
            'valid': True,
            'safe': True,
            'message': f'Port {port} is available and safe to use',
            'suggested_port': None
        }
    
    def get_suggested_port(self, start_port=8888, max_attempts=100):
        """Find the next available port using netstat check"""
        port = start_port
        for _ in range(max_attempts):
            if self.is_port_available(port):
                return port
            port += 1
        return start_port + max_attempts
    
    def get_port_info(self, port):
        """Get detailed information about a port"""
        available = self.is_port_available(port)
        containers = self.get_docker_containers_on_port(port) if not available else []
        processes = self.get_windows_processes_on_port(port) if not available else []
        
        return {
            'port': port,
            'available': available,
            'containers': containers,
            'processes': processes,
            'suggested': self.get_suggested_port(start_port=port + 1) if not available else None
        }
    
    def _log(self, message):
        """Log message if callback provided"""
        if self.update_log:
            self.update_log(message + "\n")