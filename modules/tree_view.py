import tkinter as tk
from tkinter import ttk

LANE_COLORS = [
    "#888780",  # main / gray
    "#534AB7",  # purple
    "#0F6E56",  # teal
    "#D85A30",  # coral
    "#185FA5",  # blue
    "#639922",  # green
    "#BA7517",  # amber
    "#993556",  # pink
]

ROW_H  = 34
COL_W  = 22
RADIUS = 7
PAD_X  = 30
PAD_Y  = 28


class TreeView:
    """
    GitHub-style commit graph. Pure UI — knows nothing about git commands.

    Data flows in via handle_tree_data(raw_line) where raw_line is the
    string after the [TREE] prefix, formatted as:
        sha::subject::branch::parent_sha1[,parent_sha2]
    """

    def __init__(self, parent):
        self.parent = parent
        self.commits = []
        self.sha_idx = {}
        self._selected_row = None
        self._build_widgets()

    # ── widget construction ───────────────────────────────────────

    def _build_widgets(self):
        frame = tk.Frame(self.parent)
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, bg="#ffffff", highlightthickness=0)
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self.canvas.yview)
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>",   lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>",   lambda e: self.canvas.yview_scroll( 1, "units"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── public API ────────────────────────────────────────────────

    def handle_tree_data(self, raw_line: str):
        """Accumulate one [TREE] line and redraw."""
        parts = raw_line.split("::")
        if len(parts) < 4:
            return
        sha, subject, branch, parents_raw = parts[0], parts[1], parts[2], parts[3]
        parents = [p.strip()[:7] for p in parents_raw.split(",") if p.strip()]

        self.commits.append({
            "sha":     sha[:7],
            "subject": subject,
            "branch":  branch,
            "parents": parents,
        })
        self._rebuild_index()
        self.canvas.after(0, self._draw)

    def clear(self):
        self.commits.clear()
        self.sha_idx.clear()
        self._selected_row = None
        self.canvas.delete("all")

    def get_selected_sha(self, canvas_y: int):
        """Return sha nearest to canvas_y — used by the right-click handler."""
        row = round((self.canvas.canvasy(canvas_y) - PAD_Y) / ROW_H)
        if 0 <= row < len(self.commits):
            return self.commits[row]["sha"]
        return None

    def get_selected_item(self, y):
        """Legacy compat shim — returns sha or None."""
        return self.get_selected_sha(y)

    def select_item(self, sha_or_row):
        """Highlight a row by sha string or row index."""
        if isinstance(sha_or_row, int):
            self._selected_row = sha_or_row
        else:
            self._selected_row = self.sha_idx.get(sha_or_row)
        self.canvas.after(0, self._draw)

    def get_item_values(self, sha_or_row):
        """Return (sha, subject, branch) tuple — matches old ttk.Treeview API shape."""
        if isinstance(sha_or_row, int):
            row = sha_or_row
        else:
            row = self.sha_idx.get(sha_or_row, -1)
        if 0 <= row < len(self.commits):
            c = self.commits[row]
            return (c["sha"], c["subject"], c["branch"])
        return ()

    def bind(self, sequence, func):
        """Proxy canvas.bind so SafeJupyterLauncher can attach <Button-3>."""
        self.canvas.bind(sequence, func)

    # ── layout helpers ────────────────────────────────────────────

    def _rebuild_index(self):
        self.sha_idx = {c["sha"]: i for i, c in enumerate(self.commits)}

    def _assign_lanes(self) -> dict:
        """One lane per unique branch name, assigned on first appearance."""
        lanes, counter = {}, 0
        for c in self.commits:
            if c["branch"] not in lanes:
                lanes[c["branch"]] = counter
                counter += 1
        return lanes

    def _xy(self, row: int, lane: int):
        return PAD_X + lane * COL_W, PAD_Y + row * ROW_H

    # ── drawing ───────────────────────────────────────────────────

    def _draw(self):
        self.canvas.delete("all")
        if not self.commits:
            return

        lanes   = self._assign_lanes()
        n_lanes = max(lanes.values()) + 1
        total_w = PAD_X + n_lanes * COL_W + 640
        total_h = PAD_Y + len(self.commits) * ROW_H + PAD_Y
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

        # ── highlight selected row ─────────────────────────────────
        if self._selected_row is not None:
            _, ry = self._xy(self._selected_row, 0)
            self.canvas.create_rectangle(
                0, ry - ROW_H // 2, total_w, ry + ROW_H // 2,
                fill="#f0f0ff", outline="", tags="highlight"
            )

        # ── edges ─────────────────────────────────────────────────
        for row, commit in enumerate(self.commits):
            lane   = lanes.get(commit["branch"], 0)
            cx, cy = self._xy(row, lane)

            for p_sha in commit["parents"]:
                p_row = self.sha_idx.get(p_sha)
                if p_row is None:
                    continue
                p_lane     = lanes.get(self.commits[p_row]["branch"], 0)
                px, py     = self._xy(p_row, p_lane)
                edge_color = LANE_COLORS[p_lane % len(LANE_COLORS)]

                if cx == px:
                    self.canvas.create_line(
                        cx, cy + RADIUS,
                        px, py - RADIUS,
                        fill=edge_color, width=2
                    )
                else:
                    mid = (cy + py) // 2
                    self.canvas.create_line(
                        cx, cy + RADIUS,
                        cx, mid,
                        px, mid,
                        px, py - RADIUS,
                        fill=edge_color, width=2,
                        smooth=True, splinesteps=16
                    )

        # ── dots + labels ─────────────────────────────────────────
        sha_col = PAD_X + n_lanes * COL_W + 10
        msg_col = sha_col + 72

        for row, commit in enumerate(self.commits):
            lane   = lanes.get(commit["branch"], 0)
            color  = LANE_COLORS[lane % len(LANE_COLORS)]
            cx, cy = self._xy(row, lane)

            # commit dot
            self.canvas.create_oval(
                cx - RADIUS, cy - RADIUS,
                cx + RADIUS, cy + RADIUS,
                fill=color, outline="#ffffff", width=2,
                tags=("commit_dot", f"row_{row}")
            )

            # sha label
            self.canvas.create_text(
                sha_col, cy,
                text=commit["sha"],
                anchor=tk.W,
                font=("Consolas", 10),
                fill="#888780"
            )

            # commit subject
            self.canvas.create_text(
                msg_col, cy,
                text=commit["subject"],
                anchor=tk.W,
                font=("Segoe UI", 10),
                fill="#2C2C2A"
            )

            # branch pill — only on first occurrence of that branch
            first_in_branch = all(
                self.commits[r]["branch"] != commit["branch"]
                for r in range(row)
            )
            if first_in_branch:
                pill_x = msg_col + len(commit["subject"]) * 6.5 + 14
                pill_w = len(commit["branch"]) * 6.5 + 14
                self.canvas.create_rectangle(
                    pill_x,          cy - 9,
                    pill_x + pill_w, cy + 9,
                    fill=color, outline=color, width=0
                )
                self.canvas.create_text(
                    pill_x + pill_w / 2, cy,
                    text=commit["branch"],
                    font=("Segoe UI", 9),
                    fill="#ffffff"
                )

        # click selects row
        self.canvas.tag_bind("commit_dot", "<Button-1>", self._on_dot_click)

    def _on_dot_click(self, event):
        cy  = self.canvas.canvasy(event.y)
        row = round((cy - PAD_Y) / ROW_H)
        if 0 <= row < len(self.commits):
            self._selected_row = row
            self._draw()