# modules/systemcheck/system_checker.py
import subprocess
import platform
import re
import os
import glob


class SystemChecker:
    """System configuration checker for Docker, GPU, CUDA requirements"""
    
    def __init__(self, update_log_callback=None):
        self.update_log = update_log_callback
        self.results = {}
    
    def _log(self, message):
        if self.update_log:
            self.update_log(message + "\n")
    
    def run_command(self, cmd, timeout=10):
        """Run a command and return output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None
    
    def check_os(self):
        """Get OS information"""
        info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
        
        # Get Windows version details
        if info['system'] == 'Windows':
            try:
                result = self.run_command('wmic os get Caption,Version /value')
                if result:
                    for line in result.splitlines():
                        if 'Caption=' in line:
                            info['windows_version'] = line.replace('Caption=', '').strip()
                        elif 'Version=' in line:
                            info['windows_build'] = line.replace('Version=', '').strip()
            except:
                pass
        
        return info
    
    def check_docker(self):
        """Check Docker installation and status"""
        info = {
            'installed': False,
            'running': False,
            'version': None,
            'compose_version': None,
            'error': None
        }
        
        # Check if docker command exists
        docker_path = self.run_command('where docker' if platform.system() == 'Windows' else 'which docker')
        if docker_path:
            info['installed'] = True
            info['path'] = docker_path
            
            # Get Docker version
            version = self.run_command('docker version --format "{{.Server.Version}}"')
            if version:
                info['version'] = version
                info['running'] = True
            else:
                # Docker installed but not running
                client_version = self.run_command('docker version --format "{{.Client.Version}}"')
                if client_version:
                    info['client_version'] = client_version
                    info['running'] = False
            
            # Get Docker Compose version
            compose_version = self.run_command('docker compose version --short')
            if compose_version:
                info['compose_version'] = compose_version
        else:
            info['error'] = 'Docker not found in PATH'
        
        return info
    
    def check_gpu(self):
        """Check GPU and CUDA information"""
        info = {
            'has_nvidia': False,
            'has_amd': False,
            'has_intel': False,
            'gpus': [],
            'nvidia_driver': None,
            'cuda_version': None,
            'cudnn_version': None
        }
        
        system = platform.system()
        
        # Check NVIDIA GPU using nvidia-smi
        nvidia_smi = self.run_command('nvidia-smi')
        if nvidia_smi:
            info['has_nvidia'] = True
            
            # Parse GPU information
            for line in nvidia_smi.splitlines():
                # Get GPU name
                if 'GeForce' in line or 'Quadro' in line or 'Tesla' in line or 'RTX' in line:
                    gpu_name = line.strip()
                    if gpu_name and gpu_name not in [g['name'] for g in info['gpus']]:
                        info['gpus'].append({'name': gpu_name, 'type': 'NVIDIA'})
                
                # Get driver version
                if 'Driver Version:' in line:
                    info['nvidia_driver'] = line.split('Driver Version:')[1].strip().split()[0]
                
                # Get CUDA version
                if 'CUDA Version:' in line:
                    info['cuda_version'] = line.split('CUDA Version:')[1].strip()
            
            # Get CUDA version from nvcc if available
            nvcc = self.run_command('nvcc --version')
            if nvcc:
                for line in nvcc.splitlines():
                    if 'release' in line.lower():
                        match = re.search(r'release (\d+\.\d+)', line)
                        if match:
                            info['cuda_toolkit'] = match.group(1)
            
            # Get cuDNN version
            cudnn_version = self.get_cudnn_version()
            if cudnn_version:
                info['cudnn_version'] = cudnn_version
        
        # Check other GPUs on Windows
        if system == 'Windows':
            wmic = self.run_command('wmic path win32_VideoController get name')
            if wmic:
                for line in wmic.splitlines():
                    line = line.strip()
                    if line and 'Name' not in line and line not in ['', ' ']:
                        if 'NVIDIA' in line:
                            if not any(g['name'] == line for g in info['gpus']):
                                info['gpus'].append({'name': line, 'type': 'NVIDIA'})
                        elif 'AMD' in line or 'Radeon' in line:
                            info['has_amd'] = True
                            info['gpus'].append({'name': line, 'type': 'AMD'})
                        elif 'Intel' in line:
                            info['has_intel'] = True
                            info['gpus'].append({'name': line, 'type': 'Intel'})
        
        # Check Linux GPUs
        elif system == 'Linux':
            lspci = self.run_command('lspci | grep -i "vga\\|3d"')
            if lspci:
                for line in lspci.splitlines():
                    if 'NVIDIA' in line:
                        info['has_nvidia'] = True
                        info['gpus'].append({'name': line.split(':')[-1].strip(), 'type': 'NVIDIA'})
                    elif 'AMD' in line:
                        info['has_amd'] = True
                        info['gpus'].append({'name': line.split(':')[-1].strip(), 'type': 'AMD'})
                    elif 'Intel' in line:
                        info['has_intel'] = True
                        info['gpus'].append({'name': line.split(':')[-1].strip(), 'type': 'Intel'})
        
        return info
    
    def get_cudnn_version(self):
        """Get cuDNN version from installed files"""
        system = platform.system()
        
        if system == 'Windows':
            # Common cuDNN locations on Windows
            possible_paths = [
                r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v*\include\cudnn.h',
                r'C:\Program Files\NVIDIA\CUDNN\v*\include\cudnn.h',
                r'C:\cuda\include\cudnn.h'
            ]
        else:
            # Common cuDNN locations on Linux
            possible_paths = [
                '/usr/include/cudnn.h',
                '/usr/local/cuda/include/cudnn.h',
                '/usr/local/cuda-*/include/cudnn.h'
            ]
        
        for path_pattern in possible_paths:
            files = glob.glob(path_pattern)
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Look for cuDNN version defines
                        major_match = re.search(r'#define\s+CUDNN_MAJOR\s+(\d+)', content)
                        minor_match = re.search(r'#define\s+CUDNN_MINOR\s+(\d+)', content)
                        patch_match = re.search(r'#define\s+CUDNN_PATCHLEVEL\s+(\d+)', content)
                        
                        if major_match and minor_match and patch_match:
                            return f"{major_match.group(1)}.{minor_match.group(1)}.{patch_match.group(1)}"
                except:
                    pass
        return None
    
    def get_requirements(self):
        """Get requirements for the Docker image"""
        return {
            'docker_image': 'tensorflow/tensorflow:2.15.0-gpu-jupyter',
            'requirements': {
                'docker': 'Docker Desktop 2.0+',
                'gpu': 'NVIDIA GPU with Compute Capability 3.5+',
                'driver': 'NVIDIA Driver 450.80.02+',
                'cuda': 'CUDA 12.2+ (for GPU container)',
                'memory': '8GB RAM minimum, 16GB recommended',
                'disk': '10GB free space'
            },
            'docker_commands': {
                'install': 'https://www.docker.com/products/docker-desktop/',
                'verify': 'docker version',
                'pull': 'docker pull tensorflow/tensorflow:2.15.0-gpu-jupyter',
                'run': 'docker run --gpus all -p 8888:8888 tensorflow/tensorflow:2.15.0-gpu-jupyter'
            }
        }
    
    def get_all_info(self):
        """Get all system information"""
        self.results['os'] = self.check_os()
        self.results['docker'] = self.check_docker()
        self.results['gpu'] = self.check_gpu()
        self.results['requirements'] = self.get_requirements()
        
        # Check if system meets requirements
        self.results['status'] = self.check_status()
        
        return self.results
    
    def check_status(self):
        """Check if system meets requirements"""
        status = {
            'docker_ready': False,
            'gpu_ready': False,
            'overall': False,
            'issues': []
        }
        
        # Check Docker
        docker = self.results.get('docker', {})
        if docker.get('installed') and docker.get('running'):
            status['docker_ready'] = True
        else:
            if not docker.get('installed'):
                status['issues'].append('Docker is not installed')
            elif not docker.get('running'):
                status['issues'].append('Docker is not running')
        
        # Check GPU
        gpu = self.results.get('gpu', {})
        if gpu.get('has_nvidia'):
            if gpu.get('cuda_version'):
                status['gpu_ready'] = True
            else:
                status['issues'].append('NVIDIA GPU detected but CUDA not available')
        else:
            status['issues'].append('No NVIDIA GPU detected - will use CPU mode')
            # CPU mode is still OK
            status['gpu_ready'] = True
        
        # Overall status
        status['overall'] = status['docker_ready'] and status['gpu_ready']
        
        return status