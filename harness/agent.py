"""The agent — the harness drive loop. Grows one primitive per chapter.

ch-02 — Loop + history. The model is still stateless: every call is independent.
So the harness keeps the conversation in a list and replays the whole thing on
every turn. That list — plus the append/replay/append loop in ``send`` — is the
entire reason the agent now feels like it remembers.

  The model isn't stateful. The harness is.

The single ``chat`` call still goes through the ``model/`` seam, so swapping
providers never touches this file.
"""

from __future__ import annotations

from model import Provider, chat


EXIT_COMMANDS = {"exit", "quit", "bye", "stop", "shutdown"}


def should_exit(user_text: str) -> bool:
    """Return True when the user asks to end the REPL session."""
    normalized = user_text.strip().lower()
    if not normalized:
        return False
    return normalized in EXIT_COMMANDS or normalized.startswith(tuple(f"{cmd}!" for cmd in EXIT_COMMANDS))


class Agent:
    """A model wrapped in conversation memory the harness owns."""

    def __init__(self, model: str | None = None, provider: Provider | None = None) -> None:
        self.model = model
        self.provider = provider
        self.messages: list[dict] = []  # <-- the ONLY new attribute over ch-01

    def send(self, user_text: str) -> str:
        """Append the turn, replay the whole history, keep the reply."""
        self.messages.append({"role": "user", "content": user_text})
        resp = chat(self.messages, model=self.model, provider=self.provider)
        self.messages.append({"role": "assistant", "content": resp.content})
        return resp.content


def main() -> None:
    agent = Agent()
    print("agent ready (ch-02) — it remembers within this session. Ctrl-D to exit.")
    while True:
        try:
            user = input("you> ")
        except EOFError:
            print()
            break
        if not user.strip():
            continue
        if should_exit(user):
            print("bot> Goodbye!")
            break
        print("bot>", agent.send(user))


if __name__ == "__main__":
    main()
