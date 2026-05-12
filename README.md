# mcp-paint-agent

MCP (Model Context Protocol) Agent that uses an LLM to draw a rectangle and write text inside it in a drawing application — without any direct API access to the app. Built for EAG V3 – Session 4 Assignment.

---

## Assignment

The goal is to connect a drawing application (Paint, Keynote, LibreOffice Draw, etc.) — which has no MCP server — to an LLM-driven MCP client, and have the LLM autonomously:

1. Open the drawing app
2. Draw a rectangle
3. Write text (a question + answer) inside the rectangle

**Constraints:**
- You cannot manually call any paint-related commands — the LLM must call them via the agent loop
- Prompt engineering is critical: Gemini Flash 2.0 (1M token context) must understand when and how to invoke each tool
- Pixel coordinates may need to be adjusted for your screen/monitor setup

**Platform notes:**
- Windows: `pip install pywin32 pywinauto`
- Linux/Mac: use equivalent GUI automation libraries (e.g. `pyautogui`, `Quartz`, `AppKit`)

**Bonus (2000 pts):** Instead of drawing, have the LLM send an email via Gmail MCP. Show LLM logs.

---

## What You Are Learning

- Prompting is the key lever — but not the *only* lever. How you process inputs and outputs matters equally.
- You are asking the LLM a question and making it write the answer inside a box in the drawing app.
- You are "hacking" an app with no API into an LLM-controlled tool — the same pattern used to drive CNC machines or any UI-driven system via MCP.

---

## Project Structure

```
mcp-paint-agent/
├── README.md
├── Reference_code/
│   ├── talk2mcp.py          # Reference MCP client (agent loop + Gemini)
│   ├── example2.py          # Reference MCP server (math + paint tools)
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

### Phase 1 — Understand the reference code
- [x] Read `Reference_code/talk2mcp.py` — the agent loop that calls Gemini, parses `FUNCTION_CALL` / `FINAL_ANSWER`, and dispatches to MCP tools
- [x] Read `Reference_code/example2.py` — the MCP server exposing math tools + `open_paint`, `draw_rectangle`, `add_text_in_paint`
- [ ] Identify which parts are Windows-specific (win32gui, win32con, pywinauto) and need Mac/Linux replacements

### Phase 2 — Mac/Linux adaptation
- [ ] Replace `win32gui` / `pywinauto` calls with `pyautogui` + `subprocess` (or `AppKit` / `Quartz` on macOS)
- [ ] Verify screen coordinates for single-monitor setup (reference code targets a second monitor)
- [ ] Implement `open_paint` equivalent — open Preview, Keynote, or LibreOffice Draw
- [ ] Implement `draw_rectangle` — use `pyautogui` drag to simulate mouse drawing
- [ ] Implement `add_text_in_paint` — click inside the rectangle and type text

### Phase 3 — MCP server (`paint_server.py`)
- [ ] Create a new MCP server exposing exactly three tools:
  - `open_paint()` → opens the drawing application
  - `draw_rectangle(x1, y1, x2, y2)` → draws a rectangle via mouse automation
  - `add_text_in_paint(text)` → clicks inside the rectangle and types the text
- [ ] Test each tool in isolation before wiring up the agent

### Phase 4 — Agent client (`talk2mcp.py`)
- [ ] Update `server_params` to point to the new `paint_server.py`
- [ ] Craft a system prompt that teaches the LLM the correct tool-call sequence:
  1. Call `open_paint`
  2. Call `draw_rectangle` with appropriate coordinates
  3. Call `add_text_in_paint` with the answer text
- [ ] Replace the hard-coded `FINAL_ANSWER` handler (which manually called paint tools) so the LLM drives all three calls autonomously
- [ ] Tune `max_iterations` and prompt phrasing until the LLM reliably executes the full sequence

### Phase 5 — Test & record
- [ ] Run end-to-end: LLM opens app → draws rectangle → writes text
- [ ] Record a screen capture showing:
  - The drawing app with the rectangle and text visible
  - Terminal scroll-through of LLM logs proving the LLM issued the tool calls
- [ ] Upload video to YouTube and link below

### Phase 6 — Bonus: Gmail MCP
- [ ] Configure Gmail MCP server (OAuth2 credentials)
- [ ] Add `send_email(to, subject, body)` tool to the agent
- [ ] Update prompt so the LLM sends an email with the answer instead of (or in addition to) drawing
- [ ] Record a second video showing the received email and LLM logs

---

## Submission

| Item | Status | Link |
|------|--------|------|
| YouTube demo (drawing + LLM logs) | pending | — |
| `talk2mcp.py` on GitHub | pending | — |
| Bonus: Gmail MCP video | pending | — |

---

## Setup

```bash
# Clone
git clone https://github.com/sujitojha1/mcp-paint-agent.git
cd mcp-paint-agent

# Install dependencies
pip install python-dotenv mcp google-generativeai pyautogui

# macOS extras (for screen/keyboard control)
pip install pyobjc-framework-Quartz pyobjc-framework-AppKit

# Windows extras
pip install pywin32 pywinauto

# Set API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Run the agent
python talk2mcp.py
```

---

## Key Design Decisions

- **No manual paint calls** — all three paint tool calls must come from the LLM's own reasoning, not hard-coded post-loop logic
- **Gemini Flash 2.0** — chosen for its 1M token context window, making it tolerant of large tool description payloads
- **Structured response protocol** — the agent uses `FUNCTION_CALL: name|arg1|arg2` and `FINAL_ANSWER: [value]` to keep parsing deterministic
