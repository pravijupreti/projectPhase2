# Windows/UImodules/workspace/terminal_widget.py
import tkinter as tk
import subprocess
import threading
import os
import sys


class TerminalWidget:
    """Real terminal like VS Code - type directly in the terminal"""
    
    def __init__(self, parent, workspace_manager=None, height=10):
        self.parent = parent
        self.workspace_manager = workspace_manager
        self.current_dir = None
        self.process = None
        self.current_line = ""
        self.prompt = "$> "
        
        self.frame = tk.LabelFrame(parent, text=" Terminal ", padx=2, pady=2, bg="black")
        
        # Text widget - start as NORMAL so user can type
        self.terminal = tk.Text(
            self.frame, 
            bg="black", 
            fg="white",
            insertbackground="white",
            font=("Consolas", 10),
            height=height,
            wrap=tk.WORD
        )
        self.terminal.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(self.terminal, orient=tk.VERTICAL, command=self.terminal.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal.configure(yscrollcommand=scrollbar.set)
        
        # Bind keys
        self.terminal.bind("<Return>", self._execute_line)
        self.terminal.bind("<BackSpace>", self._handle_backspace)
        self.terminal.bind("<Up>", self._history_up)
        self.terminal.bind("<Down>", self._history_down)
        self.terminal.bind("<Control-c>", self._interrupt)
        self.terminal.bind("<Key>", self._on_key, add=True)
        
        # Command history
        self.history = []
        self.history_index = 0
        
        # Update directory and show prompt
        self._update_directory()
        self._show_prompt()
        
        # Focus on terminal
        self.terminal.focus_set()
    
    def _update_directory(self):
        """Update current working directory"""
        if self.workspace_manager:
            ws = self.workspace_manager.get_workspace_path()
            if ws and ws != self.workspace_manager._get_default_workspace():
                self.current_dir = ws
            else:
                self.current_dir = os.getcwd()
        else:
            self.current_dir = os.getcwd()
    
    def _show_prompt(self):
        """Display prompt at current cursor position"""
        # Make sure terminal is in NORMAL state
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.insert(tk.END, f"{self.prompt}")
        self.terminal.configure(state=tk.NORMAL)  # Keep it NORMAL so user can type
        self.terminal.see(tk.END)
        # Store the position where current line starts
        self.line_start = self.terminal.index("end-1c linestart")
        self.prompt_end = self.terminal.index("end-1c")
    
    def _get_current_line(self):
        """Get the current line being typed"""
        return self.terminal.get(f"{self.prompt_end}", "end-1c")
    
    def _execute_line(self, event=None):
        """Execute the command on current line"""
        cmd = self._get_current_line().strip()
        
        # Insert newline
        self.terminal.insert(tk.END, "\n")
        
        if not cmd:
            self._show_prompt()
            return "break"
        
        # Add to history
        self.history.append(cmd)
        self.history_index = len(self.history)
        
        # Execute command
        threading.Thread(target=self._run_command, args=(cmd,), daemon=True).start()
        
        return "break"
    
    def _run_command(self, cmd):
        """Run command and show output"""
        self._update_directory()
        
        try:
            if sys.platform == "win32":
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.current_dir,
                    shell=True
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.current_dir,
                    shell=True
                )
            
            # Read output
            for line in proc.stdout:
                self._append_output(line)
            for line in proc.stderr:
                self._append_output(line, "error")
            
            proc.wait()
            
        except Exception as e:
            self._append_output(f"Error: {str(e)}\n", "error")
        
        # Show next prompt
        self._show_prompt()
    
    def _append_output(self, text, tag="output"):
        """Append output to terminal"""
        def _append():
            self.terminal.configure(state=tk.NORMAL)
            self.terminal.insert(tk.END, text)
            self.terminal.see(tk.END)
            self.terminal.configure(state=tk.NORMAL)
        self.terminal.after(0, _append)
    
    def _on_key(self, event):
        """Handle key press - prevent typing before prompt"""
        # Don't allow typing before the prompt end
        if self.terminal.compare("insert", "<", self.prompt_end):
            self.terminal.mark_set("insert", self.prompt_end)
        return None
    
    def _handle_backspace(self, event):
        """Handle backspace - prevent deleting prompt"""
        if self.terminal.compare("insert", "<=", self.prompt_end):
            return "break"
        return None
    
    def _history_up(self, event):
        """Navigate to previous command"""
        if self.history_index > 0:
            self.history_index -= 1
            self._replace_current_line(self.history[self.history_index])
        return "break"
    
    def _history_down(self, event):
        """Navigate to next command"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._replace_current_line(self.history[self.history_index])
        elif self.history_index == len(self.history) - 1:
            self.history_index = len(self.history)
            self._replace_current_line("")
        return "break"
    
    def _replace_current_line(self, text):
        """Replace current line content"""
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.delete(f"{self.prompt_end}", "end-1c")
        self.terminal.insert(f"{self.prompt_end}", text)
        self.terminal.configure(state=tk.NORMAL)
    
    def _interrupt(self, event):
        """Handle Ctrl+C"""
        self._append_output("^C\n")
        self._show_prompt()
        return "break"
    
    def clear(self):
        """Clear terminal"""
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state=tk.NORMAL)
        self._show_prompt()
    
    def get_frame(self):
        return self.frame