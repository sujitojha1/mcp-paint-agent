# mcp-paint-agent

MCP (Model Context Protocol) Agent that uses a Gemini LLM to draw a rectangle and write text inside it in a custom drawing application — and optionally send the answer via Gmail — without any direct API access to the apps. Built for EAG V3 – Session 4 Assignment.

---

## Assignment

The goal is to connect a drawing application (Paint, Keynote, LibreOffice Draw, etc.) — which has no MCP server — to an LLM-driven MCP client, and have the LLM autonomously:

1. Open the drawing app
2. Draw a rectangle
3. Write text (a question + answer) inside the rectangle

**Constraints:**
- You cannot manually call any paint-related commands — the LLM must call them via the agent loop
- Prompt engineering is critical: Gemini Flash must understand when and how to invoke each tool
- All three paint steps must be issued autonomously by the LLM

**Platform notes:**
- macOS/Linux: uses `tkinter` (built-in) + `subprocess` — no platform-specific GUI automation needed
- Windows: same approach works out of the box

**Bonus (2000 pts):** Instead of drawing, have the LLM send an email via Gmail MCP. Show LLM logs.

---

## What You Are Learning

- Prompting is the key lever — but not the *only* lever. How you process inputs and outputs matters equally.
- You are asking the LLM a question and making it write the answer inside a box in the drawing app.
- You are "hacking" an app with no API into an LLM-controlled tool — the same pattern used to drive CNC machines or any UI-driven system via MCP.
- Inter-process communication via temp JSON files is a simple and reliable IPC pattern for tool servers.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        talk2mcp.py                          │
│                  (Gemini agent loop / MCP client)           │
│                                                             │
│  Query → LLM → FUNCTION_CALL / FINAL_ANSWER parsing        │
│        ↕  stdio (MCP protocol)                             │
│                  paint_server.py                            │
│          (FastMCP server: math tools + paint tools)         │
│                        ↕                                    │
│          /tmp/paint_window.json  (canvas ready signal)      │
│          /tmp/paint_command.json (draw/text command IPC)    │
│                        ↕                                    │
│                   paint_app.py                              │
│           (tkinter canvas: polls & executes commands)       │
└─────────────────────────────────────────────────────────────┘
```

**IPC design:** `paint_server.py` writes a JSON command to `/tmp/paint_command.json`; `paint_app.py` polls every 150 ms, executes the command, and deletes the file as an acknowledgement. This avoids sockets, pipes, or platform-specific window handles entirely.

---

## Project Structure

```
mcp-paint-agent/
├── README.md
├── talk2mcp.py          # MCP agent client (Gemini-powered agent loop)
├── paint_server.py      # FastMCP server (math tools + paint tools)
├── paint_app.py         # tkinter drawing app (IPC via temp JSON files)
├── requirements.txt
├── pyproject.toml
├── .env.example
├── Reference_code/
│   ├── talk2mcp.py          # Original Windows reference client
│   ├── example2.py          # Original Windows MCP server (win32gui)
│   ├── example_mcp_server.py
│   └── decorator.py
└── prefab/
    ├── 00_prelesson/
    ├── 01_hello_prefab/
    ├── 02_state_and_events/
    ├── 03_prefab_in_mcp/
    └── 04_talk_to_app/      # Lesson D: dynamic app builder via MCP
```

---

## Development Plan

### Phase 1 — Understand the reference code ✅
- [x] Read `Reference_code/talk2mcp.py` — the agent loop that calls Gemini, parses `FUNCTION_CALL` / `FINAL_ANSWER`, and dispatches to MCP tools
- [x] Read `Reference_code/example2.py` — the MCP server exposing math tools + `open_paint`, `draw_rectangle`, `add_text_in_paint`
- [x] Identified Windows-specific parts (`win32gui`, `win32con`, `pywinauto`) — replaced with a custom tkinter app instead of automating an existing OS GUI

### Phase 2 — Mac/Linux adaptation ✅
- [x] Replaced `win32gui` / `pywinauto` with a self-contained `tkinter` canvas (`paint_app.py`) — cross-platform, zero extra dependencies
- [x] Implemented IPC via `/tmp/paint_window.json` (ready signal) and `/tmp/paint_command.json` (command queue) — cleaner than screen-coordinate automation
- [x] No screen-coordinate calibration needed: the canvas is always 800×600 at a fixed window position

### Phase 3 — MCP server (`paint_server.py`) ✅
- [x] `open_paint()` — launches `paint_app.py` as a subprocess and waits for the ready signal
- [x] `draw_rectangle(x1, y1, x2, y2)` — sends a draw command via the JSON IPC file
- [x] `add_text_in_paint(text)` — sends a text command placed just inside the last drawn rectangle
- [x] Math tools: `add`, `subtract`, `multiply`, `divide`, `strings_to_chars_to_int`, `int_list_to_exponential_sum`, `fibonacci_numbers`
- [x] Each tool tested in isolation via `python paint_server.py dev`

### Phase 4 — Agent client (`talk2mcp.py`) ✅
- [x] `server_params` points to `paint_server.py` via stdio transport
- [x] System prompt instructs the LLM to follow a strict 4-step sequence: solve → open_paint → draw_rectangle → add_text_in_paint → FINAL_ANSWER
- [x] LLM drives all three paint calls autonomously — no hard-coded post-loop logic
- [x] `parse_arguments()` handles typed conversion (int, float, array) from pipe-delimited LLM output
- [x] `max_iterations = 10` with per-iteration logging fed back to the LLM for self-correction

### Phase 5 — Test & record ✅
- [x] End-to-end run: LLM opens app → draws rectangle → writes the exponential sum answer
- [x] Verified: Paint window appears, rectangle is drawn at (80,80)→(720,520), answer text rendered inside
- [x] Terminal shows full LLM logs with each `FUNCTION_CALL` and the `FINAL_ANSWER`

### Phase 6 — Bonus: Gmail MCP ✅
- [x] Added `send_email(to, subject, body)` tool directly to `paint_server.py` using Python's built-in `smtplib` — no external MCP server needed
- [x] Authenticates via Gmail App Password (set `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` in `.env`)
- [x] Updated system prompt in `talk2mcp.py`: after drawing in Paint the LLM calls `send_email` with the answer before `FINAL_ANSWER`
- [x] Verified: email arrives in inbox; LLM logs show the `send_email` tool call with correct arguments

---

## Gmail Setup

The `send_email` tool is built into `paint_server.py` using Python's standard `smtplib` — no OAuth, no external server, no Node.js required.

**Steps:**

1. Enable **2-Step Verification** on your Google account (required for App Passwords)
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for **Mail** → copy the 16-character password
4. Add to your `.env`:
   ```
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

That's it. The LLM can now call `send_email` just like any other tool.

**LLM log excerpt:**
```
Iteration 7
LLM → FUNCTION_CALL: send_email|sujit.ojha@gmail.com|Math Answer|The answer is 1.4615e+73
Calling send_email({'to': 'sujit.ojha@gmail.com', 'subject': 'Math Answer', 'body': 'The answer is 1.4615e+73'})
Result: Email sent to sujit.ojha@gmail.com with subject 'Math Answer'.

Iteration 8
LLM → FINAL_ANSWER: [1.4615e+73]
```

---

## Submission

| Item | Status | Link |
|------|--------|------|
| `talk2mcp.py` on GitHub | ✅ complete | [github.com/sujitojha1/mcp-paint-agent](https://github.com/sujitojha1/mcp-paint-agent) |
| `paint_server.py` on GitHub | ✅ complete | [github.com/sujitojha1/mcp-paint-agent](https://github.com/sujitojha1/mcp-paint-agent) |
| `paint_app.py` on GitHub | ✅ complete | [github.com/sujitojha1/mcp-paint-agent](https://github.com/sujitojha1/mcp-paint-agent) |
| YouTube demo (drawing + LLM logs) | ✅ complete | *(link TBD — upload pending)* |
| Bonus: Gmail MCP video | ✅ complete | *(link TBD — upload pending)* |

---

## Setup

```bash
# Clone
git clone https://github.com/sujitojha1/mcp-paint-agent.git
cd mcp-paint-agent

# Create a virtual environment (Python 3.11+)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run the agent
python talk2mcp.py
```

**Dependencies** (`requirements.txt`):
```
mcp
google-genai
python-dotenv
pillow
```

`tkinter` is part of the Python standard library — no extra install needed on macOS/Linux. On some minimal Linux installs: `sudo apt install python3-tk`.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Custom tkinter canvas instead of automating OS Paint | Cross-platform, no screen-coordinate calibration, deterministic rendering |
| JSON temp-file IPC (`/tmp/paint_command.json`) | Simple, debuggable, no sockets or named pipes needed |
| LLM drives all paint steps, no hard-coded fallback | Assignment constraint; forces prompt engineering to be the solution |
| `FUNCTION_CALL: name\|arg1\|arg2` response protocol | Deterministic parsing; avoids fragile JSON extraction from free-form LLM output |
| Gemini Flash with 1M token context | Tolerant of large tool description payloads; fast iteration during prompt tuning |
| Per-iteration log fed back to LLM | Enables self-correction; LLM can recover from failed or skipped steps |
