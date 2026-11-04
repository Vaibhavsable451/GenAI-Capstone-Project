"""Agent loop: Understand Task -> Decide Action -> Use Tool -> Process Result -> Respond."""
import json

from .llm import chat
from .prompts import build_system
from .tools import TOOL_SPECS


def run_agent(client, toolbox, mode, history, user_input, enabled,
              allow_destructive=False, max_steps=6, temperature=0.3):
    """Generator of events: tool_call, tool_result, final. `history` = prior user/assistant turns."""
    messages = [{"role": "system", "content": build_system(mode)}] + history[-10:]
    messages.append({"role": "user", "content": user_input})
    tools = [TOOL_SPECS[n] for n in TOOL_SPECS if n in enabled]
    tin = tout = 0

    for step in range(1, max_steps + 1):
        resp = chat(client, messages, temperature, tools=tools)
        tin += resp.usage.prompt_tokens
        tout += resp.usage.completion_tokens
        msg = resp.choices[0].message

        if not msg.tool_calls:
            yield {"type": "final", "content": msg.content or "", "steps": step, "tokens": tin + tout}
            return

        messages.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                           for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            yield {"type": "tool_call", "name": tc.function.name, "args": args}
            result = toolbox.execute(tc.function.name, args, enabled, allow_destructive)
            yield {"type": "tool_result", "name": tc.function.name, "result": result}
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    yield {"type": "final", "steps": max_steps, "tokens": tin + tout,
           "content": f"⚠️ Stopped after {max_steps} steps for safety. Try a more specific request."}
