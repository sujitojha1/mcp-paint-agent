"""
paint_server.py – FastMCP server exposing math tools, paint tools, and Gmail.

Paint tools communicate with paint_app.py via two temp files:
  /tmp/paint_window.json  – written by paint_app; tells us the canvas is ready.
  /tmp/paint_command.json – we write a command; paint_app deletes it when done.

Gmail tool uses SMTP with an App Password (set GMAIL_ADDRESS and
GMAIL_APP_PASSWORD in .env — no OAuth needed).

Run with:
    python paint_server.py          # stdio transport (used by talk2mcp.py)
    python paint_server.py dev      # in-process dev server
"""

import json
import math
import os
import smtplib
import sys
import time
from email.mime.text import MIMEText

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

load_dotenv()

mcp = FastMCP("PaintServer")

WINDOW_INFO_FILE = "/tmp/paint_window.json"
COMMAND_FILE = "/tmp/paint_command.json"

_paint_process = None   # subprocess.Popen handle
_last_rect: tuple[int, int, int, int] | None = None   # (x1, y1, x2, y2)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text_result(msg: str) -> dict:
    return {"content": [TextContent(type="text", text=msg)]}


def _send_command(cmd: dict, timeout: float = 4.0) -> bool:
    """Write cmd JSON and wait for paint_app to consume (delete) the file."""
    with open(COMMAND_FILE, "w") as fh:
        json.dump(cmd, fh)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not os.path.exists(COMMAND_FILE):
            return True
        time.sleep(0.1)
    # Timed out – remove stale file
    try:
        os.remove(COMMAND_FILE)
    except FileNotFoundError:
        pass
    return False


# ── Math tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return int(a + b)


@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    return int(a - b)


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return int(a * b)


@mcp.tool()
def divide(a: int, b: int) -> float:
    """Divide two numbers"""
    return float(a / b)


@mcp.tool()
def strings_to_chars_to_int(string: str) -> list[int]:
    """Return the ASCII values of each character in the given word"""
    return [int(ord(ch)) for ch in string]


@mcp.tool()
def int_list_to_exponential_sum(int_list: list) -> float:
    """Return the sum of e^x for each number x in the list"""
    return sum(math.exp(i) for i in int_list)


@mcp.tool()
def fibonacci_numbers(n: int) -> list:
    """Return the first n Fibonacci numbers"""
    if n <= 0:
        return []
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


# ── Paint tools ───────────────────────────────────────────────────────────────

@mcp.tool()
async def open_paint() -> dict:
    """Open the Paint drawing application.
    Always call this tool first, before draw_rectangle or add_text_in_paint."""
    global _paint_process

    import subprocess

    # Remove any stale temp files from a previous run
    for path in (WINDOW_INFO_FILE, COMMAND_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paint_app.py")
    _paint_process = subprocess.Popen([sys.executable, script])

    # Wait up to 5 s for the app to write window info
    for _ in range(25):
        if os.path.exists(WINDOW_INFO_FILE):
            break
        time.sleep(0.2)
    else:
        return _text_result("Error: Paint window did not open in time.")

    time.sleep(0.2)  # let the first poll cycle settle
    return _text_result(
        "Paint opened successfully. Canvas is 800×600 pixels. "
        "Origin (0,0) is the top-left corner of the canvas."
    )


@mcp.tool()
async def draw_rectangle(x1: int, y1: int, x2: int, y2: int) -> dict:
    """Draw a rectangle on the Paint canvas from top-left (x1,y1) to bottom-right (x2,y2).
    Canvas dimensions: 800 wide × 600 tall (pixels).
    Recommended full-canvas box: x1=80, y1=80, x2=720, y2=520.
    You must call open_paint before this tool."""
    global _last_rect

    if not os.path.exists(WINDOW_INFO_FILE):
        return _text_result("Paint is not open. Call open_paint first.")

    ok = _send_command({"action": "draw_rectangle",
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2})
    if not ok:
        return _text_result("Error: Paint did not acknowledge the draw_rectangle command.")

    _last_rect = (x1, y1, x2, y2)
    return _text_result(f"Rectangle drawn from ({x1},{y1}) to ({x2},{y2}).")


@mcp.tool()
async def add_text_in_paint(text: str) -> dict:
    """Write text inside the rectangle that was drawn in Paint.
    You must call draw_rectangle before this tool.
    The text is placed near the top-left interior of the last drawn rectangle."""

    if not os.path.exists(WINDOW_INFO_FILE):
        return _text_result("Paint is not open. Call open_paint first.")

    # Place text just inside the top-left corner of the last rectangle
    if _last_rect:
        tx = _last_rect[0] + 15
        ty = _last_rect[1] + 15
    else:
        tx, ty = 30, 30

    ok = _send_command({"action": "add_text", "x": tx, "y": ty, "text": text})
    if not ok:
        return _text_result("Error: Paint did not acknowledge the add_text command.")

    return _text_result(f"Text written in Paint: '{text}'")


# ── Gmail tool ────────────────────────────────────────────────────────────────

@mcp.tool()
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email via Gmail SMTP using an App Password.
    Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in the environment (.env).
    to: recipient email address.
    subject: email subject line.
    body: plain-text email body."""
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not password:
        return _text_result(
            "Error: GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env. "
            "Generate an App Password at https://myaccount.google.com/apppasswords"
        )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())
        return _text_result(f"Email sent to {to} with subject '{subject}'.")
    except smtplib.SMTPAuthenticationError:
        return _text_result(
            "Error: Gmail authentication failed. "
            "Make sure you are using an App Password, not your account password."
        )
    except Exception as exc:
        return _text_result(f"Error sending email: {exc}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
