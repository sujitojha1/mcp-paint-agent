"""
talk2mcp.py – MCP agent client that uses Gemini Flash to autonomously:
  1. Solve a math problem step by step via tool calls.
  2. Open the Paint app, draw a rectangle, and write the answer inside it.

The LLM drives ALL three paint steps — no manual calls are made here.

Usage:
    python talk2mcp.py

Requires GEMINI_API_KEY in .env (or environment).
"""

import asyncio
import os
from concurrent.futures import TimeoutError
from dotenv import load_dotenv
from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"
MAX_ITERATIONS = 10
LLM_TIMEOUT = 30  # seconds

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── State (reset per run) ─────────────────────────────────────────────────────

iteration = 0
last_response = None
iteration_log: list[str] = []


def reset_state() -> None:
    global iteration, last_response, iteration_log
    iteration = 0
    last_response = None
    iteration_log = []


# ── LLM helper ────────────────────────────────────────────────────────────────

async def llm_generate(prompt: str, timeout: int = LLM_TIMEOUT) -> str:
    loop = asyncio.get_event_loop()
    response = await asyncio.wait_for(
        loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt
            ),
        ),
        timeout=timeout,
    )
    return response.text.strip()


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """\
You are an agent that solves math problems and then draws the result \
in a Paint application.

Available tools:
{tools}

=== RESPONSE FORMAT ===
Each response must be EXACTLY ONE LINE in one of these two formats:

  FUNCTION_CALL: function_name|param1|param2|...
  FINAL_ANSWER: [value]

No other text. No explanations. One line only.

=== YOUR TASK ===
Solve the math problem below step by step using the math tools, then \
draw the final answer in the Paint app.

After you have computed the final numeric answer you MUST execute ALL \
of the following steps IN ORDER before outputting FINAL_ANSWER:

  Step A → FUNCTION_CALL: open_paint
  Step B → FUNCTION_CALL: draw_rectangle|80|80|720|520
  Step C → FUNCTION_CALL: add_text_in_paint|<your answer as a string>
  Step D → FUNCTION_CALL: send_email|sujit.ojha@gmail.com|Math Answer|The answer is <your answer>
  Step E → FINAL_ANSWER: [the numeric answer]

Do NOT skip any step. Do NOT output FINAL_ANSWER before Steps C and D are done.

=== RULES ===
- Separate arguments with | (pipe character).
- When a tool returns a list, pass it as the next tool's argument \
  (e.g., FUNCTION_CALL: int_list_to_exponential_sum|[73,78,68,73,65]).
- open_paint takes no arguments.
"""

QUERY = (
    "Find the ASCII values of the characters in INDIA "
    "and then return the sum of exponentials of those values."
)


# ── Argument parser ───────────────────────────────────────────────────────────

def parse_arguments(tool, raw_params: list[str]) -> dict:
    """Convert a list of raw string params to typed arguments using the tool schema."""
    arguments: dict = {}
    schema_props: dict = tool.inputSchema.get("properties", {})

    for param_name, param_info in schema_props.items():
        if not raw_params:
            raise ValueError(f"Not enough parameters for '{tool.name}'")
        value = raw_params.pop(0)
        ptype = param_info.get("type", "string")

        if ptype == "integer":
            arguments[param_name] = int(value)
        elif ptype == "number":
            arguments[param_name] = float(value)
        elif ptype == "array":
            if isinstance(value, str):
                value = value.strip("[]").strip()
            parts = [v.strip() for v in value.split(",") if v.strip()]
            arguments[param_name] = [float(p) if "." in p else int(p) for p in parts]
        else:
            arguments[param_name] = str(value)

    return arguments


# ── Main agent loop ───────────────────────────────────────────────────────────

async def main() -> None:
    reset_state()
    global iteration, last_response

    print("Connecting to MCP server …")
    server_params = StdioServerParameters(
        command="python",
        args=["paint_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = tools_result.tools
            print(f"Server exposed {len(tools)} tools.")

            # Build human-readable tool list for the prompt
            tool_lines = []
            for i, t in enumerate(tools, 1):
                props = t.inputSchema.get("properties", {})
                params_str = ", ".join(
                    f"{n}: {info.get('type','?')}"
                    for n, info in props.items()
                ) or "no parameters"
                tool_lines.append(f"  {i}. {t.name}({params_str}) – {t.description}")
            tools_description = "\n".join(tool_lines)

            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools=tools_description)
            current_query = QUERY

            while iteration < MAX_ITERATIONS:
                print(f"\n{'─'*60}")
                print(f"Iteration {iteration + 1}")

                if last_response is not None:
                    current_query = (
                        QUERY + "\n\n"
                        + " ".join(iteration_log)
                        + "\n\nWhat should I do next?"
                    )

                prompt = f"{system_prompt}\n\nQuery: {current_query}"

                try:
                    response_text = await llm_generate(prompt)
                except TimeoutError:
                    print("LLM timed out – aborting.")
                    break
                except Exception as exc:
                    print(f"LLM error: {exc}")
                    break

                # Extract the first FUNCTION_CALL or FINAL_ANSWER line
                chosen_line = ""
                for line in response_text.splitlines():
                    line = line.strip()
                    if line.startswith("FUNCTION_CALL:") or line.startswith("FINAL_ANSWER:"):
                        chosen_line = line
                        break

                if not chosen_line:
                    print(f"Unexpected LLM output:\n{response_text}")
                    iteration += 1
                    continue

                print(f"LLM → {chosen_line}")

                # ── Handle FUNCTION_CALL ──────────────────────────────────
                if chosen_line.startswith("FUNCTION_CALL:"):
                    _, raw = chosen_line.split(":", 1)
                    parts = [p.strip() for p in raw.split("|")]
                    func_name, raw_params = parts[0], parts[1:]

                    tool = next((t for t in tools if t.name == func_name), None)
                    if tool is None:
                        print(f"Unknown tool: {func_name}")
                        iteration_log.append(
                            f"Iteration {iteration+1}: tool '{func_name}' not found."
                        )
                        iteration += 1
                        continue

                    try:
                        arguments = parse_arguments(tool, list(raw_params))
                        print(f"Calling {func_name}({arguments})")
                        result = await session.call_tool(func_name, arguments=arguments)

                        # Collect result text
                        if hasattr(result, "content"):
                            if isinstance(result.content, list):
                                result_parts = [
                                    item.text if hasattr(item, "text") else str(item)
                                    for item in result.content
                                ]
                                result_str = " | ".join(result_parts)
                            else:
                                result_str = str(result.content)
                        else:
                            result_str = str(result)

                        print(f"Result: {result_str}")
                        iteration_log.append(
                            f"Iteration {iteration+1}: called {func_name}({arguments}), "
                            f"returned: {result_str}."
                        )
                        last_response = result_str

                    except Exception as exc:
                        import traceback
                        traceback.print_exc()
                        iteration_log.append(
                            f"Iteration {iteration+1}: error calling {func_name}: {exc}"
                        )

                # ── Handle FINAL_ANSWER ───────────────────────────────────
                elif chosen_line.startswith("FINAL_ANSWER:"):
                    print("\n" + "=" * 60)
                    print("Agent finished.")
                    print(chosen_line)
                    print("=" * 60)
                    break

                iteration += 1

            else:
                print(f"Reached max iterations ({MAX_ITERATIONS}) without a final answer.")


if __name__ == "__main__":
    asyncio.run(main())
