"""Persist the latest submitted user prompt for turn-paired capture.

Cursor's afterAgentResponse hook receives the assistant response payload but
not the triggering user prompt. The beforeSubmitPrompt hook writes the user
text to a pending-user-turn file which the afterAgentResponse capture hook
then reads, ensuring every captured artifact has both halves of the turn.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .shared import first_text, parse_hook_payload


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Persist latest user prompt from hook payload for turn pairing.",
    )
    parser.add_argument("--hook-input", required=True, help="Path to hook JSON payload.")
    parser.add_argument(
        "--output-file",
        required=True,
        help="Path to write pending user turn JSON.",
    )
    args = parser.parse_args(argv)

    payload = parse_hook_payload(args.hook_input)
    user_text = first_text(
        payload,
        ("prompt", "user_prompt", "user_message", "message", "input", "text"),
    )
    if not user_text.strip():
        return 0
    conversation_id = first_text(
        payload,
        ("conversation_id", "source_conversation_id", "thread_id"),
    )
    out = {
        "user_text": user_text.strip(),
        "conversation_id": conversation_id.strip(),
    }
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
