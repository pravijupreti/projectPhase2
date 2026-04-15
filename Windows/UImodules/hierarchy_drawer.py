import tkinter as tk


class HierarchyDrawer:
    """Branch hierarchy visualization component"""
    
    def __init__(self, parent):
        self.parent = parent
        self.create_canvas()
    
    def create_canvas(self):
        """Create canvas for drawing"""
        self.canvas = tk.Canvas(
            self.parent, height=150, bg="#ffffff", highlightthickness=0
        )
        self.canvas.pack(fill=tk.X, expand=True)
    
    def draw(self, branch_links, current_branch):
        """Draw branch hierarchy"""
        self.canvas.delete("all")
        x_start = 20
        y_start = 30
        spacing = 35
        
        for i, (local, remote) in enumerate(branch_links):
            y = y_start + (i * spacing)
            is_active = (local == current_branch)
            
            # Local Node
            color = "#2196F3" if is_active else "#607D8B"
            width = 3 if is_active else 1
            self.canvas.create_text(
                x_start, y, text=f" {local} ", anchor="w",
                font=("Arial", 10, "bold"), fill=color
            )
            
            # Link Arrow
            dash_start = x_start + 110
            arrow_end = dash_start + 160
            line_color = "#4CAF50" if remote != "NO_UPSTREAM" else "#f44336"
            dash_pattern = None if remote != "NO_UPSTREAM" else (5, 5)
            
            self.canvas.create_line(
                dash_start, y, arrow_end, y,
                arrow=tk.LAST, fill=line_color, dash=dash_pattern, width=width
            )
            
            # Remote Node
            remote_text = remote if remote != "NO_UPSTREAM" else "⚠️ Disconnected"
            self.canvas.create_text(
                arrow_end + 10, y, text=remote_text,
                anchor="w", font=("Consolas", 9), fill=line_color
            )
    
    def clear(self):
        """Clear canvas"""
        self.canvas.delete("all")