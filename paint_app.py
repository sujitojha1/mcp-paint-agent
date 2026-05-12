"""
paint_app.py – lightweight tkinter drawing application.

The MCP server (paint_server.py) communicates with this process via two
temp files:
  /tmp/paint_window.json  – written by this app on startup so the server
                            knows the on-screen canvas origin.
  /tmp/paint_command.json – written by the server; this app polls it every
                            150 ms, executes the command, then deletes the
                            file to acknowledge completion.

Supported command payloads:
  {"action": "draw_rectangle", "x1": int, "y1": int, "x2": int, "y2": int}
  {"action": "add_text",       "x": int,  "y": int,  "text": str}

The canvas also supports interactive mouse drawing (click-drag) so a human
can verify the app works independently.
"""

import json
import os
import sys
import tkinter as tk

WINDOW_INFO_FILE = "/tmp/paint_window.json"
COMMAND_FILE = "/tmp/paint_command.json"
CANVAS_W, CANVAS_H = 800, 600
POLL_MS = 150


class PaintApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Paint")
        self.root.geometry(f"{CANVAS_W}x{CANVAS_H}+100+100")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="white")
        self.canvas.pack()

        # Interactive drawing state
        self._start_x: int | None = None
        self._start_y: int | None = None
        self._live_rect: int | None = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Publish window geometry and start command polling after first render
        self.root.after(300, self._write_window_info)
        self.root.after(POLL_MS, self._poll_commands)

    # ── Window info ──────────────────────────────────────────────────────────

    def _write_window_info(self) -> None:
        self.root.update_idletasks()
        info = {
            "canvas_x": self.canvas.winfo_rootx(),
            "canvas_y": self.canvas.winfo_rooty(),
            "canvas_width": self.canvas.winfo_width(),
            "canvas_height": self.canvas.winfo_height(),
        }
        with open(WINDOW_INFO_FILE, "w") as fh:
            json.dump(info, fh)

    # ── Command polling ──────────────────────────────────────────────────────

    def _poll_commands(self) -> None:
        if os.path.exists(COMMAND_FILE):
            try:
                with open(COMMAND_FILE) as fh:
                    cmd = json.load(fh)
                os.remove(COMMAND_FILE)  # acknowledge before executing
                self._execute(cmd)
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        self.root.after(POLL_MS, self._poll_commands)

    def _execute(self, cmd: dict) -> None:
        action = cmd.get("action")
        if action == "draw_rectangle":
            self.canvas.create_rectangle(
                cmd["x1"], cmd["y1"], cmd["x2"], cmd["y2"],
                outline="black", width=2,
            )
        elif action == "add_text":
            self.canvas.create_text(
                cmd["x"], cmd["y"],
                text=cmd["text"],
                font=("Arial", 14),
                anchor="nw",
                fill="black",
            )

    # ── Interactive mouse drawing ────────────────────────────────────────────

    def _on_press(self, event: tk.Event) -> None:
        self._start_x = event.x
        self._start_y = event.y
        self._live_rect = self.canvas.create_rectangle(
            event.x, event.y, event.x + 1, event.y + 1,
            outline="black", width=2,
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self._live_rect is not None and self._start_x is not None:
            self.canvas.coords(
                self._live_rect,
                self._start_x, self._start_y, event.x, event.y,
            )

    def _on_release(self, event: tk.Event) -> None:
        if self._live_rect is not None:
            coords = self.canvas.coords(self._live_rect)
            if abs(coords[2] - coords[0]) < 3 and abs(coords[3] - coords[1]) < 3:
                self.canvas.delete(self._live_rect)
        self._start_x = None
        self._start_y = None
        self._live_rect = None


def _cleanup() -> None:
    for path in (WINDOW_INFO_FILE, COMMAND_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    PaintApp(root)
    try:
        root.mainloop()
    finally:
        _cleanup()
